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

from easycord import Bot
from easycord.middleware import catch_errors, log_middleware, rate_limit
from server_commands import FunPlugin, InfoPlugin, ModerationPlugin

bot = Bot()

bot.use(log_middleware())
bot.use(catch_errors())
bot.use(rate_limit(limit=5, window=10))

bot.add_plugin(FunPlugin())
bot.add_plugin(ModerationPlugin())
bot.add_plugin(InfoPlugin())

if __name__ == "__main__":
    if not (token := os.environ.get("DISCORD_TOKEN")):
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    bot.run(token)
