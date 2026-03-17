"""慧尖语音助手 - LLM 传输层."""

import logging

import anyio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from . import Dict
from .ws_transport import WsTransport

_LOGGER = logging.getLogger(__name__)


class LlmTransport(WsTransport):
    """LLM transport using WebSocket."""

    _transport_type = "llm"

    def init(self):
        self.logger = _LOGGER

    async def await_message(self, timeout: int = 180):
        """Wait for response message."""
        content = ""
        try:
            with anyio.fail_after(timeout):
                async for data in self._recv_reader:
                    if data.state == "end":
                        break
                    if data.type != "text":
                        continue
                    if data.state == "start":
                        content = ""
                    if data.state == "sentence_end" and isinstance(data.data, str):
                        content += data.data
                yield Dict(role="assistant", content=content)
        except TimeoutError:
            _LOGGER.error("Response timeout")
            yield Dict(error="Response timeout")

    async def async_remove_entry(self):
        """Remove entry."""
        entry = self.entry
        this_data: dict = get_entry_data(self.hass, entry)
        transport: LlmTransport | None = this_data.pop("llm_transport", None)
        self.logger.info(
            "Remove entry from LLM transport: title=%s id=%s",
            entry.title,
            entry.entry_id,
        )
        if transport:
            await transport.stop("Remove entry")


def get_entry_data(hass, entry, field=None, set_default=None, pop=False):
    """Get entry data."""
    domain_data = hass.data.setdefault("huijian_yuyin", {})
    data = domain_data.setdefault(entry.entry_id, {})

    if field and pop:
        return data.pop(field, None)
    if field and set_default is not None:
        return data.setdefault(field, set_default)
    if field:
        return data.get(field)
    return data


def get_entry_transport(hass: HomeAssistant, entry: ConfigEntry) -> LlmTransport:
    """Get entry transport."""
    endpoint: str | None = entry.data.get("llm_endpoint")
    if not endpoint:
        raise Exception("No LLM endpoint configured")

    this_data: dict = get_entry_data(hass, entry)
    transport: LlmTransport | None = this_data.get("llm_transport")
    if transport and transport.endpoint == endpoint and transport.available:
        return transport

    _LOGGER.info(
        "Creating new LlmTransport for entry: %s %s",
        entry.entry_id,
        entry.title,
    )
    transport = LlmTransport(hass, entry, endpoint, "llm_endpoint", _LOGGER)
    this_data["llm_transport"] = transport
    return transport
