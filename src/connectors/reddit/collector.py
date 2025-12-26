"""High-level Reddit data collector."""

import asyncio
from typing import List
from datetime import datetime
import logging

from connectors.reddit.client import RedditClient
from connectors.reddit.models import (
    RedditClientConfig,
    RedditCollectSpec,
    RedditPost,
)

logger = logging.getLogger(__name__)


class RedditCollector:
    """High-level Reddit data collector.

    Public API for collecting Reddit data according to a specification.
    """

    def __init__(self, config: RedditClientConfig):
        """Initialize Reddit collector.

        Args:
            config: Reddit client configuration with credentials
        """
        self.config = config

    async def fetch(self, spec: RedditCollectSpec) -> List[RedditPost]:
        """Fetch Reddit posts according to specification.

        Extracted from trender/app/services/reddit_collector.py lines 48-73.

        Args:
            spec: Collection specification (subreddits, sort, filters, etc.)

        Returns:
            List of RedditPost objects with typed fields

        Example:
            ```python
            config = RedditClientConfig(
                client_id="...",
                client_secret="...",
                user_agent="MyApp/1.0"
            )
            spec = RedditCollectSpec(
                subreddits=["python", "programming"],
                sort="hot",
                max_posts_per_subreddit=50
            )
            collector = RedditCollector(config)
            posts = await collector.fetch(spec)
            ```
        """
        all_posts = []

        async with RedditClient(self.config) as client:
            for subreddit_name in spec.subreddits:
                logger.info(f"Fetching from r/{subreddit_name}")

                try:
                    # Fetch submissions
                    submissions = await client.fetch_submissions(
                        subreddit_name=subreddit_name,
                        sort=spec.sort,
                        limit=spec.max_posts_per_subreddit,
                        time_filter=spec.time_filter,
                    )

                    # Process each submission
                    for submission in submissions:
                        try:
                            # Skip stickied posts if requested
                            is_stickied = getattr(submission, 'stickied', False)
                            if spec.skip_stickied and is_stickied:
                                logger.debug(f"Skipping stickied post: {submission.id}")
                                continue

                            # Fetch comments if requested
                            comments = []
                            if spec.include_comments:
                                comments = await client.fetch_comments(submission)

                            # Build typed post object
                            post = RedditPost(
                                id=submission.id,
                                title=submission.title,
                                text=submission.selftext or "",
                                author=(
                                    submission.author.name
                                    if submission.author
                                    else None
                                ),
                                created_at=datetime.fromtimestamp(
                                    submission.created_utc
                                ),
                                num_comments=submission.num_comments,
                                score=submission.score,
                                url=f"https://reddit.com{submission.permalink}",
                                subreddit=subreddit_name,
                                stickied=is_stickied,
                                comments=comments,
                            )
                            all_posts.append(post)

                        except Exception as e:
                            logger.error(
                                f"Error processing submission {submission.id}: {e}"
                            )
                            # Continue with other submissions

                except Exception as e:
                    logger.error(f"Error processing r/{subreddit_name}: {e}")
                    # Continue with other subreddits

        logger.info(
            f"Collected {len(all_posts)} posts from {len(spec.subreddits)} subreddits"
        )
        return all_posts
