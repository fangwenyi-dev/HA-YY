"""慧尖语音助手 - Intent 处理模块."""

import logging

from homeassistant.helpers import intent

from .entry_data import ESPHomeConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the intent platform."""
    _LOGGER.info("Setting up huijian_yuyin intents")
    return True


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up intent entities."""
    return True


class HuiJianIntentHandler(intent.IntentHandler):
    """慧尖语音 Intent 处理器."""

    intent_type = "HuiJianVoiceCommand"
    slot_schema = {
        intent.ATTR_TEXT: str,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        slots = intent_obj.slots
        text = slots.get("text", {}).get("value", "")
        
        _LOGGER.info("Handling intent: %s", text)
        
        response = intent_obj.create_response()
        response.async_set_speech(f"收到指令: {text}")
        
        return response


async def register_intents(hass, entry: ESPHomeConfigEntry):
    """Register intents for the entry."""
    handler = HuiJianIntentHandler()
    intent.async_register(hass, handler)
    _LOGGER.info("Registered intents for entry: %s", entry.entry_id)
