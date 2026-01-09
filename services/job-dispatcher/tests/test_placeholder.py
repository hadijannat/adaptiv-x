"""Placeholder tests for Job Dispatcher service."""


def test_health_check_exists() -> None:
    """Verify health check endpoint is defined."""
    from job_dispatcher.main import health_check

    assert health_check is not None
