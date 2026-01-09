"""
Configuration settings for Fault Injector service.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    # Service settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Upstream services
    monitor_url: str = "http://localhost:8011"
    broker_url: str = "http://localhost:8002"

    model_config = {"env_prefix": "", "case_sensitive": False}
