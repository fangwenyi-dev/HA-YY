"""慧尖语音助手常量定义."""

from typing import Final

from awesomeversion import AwesomeVersion

DOMAIN = "huijian_yuyin"

CONF_ALLOW_SERVICE_CALLS = "allow_service_calls"
CONF_SUBSCRIBE_LOGS = "subscribe_logs"
CONF_DEVICE_NAME = "device_name"
CONF_NOISE_PSK = "noise_psk"
CONF_BLUETOOTH_MAC_ADDRESS = "bluetooth_mac_address"

CONF_LLM_PROVIDER = "llm_provider"
CONF_LLM_ENDPOINT = "llm_endpoint"
CONF_LLM_API_KEY = "llm_api_key"
CONF_MCP_ENDPOINT = "mcp_endpoint"
CONF_ASSIST_MODE = "assist_mode"

DEFAULT_ALLOW_SERVICE_CALLS = True
DEFAULT_NEW_CONFIG_ALLOW_ALLOW_SERVICE_CALLS = False

DEFAULT_PORT: Final = 6053

STABLE_BLE_VERSION_STR = "2025.11.0"
STABLE_BLE_VERSION = AwesomeVersion(STABLE_BLE_VERSION_STR)
PROJECT_URLS = {
    "esphome.bluetooth-proxy": "https://esphome.github.io/bluetooth-proxies/",
}
STABLE_BLE_URL_VERSION = f"{STABLE_BLE_VERSION.major}.{STABLE_BLE_VERSION.minor}.0"
DEFAULT_URL = f"https://esphome.io/changelog/{STABLE_BLE_URL_VERSION}.html"

NO_WAKE_WORD: Final[str] = "no_wake_word"

WAKE_WORDS_DIR_NAME = "custom_wake_words"
WAKE_WORDS_API_PATH = "/api/huijian_yuyin/wake_words"

LLM_PROVIDER_XIAOZHI = "xiaozhi"
LLM_PROVIDER_OLLAMA = "ollama"
LLM_PROVIDER_HA_CLOUD = "ha_cloud"
LLM_PROVIDER_CUSTOM = "custom"

XIAOZHI_MCP_DEFAULT_ENDPOINT = "wss://api.xiaozhi.me/mcp/"

LLM_PROVIDER_NAMES = {
    LLM_PROVIDER_XIAOZHI: "小智云 (推荐)",
    LLM_PROVIDER_OLLAMA: "Ollama 本地模型",
    LLM_PROVIDER_HA_CLOUD: "HA Cloud",
    LLM_PROVIDER_CUSTOM: "自定义 API",
}

LLM_PROVIDERS = [
    LLM_PROVIDER_XIAOZHI,
    LLM_PROVIDER_OLLAMA,
    LLM_PROVIDER_HA_CLOUD,
    LLM_PROVIDER_CUSTOM,
]
