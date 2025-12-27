"""Tests for GNews API connector."""

import pytest
from datetime import datetime, timedelta
from connectors.gnews import (
    GNewsCollector,
    GNewsClientConfig,
    GNewsCollectSpec,
    GNewsArticle,
    GNewsResult,
)


class TestGNewsClientConfig:
    """Test GNews client configuration."""

    def test_valid_config(self, gnews_api_key):
        """Test creating valid GNews client config."""
        config = GNewsClientConfig(
            api_key=gnews_api_key,
            timeout=30,
        )
        assert config.api_key == gnews_api_key
        assert config.timeout == 30

    def test_custom_timeout(self, gnews_api_key):
        """Test custom timeout."""
        config = GNewsClientConfig(
            api_key=gnews_api_key,
            timeout=60,
        )
        assert config.timeout == 60


class TestGNewsCollectSpec:
    """Test GNews collection specification."""

    def test_valid_spec(self):
        """Test creating valid collect spec."""
        spec = GNewsCollectSpec(
            query="bitcoin",
            language="en",
            max_results=50,
        )
        assert spec.query == "bitcoin"
        assert spec.language == "en"
        assert spec.max_results == 50

    def test_defaults(self):
        """Test default values."""
        spec = GNewsCollectSpec(query="test")
        assert spec.language == "en"
        assert spec.country is None
        assert spec.category is None
        assert spec.sort_by == "publishedAt"
        assert spec.max_results == 10

    def test_validate_language(self):
        """Test language validation."""
        # Valid languages
        for lang in ["en", "es", "fr", "de"]:
            spec = GNewsCollectSpec(query="test", language=lang)
            assert spec.language == lang

        # Invalid language
        with pytest.raises(ValueError):
            GNewsCollectSpec(query="test", language="invalid")

    def test_validate_category(self):
        """Test category validation."""
        # Valid categories
        for category in ["technology", "business", "sports"]:
            spec = GNewsCollectSpec(query="test", category=category)
            assert spec.category == category

        # Invalid category
        with pytest.raises(ValueError):
            GNewsCollectSpec(query="test", category="invalid")

    def test_validate_sort_by(self):
        """Test sort_by validation."""
        # Valid values
        for sort_by in ["publishedAt", "relevance"]:
            spec = GNewsCollectSpec(query="test", sort_by=sort_by)
            assert spec.sort_by == sort_by

        # Invalid value
        with pytest.raises(ValueError):
            GNewsCollectSpec(query="test", sort_by="invalid")

    def test_max_results_constraints(self):
        """Test max_results constraints."""
        # Valid range
        spec = GNewsCollectSpec(query="test", max_results=50)
        assert spec.max_results == 50

        # Below minimum
        with pytest.raises(ValueError):
            GNewsCollectSpec(query="test", max_results=0)

        # Above maximum
        with pytest.raises(ValueError):
            GNewsCollectSpec(query="test", max_results=101)


@pytest.mark.asyncio
class TestGNewsCollector:
    """Test GNews collector (integration tests with real API)."""

    async def test_fetch_simple_query(self, gnews_api_key):
        """Test fetching articles with simple query."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="technology",
            language="en",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert len(result.articles) > 0
        assert len(result.articles) <= 5

        # Check article structure
        for article in result.articles:
            assert isinstance(article, GNewsArticle)
            assert article.title
            assert article.url
            assert article.source_name
            assert isinstance(article.published_at, datetime)

    async def test_fetch_with_boolean_operators(self, gnews_api_key):
        """Test fetching with boolean operators in query."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="bitcoin OR cryptocurrency",
            language="en",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert len(result.articles) > 0

    async def test_fetch_with_category(self, gnews_api_key):
        """Test fetching articles from specific category."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="latest news",
            language="en",
            category="technology",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert result.category == "technology"

    async def test_fetch_with_country(self, gnews_api_key):
        """Test fetching articles from specific country."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="news",
            language="en",
            country="us",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert result.country == "us"

    async def test_fetch_with_date_range(self, gnews_api_key):
        """Test fetching articles within date range."""
        config = GNewsClientConfig(api_key=gnews_api_key)

        # Last 7 days
        to_date = datetime.now()
        from_date = to_date - timedelta(days=7)

        spec = GNewsCollectSpec(
            query="technology",
            language="en",
            from_date=from_date,
            to_date=to_date,
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        if result.articles:
            for article in result.articles:
                # All articles should be within date range
                assert from_date <= article.published_at <= to_date

    async def test_sort_by_relevance(self, gnews_api_key):
        """Test sorting by relevance."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="artificial intelligence",
            language="en",
            sort_by="relevance",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert len(result.articles) > 0

    async def test_error_handling_invalid_key(self):
        """Test error handling with invalid API key."""
        config = GNewsClientConfig(api_key="invalid_key_12345")
        spec = GNewsCollectSpec(
            query="test",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        # Should fail gracefully
        assert result.status == "failed"
        assert result.error is not None
        assert "invalid" in result.error.lower() or "forbidden" in result.error.lower()

    async def test_metadata(self, gnews_api_key):
        """Test result metadata."""
        config = GNewsClientConfig(api_key=gnews_api_key)
        spec = GNewsCollectSpec(
            query="space exploration",
            language="en",
            category="science",
            max_results=5,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        # Check metadata is populated
        assert result.query == "space exploration"
        assert result.language == "en"
        assert result.category == "science"
        assert isinstance(result.collected_at, datetime)
        assert isinstance(result.total_articles, int)

    async def test_different_languages(self, gnews_api_key):
        """Test fetching articles in different languages."""
        config = GNewsClientConfig(api_key=gnews_api_key)

        # Test Spanish
        spec = GNewsCollectSpec(
            query="tecnología",
            language="es",
            max_results=3,
        )

        collector = GNewsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert result.language == "es"
