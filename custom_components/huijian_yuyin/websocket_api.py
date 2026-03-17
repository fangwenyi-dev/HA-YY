"""慧尖语音助手 - WebSocket API."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.components import websocket_api

_LOGGER = logging.getLogger(__name__)


def async_setup(hass: HomeAssistant) -> None:
    """Set up WebSocket API."""

    @websocket_api.websocket_command(
        {
            "type": "huijian_yuyin/setup/qrcode",
            "type": "huijian_yuyin/setup/status",
        }
    )
    @websocket_api.async_response
    async def ws_setup_qrcode(hass, connection, msg):
        """Handle setup QR code WebSocket command."""
        _LOGGER.info("Received setup QR code request: %s", msg)

        await connection.send_message(
            {
                "id": msg["id"],
                "type": "result",
                "success": True,
                "result": {
                    "qrcode": "",
                    "status": "waiting",
                },
            }
        )

    websocket_api.async_register_command(hass, "huijian_yuyin/setup/qrcode")
    websocket_api.async_register_command(hass, "huijian_yuyin/setup/status")

    _LOGGER.info("WebSocket API registered for huijian_yuyin")
