"""慧尖语音助手 - 对话集成."""

import logging

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    ConversationResult,
    DefaultAgent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from .entry_data import ESPHomeConfigEntry
from .llm_provider import get_llm_provider

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ESPHomeConfigEntry,
    async_add_entities,
) -> None:
    """Set up conversation platform."""
    async_add_entities([HuiJianConversationEntity(entry)])


class HuiJianConversationEntity(conversation.ConversationEntity):
    """慧尖语音对话实体."""

    def __init__(self, entry: ESPHomeConfigEntry) -> None:
        """Initialize the conversation entity."""
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title
        self._attr_language = "zh-CN"
        
        entry_data = entry.runtime_data
        if hasattr(entry_data, 'device_info') and entry_data.device_info:
            self._attr_device_id = entry_data.device_info.mac_address

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return ["zh-CN", "zh"]

    async def async_process(self, user_input: conversation.ConversationInput) -> ConversationResult:
        """Process user input."""
        _LOGGER.info("Processing conversation input: %s", user_input.text)
        
        try:
            provider = get_llm_provider(self.hass, self.entry)
            
            messages = [
                {"role": "system", "content": "你是一个智能家居助手，可以帮助用户控制家中的智能设备。请用简洁的中文回答。"},
                {"role": "user", "content": user_input.text},
            ]
            
            response_text = await provider.chat(messages)
            
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(response_text)
            
            return ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )
            
        except Exception as e:
            _LOGGER.error("Conversation error: %s", e)
            
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"处理您的请求时发生错误: {str(e)}"
            )
            
            return ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )
