"""
MQTT Client for Adaptiv-Monitor.

Publishes health events for downstream services like skill-broker.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any, cast

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """Async wrapper for Paho MQTT client."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "adaptiv-monitor",
    ) -> None:
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self._client: mqtt.Client | None = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> None:
        """Connect to the MQTT broker."""
        self._loop = asyncio.get_event_loop()
        self._client = mqtt.Client(client_id=self.client_id)

        # Set callbacks
        client_any = cast(Any, self._client)
        client_any.on_connect = self._on_connect
        client_any.on_disconnect = self._on_disconnect

        try:
            self._client.connect_async(self.broker_host, self.broker_port)
            self._client.loop_start()

            # Wait for connection with timeout
            for _ in range(50):  # 5 seconds timeout
                if self._connected:
                    logger.info(
                        "Connected to MQTT broker at %s:%s",
                        self.broker_host,
                        self.broker_port,
                    )
                    return
                await asyncio.sleep(0.1)

            logger.warning("MQTT connection timeout - continuing without MQTT")
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e} - continuing without MQTT")

    async def ensure_connected(self) -> None:
        """Ensure the client is connected (best-effort reconnect)."""
        if self._connected:
            return
        if not self._client:
            await self.connect()
            return

        try:
            self._client.connect_async(self.broker_host, self.broker_port)
            for _ in range(20):
                if self._connected:
                    return
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.debug("MQTT reconnect failed: %s", e)

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
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
        """Callback when connected to broker."""
        if reason_code == 0:
            self._connected = True
            logger.debug("MQTT connected successfully")
        else:
            logger.warning(f"MQTT connection failed with code: {reason_code}")

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

    async def publish_health_event(
        self,
        asset_id: str,
        health_index: int,
        health_confidence: float | None = None,
        anomaly_score: float | None = None,
        physics_residual: float | None = None,
    ) -> None:
        """
        Publish health update event.

        Topic: adaptivx/health/{asset_id}
        """
        await self.ensure_connected()
        if not self._connected or not self._client:
            logger.debug("MQTT not connected, skipping publish")
            return

        topic = f"adaptivx/health/{asset_id}"
        payload = json.dumps(
            {
                "asset_id": asset_id,
                "health_index": health_index,
                "health_confidence": health_confidence,
                "anomaly_score": anomaly_score,
                "physics_residual": physics_residual,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        try:
            result = self._client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published health event to {topic}")
            else:
                logger.warning(f"Failed to publish to {topic}: {result.rc}")
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")

    async def publish_anomaly_event(
        self,
        asset_id: str,
        anomaly_score: float,
        physics_residual: float,
    ) -> None:
        """Publish anomaly detection event."""
        await self.ensure_connected()
        if not self._connected or not self._client:
            return

        topic = f"adaptivx/anomaly/{asset_id}"
        payload = json.dumps(
            {
                "asset_id": asset_id,
                "anomaly_score": anomaly_score,
                "physics_residual": physics_residual,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        try:
            self._client.publish(topic, payload, qos=1)
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")
