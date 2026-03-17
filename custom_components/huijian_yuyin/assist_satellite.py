"""慧尖语音助手 - 语音卫星集成."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import assist_satellite
from homeassistant.components.assist_pipeline import (
    PipelineEventType,
)
from homeassistant.components.intent import async_register_timer_handler
from homeassistant.core import HomeAssistant, callback

from .entry_data import ESPHomeConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the assist satellite platform."""
    _LOGGER.info("Setting up huijian_yuyin assist satellite")
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ESPHomeConfigEntry,
    async_add_entities,
) -> None:
    """Set up Assist satellite entity."""
    entry_data = entry.runtime_data
    
    if hasattr(entry_data, 'device_info') and entry_data.device_info:
        async_add_entities([HuiJianAssistSatellite(entry)])


class HuiJianAssistSatellite(assist_satellite.AssistSatelliteEntity):
    """慧尖语音卫星."""

    def __init__(self, entry: ESPHomeConfigEntry) -> None:
        """Initialize satellite."""
        self.config_entry = entry
        self._entry_data = entry.runtime_data
        self._is_running = True
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        
        self._satellite_config = assist_satellite.AssistSatelliteConfiguration(
            available_wake_words=[],
            active_wake_words=[],
            max_active_wake_words=1,
        )

    @callback
    def async_get_configuration(
        self,
    ) -> assist_satellite.AssistSatelliteConfiguration:
        """Get the current satellite configuration."""
        return self._satellite_config

    async def async_set_configuration(
        self, config: assist_satellite.AssistSatelliteConfiguration
    ) -> None:
        """Set the current satellite configuration."""
        self._satellite_config = config
        _LOGGER.debug("Set satellite configuration: %s", config)

    async def async_start_conversation(self, conversation_id: str | None = None) -> None:
        """Start a voice conversation."""
        _LOGGER.info("Starting conversation")
        self._is_running = True

    async def async_stop_conversation(self) -> None:
        """Stop the voice conversation."""
        _LOGGER.info("Stopping conversation")
        self._is_running = False
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def async_on_alternate_config(self, config: assist_satellite.AssistSatelliteConfiguration) -> None:
        """Handle alternate configuration."""
        pass

    async def async_handle_announce(self, announce: str) -> None:
        """Handle announcement."""
        _LOGGER.info("Announce: %s", announce)

    async def handle_pipeline_start(
        self,
        conversation_id: int | None,
        flags: int,
        timeout: int = 30,
    ) -> bool:
        """Handle pipeline start."""
        return True

    async def handle_pipeline_stop(self) -> None:
        """Handle pipeline stop."""
        self._is_running = False

    async def handle_audio(self, audio_bytes: bytes) -> None:
        """Handle incoming audio."""
        await self._audio_queue.put(audio_bytes)

    async def handle_announcement_finished(self, message_id: str) -> None:
        """Handle announcement finished."""
        _LOGGER.debug("Announcement finished: %s", message_id)

    async def handle_timer_event(self, event) -> None:
        """Handle timer event."""
        _LOGGER.debug("Timer event: %s", event)
