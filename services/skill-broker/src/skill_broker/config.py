"""
Configuration settings for Skill-Broker service.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    # Service settings
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8002
    debug: bool = False

    # BaSyx endpoints
    aas_environment_url: str = "http://localhost:4001"

    # MQTT broker
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # Policy configuration
    policy_file: str = str(
        Path(__file__).parent.parent.parent / "policy" / "thresholds.yaml"
    )

    # Polling (fallback if MQTT unavailable)
    enable_polling: bool = False
    polling_interval_seconds: float = 2.0

    # Auth (OIDC)
    auth_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    auth_cache_ttl_seconds: int = 300

    model_config = {"env_prefix": "", "case_sensitive": False}
