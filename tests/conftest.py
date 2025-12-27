"""Shared pytest fixtures for all connector tests."""

import os
import pytest
from typing import Optional


def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Get environment variable or skip test if not set."""
    value = os.environ.get(key, default)
    if not value or value.startswith("your_"):
        pytest.skip(f"Skipping test: {key} not set in environment")
    return value


@pytest.fixture
def reddit_client_id() -> str:
    """Reddit client ID from environment."""
    return get_env_var("REDDIT_CLIENT_ID")


@pytest.fixture
def reddit_client_secret() -> str:
    """Reddit client secret from environment."""
    return get_env_var("REDDIT_CLIENT_SECRET")


@pytest.fixture
def telegram_api_id() -> str:
    """Telegram API ID from environment."""
    return get_env_var("TELEGRAM_API_ID")


@pytest.fixture
def telegram_api_hash() -> str:
    """Telegram API hash from environment."""
    return get_env_var("TELEGRAM_API_HASH")


@pytest.fixture
def telegram_phone() -> str:
    """Telegram phone number from environment."""
    return get_env_var("TELEGRAM_PHONE")


@pytest.fixture
def telegram_2fa_password() -> Optional[str]:
    """Telegram 2FA password from environment (optional)."""
    return os.environ.get("TELEGRAM_2FA_PASSWORD")


@pytest.fixture
def twitter_bearer_token() -> str:
    """Twitter bearer token from environment."""
    return get_env_var("TWITTER_BEARER_TOKEN")


@pytest.fixture
def gnews_api_key() -> str:
    """GNews API key from environment."""
    return get_env_var("GNEWS_API_KEY")


@pytest.fixture
def has_all_credentials() -> bool:
    """Check if all credentials are available."""
    required_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_PHONE",
        "TWITTER_BEARER_TOKEN",
    ]

    for var in required_vars:
        value = os.environ.get(var)
        if not value or value.startswith("your_"):
            return False

    return True


@pytest.fixture
def skip_if_no_credentials(has_all_credentials):
    """Skip test if not all credentials are available."""
    if not has_all_credentials:
        pytest.skip("Skipping integration test: Not all credentials are set")
