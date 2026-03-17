"""慧尖语音助手 - MCP 传输层."""

import logging

import anyio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from . import Dict
from .ws_transport import WsTransport

_LOGGER = logging.getLogger(__name__)


class McpTransport(WsTransport):
    """MCP (Model Context Protocol) transport using WebSocket."""

    _transport_type = "mcp"

    def init(self):
        self.logger = _LOGGER

    async def send_message(self, message: dict):
        """Send a message via MCP transport."""
        await self.send(message)

    async def send_text(self, text: str, **kwargs):
        """Send text message."""
        await self.send(Dict(type="text", data=text, **kwargs))

    async def send_audio(self, audio_data: bytes, **kwargs):
        """Send audio data."""
        await self.send(Dict(type="audio", data=audio_data, **kwargs))

    async def async_remove_entry(self):
        """Remove entry."""
        entry = self.entry
        this_data: dict = get_entry_data(self.hass, entry)
        transport: McpTransport | None = this_data.pop("mcp_transport", None)
        self.logger.info(
            "Remove entry from MCP transport: title=%s id=%s",
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


def get_entry_transport(hass: HomeAssistant, entry: ConfigEntry) -> McpTransport:
    """Get MCP entry transport."""
    endpoint: str | None = entry.data.get("mcp_endpoint")
    if not endpoint:
        endpoint = "ws://localhost:8765"
        _LOGGER.info("Using default MCP endpoint: %s", endpoint)

    this_data: dict = get_entry_data(hass, entry)
    transport: McpTransport | None = this_data.get("mcp_transport")
    if transport and transport.endpoint == endpoint and transport.available:
        return transport

    _LOGGER.info(
        "Creating new McpTransport for entry: %s %s",
        entry.entry_id,
        entry.title,
    )
    transport = McpTransport(hass, entry, endpoint, "mcp_endpoint", _LOGGER)
    this_data["mcp_transport"] = transport
    return transport


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup MCP transport entry."""
    endpoint: str | None = entry.data.get("mcp_endpoint")
    if endpoint:
        _LOGGER.info("Setting up MCP transport with endpoint: %s", endpoint)
    return True
