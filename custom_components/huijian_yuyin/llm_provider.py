"""慧尖语音助手 - LLM 提供器模块."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant

from .const import (
    CONF_LLM_PROVIDER,
    CONF_LLM_ENDPOINT,
    CONF_LLM_API_KEY,
    CONF_MCP_ENDPOINT,
    LLM_PROVIDER_XIAOZHI,
    LLM_PROVIDER_OLLAMA,
    LLM_PROVIDER_HA_CLOUD,
    LLM_PROVIDER_CUSTOM,
    XIAOZHI_MCP_DEFAULT_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = endpoint
        self.api_key = api_key

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request and return response."""
        pass


class XiaozhiProvider(BaseLLMProvider):
    """小智云 LLM 提供商."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None, mcp_endpoint: str | None = None):
        super().__init__(endpoint, api_key)
        self.mcp_endpoint = mcp_endpoint or XIAOZHI_MCP_DEFAULT_ENDPOINT

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request to Xiaozhi cloud via MCP."""
        import json
        
        _LOGGER.info("Sending chat request to Xiaozhi MCP: %s", self.mcp_endpoint)
        
        try:
            ws_url = self.mcp_endpoint
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_json({
                        "type": "chat",
                        "messages": messages,
                    })
                    
                    response_text = ""
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                if data.get("type") == "text":
                                    response_text += data.get("data", "")
                                elif data.get("type") == "end":
                                    break
                            except json.JSONDecodeError:
                                continue
                    return response_text
        except Exception as e:
            _LOGGER.error("Xiaozhi chat error: %s", e)
            return f"抱歉，处理您的请求时发生错误: {str(e)}"


class OllamaProvider(BaseLLMProvider):
    """Ollama 本地 LLM 提供商."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        super().__init__(endpoint, api_key)
        self.endpoint = endpoint or "http://localhost:11434"

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request to Ollama."""
        _LOGGER.info("Sending chat request to Ollama: %s", messages)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/api/chat",
                    json={
                        "model": kwargs.get("model", "llama2"),
                        "messages": messages,
                        "stream": False,
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("message", {}).get("content", "")
                    else:
                        error_text = await response.text()
                        _LOGGER.error("Ollama error: %s", error_text)
                        return f"Ollama 请求失败: {error_text}"
        except Exception as e:
            _LOGGER.error("Ollama connection error: %s", e)
            return f"无法连接到 Ollama 服务: {str(e)}"


class HACloudProvider(BaseLLMProvider):
    """Home Assistant Cloud LLM 提供商."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        super().__init__(endpoint, api_key)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request to HA Cloud."""
        _LOGGER.info("Sending chat request to HA Cloud")
        
        try:
            from homeassistant.components.conversation import default_agent
            
            agent = default_agent.async_get_default_agent(self.hass)
            result = await agent.async_process(
                messages[-1].get("content", ""),
                context={},
            )
            return result.response.speech.get("plain", {}).get("speech", "")
        except Exception as e:
            _LOGGER.error("HA Cloud error: %s", e)
            return f"HA Cloud 处理失败: {str(e)}"


class CustomProvider(BaseLLMProvider):
    """自定义 LLM 提供商."""

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        super().__init__(endpoint, api_key)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send chat request to custom endpoint."""
        _LOGGER.info("Sending chat request to custom provider: %s", self.endpoint)
        
        if not self.endpoint:
            return "未配置自定义 LLM 端点"

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json={
                        "messages": messages,
                        **kwargs,
                    },
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("content", "") or data.get("response", "")
                    else:
                        error_text = await response.text()
                        return f"自定义 LLM 请求失败: {error_text}"
        except Exception as e:
            _LOGGER.error("Custom provider error: %s", e)
            return f"无法连接到自定义 LLM 服务: {str(e)}"


LLM_PROVIDER_CLASSES = {
    LLM_PROVIDER_XIAOZHI: XiaozhiProvider,
    LLM_PROVIDER_OLLAMA: OllamaProvider,
    LLM_PROVIDER_HA_CLOUD: HACloudProvider,
    LLM_PROVIDER_CUSTOM: CustomProvider,
}


def create_llm_provider(
    provider_type: str,
    endpoint: str | None = None,
    api_key: str | None = None,
    mcp_endpoint: str | None = None,
) -> BaseLLMProvider:
    """Create an LLM provider instance."""
    if provider_type == LLM_PROVIDER_XIAOZHI:
        return XiaozhiProvider(endpoint=endpoint, api_key=api_key, mcp_endpoint=mcp_endpoint)
    provider_class = LLM_PROVIDER_CLASSES.get(provider_type, XiaozhiProvider)
    return provider_class(endpoint=endpoint, api_key=api_key)


async def async_setup_llm_providers(hass: HomeAssistant) -> None:
    """Setup LLM providers."""
    _LOGGER.info("Setting up LLM providers")
    hass.data["huijian_yuyin_llm_providers"] = {}


def get_llm_provider(hass: HomeAssistant, entry) -> BaseLLMProvider:
    """Get LLM provider for an entry."""
    provider_type = entry.data.get(CONF_LLM_PROVIDER, LLM_PROVIDER_XIAOZHI)
    endpoint = entry.data.get(CONF_LLM_ENDPOINT)
    api_key = entry.data.get(CONF_LLM_API_KEY)
    mcp_endpoint = entry.data.get(CONF_MCP_ENDPOINT)
    
    return create_llm_provider(provider_type, endpoint, api_key, mcp_endpoint)
