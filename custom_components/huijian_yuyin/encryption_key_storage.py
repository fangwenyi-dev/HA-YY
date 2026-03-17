"""慧尖语音助手 - 加密密钥存储."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

ENCRYPTION_KEY_STORAGE_KEY = "huijian_yuyin_encryption_keys"


class EncryptionKeyStorage:
    """Encryption key storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self.hass = hass
        self._store = Store(hass, "1", ENCRYPTION_KEY_STORAGE_KEY)
        self._keys: dict = {}

    async def _load(self) -> None:
        """Load keys from storage."""
        data = await self._store.async_load()
        if data:
            self._keys = data.get("keys", {})

    async def async_get_key(self, unique_id: str) -> str | None:
        """Get encryption key for a device."""
        if not self._keys:
            await self._load()
        return self._keys.get(unique_id)

    async def async_set_key(self, unique_id: str, key: str) -> None:
        """Set encryption key for a device."""
        self._keys[unique_id] = key
        await self._store.async_save({"keys": self._keys})

    async def async_remove_key(self, unique_id: str) -> None:
        """Remove encryption key for a device."""
        self._keys.pop(unique_id, None)
        await self._store.async_save({"keys": self._keys})


async def async_get_encryption_key_storage(hass: HomeAssistant) -> EncryptionKeyStorage:
    """Get encryption key storage."""
    return EncryptionKeyStorage(hass)
