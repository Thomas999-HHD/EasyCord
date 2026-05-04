from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot


class Plugin:
    """Base class for grouping related slash commands and event handlers.

    Subclass ``Plugin``, decorate methods with ``@slash`` and ``@on``, then
    add it to your bot with ``bot.add_plugin()``. Commands and handlers are
    registered automatically.

    Example::

        from easycord import Plugin, slash, on

        class GreetPlugin(Plugin):

            async def on_load(self):
                print(f"GreetPlugin ready on {self.bot.user}")

            @slash(description="Say hello to someone")
            async def hello(self, ctx, name: str):
                await ctx.respond(f"Hello, {name}!")

            @on("member_join")
            async def welcome(self, member):
                await member.send(f"Welcome to {member.guild.name}!")

        bot.add_plugin(GreetPlugin())

    Lifecycle contract
    ------------------
    The framework enforces the following ordering guarantee:

    1. ``bot.add_plugin(plugin)``
       - Scans methods and registers slash commands + event handlers
         (synchronously, before any async work).
       - Atomically: registry entry is created BEFORE the Discord tree is
         updated; if the tree rejects the command the registry rolls back.
       - ``plugin._bot`` is set before any lifecycle hook is called.

    2. ``on_load()``
       - Called once, after command registration, when the bot is ready
         (or immediately via ``asyncio.create_task`` if already running).
       - Safe to call ``self.bot``, open connections, query the DB, etc.
       - Commands are already registered in Discord at this point.

    3. ``on_ready()``
       - Called on every ``READY`` event (startup + each reconnect).
       - Idempotent setup belongs here; one-time setup belongs in ``on_load``.

    4. ``bot.remove_plugin(plugin)``
       - Commands are removed from Discord tree and registry atomically.
       - ``on_unload()`` is called last, after all deregistration is complete.
       - Background tasks (``@task``) are cancelled before ``on_unload``.

    Invariant: a command exists in ``bot.registry`` if and only if it is
    registered in the Discord command tree for that plugin.
    """

    def __init__(self) -> None:
        self._bot: Bot | None = None
        if not hasattr(self, "name"):
            self.name = self.__class__.__name__.lower()

    def id(self, raw: str) -> str:
        """Namespace a string with this plugin's name.

        Returns ``f"{self.name}:{raw}"``.
        """
        return f"{self.name}:{raw}"

    @property
    def bot(self) -> Bot:
        """The bot this plugin is attached to.

        Raises ``RuntimeError`` if accessed before the plugin is added to a bot.
        """
        if self._bot is None:
            raise RuntimeError(
                "Plugin has not been added to a bot yet. "
                "Call bot.add_plugin() before accessing self.bot."
            )
        return self._bot

    async def on_load(self) -> None:
        """Called once after the plugin is added and the bot is ready.

        Override this to run setup code (e.g. connecting to a database).
        """

    async def on_ready(self) -> None:
        """Called every time the bot becomes ready (after reconnects).

        Override this to run periodic setup code or check bot state.
        Called after on_load() on the first ready, then on every reconnect.
        """

    async def on_unload(self) -> None:
        """Called once when the plugin is removed with ``bot.remove_plugin()``.

        Override this to run teardown code (e.g. closing connections).
        """
