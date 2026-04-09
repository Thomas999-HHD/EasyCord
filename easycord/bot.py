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


def _make_next(
    mw: MiddlewareFn,
    ctx: Context,
    inner: Callable[[], Awaitable[None]],
) -> Callable[[], Awaitable[None]]:
    async def _next() -> None:
        await mw(ctx, inner)

    return _next


def _build_chain(
    ctx: Context,
    invoke: Callable[[], Awaitable[None]],
    middleware: list[MiddlewareFn],
) -> Callable[[], Awaitable[None]]:
    chain = invoke
    for mw in reversed(middleware):
        chain = _make_next(mw, ctx, chain)
    return chain


class EasyCord(discord.Client):
    """
    A discord.Client subclass with slash commands, middleware, events, and plugins.

    Parameters
    ----------
    intents:
        Passed to ``discord.Client``. Defaults to ``discord.Intents.default()``.
    sync_commands:
        If ``True`` (default), ``setup_hook`` calls ``await tree.sync()``.
    """

    def __init__(
        self,
        *,
        intents: discord.Intents | None = None,
        sync_commands: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(intents=intents or discord.Intents.default(), **kwargs)
        self.tree = app_commands.CommandTree(self)
        self._sync_commands = sync_commands
        self._middleware: list[MiddlewareFn] = []
        self._event_handlers: dict[str, list[Callable]] = {}
        self._plugins: list[Plugin] = []

    # ── Lifecycle ─────────────────────────────────────────────

    async def setup_hook(self) -> None:
        if self._sync_commands:
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
        """Register any callable (top-level function or bound plugin method) as a slash command.

        For both cases the first parameter of *func* is ``ctx``; the remaining
        parameters are inferred by discord.py as slash-command options.
        """
        guild = discord.Object(id=guild_id) if guild_id else None
        sig = inspect.signature(func)
        user_params = list(sig.parameters.values())[1:]  # skip ctx
        middleware = self._middleware

        async def callback(interaction: discord.Interaction, **kwargs) -> None:
            ctx = Context(interaction)

            async def invoke() -> None:
                await func(ctx, **kwargs)

            await _build_chain(ctx, invoke, middleware)()

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

    def load_plugin(self, plugin: Plugin) -> None:
        """Load a plugin, registering its slash commands and event handlers."""
        plugin._bot = self
        self._plugins.append(plugin)

        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_easycord_slash", False):
                self._register_slash(
                    method,
                    name=method._easycord_slash_name,
                    description=method._easycord_slash_description,
                    guild_id=method._easycord_slash_guild_id,
                )
            if getattr(method, "_easycord_event", False):
                event: str = method._easycord_event_name
                self._event_handlers.setdefault(event, []).append(method)

        if self.is_ready():
            asyncio.create_task(plugin.on_load())

    async def unload_plugin(self, plugin: Plugin) -> None:
        """Unload a plugin, removing its commands and event handlers."""
        if plugin not in self._plugins:
            raise ValueError("Plugin is not loaded.")

        self._plugins.remove(plugin)

        for _, method in inspect.getmembers(plugin, predicate=inspect.ismethod):
            if getattr(method, "_easycord_slash", False):
                cmd_name: str = method._easycord_slash_name
                guild_id: int | None = method._easycord_slash_guild_id
                guild = discord.Object(id=guild_id) if guild_id else None
                try:
                    self.tree.remove_command(cmd_name, guild=guild)
                except Exception:
                    pass

            if getattr(method, "_easycord_event", False):
                event = method._easycord_event_name
                try:
                    self._event_handlers[event].remove(method)
                except (KeyError, ValueError):
                    pass

        await plugin.on_unload()

    # ── Run ───────────────────────────────────────────────────

    def run(self, token: str, **kwargs) -> None:  # type: ignore[override]
        """Configure basic logging and start the bot."""
        logging.basicConfig(level=logging.INFO)
        super().run(token, **kwargs)
