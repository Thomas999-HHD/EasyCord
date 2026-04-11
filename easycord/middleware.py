"""Built-in middleware factories for EasyCord bots."""
from __future__ import annotations

import contextlib
import logging
import time
from collections import defaultdict
from typing import Awaitable, Callable

from .context import Context

MiddlewareFn = Callable[[Context, Callable[[], Awaitable[None]]], Awaitable[None]]


def log_middleware(
    level: int = logging.INFO,
    fmt: str = "/{command} invoked by {user} in {guild}",
) -> MiddlewareFn:
    """Log every slash command invocation."""
    logger = logging.getLogger("easycord")

    async def handler(ctx: Context, proceed: Callable[[], Awaitable[None]]) -> None:
        logger.log(
            level,
            fmt.format(
                command=ctx.command_name,
                user=ctx.user,
                guild=ctx.guild or "DM",
            ),
        )
        await proceed()

    return handler


def guild_only() -> MiddlewareFn:
    """Block commands invoked outside of a guild (i.e. in DMs)."""

    async def handler(ctx: Context, proceed: Callable[[], Awaitable[None]]) -> None:
        if ctx.guild is None:
            await ctx.respond(
                "This command can only be used inside a server.", ephemeral=True
            )
            return
        await proceed()

    return handler


def rate_limit(
    limit: int = 5,
    window: float = 10.0,
) -> MiddlewareFn:
    """Per-user sliding-window rate limiter."""
    if limit < 1:
        raise ValueError("rate_limit: limit must be at least 1")
    if window <= 0:
        raise ValueError("rate_limit: window must be greater than 0")
    _history: dict[int, list[float]] = defaultdict(list)

    async def handler(ctx: Context, proceed: Callable[[], Awaitable[None]]) -> None:
        uid = ctx.user.id
        now = time.monotonic()
        cutoff = now - window
        _history[uid] = [t for t in _history[uid] if t > cutoff]

        if len(_history[uid]) >= limit:
            wait = window - (now - _history[uid][0])
            await ctx.respond(
                f"You're being rate limited. Try again in {wait:.1f}s.",
                ephemeral=True,
            )
            return

        _history[uid].append(now)
        await proceed()

    return handler


def catch_errors(
    message: str = "Something went wrong. Please try again.",
) -> MiddlewareFn:
    """Catch unhandled exceptions, log them, and send an ephemeral error reply."""
    logger = logging.getLogger("easycord")

    async def handler(ctx: Context, proceed: Callable[[], Awaitable[None]]) -> None:
        try:
            await proceed()
        except Exception as exc:  # noqa: BLE001 — intentional broad catch for error handler
            logger.exception("Unhandled error in /%s: %s", ctx.command_name, exc)
            with contextlib.suppress(Exception):
                await ctx.respond(message, ephemeral=True)

    return handler
