"""Configuration settings for Job-Dispatcher service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8003
    debug: bool = False

    aas_registry_url: str = "http://localhost:4000"
    aas_environment_url: str = "http://localhost:4001"
    submodel_registry_url: str = "http://localhost:4002"

    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # VDI/VDE 2193 bidding mode
    enable_bidding_mode: bool = True
    bid_timeout_seconds: float = 5.0

    model_config = {"env_prefix": "", "case_sensitive": False}
