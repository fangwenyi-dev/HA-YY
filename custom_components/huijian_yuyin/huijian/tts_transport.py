"""慧尖语音助手 - TTS 传输层."""

import logging
import base64

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from . import Dict
from .ws_transport import WsTransport

_LOGGER = logging.getLogger(__name__)


class TtsTransport(WsTransport):
    """Text-to-Speech transport using WebSocket."""

    _transport_type = "tts"

    def init(self):
        self.logger = _LOGGER

    async def speak(self, text: str) -> bytes:
        """Convert text to speech and return audio data."""
        if not await self.ensure_connected():
            raise Exception("Failed to connect to TTS service")

        await self.send(Dict(type="tts", data=text))

        audio_data = b""
        try:
            async for data in self._recv_reader:
                if data.type == "tts_result":
                    audio_b64 = data.get("audio", "")
                    audio_data = base64.b64decode(audio_b64)
                    break
        except Exception as e:
            _LOGGER.error("TTS synthesis error: %s", e)

        return audio_data

    async def async_remove_entry(self):
        """Remove entry."""
        entry = self.entry
        this_data: dict = get_entry_data(self.hass, entry)
        transport: TtsTransport | None = this_data.pop("tts_transport", None)
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


def get_entry_transport(hass: HomeAssistant, entry: ConfigEntry) -> TtsTransport:
    """Get TTS entry transport."""
    endpoint: str | None = entry.data.get("tts_endpoint")
    if not endpoint:
        raise Exception("No TTS endpoint configured")

    this_data: dict = get_entry_data(hass, entry)
    transport: TtsTransport | None = this_data.get("tts_transport")
    if transport and transport.endpoint == endpoint and transport.available:
        return transport

    _LOGGER.info(
        "Creating new TtsTransport for entry: %s %s",
        entry.entry_id,
        entry.title,
    )
    transport = TtsTransport(hass, entry, endpoint, "tts_endpoint", _LOGGER)
    this_data["tts_transport"] = transport
    return transport
