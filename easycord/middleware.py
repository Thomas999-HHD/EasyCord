from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Awaitable, Callable

from .context import Context

MiddlewareFn = Callable[[Context, Callable[[], Awaitable[None]]], Awaitable[None]]


def logging_middleware(
    level: int = logging.INFO,
    fmt: str = "/{command} invoked by {user} in {guild}",
) -> MiddlewareFn:
    """Log every slash command invocation."""
    logger = logging.getLogger("easycord")

    async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None:
        logger.log(
            level,
            fmt.format(
                command=ctx.command_name,
                user=ctx.user,
                guild=ctx.guild or "DM",
            ),
        )
        await next()

    return middleware


def guild_only_middleware() -> MiddlewareFn:
    """Block commands invoked outside of a guild (i.e. in DMs)."""

    async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None:
        if ctx.guild is None:
            await ctx.respond(
                "This command can only be used inside a server.", ephemeral=True
            )
            return
        await next()

    return middleware


def rate_limit_middleware(
    max_calls: int = 5,
    window_seconds: float = 10.0,
) -> MiddlewareFn:
    """Per-user sliding-window rate limiter."""
    _history: dict[int, list[float]] = defaultdict(list)

    async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None:
        uid = ctx.user.id
        now = time.monotonic()
        cutoff = now - window_seconds
        _history[uid] = [t for t in _history[uid] if t > cutoff]

        if len(_history[uid]) >= max_calls:
            wait = window_seconds - (now - _history[uid][0])
            await ctx.respond(
                f"⏳ You're being rate limited. Try again in {wait:.1f}s.",
                ephemeral=True,
            )
            return

        _history[uid].append(now)
        await next()

    return middleware


def error_handler_middleware(
    message: str = "💥 Something went wrong. Please try again.",
) -> MiddlewareFn:
    """Catch unhandled exceptions, log them, and send an ephemeral error reply."""
    logger = logging.getLogger("easycord")

    async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None:
        try:
            await next()
        except Exception as exc:
            logger.exception("Unhandled error in /%s: %s", ctx.command_name, exc)
            try:
                await ctx.respond(message, ephemeral=True)
            except Exception:
                pass

    return middleware
