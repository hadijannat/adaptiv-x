"""
MQTT Subscriber for Skill-Broker.

Subscribes to health events from adaptiv-monitor.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, cast

import paho.mqtt.client as mqtt

from skill_broker.models import HealthEvent

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """MQTT subscriber for health events."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "skill-broker",
        on_health_event: Callable[[HealthEvent], Awaitable[None]] | None = None,
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self._on_health_event = on_health_event
        self._client: mqtt.Client | None = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> None:
        """Connect to the MQTT broker and subscribe to topics."""
        self._loop = asyncio.get_event_loop()
        self._client = mqtt.Client(client_id=self.client_id)

        # Set callbacks
        client_any = cast(Any, self._client)
        setattr(client_any, "on_connect", self._on_connect)
        setattr(client_any, "on_disconnect", self._on_disconnect)
        setattr(client_any, "on_message", self._on_message)

        try:
            self._client.connect_async(self.broker_host, self.broker_port)
            self._client.loop_start()

            # Wait for connection with timeout
            for _ in range(50):  # 5 seconds timeout
                if self._connected:
                    # Subscribe to health events
                    self._client.subscribe("adaptivx/health/#", qos=1)
                    logger.info("Connected to MQTT and subscribed to health events")
                    return
                await asyncio.sleep(0.1)

            logger.warning("MQTT connection timeout - continuing without MQTT")
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: int,
        properties: Any = None,
    ) -> None:
        """Callback when connected to broker."""
        if reason_code == 0:
            self._connected = True
            logger.debug("MQTT connected successfully")
        else:
            logger.warning(f"MQTT connection failed: {reason_code}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: int,
        properties: Any = None,
    ) -> None:
        """Callback when disconnected from broker."""
        self._connected = False
        logger.debug("MQTT disconnected")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Callback when message received."""
        try:
            payload = json.loads(message.payload.decode())
            logger.debug(f"Received MQTT message on {message.topic}: {payload}")

            # Parse health event
            event = HealthEvent(
                asset_id=payload.get("asset_id", ""),
                health_index=payload.get("health_index", 100),
                timestamp=datetime.fromisoformat(
                    payload.get("timestamp", datetime.now(UTC).isoformat())
                ),
            )

            # Invoke callback in event loop
            if self._on_health_event and self._loop:
                coro = cast(Coroutine[Any, Any, None], self._on_health_event(event))
                asyncio.run_coroutine_threadsafe(coro, self._loop)

        except Exception as e:
            logger.error(f"Failed to process MQTT message: {e}")
