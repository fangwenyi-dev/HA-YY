"""慧尖语音助手 - STT 传输层."""

import logging
import json
import base64

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from . import Dict
from .ws_transport import WsTransport

_LOGGER = logging.getLogger(__name__)


class SttTransport(WsTransport):
    """Speech-to-Text transport using WebSocket."""

    _transport_type = "stt"

    def init(self):
        self.logger = _LOGGER
        self._text_buffer = []

    async def recognize(self, audio_data: bytes) -> str:
        """Recognize speech from audio data."""
        if not await self.ensure_connected():
            raise Exception("Failed to connect to STT service")

        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        await self.send(Dict(type="stt", data=audio_b64))

        text = ""
        try:
            async for data in self._recv_reader:
                if data.type == "stt_result":
                    text = data.get("text", "")
                    break
        except Exception as e:
            _LOGGER.error("STT recognition error: %s", e)

        return text

    async def async_remove_entry(self):
        """Remove entry."""
        entry = self.entry
        this_data: dict = get_entry_data(self.hass, entry)
        transport: SttTransport | None = this_data.pop("stt_transport", None)
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


def get_entry_transport(hass: HomeAssistant, entry: ConfigEntry) -> SttTransport:
    """Get STT entry transport."""
    endpoint: str | None = entry.data.get("stt_endpoint")
    if not endpoint:
        raise Exception("No STT endpoint configured")

    this_data: dict = get_entry_data(hass, entry)
    transport: SttTransport | None = this_data.get("stt_transport")
    if transport and transport.endpoint == endpoint and transport.available:
        return transport

    _LOGGER.info(
        "Creating new SttTransport for entry: %s %s",
        entry.entry_id,
        entry.title,
    )
    transport = SttTransport(hass, entry, endpoint, "stt_endpoint", _LOGGER)
    this_data["stt_transport"] = transport
    return transport
