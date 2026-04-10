from __future__ import annotations

import logging

import discord

from . import middleware as _mw
from .bot import EasyCord
from .middleware import MiddlewareFn
from .plugin import Plugin


class Composer:
    """Fluent builder for composing an EasyCord bot.

    Chain configuration methods and call :meth:`build` to produce a ready-to-run
    :class:`~easycord.EasyCord` instance.

    Example::

        from easycord import Composer
        from my_bot.plugins import ModerationPlugin, FunPlugin

        bot = (
            Composer()
            .intents(discord.Intents.default())
            .log()
            .catch_errors()
            .rate_limit(max_calls=5, window_seconds=10.0)
            .guild_only()
            .load_plugin(ModerationPlugin())
            .load_plugin(FunPlugin())
            .build()
        )

        bot.run("YOUR_TOKEN")
    """

    def __init__(self) -> None:
        self._intents: discord.Intents | None = None
        self._sync_commands: bool = True
        self._middleware: list[MiddlewareFn] = []
        self._plugins: list[Plugin] = []

    # ── Bot options ───────────────────────────────────────────

    def intents(self, intents: discord.Intents) -> Composer:
        """Set the Discord gateway intents."""
        self._intents = intents
        return self

    def sync_commands(self, enabled: bool = True) -> Composer:
        """Enable or disable automatic slash-command syncing on startup."""
        self._sync_commands = enabled
        return self

    # ── Built-in middleware ───────────────────────────────────

    def log(
        self,
        level: int = logging.INFO,
        fmt: str = "/{command} invoked by {user} in {guild}",
    ) -> Composer:
        """Add the built-in logging middleware."""
        self._middleware.append(_mw.log_middleware(level=level, fmt=fmt))
        return self

    def guild_only(self) -> Composer:
        """Add the built-in guild-only guard (blocks DM invocations)."""
        self._middleware.append(_mw.guild_only())
        return self

    def rate_limit(
        self,
        max_calls: int = 5,
        window_seconds: float = 10.0,
    ) -> Composer:
        """Add the built-in per-user sliding-window rate limiter."""
        self._middleware.append(_mw.rate_limit(max_calls, window_seconds))
        return self

    def catch_errors(
        self,
        message: str = "Something went wrong. Please try again.",
    ) -> Composer:
        """Add the built-in error-handler middleware."""
        self._middleware.append(_mw.catch_errors(message))
        return self

    # ── Custom middleware & plugins ───────────────────────────

    def use(self, middleware: MiddlewareFn) -> Composer:
        """Add a custom middleware function."""
        self._middleware.append(middleware)
        return self

    def load_plugin(self, plugin: Plugin) -> Composer:
        """Queue a plugin to be loaded into the bot."""
        self._plugins.append(plugin)
        return self

    # ── Build ─────────────────────────────────────────────────

    def build(self) -> EasyCord:
        """Construct and return the fully configured :class:`~easycord.EasyCord` bot."""
        bot = EasyCord(
            intents=self._intents,
            sync_commands=self._sync_commands,
        )
        for mw in self._middleware:
            bot.use(mw)
        for plugin in self._plugins:
            bot.load_plugin(plugin)
        return bot
