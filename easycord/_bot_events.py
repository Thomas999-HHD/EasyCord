"""Event dispatch, middleware registration, and bot utility helpers."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Literal

import discord

from .middleware import MiddlewareFn

logger = logging.getLogger("easycord")


class _EventsMixin:
    """Mixin: event dispatch, middleware, presence, and lookup helpers."""

    # ── Events ────────────────────────────────────────────────

    def on(self, event: str) -> Callable:  # type: ignore[override]
        """Decorator that registers an event listener.

        Use the event name without the ``on_`` prefix::

            @bot.on("member_join")
            async def welcome(member):
                await member.send("Welcome!")
        """
        if not isinstance(event, str) or not event:
            raise ValueError("event name must be a non-empty string")

        def decorator(func: Callable) -> Callable:
            if not callable(func):
                raise TypeError(
                    f"event handler must be callable, got {type(func).__name__!r}"
                )
            self._event_handlers.setdefault(event, []).append(func)
            return func

        return decorator

    def dispatch(self, event: str, /, *args, **kwargs) -> None:
        super().dispatch(event, *args, **kwargs)
        for handler in list(self._event_handlers.get(event, [])):
            task = asyncio.create_task(handler(*args, **kwargs))
            task.add_done_callback(self._log_task_exception)

    def _log_task_exception(self, task: asyncio.Task) -> None:
        if not task.cancelled() and (exc := task.exception()):
            logger.exception("Unhandled error in event handler task", exc_info=exc)

    # ── Middleware ────────────────────────────────────────────

    def use(self, middleware: MiddlewareFn) -> MiddlewareFn:
        """Register a middleware function that runs before every slash command.

        Can be used as a decorator or called directly::

            @bot.use
            async def my_middleware(ctx, proceed):
                print("before")
                await proceed()
                print("after")
        """
        if not callable(middleware):
            raise TypeError(
                f"middleware must be callable, got {type(middleware).__name__!r}"
            )
        self._middleware.append(middleware)
        return middleware

    # ── User & member lookup ──────────────────────────────────

    async def fetch_member(self, guild_id: int, user_id: int) -> discord.Member:
        """Fetch a guild member by guild ID and user ID.

        Tries the cache first; falls back to an API call.
        Raises ``discord.NotFound`` if the user is not in the guild.
        """
        guild = self.get_guild(guild_id) or await super().fetch_guild(guild_id)
        return await guild.fetch_member(user_id)

    async def fetch_user(self, user_id: int) -> discord.User:
        """Fetch a Discord user by ID (not guild-specific).

        Checks the internal cache first; falls back to an API call.
        Raises ``discord.NotFound`` if no user with that ID exists.
        """
        return self.get_user(user_id) or await super().fetch_user(user_id)

    # ── Presence ──────────────────────────────────────────────

    async def set_status(
        self,
        status: Literal["online", "idle", "dnd", "invisible"] = "online",
        *,
        activity: str | None = None,
        activity_type: Literal["playing", "watching", "listening"] = "playing",
    ) -> None:
        """Set the bot's presence status and optional activity text."""
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        discord_status = status_map.get(status, discord.Status.online)
        discord_activity: discord.BaseActivity | None = None
        if activity is not None:
            if activity_type == "playing":
                discord_activity = discord.Game(activity)
            elif activity_type == "watching":
                discord_activity = discord.Activity(
                    type=discord.ActivityType.watching, name=activity
                )
            elif activity_type == "listening":
                discord_activity = discord.Activity(
                    type=discord.ActivityType.listening, name=activity
                )
            else:
                discord_activity = discord.Game(activity)
        await self.change_presence(status=discord_status, activity=discord_activity)
