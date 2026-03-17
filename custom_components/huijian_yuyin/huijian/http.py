"""慧尖语音助手 - HTTP 服务."""

import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_https(hass: HomeAssistant) -> None:
    """Setup HTTP services."""
    _LOGGER.info("Setting up HTTP services for huijian_yuyin")
