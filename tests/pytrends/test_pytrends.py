"""Tests for Google Trends connector."""

import pytest
from datetime import datetime
from connectors.pytrends import (
    PyTrendsCollector,
    PyTrendsClientConfig,
    PyTrendsCollectSpec,
    PyTrendsResult,
    TrendData,
)


class TestPyTrendsClientConfig:
    """Test Google Trends client configuration."""

    def test_valid_config(self):
        """Test creating valid PyTrends client config."""
        config = PyTrendsClientConfig(
            timeout=30,
            retries=3,
            backoff_factor=0.5,
        )
        assert config.timeout == 30
        assert config.retries == 3
        assert config.backoff_factor == 0.5

    def test_defaults(self):
        """Test default configuration values."""
        config = PyTrendsClientConfig()
        assert config.timeout == 30
        assert config.retries == 3
        assert config.backoff_factor == 0.5


class TestPyTrendsCollectSpec:
    """Test Google Trends collection specification."""

    def test_valid_spec(self):
        """Test creating valid collect spec."""
        spec = PyTrendsCollectSpec(
            keywords=["bitcoin", "ethereum"],
            timeframe="today 3-m",
            geo="US",
        )
        assert spec.keywords == ["bitcoin", "ethereum"]
        assert spec.timeframe == "today 3-m"
        assert spec.geo == "US"

    def test_defaults(self):
        """Test default values."""
        spec = PyTrendsCollectSpec(keywords=["bitcoin"])
        assert spec.timeframe == "today 3-m"
        assert spec.geo == ""
        assert spec.category == 0
        assert spec.include_related_queries is True
        assert spec.include_interest_by_region is False

    def test_max_keywords(self):
        """Test that maximum 5 keywords are enforced."""
        with pytest.raises(ValueError):
            PyTrendsCollectSpec(
                keywords=["a", "b", "c", "d", "e", "f"]  # 6 keywords
            )

    def test_min_keywords(self):
        """Test that at least 1 keyword is required."""
        with pytest.raises(ValueError):
            PyTrendsCollectSpec(keywords=[])


@pytest.mark.asyncio
class TestPyTrendsCollector:
    """Test Google Trends collector (integration tests with real API)."""

    async def test_fetch_interest_over_time(self):
        """Test fetching interest over time data."""
        config = PyTrendsClientConfig()
        spec = PyTrendsCollectSpec(
            keywords=["python"],
            timeframe="today 1-m",  # Last month
            geo="",  # Worldwide
            include_related_queries=False,
            include_interest_by_region=False,
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert result.keywords == ["python"]
        assert result.timeframe == "today 1-m"
        assert len(result.interest_over_time) > 0

        # Check trend data structure
        for trend in result.interest_over_time:
            assert isinstance(trend, TrendData)
            assert trend.keyword == "python"
            assert isinstance(trend.date, datetime)
            assert isinstance(trend.interest, int)
            assert 0 <= trend.interest <= 100

    async def test_fetch_multiple_keywords(self):
        """Test fetching data for multiple keywords."""
        config = PyTrendsClientConfig()
        spec = PyTrendsCollectSpec(
            keywords=["bitcoin", "ethereum"],
            timeframe="today 1-m",
            geo="US",
            include_related_queries=False,
            include_interest_by_region=False,
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert len(result.keywords) == 2

        # Check we have data for both keywords
        keywords_in_data = {trend.keyword for trend in result.interest_over_time}
        assert "bitcoin" in keywords_in_data
        assert "ethereum" in keywords_in_data

    async def test_fetch_with_related_queries(self):
        """Test fetching related queries."""
        config = PyTrendsClientConfig()
        spec = PyTrendsCollectSpec(
            keywords=["python"],
            timeframe="today 1-m",
            geo="",
            include_related_queries=True,
            include_interest_by_region=False,
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        # Related queries may or may not be present depending on Google's data
        # Just check the structure exists
        assert isinstance(result.related_queries_top, dict)
        assert isinstance(result.related_queries_rising, dict)

    async def test_fetch_with_regional_data(self):
        """Test fetching interest by region."""
        config = PyTrendsClientConfig()
        spec = PyTrendsCollectSpec(
            keywords=["python"],
            timeframe="today 3-m",
            geo="US",  # US regions
            include_related_queries=False,
            include_interest_by_region=True,
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        # Regional data may or may not be present
        assert isinstance(result.interest_by_region, dict)

    async def test_fetch_with_custom_timeframe(self):
        """Test different timeframes."""
        config = PyTrendsClientConfig()

        # Test 'today 12-m' (past year)
        spec = PyTrendsCollectSpec(
            keywords=["crypto"],
            timeframe="today 12-m",
            include_related_queries=False,
            include_interest_by_region=False,
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        assert result.status == "success"
        assert result.timeframe == "today 12-m"
        assert len(result.interest_over_time) > 0

    async def test_error_handling(self):
        """Test error handling with invalid keywords."""
        config = PyTrendsClientConfig(timeout=5)

        # Use very long keyword that might cause issues
        spec = PyTrendsCollectSpec(
            keywords=["x" * 1000],  # Extremely long keyword
            timeframe="today 1-m",
        )

        collector = PyTrendsCollector(config)
        result = await collector.fetch(spec)

        # Should either succeed or fail gracefully
        assert result.status in ["success", "failed"]
        if result.status == "failed":
            assert result.error is not None
            assert len(result.error) > 0
