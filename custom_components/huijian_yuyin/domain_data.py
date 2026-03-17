"""慧尖语音助手 - 域数据管理."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

DOMAIN_DATA_KEY = "huijian_yuyin_domain_data"


class DomainData:
    """Domain data manager for huijian_yuyin."""

    _instance = None

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize domain data."""
        self.hass = hass
        self._stores = {}

    @classmethod
    def get(cls, hass: HomeAssistant) -> "DomainData":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(hass)
        return cls._instance

    def get_or_create_store(self, hass: HomeAssistant, entry) -> Store:
        """Get or create a store for an entry."""
        key = f"{DOMAIN_DATA_KEY}_{entry.entry_id}"
        if key not in self._stores:
            self._stores[key] = Store(hass, "1", key)
        return self._stores[key]
