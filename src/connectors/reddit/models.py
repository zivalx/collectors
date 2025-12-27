"""Pydantic models for Reddit connector."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from connectors.common.config import BaseClientConfig, BaseCollectSpec


class RedditClientConfig(BaseClientConfig):
    """Reddit API credentials and client settings.

    Contains only credentials and HTTP settings.
    Does NOT contain subreddit lists (those go in CollectSpec).
    """
    client_id: str = Field(..., description="Reddit API client ID")
    client_secret: str = Field(..., description="Reddit API client secret")
    user_agent: str = Field(..., description="User agent string for Reddit API")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit: Optional[int] = Field(
        default=60,
        description="Requests per minute (default 60)"
    )


class RedditCollectSpec(BaseCollectSpec):
    """Specification for Reddit data collection (runtime input).

    Describes WHAT to collect on each run.
    Passed as argument to collector.fetch().
    """
    subreddits: List[str] = Field(
        ...,
        min_length=1,
        description="List of subreddit names (without r/ prefix)"
    )
    sort: str = Field(
        default="hot",
        description="Sort method: hot, new, top, rising"
    )
    time_filter: str = Field(
        default="day",
        description="Time filter for 'top' sort: hour, day, week, month, year, all"
    )
    max_posts_per_subreddit: int = Field(
        default=20,
        ge=1,
        description="Maximum posts to fetch per subreddit (PRAW handles pagination automatically)"
    )
    include_comments: bool = Field(
        default=True,
        description="Whether to fetch comments for each post"
    )
    max_comment_depth: Optional[int] = Field(
        default=None,
        description="Maximum comment nesting depth (None = unlimited)"
    )
    skip_stickied: bool = Field(
        default=False,
        description="Skip pinned/stickied posts (moderator announcements)"
    )

    @field_validator('subreddits')
    @classmethod
    def strip_r_prefix(cls, v: List[str]) -> List[str]:
        """Remove 'r/' prefix if present."""
        return [sub.removeprefix('r/').removeprefix('/') for sub in v]


class RedditPost(BaseModel):
    """Reddit post data model.

    Represents a single Reddit submission with optional comments.
    """
    id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Post title")
    text: str = Field(default="", description="Post selftext/body")
    author: Optional[str] = Field(default=None, description="Post author username")
    created_at: datetime = Field(..., description="Post creation timestamp")
    num_comments: int = Field(default=0, description="Number of comments")
    score: int = Field(default=0, description="Post score (upvotes - downvotes)")
    url: str = Field(..., description="Reddit permalink URL")
    subreddit: str = Field(..., description="Subreddit name")
    stickied: bool = Field(default=False, description="Whether post is pinned/stickied")
    comments: List[str] = Field(
        default_factory=list,
        description="List of comment texts (if include_comments=True)"
    )

    class Config:
        frozen = False
