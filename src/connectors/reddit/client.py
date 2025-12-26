"""Low-level Reddit API client using asyncpraw."""

import asyncpraw
import asyncio
from typing import List, Optional
from datetime import datetime
import logging

from connectors.reddit.models import RedditClientConfig
from connectors.common.http import RateLimiter
from connectors.common.exceptions import AuthenticationError, DataFetchError

logger = logging.getLogger(__name__)


class RedditClient:
    """Low-level Reddit API client using asyncpraw.

    Handles connection lifecycle, rate limiting, and raw API calls.
    """

    def __init__(self, config: RedditClientConfig):
        """Initialize Reddit client.

        Args:
            config: Reddit client configuration with credentials
        """
        self.config = config
        self._reddit: Optional[asyncpraw.Reddit] = None
        self._rate_limiter = (
            RateLimiter(config.rate_limit) if config.rate_limit else None
        )

    async def __aenter__(self):
        """Async context manager entry - initialize Reddit client."""
        try:
            self._reddit = asyncpraw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                user_agent=self.config.user_agent,
            )
            logger.info("Reddit client initialized")
            return self
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Reddit client: {e}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup Reddit client."""
        if self._reddit:
            await self._reddit.close()
            logger.info("Reddit client closed")

    async def fetch_submissions(
        self,
        subreddit_name: str,
        sort: str = "hot",
        limit: int = 20,
        time_filter: str = "day"
    ) -> List:
        """Fetch submissions from a subreddit.

        Extracted from trender/app/services/reddit_collector.py lines 20-32.

        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            sort: Sort method (hot, new, top, rising)
            limit: Maximum submissions to fetch
            time_filter: Time filter for 'top' sort

        Returns:
            List of asyncpraw Submission objects

        Raises:
            DataFetchError: If fetching fails
        """
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        try:
            subreddit = await self._reddit.subreddit(subreddit_name)
            submissions = []

            # Select sort method
            if sort == "hot":
                async for submission in subreddit.hot(limit=limit):
                    submissions.append(submission)
            elif sort == "new":
                async for submission in subreddit.new(limit=limit):
                    submissions.append(submission)
            elif sort == "top":
                async for submission in subreddit.top(
                    time_filter=time_filter, limit=limit
                ):
                    submissions.append(submission)
            elif sort == "rising":
                async for submission in subreddit.rising(limit=limit):
                    submissions.append(submission)
            else:
                logger.warning(
                    f"Unknown sort method '{sort}', defaulting to 'hot'"
                )
                async for submission in subreddit.hot(limit=limit):
                    submissions.append(submission)

            logger.info(
                f"Fetched {len(submissions)} submissions from r/{subreddit_name}"
            )
            return submissions

        except Exception as e:
            raise DataFetchError(
                f"Error fetching from r/{subreddit_name}: {e}"
            )

    async def fetch_comments(self, submission) -> List[str]:
        """Fetch comments for a submission.

        Extracted from trender/app/services/reddit_collector.py lines 34-46.

        Args:
            submission: asyncpraw Submission object

        Returns:
            List of comment body texts
        """
        comments_list = []
        try:
            # Refresh submission to get comments
            submission = await self._reddit.submission(id=submission.id)

            # Expand all "MoreComments" objects
            await submission.comments.replace_more(limit=None)

            # Extract comment text
            for comment in submission.comments.list():
                if hasattr(comment, 'body'):
                    comments_list.append(comment.body)

            logger.debug(
                f"Fetched {len(comments_list)} comments for submission {submission.id}"
            )

        except Exception as e:
            logger.error(
                f"Error fetching comments for submission {submission.id}: {e}"
            )
            # Return empty list instead of failing - comments are optional

        return comments_list
