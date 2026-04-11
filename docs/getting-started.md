# Getting started

## Create a bot application

1. Create an application in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Under **Bot**, copy the token and enable any intents you need (e.g. "Server Members Intent" for `member_join` events).
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, then invite the bot to your server.

## Installation

```bash
git clone https://github.com/rolling-codes/EasyCord.git
cd EasyCord
pip install -e .
```

## Running a bot

Set your token via environment variable:

```bash
DISCORD_TOKEN=your_token_here python my_bot.py
```

## Minimal bot

**discord.py** — set up a client subclass, build a command tree, sync in `setup_hook`.

```python
import discord
from discord import app_commands

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.tree.command(name="ping", description="Ping the bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

client.run("TOKEN")
```

**EasyCord** — `Bot` handles the tree, sync, and interaction wrapping for you.

```python
import os
from easycord import Bot

bot = Bot()

@bot.slash(description="Ping the bot")
async def ping(ctx):
    await ctx.respond("Pong!")

bot.run(os.environ["DISCORD_TOKEN"])
```

## Adding middleware and plugins

**discord.py** — no built-in middleware concept. You implement cross-cutting concerns (logging, rate limits, error handling) inside each command or via `Cog` check methods.

**EasyCord** — register middleware once, it runs for every slash command automatically.

```python
from easycord import Bot, Composer
from easycord.middleware import log_middleware, catch_errors, rate_limit

# Option A: imperative
bot = Bot()
bot.use(log_middleware())
bot.use(catch_errors())
bot.use(rate_limit(limit=5, window=10))
bot.add_plugin(MyPlugin())

# Option B: fluent builder
bot = (
    Composer()
    .log()
    .catch_errors()
    .rate_limit(limit=5, window=10)
    .add_plugin(MyPlugin())
    .build()
)

bot.run(os.environ["DISCORD_TOKEN"])
```

## Project layout (recommended)

```
my_bot/
├── easycord/            # EasyCord framework source
├── plugins/
│   ├── fun.py
│   └── moderation.py
├── main.py
└── pyproject.toml
```

In `main.py`:

```python
import os
from easycord import Bot
from plugins.fun import FunPlugin
from plugins.moderation import ModerationPlugin

bot = Bot()
bot.add_plugin(FunPlugin())
bot.add_plugin(ModerationPlugin())
bot.run(os.environ["DISCORD_TOKEN"])
```

## Command syncing

By default, `Bot(auto_sync=True)` syncs the global slash command tree in `setup_hook`.

- **Global commands** can take up to ~1 hour to appear in Discord.
- During development, use `guild_id=YOUR_SERVER_ID` for instant updates:

```python
@bot.slash(description="Dev-only test", guild_id=123456789012345678)
async def test(ctx):
    await ctx.respond("Instant in this guild.")
```

## Logging

`Bot.run()` configures basic logging and delegates to `discord.Client.run()`. Configure logging yourself before calling `run()` if you want custom formatting or handlers.
