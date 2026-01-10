"""
Configuration settings for Fault Injector service.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration loaded from environment variables."""

    # Service settings
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000
    debug: bool = False

    # Upstream services
    monitor_url: str = "http://localhost:8011"
    broker_url: str = "http://localhost:8002"

    # Auth (OIDC)
    auth_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    auth_cache_ttl_seconds: int = 300

    model_config = {"env_prefix": "", "case_sensitive": False}
