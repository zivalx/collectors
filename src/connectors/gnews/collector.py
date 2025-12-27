"""High-level GNews API data collector."""

import asyncio
from typing import List
from datetime import datetime
import logging

from connectors.gnews.client import GNewsClient
from connectors.gnews.models import (
    GNewsClientConfig,
    GNewsCollectSpec,
    GNewsArticle,
    GNewsResult,
)

logger = logging.getLogger(__name__)


class GNewsCollector:
    """High-level GNews API data collector.

    Public API for collecting news articles according to a specification.

    Error handling strategy:
    - API failures return status='failed' with error message
    - Rate limit errors (100/day) are logged and returned with status='failed'
    - This ensures GNews API issues won't break calling applications
    """

    def __init__(self, config: GNewsClientConfig):
        """Initialize GNews collector.

        Args:
            config: GNews client configuration with API key
        """
        self.config = config

    async def fetch(self, spec: GNewsCollectSpec) -> GNewsResult:
        """Fetch news articles according to specification.

        Args:
            spec: Collection specification (query, language, filters, etc.)

        Returns:
            GNewsResult object with articles and status
            - status='success' if articles collected successfully
            - status='failed' if collection failed (logged, won't crash)

        Example:
            ```python
            config = GNewsClientConfig(api_key="your_api_key")
            spec = GNewsCollectSpec(
                query="bitcoin OR cryptocurrency",
                language="en",
                max_results=50
            )
            collector = GNewsCollector(config)
            result = await collector.fetch(spec)
            if result.status == "success":
                # Process articles
                for article in result.articles:
                    print(article.title)
            else:
                # Handle failure gracefully
                logger.warning(f"GNews failed: {result.error}")
            ```
        """
        result = GNewsResult(
            query=spec.query,
            language=spec.language,
            country=spec.country,
            category=spec.category,
            collected_at=datetime.now(),
        )

        try:
            logger.info(
                f"Fetching news articles for query: '{spec.query}' "
                f"(max: {spec.max_results})"
            )

            async with GNewsClient(self.config) as client:
                # Fetch articles
                data = await client.search(
                    q=spec.query,
                    lang=spec.language,
                    country=spec.country,
                    category=spec.category,
                    from_date=spec.from_date,
                    to_date=spec.to_date,
                    sortby=spec.sort_by,
                    max_results=spec.max_results,
                )

                # Process articles
                articles_data = data.get("articles", [])
                result.total_articles = len(articles_data)

                for article_data in articles_data:
                    try:
                        # Parse published date
                        published_at = datetime.fromisoformat(
                            article_data["publishedAt"].replace("Z", "+00:00")
                        )

                        # Build article object
                        article = GNewsArticle(
                            title=article_data["title"],
                            description=article_data.get("description", ""),
                            content=article_data.get("content", ""),
                            url=article_data["url"],
                            image=article_data.get("image"),
                            published_at=published_at,
                            source_name=article_data.get("source", {}).get(
                                "name", "Unknown"
                            ),
                            source_url=article_data.get("source", {}).get("url", ""),
                        )
                        result.articles.append(article)

                    except Exception as e:
                        logger.warning(
                            f"Error processing article '{article_data.get('title', 'unknown')}': {e}"
                        )
                        # Continue with other articles

                result.status = "success"
                logger.info(
                    f"Successfully collected {len(result.articles)} articles for query '{spec.query}'"
                )

        except Exception as e:
            # Handle all failures gracefully
            logger.error(f"Error collecting GNews articles: {e}")
            result.status = "failed"
            result.error = str(e)

        return result
