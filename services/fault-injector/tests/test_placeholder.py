"""Placeholder tests for Fault Injector service."""


def test_health_check_exists() -> None:
    """Verify health check endpoint is defined."""
    from fault_injector.main import health_check

    assert health_check is not None
