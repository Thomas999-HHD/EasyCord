"""
examples/plugin_bot.py
~~~~~~~~~~~~~~~~~~~~~~
Demonstrates the EasyCord plugin system.

Each ``Plugin`` subclass groups related commands and event handlers
into a self-contained, reloadable unit.

Run:
    DISCORD_TOKEN=<token> python examples/plugin_bot.py
"""

import os

from easycord import EasyCord
from easycord.middleware import (
    error_handler_middleware,
    logging_middleware,
    rate_limit_middleware,
)
from server_commands import FunPlugin, InfoPlugin, ModerationPlugin

bot = EasyCord()

bot.use(logging_middleware())
bot.use(error_handler_middleware())
bot.use(rate_limit_middleware(max_calls=5, window_seconds=10))

bot.load_plugin(FunPlugin())
bot.load_plugin(ModerationPlugin())
bot.load_plugin(InfoPlugin())

if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    bot.run(token)

