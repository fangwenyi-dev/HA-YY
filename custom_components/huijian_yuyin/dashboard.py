"""慧尖语音助手 - Dashboard 集成."""

import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the dashboard platform."""
    _LOGGER.info("Setting up huijian_yuyin dashboard")
    return True


async def async_get_or_create_dashboard_manager(hass: HomeAssistant):
    """Get or create dashboard manager."""
    return None


async def async_set_dashboard_info(hass: HomeAssistant, addon_slug: str, url: str):
    """Set dashboard info."""
    _LOGGER.info("Setting dashboard info: %s, %s", addon_slug, url)
