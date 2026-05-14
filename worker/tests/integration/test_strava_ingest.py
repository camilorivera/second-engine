"""
Integration tests for Strava ingest.
Require a live Postgres instance at DATABASE_URL.
Run via: docker compose run --rm worker pytest tests/integration -v
"""
import pytest


@pytest.mark.integration
def test_placeholder():
    """Phase 2: implement with mocked Strava API responses + real DB assertions."""
    pass
