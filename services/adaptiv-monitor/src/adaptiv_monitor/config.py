"""
Configuration settings for Adaptiv-Monitor service.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    # Service settings
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8011
    debug: bool = False
    app_env: str = "dev"

    # BaSyx endpoints
    aas_environment_url: str = "http://localhost:4001"
    aas_registry_url: str = "http://localhost:4000"
    submodel_registry_url: str = "http://localhost:4002"

    # MQTT broker
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # MinIO (for FMU storage)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket: str = "adaptivx-fmu"
    minio_secure: bool = False

    # ML Model settings
    anomaly_model_path: str | None = None
    anomaly_window_size: int = 200
    anomaly_min_samples: int = 20
    anomaly_zscore_threshold: float = 3.0
    anomaly_threshold_vib_rms: float = 3.0
    anomaly_threshold_factor: float = 2.0

    # Health fusion weights
    ml_weight: float = 0.6
    physics_weight: float = 0.4

    model_config = {"env_prefix": "", "case_sensitive": False}

    @model_validator(mode="after")
    def _validate_minio_credentials(self) -> "Settings":
        if self.app_env.lower() == "prod" and (
            not self.minio_access_key or not self.minio_secret_key
        ):
            raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set")
        return self
