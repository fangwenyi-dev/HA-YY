"""慧尖语音助手 - 配置流程."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
import logging
from typing import Any

from aioesphomeapi import (
    APIClient,
    APIConnectionError,
    DeviceInfo,
    InvalidAuthAPIError,
    InvalidEncryptionKeyAPIError,
    RequiresEncryptionAPIError,
    ResolveAPIError,
    wifi_mac_to_bluetooth_mac,
)
import voluptuous as vol

from homeassistant.components import zeroconf

try:
    from homeassistant.components.espdiscovery import async_discover_service
    ESPDISCOVERY_AVAILABLE = True
except ImportError:
    async_discover_service = None
    ESPDISCOVERY_AVAILABLE = False

from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigEntryBaseFlow,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector, discovery_flow
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.util import ulid

from .const import (
    CONF_ALLOW_SERVICE_CALLS,
    CONF_DEVICE_NAME,
    CONF_NOISE_PSK,
    CONF_LLM_PROVIDER,
    CONF_LLM_ENDPOINT,
    CONF_LLM_API_KEY,
    CONF_MCP_ENDPOINT,
    CONF_ASSIST_MODE,
    LLM_PROVIDER_XIAOZHI,
    LLM_PROVIDER_OLLAMA,
    LLM_PROVIDER_HA_CLOUD,
    LLM_PROVIDER_CUSTOM,
    LLM_PROVIDER_NAMES,
    DEFAULT_ALLOW_SERVICE_CALLS,
    DEFAULT_PORT,
    DOMAIN,
)
from .entry_data import ESPHomeConfigEntry
from .huijian import Dict, get_haid
from .huijian.http import async_setup_https

ERROR_REQUIRES_ENCRYPTION_KEY = "requires_encryption_key"
ERROR_INVALID_ENCRYPTION_KEY = "invalid_psk"
ERROR_INVALID_PASSWORD_AUTH = "invalid_auth"
_LOGGER = logging.getLogger(__name__)

ZERO_NOISE_PSK = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
DEFAULT_NAME = "慧尖语音"


class BaseFlow(ConfigEntryBaseFlow):
    def init(self):
        self._extra = Dict()
        self._extra.setdefault("config_data", {})

    @property
    def this_data(self):
        return self.hass.data.setdefault(DOMAIN, {})

    @property
    def setup_data(self):
        return self.this_data.setdefault(self.setup_uuid, None)

    @property
    def setup_uuid(self):
        return self._extra.setup_uuid

    @setup_uuid.setter
    def setup_uuid(self, uuid):
        if uuid:
            self._extra.setup_uuid = uuid
            self.this_data[uuid] = None
            _LOGGER.info("Waiting for setup data: %s", uuid)

    def clean_setup(self):
        self.this_data.pop(self.setup_uuid, None)
        self._extra.pop("setup_uuid", None)


class ConfigFlowHandler(ConfigFlow, BaseFlow, domain=DOMAIN):
    """Handle a huijian_yuyin config flow."""

    VERSION = 1

    _reauth_entry: ConfigEntry
    _reconfig_entry: ConfigEntry

    def __init__(self) -> None:
        """Initialize flow."""
        self._host: str | None = None
        self._connected_address: str | None = None
        self.__name: str | None = None
        self._port: int | None = None
        self._password: str | None = None
        self._noise_required: bool | None = None
        self._noise_psk: str | None = None
        self._device_info: DeviceInfo | None = None
        self._device_name: str | None = None
        self._device_mac: str | None = None
        self._entry_with_name_conflict: ConfigEntry | None = None
        self._llm_provider: str = LLM_PROVIDER_XIAOZHI
        self._llm_endpoint: str | None = None
        self._llm_api_key: str | None = None
        self._mcp_endpoint: str | None = None
        self.init()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        return await self.async_step_choice(user_input)

    async def async_step_choice(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """让用户选择配置方式."""
        if user_input is not None:
            if user_input.get("setup_method") == "esphome":
                return await self.async_step_esphome_discovery()
            else:
                return await self.async_step_manual_config()

        return self.async_show_form(
            step_id="choice",
            data_schema=vol.Schema({
                vol.Required("setup_method"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value="esphome",
                                label="ESPHome 自动发现 (推荐)",
                            ),
                            selector.SelectOptionDict(
                                value="manual",
                                label="手动输入 IP 地址",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }),
        )

    async def async_step_esphome_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """通过 ESPHome 发现设备."""
        errors = {}
        discovered_devices = []

        if not ESPDISCOVERY_AVAILABLE:
            return self.async_abort(reason="espdiscovery_not_available")

        try:
            discovered = await async_discover_service(self.hass, "esp")
            for service in discovered:
                if "hostname" in service:
                    discovered_devices.append({
                        "hostname": service.get("hostname", ""),
                        "address": service.get("addresses", [None])[0],
                        "port": service.get("port", 6053),
                        "name": service.get("name", service.get("hostname", "")),
                    })
        except Exception as err:
            _LOGGER.warning("ESPHome discovery failed: %s", err)
            errors["base"] = "discovery_failed"

        if user_input is not None:
            selected = user_input.get("device")
            if selected:
                device = discovered_devices[int(selected)]
                self._host = device["host"]
                self._port = device["port"]
                self._device_mac = device.get("mac")
                self._device_name = device["name"]
                self._name = device["name"]
                return await self._async_try_fetch_device_info()

        options = [
            selector.SelectOptionDict(
                value=str(i),
                label=f"{d['name']} ({d['host']})",
            )
            for i, d in enumerate(discovered_devices)
        ]

        if not options:
            return self.async_show_form(
                step_id="esphome_discovery",
                errors={"base": "no_devices_found"},
                data_schema=vol.Schema({}),
                description_placeholders={
                    "tip": "未发现 ESPHome 设备，请确保设备已联网并开启 API 服务",
                },
            )

        return self.async_show_form(
            step_id="esphome_discovery",
            data_schema=vol.Schema({
                vol.Required("device"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options),
                ),
            }),
            errors=errors,
        )

    async def async_step_manual_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """手动输入设备地址."""
        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, DEFAULT_PORT)
            self._device_name = user_input.get(CONF_DEVICE_NAME, "慧尖语音设备")
            self._name = self._device_name
            return await self._async_try_fetch_device_info()

        return self.async_show_form(
            step_id="manual_config",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_DEVICE_NAME): str,
            }),
        )

    async def _async_try_fetch_device_info(self) -> ConfigFlowResult:
        """尝试获取设备信息."""
        response = await self.fetch_device_info()

        if response == ERROR_REQUIRES_ENCRYPTION_KEY:
            return await self.async_step_encryption_key()
        if response is not None:
            return self.async_show_form(
                step_id="manual_config",
                errors={"base": response},
                data_schema=vol.Schema({
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }),
            )
        return await self._async_authenticate_or_add()

    async def _async_authenticate_or_add(self) -> ConfigFlowResult:
        """认证或添加设备."""
        assert self._device_info is not None
        if self._device_info.uses_password:
            return await self.async_step_authenticate()

        self._password = ""
        return await self.async_step_llm_config()

    async def async_step_authenticate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """认证步骤."""
        errors = {}

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            error = await self.fetch_device_info()
            if error is None:
                return await self.async_step_llm_config()
            errors["base"] = error

        return self.async_show_form(
            step_id="authenticate",
            data_schema=vol.Schema({
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
            description_placeholders={"name": self._name},
        )

    async def async_step_encryption_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """加密密钥步骤."""
        errors = {}

        if user_input is not None:
            self._noise_psk = user_input[CONF_NOISE_PSK]
            error = await self.fetch_device_info()
            if error is None:
                return await self._async_authenticate_or_add()
            errors["base"] = error

        return self.async_show_form(
            step_id="encryption_key",
            data_schema=vol.Schema({
                vol.Required(CONF_NOISE_PSK): str,
            }),
            errors=errors,
            description_placeholders={"name": self._name},
        )

    async def async_step_llm_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """LLM 配置步骤 - 选择 LLM 提供商."""
        if user_input is not None:
            self._llm_provider = user_input.get(CONF_LLM_PROVIDER, LLM_PROVIDER_XIAOZHI)
            self._llm_endpoint = user_input.get(CONF_LLM_ENDPOINT)
            self._llm_api_key = user_input.get(CONF_LLM_API_KEY)

            if self._llm_provider == LLM_PROVIDER_XIAOZHI:
                return await self.async_step_xiaozhi_config()
            elif self._llm_provider == LLM_PROVIDER_OLLAMA:
                return await self.async_step_ollama_config()
            else:
                return await self._async_validated_connection()

        provider_options = [
            selector.SelectOptionDict(
                value=LLM_PROVIDER_XIAOZHI,
                label=f"{LLM_PROVIDER_NAMES[LLM_PROVIDER_XIAOZHI]} (默认)",
            ),
            selector.SelectOptionDict(
                value=LLM_PROVIDER_OLLAMA,
                label=LLM_PROVIDER_NAMES[LLM_PROVIDER_OLLAMA],
            ),
            selector.SelectOptionDict(
                value=LLM_PROVIDER_HA_CLOUD,
                label=LLM_PROVIDER_NAMES[LLM_PROVIDER_HA_CLOUD],
            ),
            selector.SelectOptionDict(
                value=LLM_PROVIDER_CUSTOM,
                label=LLM_PROVIDER_NAMES[LLM_PROVIDER_CUSTOM],
            ),
        ]

        return self.async_show_form(
            step_id="llm_config",
            data_schema=vol.Schema({
                vol.Required(CONF_LLM_PROVIDER): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=provider_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                ),
            }),
        )

    async def async_step_xiaozhi_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """小智云配置."""
        if user_input is not None:
            self._mcp_endpoint = user_input.get(CONF_MCP_ENDPOINT)
            return await self._async_validated_connection()

        return self.async_show_form(
            step_id="xiaozhi_config",
            data_schema=vol.Schema({
                vol.Optional(CONF_MCP_ENDPOINT): str,
            }),
            description_placeholders={
                "tip": "小智云 MCP 地址，留空使用默认服务器",
            },
        )

    async def async_step_ollama_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ollama 本地配置."""
        if user_input is not None:
            self._llm_endpoint = user_input.get(CONF_LLM_ENDPOINT, "http://localhost:11434")
            return await self._async_validated_connection()

        return self.async_show_form(
            step_id="ollama_config",
            data_schema=vol.Schema({
                vol.Required(CONF_LLM_ENDPOINT, default="http://localhost:11434"): str,
            }),
            description_placeholders={
                "tip": "Ollama 服务器地址",
            },
        )

    async def _async_validated_connection(self) -> ConfigFlowResult:
        """完成配置流程."""
        assert self._device_info is not None

        if not self._device_name:
            self._device_name = self._device_info.name

        mac_address = self._device_mac
        if not mac_address and self._device_info:
            mac_address = format_mac(self._device_info.mac)

        await self.async_set_unique_id(mac_address)

        config_data = {
            CONF_HOST: self._host,
            CONF_PORT: self._port,
            CONF_DEVICE_NAME: self._device_name,
            CONF_ASSIST_MODE: "device",
        }

        if self._password:
            config_data[CONF_PASSWORD] = self._password

        if self._noise_psk:
            config_data[CONF_NOISE_PSK] = self._noise_psk

        if self._llm_provider:
            config_data[CONF_LLM_PROVIDER] = self._llm_provider
            if self._llm_endpoint:
                config_data[CONF_LLM_ENDPOINT] = self._llm_endpoint
            if self._llm_api_key:
                config_data[CONF_LLM_API_KEY] = self._llm_api_key
            if self._mcp_endpoint:
                config_data[CONF_MCP_ENDPOINT] = self._mcp_endpoint

        return self.async_create_entry(
            title=self._name,
            data=config_data,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """重新认证."""
        self._reauth_entry = self._get_reauth_entry()
        self._host = entry_data.get(CONF_HOST)
        self._port = entry_data.get(CONF_PORT)
        self._password = entry_data.get(CONF_PASSWORD)
        self._device_name = entry_data.get(CONF_DEVICE_NAME)
        self._name = self._reauth_entry.title
        self._llm_provider = entry_data.get(CONF_LLM_PROVIDER, LLM_PROVIDER_XIAOZHI)
        self._llm_endpoint = entry_data.get(CONF_LLM_ENDPOINT)
        self._llm_api_key = entry_data.get(CONF_LLM_API_KEY)
        return await self.async_step_llm_config()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """重新配置."""
        self._reconfig_entry = self._get_reconfigure_entry()
        data = self._reconfig_entry.data
        self._host = data.get(CONF_HOST)
        self._port = data.get(CONF_PORT, DEFAULT_PORT)
        self._noise_psk = data.get(CONF_NOISE_PSK)
        self._device_name = data.get(CONF_DEVICE_NAME)
        self._llm_provider = data.get(CONF_LLM_PROVIDER, LLM_PROVIDER_XIAOZHI)
        self._llm_endpoint = data.get(CONF_LLM_ENDPOINT)
        return await self.async_step_llm_config()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """ZeroConf 发现."""
        mac_address: str | None = discovery_info.properties.get("mac")

        if mac_address is None:
            return self.async_abort(reason="mdns_missing_mac")

        mac_address = format_mac(mac_address)
        device_name = discovery_info.hostname.removesuffix(".local.")

        self._device_name = device_name
        self._name = discovery_info.properties.get("friendly_name", device_name)
        self._host = discovery_info.host
        self._port = discovery_info.port
        self._device_mac = mac_address
        self._noise_required = bool(discovery_info.properties.get("api_encryption"))

        await self.async_set_unique_id(mac_address)
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """确认发现."""
        if user_input is not None:
            return await self._async_try_fetch_device_info()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._name},
        )

    async def fetch_device_info(self) -> str | None:
        """获取设备信息."""
        cli = APIClient(
            self._host,
            self._port,
            self._password,
            client_info="Home Assistant",
            noise_psk=self._noise_psk,
            zeroconf_instance=await zeroconf.async_get_instance(self.hass),
        )

        try:
            await cli.connect()
            self._device_info = await cli.device_info()
            self._device_name = self._device_info.name
            self._device_mac = format_mac(self._device_info.mac)
            self._noise_required = self._device_info.uses_password
        except RequiresEncryptionAPIError:
            return ERROR_REQUIRES_ENCRYPTION_KEY
        except InvalidEncryptionKeyAPIError:
            return ERROR_INVALID_ENCRYPTION_KEY
        except InvalidAuthAPIError:
            return ERROR_INVALID_PASSWORD_AUTH
        except ResolveAPIError:
            return "connection_error"
        except APIConnectionError:
            return "connection_error"
        except Exception as err:
            _LOGGER.exception("Unexpected error: %s", err)
            return "unknown"
        finally:
            await cli.disconnect()

        return None

    @property
    def _name(self) -> str:
        return self.__name or DEFAULT_NAME

    @_name.setter
    def _name(self, value: str) -> None:
        self.__name = value
        self.context["title_placeholders"] = {
            "name": self._name
        }
