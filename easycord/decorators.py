"""Decorators for marking Plugin methods as slash commands or event handlers."""
from __future__ import annotations

from typing import Callable


def slash(
    name: str | None = None,
    *,
    description: str = "No description provided.",
    guild_id: int | None = None,
    permissions: list[str] | None = None,
    cooldown: float | None = None,
) -> Callable:
    """Mark a Plugin method as a slash command.

    Parameters
    ----------
    name:
        The command name shown in Discord. Defaults to the method name.
    description:
        Short description shown in the Discord command picker.
    guild_id:
        Register to one specific server only (instant; global takes up to 1 hour).
    permissions:
        List of ``discord.Permissions`` attribute names required to run the command
        (e.g. ``["kick_members"]``). Responds ephemerally and skips the command if
        any are missing.
    cooldown:
        Per-user cooldown in seconds. Blocks the command ephemerally until the
        window expires.

    Example::

        class MyPlugin(Plugin):

            @slash(description="Kick a member", permissions=["kick_members"])
            async def kick(self, ctx, member: discord.Member):
                await member.kick()
                await ctx.respond(f"Kicked {member.display_name}.")

            @slash(description="Roll a dice", cooldown=5)
            async def roll(self, ctx, sides: int = 6):
                import random
                await ctx.respond(f"You rolled {random.randint(1, sides)}!")
    """

    def decorator(func: Callable) -> Callable:
        func._is_slash = True
        func._slash_name = name or func.__name__
        func._slash_desc = description
        func._slash_guild = guild_id
        func._slash_permissions = permissions
        func._slash_cooldown = cooldown
        return func

    return decorator


def on(event: str) -> Callable:
    """Mark a Plugin method as an event handler.

    Use the event name without the ``on_`` prefix. Any arguments that
    discord.py normally passes to ``on_<event>`` are forwarded to your method.

    Example::

        class MyPlugin(Plugin):

            @on("member_join")
            async def welcome(self, member):
                await member.send(f"Welcome to {member.guild.name}!")

            @on("message")
            async def echo(self, message):
                if "hello bot" in message.content.lower():
                    await message.reply("Hello!")
    """

    def decorator(func: Callable) -> Callable:
        func._is_event = True
        func._event_name = event
        return func

    return decorator
