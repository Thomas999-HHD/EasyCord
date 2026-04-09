from __future__ import annotations

from typing import Callable


def slash(
    name: str | None = None,
    *,
    description: str = "No description provided.",
    guild_id: int | None = None,
) -> Callable:
    """Mark a Plugin method as a slash command.

    Usage::

        class MyPlugin(Plugin):
            @slash(description="Say hello")
            async def hello(self, ctx, name: str): ...
    """

    def decorator(func: Callable) -> Callable:
        func._easycord_slash = True
        func._easycord_slash_name = name or func.__name__
        func._easycord_slash_description = description
        func._easycord_slash_guild_id = guild_id
        return func

    return decorator


def on(event: str) -> Callable:
    """Mark a Plugin method as an event handler.

    Usage::

        class MyPlugin(Plugin):
            @on("member_join")
            async def welcome(self, member): ...
    """

    def decorator(func: Callable) -> Callable:
        func._easycord_event = True
        func._easycord_event_name = event
        return func

    return decorator
