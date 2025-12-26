"""HTTP utilities for retry logic and rate limiting."""

import asyncio
import time
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx


def with_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10
):
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Example:
        @with_retry(max_attempts=5)
        async def fetch_data():
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError))
    )


class RateLimiter:
    """Token bucket rate limiter for API calls.

    Ensures requests don't exceed a specified rate limit.

    Example:
        limiter = RateLimiter(requests_per_minute=60)
        async with limiter:
            # Make API call
            await client.fetch()
    """

    def __init__(self, requests_per_minute: int):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.rate = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request.

        Blocks if rate limit would be exceeded.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update

            # Replenish tokens based on time elapsed
            self.tokens = min(
                self.rate,
                self.tokens + elapsed * (self.rate / 60)
            )
            self.last_update = now

            # If not enough tokens, wait until we have one
            if self.tokens < 1:
                sleep_time = (1 - self.tokens) * (60 / self.rate)
                await asyncio.sleep(sleep_time)
                self.tokens = 0
            else:
                self.tokens -= 1

    async def __aenter__(self):
        """Context manager entry - acquire a token."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
