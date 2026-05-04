"""Tests for tool rate limiting."""
from datetime import datetime, timedelta

from easycord.tool_limits import RateLimit, ToolLimiter


def test_rate_limit_init():
    """RateLimit can be created with max_calls and window."""
    limit = RateLimit(max_calls=3, window_minutes=60)
    assert limit.max_calls == 3
    assert limit.window_minutes == 60


def test_tool_limiter_allows_within_limit():
    """Limiter allows calls within the limit."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=2, window_minutes=60)

    allowed, reason = limiter.check_limit(123, "ban_user", limit)
    assert allowed is True
    assert reason is None


def test_tool_limiter_blocks_over_limit():
    """Limiter blocks calls over the limit."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=2, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    limiter.check_limit(123, "ban_user", limit)
    allowed, reason = limiter.check_limit(123, "ban_user", limit)

    assert allowed is False
    assert "Rate limit exceeded" in reason


def test_tool_limiter_resets_after_window():
    """Limiter resets after time window expires."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=1, window_minutes=1)

    # Hit limit
    limiter.check_limit(123, "ban_user", limit)
    allowed, reason = limiter.check_limit(123, "ban_user", limit)
    assert allowed is False

    # Manually expire the entry
    key = (123, "ban_user")
    if key in limiter._usage:
        entry = limiter._usage[key]
        # Move timestamp back 2 minutes
        entry.timestamps = [
            ts - timedelta(minutes=2) for ts in entry.timestamps
        ]

    # Should allow again
    allowed, reason = limiter.check_limit(123, "ban_user", limit)
    assert allowed is True


def test_tool_limiter_per_user():
    """Different users have independent limits."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=1, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    limiter.check_limit(123, "ban_user", limit)
    allowed, reason = limiter.check_limit(123, "ban_user", limit)
    assert allowed is False

    # Different user should still be allowed
    allowed, reason = limiter.check_limit(456, "ban_user", limit)
    assert allowed is True


def test_tool_limiter_per_tool():
    """Different tools have independent limits."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=1, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    allowed, reason = limiter.check_limit(123, "ban_user", limit)
    assert allowed is False

    # Different tool should be allowed
    allowed, reason = limiter.check_limit(123, "kick_user", limit)
    assert allowed is True


def test_tool_limiter_reset_user():
    """reset_user clears all entries for a user."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=1, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    limiter.check_limit(123, "kick_user", limit)
    assert len(limiter._usage) == 2

    limiter.reset_user(123)
    assert len(limiter._usage) == 0


def test_tool_limiter_reset_tool():
    """reset_tool clears all entries for a tool."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=1, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    limiter.check_limit(456, "ban_user", limit)
    assert len(limiter._usage) == 2

    limiter.reset_tool("ban_user")
    assert len(limiter._usage) == 0


def test_tool_limiter_get_stats():
    """get_stats returns tracking info."""
    limiter = ToolLimiter()
    limit = RateLimit(max_calls=2, window_minutes=60)

    limiter.check_limit(123, "ban_user", limit)
    limiter.check_limit(456, "ban_user", limit)
    limiter.check_limit(123, "kick_user", limit)

    stats = limiter.get_stats()
    assert stats["tracked_limits"] == 3
    assert stats["total_calls"] == 3
