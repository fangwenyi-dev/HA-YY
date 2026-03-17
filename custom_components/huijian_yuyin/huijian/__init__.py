"""慧尖语音助手 - 核心模块."""
import logging

LOGGER = logging.getLogger("huijian_yuyin")

class Dict(dict):
    """Dict wrapper for easy attribute access."""
    def __getattr__(self, item):
        value = self.get(item)
        return Dict(value) if isinstance(value, dict) else value

    def __setattr__(self, key, value):
        self[key] = Dict(value) if isinstance(value, dict) else value

    def to_json(self, **kwargs):
        return __import__("json").dumps(self, **kwargs)

from .ws_transport import WsTransport
from .llm_transport import LlmTransport
from .mcp_transport import McpTransport
from .stt_transport import SttTransport
from .tts_transport import TtsTransport
from .audio import AudioBuffer, AudioProcessor

__all__ = [
    "Dict",
    "WsTransport",
    "LlmTransport",
    "McpTransport",
    "SttTransport",
    "TtsTransport",
    "AudioBuffer",
    "AudioProcessor",
    "LOGGER",
]


def get_haid(hass):
    """Get Home Assistant instance ID."""
    from homeassistant.const import DATA_DIR
    from pathlib import Path
    import hashlib

    haid_file = Path(DATA_DIR) / ".hauuid"
    if haid_file.exists():
        return haid_file.read_text().strip()
    
    import uuid
    haid = str(uuid.uuid4())
    haid_file.write_text(haid)
    return haid


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


def mcp_transport(hass, entry, field=None):
    """Get MCP transport."""
    from .mcp_transport import get_entry_transport as _get_mcp_transport
    return _get_mcp_transport(hass, entry)


mcp_transport = mcp_transport


llm_transport = mcp_transport
stt_transport = mcp_transport
tts_transport = mcp_transport
