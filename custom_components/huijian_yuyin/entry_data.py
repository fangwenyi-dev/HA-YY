"""慧尖语音助手 - 入口数据定义."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aioesphomeapi import APIClient

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store


@dataclass
class RuntimeEntryData:
    """Runtime entry data."""

    client: APIClient
    entry_id: str
    title: str
    store: Store
    original_options: dict[str, Any]
    loaded_platforms: set[str] = field(default_factory=set)
    entity_info: list | None = None
    available: bool = True
    device_info: Any | None = None
    noise_psk: str | None = None
    next_id: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "loaded_platforms": list(self.loaded_platforms),
        }


ESPHomeConfigEntry = Any
