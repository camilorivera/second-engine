import os
import pytest
from unittest.mock import MagicMock

# Ensure test env vars are set before any module import
os.environ.setdefault("DATABASE_URL", "postgresql://secondengine:changeme@localhost:5432/secondengine_test")
os.environ.setdefault("STRAVA_CLIENT_ID", "test_client_id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("STRAVA_REFRESH_TOKEN", "test_refresh_token")
os.environ.setdefault("WITHINGS_CLIENT_ID", "test_client_id")
os.environ.setdefault("WITHINGS_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("WITHINGS_REFRESH_TOKEN", "test_refresh_token")


@pytest.fixture
def mock_session():
    return MagicMock()
