"""MQTT subscriber for capability updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, cast

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class CapabilityMQTTSubscriber:
    """Subscribe to capability update events."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "job-dispatcher",
        on_capability_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self._on_capability_event = on_capability_event
        self._client: mqtt.Client | None = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> None:
        """Connect and subscribe."""
        self._loop = asyncio.get_event_loop()
        self._client = mqtt.Client(client_id=self.client_id)
        client_any = cast(Any, self._client)
        client_any.on_connect = self._on_connect
        client_any.on_disconnect = self._on_disconnect
        client_any.on_message = self._on_message

        try:
            self._client.connect_async(self.broker_host, self.broker_port)
            self._client.loop_start()

            for _ in range(50):
                if self._connected:
                    self._client.subscribe("adaptivx/capability/#", qos=1)
                    logger.info("Subscribed to capability updates")
                    return
                await asyncio.sleep(0.1)
            logger.warning("MQTT connection timeout - continuing without MQTT")
        except Exception as e:
            logger.warning("MQTT connection failed: %s", e)

    async def ensure_connected(self) -> None:
        """Best-effort reconnect."""
        if self._connected:
            return
        if not self._client:
            await self.connect()
            return
        try:
            self._client.connect_async(self.broker_host, self.broker_port)
            for _ in range(20):
                if self._connected:
                    self._client.subscribe("adaptivx/capability/#", qos=1)
                    return
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.debug("MQTT reconnect failed: %s", e)

    async def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            self._client = None

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: int,
        properties: Any = None,
    ) -> None:
        if reason_code == 0:
            self._connected = True
            logger.debug("MQTT connected")
        else:
            logger.warning("MQTT connect failed: %s", reason_code)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: int,
        properties: Any = None,
    ) -> None:
        self._connected = False
        logger.debug("MQTT disconnected")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        try:
            payload = json.loads(message.payload.decode())
            if self._on_capability_event and self._loop:
                coro = cast(
                    Coroutine[Any, Any, None],
                    self._on_capability_event(payload),
                )
                asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception as e:
            logger.error("Failed to process capability event: %s", e)
