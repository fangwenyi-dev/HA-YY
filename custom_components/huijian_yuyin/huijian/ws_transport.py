"""慧尖语音助手 - WebSocket 传输层."""

import logging
import json
import time
import anyio
import asyncio
import aiohttp
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed

from . import LOGGER

_LOGGER = logging.getLogger(__name__)


class Dict(dict):
    """Dict wrapper for easy attribute access."""

    def __getattr__(self, item):
        value = self.get(item)
        return Dict(value) if isinstance(value, dict) else value

    def __setattr__(self, key, value):
        self[key] = Dict(value) if isinstance(value, dict) else value

    def to_json(self, **kwargs):
        return json.dumps(self, **kwargs)


class WsTransport:
    """Handles WebSocket transport."""

    _transport_type = ""
    _recv_binary = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        endpoint: str,
        attr_endpoint: str,
        logger=None,
    ):
        self.stop_event = asyncio.Event()
        self.endpoint = endpoint
        self.attr_endpoint = attr_endpoint
        self.reconnect_times = 0
        self.should_reconnect = True
        self._current_ws = None
        self._idle_timeout = 180
        self._last_activity_time = 0
        self._is_connected = False

        self.hass = hass
        self.entry = entry
        self.logger = logger or _LOGGER
        self._connection_lock = asyncio.Lock()

        self._recv_writer: MemoryObjectSendStream = None
        self._recv_reader: MemoryObjectReceiveStream = None
        self._send_writer: MemoryObjectSendStream = None
        self._send_reader: MemoryObjectReceiveStream = None

        self.init()

    def init(self):
        """Initialize transport."""
        pass

    @property
    def available(self):
        """Check if transport is available."""
        return not self.stop_event.is_set() and self.should_reconnect

    def update_activity_time(self):
        """Update last activity time."""
        self._last_activity_time = time.monotonic()

    def ws_log(self, msg, *args, **kwargs):
        """Log with dynamic level."""
        lvl = logging.ERROR if self.reconnect_times >= 3 else logging.INFO
        self.logger.log(lvl, msg, *args, **kwargs)

    @property
    def is_connected(self):
        """Check if connected."""
        return (
            self._is_connected
            and self._current_ws
            and not self._current_ws.closed
        )

    async def ensure_connected(self):
        """Ensure WebSocket is connected."""
        if not self.should_reconnect:
            self.logger.info("Interrupted before ensure connected")
            return False

        if self.is_connected:
            self.update_activity_time()
            return True

        async with self._connection_lock:
            if self.is_connected:
                self.update_activity_time()
                return True

            if not self.endpoint:
                self.logger.error("No endpoint configured in config entry")
                return False

            self.logger.info("On-demand connecting to WebSocket: %s", self.endpoint)
            self.update_activity_time()

            self.entry.async_create_background_task(
                self.hass,
                self.run_connection_loop(),
                f"transport_loop:{self._transport_type}",
            )

            for _ in range(150):
                if not self.should_reconnect:
                    self.logger.info("Interrupted wait connected")
                    return False
                if self.is_connected:
                    return True
                await asyncio.sleep(0.1)

            self.logger.error("Timed out waiting for WebSocket connection")
            return False

    async def _create_streams(self):
        """Create memory object streams for communication."""
        self._recv_writer, self._recv_reader = anyio.create_memory_object_stream(0)
        self._send_writer, self._send_reader = anyio.create_memory_object_stream(0)

    async def run_connection_loop(self) -> None:
        """Run the connection loop with automatic reconnection."""
        while self.should_reconnect:
            try:
                if not await self.connect_to_client():
                    break
            except ConfigEntryAuthFailed:
                raise
            except Exception as err:
                self.logger.warning(
                    "Websocket disconnected or failed: %s", err
                )
            finally:
                self._is_connected = False
            if self.should_reconnect:
                seconds = max(min(60, self.reconnect_times * 5), 3)
                self.logger.info(
                    "Websocket retry after %s seconds, times: %s",
                    seconds,
                    self.reconnect_times,
                )
                self.reconnect_times += 1
                if seconds > 0:
                    await asyncio.sleep(seconds)

    async def connect_to_client(self) -> bool:
        """Connect to WebSocket endpoint."""
        if not self.endpoint:
            self.logger.error("No endpoint configured in config entry")
            return False

        if not self.should_reconnect:
            self.logger.info("Interrupted before connect")
            return False

        try:
            await self._create_streams()
            await self._establish_websocket_connection()
        except Exception as err:
            self.logger.exception(
                "Failed to connect to websocket at %s: %s",
                self.endpoint,
                err,
            )
            return False

        return self.should_reconnect

    async def _establish_websocket_connection(self):
        """Establish WebSocket connection."""
        timeout = aiohttp.ClientTimeout(total=None, connect=30)
        async with aiohttp.ClientSession(timeout=timeout) as client_session:
            async with client_session.ws_connect(self.endpoint) as ws:
                self._current_ws = ws
                self._is_connected = True
                self.update_activity_time()
                self.reconnect_times = 0

                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._handle_incoming_messages, tg.cancel_scope)
                    tg.start_soon(self._handle_outgoing_messages)
                    tg.start_soon(self._heartbeat_task)

    async def _handle_incoming_messages(self, cancel_scope):
        """Handle incoming messages."""
        try:
            async for msg in self._current_ws:
                if not self.should_reconnect:
                    cancel_scope.cancel()
                    return

                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = Dict(json.loads(msg.data))
                    except json.JSONDecodeError:
                        data = Dict(raw=msg.data)
                    await self._recv_writer.send(data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error("WebSocket error: %s", msg.data)
                    break
        except anyio.ClosedResourceError:
            pass
        finally:
            self._is_connected = False

    async def _handle_outgoing_messages(self):
        """Handle outgoing messages."""
        try:
            async for data in self._send_reader:
                if not self.should_reconnect:
                    break
                if isinstance(data, dict):
                    await self._current_ws.send_str(json.dumps(data))
                else:
                    await self._current_ws.send_str(str(data))
                self.update_activity_time()
        except anyio.ClosedResourceError:
            pass

    async def _heartbeat_task(self):
        """Heartbeat task."""
        while self.should_reconnect and self.is_connected:
            await asyncio.sleep(30)
            if self.is_connected:
                try:
                    await self._current_ws.ping()
                except Exception:
                    pass

    async def stop(self, reason: str = "stopped"):
        """Stop the transport."""
        self.logger.info("Stopping transport: %s", reason)
        self.should_reconnect = False
        self.stop_event.set()
        if self._current_ws:
            await self._current_ws.close()
        self._is_connected = False

    async def send(self, data):
        """Send data."""
        if self._send_writer:
            await self._send_writer.send(data)

    async def async_remove_entry(self):
        """Remove entry."""
        await self.stop("Remove entry")
