from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Awaitable, Callable

import discord
from discord import app_commands

from .context import Context
from .middleware import MiddlewareFn
from .plugin import Plugin

logger = logging.getLogger("easycord")


def _wrap(
    mw: MiddlewareFn,
    ctx: Context,
    proceed: Callable[[], Awaitable[None]],
) -> Callable[[], Awaitable[None]]:
    """Bind a middleware function to a context and its inner next-step."""
    async def step() -> None:
        await mw(ctx, proceed)
    return step


def _build_chain(
    ctx: Context,
    invoke: Callable[[], Awaitable[None]],
    middleware: list[MiddlewareFn],
) -> Callable[[], Awaitable[None]]:
    """Wrap invoke in the full middleware stack, outermost first."""
    chain = invoke
    for mw in reversed(middleware):
        chain = _wrap(mw, ctx, chain)
    return chain


class Bot(discord.Client):
    """
    A discord.Client subclass with slash commands, middleware, events, and plugins.

    Parameters
    ----------
    intents:
        Passed to ``discord.Client``. Defaults to ``discord.Intents.default()``.
    auto_sync:
        If ``True`` (default), slash commands are synced with Discord on startup.
    """

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        auto_sync: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.default(), **kwargs)
        self.tree = app_commands.CommandTree(self)
        self._auto_sync = auto_sync
        self._middleware: list[MiddlewareFn] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._plugins: list[Plugin] = []

    # ── Lifecycle ─────────────────────────────────────────────

    async def setup_hook(self) -> None:
        if self._auto_sync:
            await self.tree.sync()
        for plugin in self._plugins:
            await plugin.on_load()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    def dispatch(self, event: str, /, *args, **kwargs) -> None:
        super().dispatch(event, *args, **kwargs)
        for handler in self._event_handlers.get(event, []):
            asyncio.create_task(handler(*args, **kwargs))

    # ── Slash commands ────────────────────────────────────────

    def slash(
        self,
        name: str | None = None,
        *,
        description: str = "No description provided.",
        guild_id: int | None = None,
    ) -> Callable:
        """Decorator that registers a top-level slash command."""

        def decorator(func: Callable) -> Callable:
            self._register_slash(
                func,
                name=name or func.__name__,
                description=description,
                guild_id=guild_id,
            )
            return func

        return decorator

    def _register_slash(
        self,
        func: Callable,
        *,
        name: str,
        description: str,
        guild_id: int | None,
    ) -> None:
        """Register a callable as a slash command in the app-command tree."""
        guild = discord.Object(id=guild_id) if guild_id else None
        sig = inspect.signature(func)
        user_params = list(sig.parameters.values())[1:]  # skip ctx

        async def callback(interaction: discord.Interaction, **kwargs) -> None:
            ctx = Context(interaction)

            async def invoke() -> None:
                await func(ctx, **kwargs)

            await _build_chain(ctx, invoke, self._middleware)()

        interaction_param = inspect.Parameter(
            "interaction",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=discord.Interaction,
        )
        callback.__signature__ = sig.replace(
            parameters=[interaction_param] + user_params
        )
        self.tree.add_command(
            app_commands.Command(name=name, description=description, callback=callback),
            guild=guild,
        )

    # ── Events ────────────────────────────────────────────────

    def on(self, event: str) -> Callable:  # type: ignore[override]
        """Decorator that registers an event listener (no ``on_`` prefix)."""

        def decorator(func: Callable) -> Callable:
            self._event_handlers.setdefault(event, []).append(func)
            return func

        return decorator

    # ── Middleware ────────────────────────────────────────────

    def use(self, middleware: MiddlewareFn) -> MiddlewareFn:
        """Register a middleware function. Runs for all slash commands."""
        self._middleware.append(middleware)
        return middleware

    # ── Plugins ───────────────────────────────────────────────

    def add_plugin(self, plugin: Plugin) -> None:
        """Add a plugin, registering its slash commands and event handlers."""
        plugin._bot = self
        self._plugins.append(plugin)

        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_is_slash", False):
                self._register_slash(
                    method,
                    name=method._slash_name,
                    description=method._slash_desc,
                    guild_id=method._slash_guild,
                )
            if getattr(method, "_is_event", False):
                self._event_handlers.setdefault(method._event_name, []).append(method)

        if self.is_ready():
            asyncio.create_task(plugin.on_load())

    async def remove_plugin(self, plugin: Plugin) -> None:
        """Remove a plugin, deregistering its commands and event handlers."""
        if plugin not in self._plugins:
            raise ValueError("Plugin is not loaded.")

        self._plugins.remove(plugin)

        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_is_slash", False):
                guild = discord.Object(id=method._slash_guild) if method._slash_guild else None
                try:
                    self.tree.remove_command(method._slash_name, guild=guild)
                except Exception:
                    logger.debug("Could not remove command %r during unload", method._slash_name)

            if getattr(method, "_is_event", False):
                try:
                    self._event_handlers[method._event_name].remove(method)
                except (KeyError, ValueError):
                    pass

        await plugin.on_unload()

    # ── Run ───────────────────────────────────────────────────

    def run(self, token: str, **kwargs) -> None:  # type: ignore[override]
        """Configure basic logging and start the bot."""
        logging.basicConfig(level=logging.INFO)
        super().run(token, **kwargs)
