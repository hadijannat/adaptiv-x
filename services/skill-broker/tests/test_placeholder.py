"""Placeholder tests for Skill Broker service."""


def test_health_check_exists() -> None:
    """Verify health check endpoint is defined."""
    from skill_broker.main import health_check

    assert health_check is not None
