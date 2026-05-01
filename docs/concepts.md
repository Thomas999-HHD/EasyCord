# Concepts

## Slash commands

### discord.py way

Registering a slash command in raw discord.py requires a `CommandTree`, working directly with `discord.Interaction`, and manually syncing in `setup_hook`:

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

@client.tree.command(name="hello", description="Say hello to someone")
@app_commands.describe(name="Who to greet", loud="Shout it?")
async def hello(interaction: discord.Interaction, name: str, loud: bool = False):
    msg = f"Hello, {name}!"
    await interaction.response.send_message(msg.upper() if loud else msg)
```

### Framework way

Parameters become Discord options from type annotations automatically. No tree, no interaction, no manual sync.

```python
@bot.slash(description="Say hello to someone")
async def hello(ctx, name: str, loud: bool = False):
    msg = f"Hello, {name}!"
    await ctx.respond(msg.upper() if loud else msg)
```

### How the framework maps to discord.py internally

The framework must register an `app_commands.Command` callback that receives a `discord.Interaction`. It wraps your handler to:

1. build a `Context(interaction)`
2. run the middleware chain
3. call your handler with `ctx` and the parsed options

### Signature rewriting

`discord.py` discovers slash options by inspecting the registered callback signature. The framework rewrites the internal callback's first parameter to `interaction: discord.Interaction` (what discord.py expects), then strips the leading `ctx` from your handler before forwarding remaining parameters.

- **Standalone handler**: `async def cmd(ctx, ...)`
- **Plugin handler**: `async def cmd(self, ctx, ...)`

---

## Permission checks

### discord.py way

You check permissions manually at the top of every command — 8–10 lines per command.

```python
@client.tree.command()
async def kick(interaction: discord.Interaction, member: discord.Member):
    if not interaction.guild:
        await interaction.response.send_message("Server only.", ephemeral=True)
        return
    m = interaction.guild.get_member(interaction.user.id)
    if not m or not m.guild_permissions.kick_members:
        await interaction.response.send_message("Missing permission.", ephemeral=True)
        return
    await member.kick()
    await interaction.response.send_message(f"Kicked {member.display_name}.")
```

### Framework way

Declare the required permissions on the decorator. The framework checks them before your handler runs and responds ephemerally with a clear error if any are missing.

```python
@bot.slash(description="Kick a member", permissions=["kick_members"])
async def kick(ctx, member: discord.Member):
    await member.kick()
    await ctx.respond(f"Kicked {member.display_name}.")
```

Any valid `discord.Permissions` attribute name works: `"ban_members"`, `"manage_guild"`, `"administrator"`, etc. Pass multiple in the list to require all of them.

---

## Per-command cooldowns

### discord.py way

You track per-user timestamps yourself in a module-level dict and check on every invocation.

```python
import time

_last_used: dict[int, float] = {}

@client.tree.command()
async def roll(interaction: discord.Interaction):
    now = time.monotonic()
    remaining = 5.0 - (now - _last_used.get(interaction.user.id, 0.0))
    if remaining > 0:
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {remaining:.1f}s.",
            ephemeral=True,
        )
        return
    _last_used[interaction.user.id] = now
    import random
    await interaction.response.send_message(str(random.randint(1, 6)))
```

### Framework way

One argument on the decorator. The dict and the time check are handled internally, per-command and per-user.

```python
@bot.slash(description="Roll dice", cooldown=5)
async def roll(ctx):
    import random
    await ctx.respond(str(random.randint(1, 6)))
```

---

## Events

`Bot.on("message")` registers a handler for that event name (without the `on_` prefix).

### discord.py way

Only one `on_message` can be defined per client. Subclassing is required to add multiple handlers cleanly.

```python
@client.event
async def on_message(message):
    ...  # only one allowed without extra wiring
```

### Framework way

Multiple handlers for the same event are all called. No subclassing needed.

```python
@bot.on("message")
async def log_message(message): ...

@bot.on("message")
async def filter_message(message): ...
```

The framework overrides `discord.Client.dispatch` and schedules each handler as an `asyncio.create_task`, so a failure in one handler doesn't block the others.

---

## Middleware

Middleware wraps **every slash command invocation** (not events).

```python
async def middleware(ctx, next):
    # runs before the command
    await next()
    # runs after
```

Middleware is registered with `bot.use(fn)` and executes in registration order. If middleware does not call `await next()`, the command handler never runs — this is how `guild_only()` and rate limiting work.

### Built-in middleware factories

| Factory | What it does |
|---|---|
| `log_middleware()` | Logs every invocation via `logging` |
| `catch_errors()` | Catches unhandled exceptions, sends ephemeral error response |
| `rate_limit(limit, window)` | Per-user sliding-window rate limit across all commands |
| `guild_only()` | Blocks invocations from DMs |

---

## Plugins

Plugins group related slash commands and event handlers into a class. Compare to discord.py `Cog`s, but without the `commands.Bot` dependency.

### discord.py way

```python
from discord.ext import commands

class FunCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Roll dice")
    async def roll(self, interaction: discord.Interaction):
        await interaction.response.send_message(str(random.randint(1, 6)))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await member.send("Welcome!")

async def setup(bot):
    await bot.add_cog(FunCog(bot))
```

### Framework way

```python
from easycord import Plugin, slash, on

class FunPlugin(Plugin):
    @slash(description="Roll dice")
    async def roll(self, ctx):
        await ctx.respond(str(random.randint(1, 6)))

    @on("member_join")
    async def welcome(self, member):
        await member.send("Welcome!")

bot.add_plugin(FunPlugin())
```

Use `rate_limit=(limit, window)` on `@slash` when a single command should have its own per-user cap, and `@on(..., on_cleanup=...)` when a handler needs teardown logic during plugin unload.

### Plugin lifecycle

- `add_plugin()`:
  - sets `plugin._bot = bot`
  - scans methods and registers slash commands + event handlers
  - if the bot is already ready, schedules `plugin.on_load()` as a task
- `setup_hook()`:
  - syncs commands (if `auto_sync=True`)
  - calls `on_load()` for plugins loaded before `run()`
- `remove_plugin()` (async):
  - removes the plugin's slash commands from the command tree
  - deregisters event handlers
  - awaits `plugin.on_unload()`

`Plugin.bot` raises `RuntimeError` if accessed before the plugin is added to a bot.
