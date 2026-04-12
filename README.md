# EasyCord

EasyCord is a modern wrapper framework built on top of discord.py 2.x (not affiliated with other projects using the same name).

A developer-friendly Python framework for building Discord bots, built on top of [discord.py 2.x](https://discordpy.readthedocs.io/).

EasyCord keeps the full power of discord.py within reach while removing the boilerplate — decorators handle slash commands and events, a middleware chain wraps every command, and plugins let you organise code into clean, reusable modules.

---

## The Backstory

This project wasn't just a coding exercise — it was a solution to a real problem. I founded and managed the Senior IT Program Discord server for my school.

When you're running a live server for a class full of IT students, you need a bot that can scale *now*. I found myself spending too much time on "plumbing" — syncing slash commands, manually handling events, and writing the same permission checks over and over.

The fix: I decided to stop being just a user and started being an architect. EasyCord handles the heavy lifting automatically, so I could move from a "we need this feature" idea to a live, working tool without the usual Discord API headaches.

---

## Installation

Clone the repo, then install in editable mode (dependencies are declared in `pyproject.toml` and installed automatically):

```bash
git clone https://github.com/rolling-codes/EasyCord.git
cd EasyCord
pip install -e .
```

---

## Quick Start

```python
from easycord import Bot
from easycord.middleware import log_middleware

bot = Bot()
bot.use(log_middleware())

@bot.slash(description="Ping the bot")
async def ping(ctx):
    await ctx.respond("Pong!")

bot.run("YOUR_TOKEN")
```

Set your token via environment variable instead of hardcoding it:

```bash
DISCORD_TOKEN=your_token_here python my_bot.py
```

---

## Slash Commands

Register slash commands with `@bot.slash`. Parameters become Discord options automatically — just use type annotations.

```python
@bot.slash(description="Say hello to someone")
async def hello(ctx, name: str, loud: bool = False):
    msg = f"Hello, {name}!"
    await ctx.respond(msg.upper() if loud else msg)
```

### Guild-only commands (instant, great for testing)

```python
@bot.slash(description="Admin test", guild_id=123456789012345678)
async def test(ctx):
    await ctx.respond("This only shows up in one server.")
```

### Permission guards

Declare required permissions directly on the command — EasyCord checks them automatically and responds ephemerally if they're missing.

```python
@bot.slash(description="Kick a member", permissions=["kick_members"])
async def kick(ctx, member: discord.Member):
    await member.kick()
    await ctx.respond(f"Kicked {member.display_name}.")
```

### Per-command cooldowns

Rate-limit individual commands per user without any global middleware.

```python
@bot.slash(description="Roll dice", cooldown=5)
async def roll(ctx):
    import random
    await ctx.respond(str(random.randint(1, 6)))
```

### Static choices (fixed dropdown)

Lock a parameter to a predefined list. Discord renders it as a dropdown with no free-text entry.

```python
@bot.slash(description="Set alert level", choices={"level": ["low", "medium", "high"]})
async def alert(ctx, level: str):
    await ctx.respond(f"Alert level set to {level}.")
```

### Server management

```python
@bot.slash(description="Manage members", permissions=["manage_nicknames"])
async def manage(ctx, member: discord.Member):
    await ctx.set_nickname(member, "Verified")
    await ctx.add_role(member, MEMBER_ROLE_ID)

@bot.slash(description="Move to AFK", permissions=["move_members"])
async def afk(ctx, member: discord.Member):
    await ctx.move_member(member, AFK_CHANNEL_ID)

@bot.slash(description="Lock channel", permissions=["manage_channels"])
async def lock(ctx):
    await ctx.lock_channel(reason="Incident")
    await ctx.respond("Locked.", ephemeral=True)

@bot.slash(description="Set slowmode", permissions=["manage_channels"])
async def slow(ctx, seconds: int = 10):
    await ctx.slowmode(seconds)
    await ctx.respond(f"Slowmode: {seconds}s", ephemeral=True)
```

### Reactions

```python
messages = await ctx.fetch_messages(1)
await ctx.react(messages[0], "👍")
await ctx.unreact(messages[0], "👍")
await ctx.clear_reactions(messages[0])
await ctx.delete_message(messages[0], delay=5.0)
```

### Autocomplete

Attach suggestions to any string parameter. The callback receives what the user has typed so far and returns a list of strings.

```python
COLORS = ["red", "green", "blue", "orange", "purple"]

async def color_suggestions(current: str) -> list[str]:
    return [c for c in COLORS if current.lower() in c]

@bot.slash(description="Pick a color", autocomplete={"color": color_suggestions})
async def paint(ctx, color: str):
    await ctx.respond(f"Painting with {color}!")
```

### Bot presence

```python
await bot.set_status("idle", activity="Maintenance mode", activity_type="watching")
await bot.set_status("online", activity="your commands", activity_type="listening")
await bot.set_status("invisible")  # go dark
```

### Context helpers

```python
async def my_command(ctx, member: discord.Member):
    ctx.user          # discord.User / Member
    ctx.guild         # discord.Guild or None (DM)
    ctx.channel       # channel object
    ctx.command_name  # "my_command"

    # Responding
    await ctx.respond("plain text")
    await ctx.respond("hidden", ephemeral=True)
    await ctx.send_embed("Title", "Description", color=discord.Color.red())
    await ctx.send_embed("Stats", fields=[("Members", "150"), ("Online", "42")], footer="just now")
    await ctx.send_file("report.pdf", content="Here you go!")
    await ctx.defer()           # for slow operations — respond within 15 minutes
    await ctx.dm("Private!")    # slide into the user's DMs
    await ctx.send_to(CHANNEL_ID, "Cross-channel message")

    # Interactive UI
    result = await ctx.ask_form("Feedback", subject=dict(label="Subject"), body=dict(label="Body", style="paragraph"))
    confirmed = await ctx.confirm("Are you sure?", timeout=30)
    choice = await ctx.choose("Pick one", ["Option A", "Option B", "Option C"])
    await ctx.paginate(["Page 1", "Page 2", "Page 3"])

    # Moderation
    await ctx.kick(member, reason="Rule violation")
    await ctx.ban(member, reason="Spam", delete_message_days=1)
    await ctx.timeout(member, 300, reason="Cooldown")  # 5 minutes
    await ctx.unban(user)
    await ctx.add_role(member, VERIFIED_ROLE_ID)
    await ctx.remove_role(member, MUTED_ROLE_ID)

    # Channel utilities
    deleted = await ctx.purge(10)
    messages = await ctx.fetch_messages(5)
    thread = await ctx.create_thread("Support: my issue")
```

---

## Event Handling

```python
@bot.on("message")
async def handle_message(message):
    if "hello bot" in message.content.lower():
        await message.reply("Hey there!")

@bot.on("member_join")
async def welcome(member):
    await member.send(f"Welcome to {member.guild.name}!")
```

Multiple handlers for the same event are all called.

---

## Middleware

Middleware wraps every slash-command invocation. Register with `@bot.use` or `bot.use(fn)`.

```python
@bot.use
async def my_middleware(ctx, next):
    print(f"Before /{ctx.command_name}")
    await next()
    print("After")
```

Middleware is executed in the order it was registered.

### Built-in middleware

```python
from easycord.middleware import (
    log_middleware,   # log every invocation
    catch_errors,     # catch unhandled exceptions
    rate_limit,       # per-user rate limiting
    guild_only,       # block DM usage
)

bot.use(log_middleware())
bot.use(catch_errors(message="Something broke"))
bot.use(rate_limit(limit=5, window=10))
bot.use(guild_only())
```

---

## Plugins

Group related commands and handlers into self-contained classes.

```python
from easycord import Plugin, slash, on

class FunPlugin(Plugin):
    """Random fun commands."""

    async def on_load(self):
        print("FunPlugin ready!")

    @slash(description="Roll a dice")
    async def roll(self, ctx, sides: int = 6):
        import random
        await ctx.respond(f"You rolled {random.randint(1, sides)}")

    @on("member_join")
    async def welcome(self, member):
        await member.send("Welcome!")

bot.add_plugin(FunPlugin())
```

### Unloading plugins at runtime

```python
plugin = FunPlugin()
bot.add_plugin(plugin)
# later...
await bot.remove_plugin(plugin)  # calls plugin.on_unload()
```

---

## Composer

`Composer` is a fluent builder that chains everything together in one readable block — no separate `bot.use(...)` and `bot.add_plugin(...)` calls scattered around.

```python
from easycord import Composer
from my_bot.plugins import ModerationPlugin, FunPlugin

bot = (
    Composer()
    .log()
    .catch_errors()
    .rate_limit(limit=5, window=10.0)
    .guild_only()
    .add_plugin(ModerationPlugin())
    .add_plugin(FunPlugin())
    .build()
)

bot.run("YOUR_TOKEN")
```

---

## Per-Guild Config

Skip complex database setup. The built-in `ServerConfigStore` saves server-specific settings to simple JSON files under `.easycord/server-config/`.

```python
from easycord import ServerConfigStore

store = ServerConfigStore()

cfg = await store.load(guild_id)
cfg.set_role("moderator", 1234567890)
cfg.set_channel("logs", 9876543210)
cfg.set_other("prefix", "!")
await store.save(cfg)
```

---

## Expanding with AI

Inside the repo there is a file called `model.md` — a "Single-Source Context Map" designed for AI agents.

Feed an AI the contents of `README.md`, `model.md`, and the `docs/` folder, then prompt:

> "Using the EasyCord framework, write me a new Plugin that adds a [feature] feature."

Drop the resulting file into `server_commands/` and the bot is updated.

---

## Project Layout

```
easycord/               # framework package
├── __init__.py
├── bot.py
├── composer.py
├── context.py
├── decorators.py
├── middleware.py
├── plugin.py
└── server_config.py
server_commands/        # example bot plugins
├── fun.py
├── moderation.py
└── info.py
examples/
├── basic_bot.py
└── plugin_bot.py
docs/
model.md
pyproject.toml
```

---

## API Reference

### `Bot`

| Method | Description |
|---|---|
| `bot.slash(name, *, description, guild_id, permissions, cooldown, autocomplete, choices)` | Decorator — register a slash command |
| `bot.on(event)` | Decorator — register an event handler |
| `bot.use(middleware)` | Register a middleware function |
| `bot.add_plugin(plugin)` | Load a `Plugin` instance |
| `await bot.remove_plugin(plugin)` | Unload a plugin at runtime |
| `await bot.set_status(status, *, activity, activity_type)` | Set the bot's presence status and activity text |
| `await bot.fetch_member(guild_id, user_id)` | Fetch a `discord.Member` by guild + user ID |
| `bot.run(token)` | Start the bot |

### `Composer`

| Method | Description |
|---|---|
| `.intents(intents)` | Set Discord gateway intents |
| `.auto_sync(enabled)` | Enable or disable slash-command syncing on startup |
| `.log(level, fmt)` | Add logging middleware |
| `.catch_errors(message)` | Add error-handler middleware |
| `.rate_limit(limit, window)` | Add per-user rate-limit middleware |
| `.guild_only()` | Add guild-only guard middleware |
| `.use(middleware)` | Add a custom middleware function |
| `.add_plugin(plugin)` | Queue a plugin to be loaded |
| `.build()` | Return the fully configured `Bot` |

### `Context`

| Attribute / Method | Description |
|---|---|
| `ctx.user` | The invoking user |
| `ctx.guild` | Guild or `None` (DM) |
| `ctx.channel` | Channel |
| `ctx.command_name` | Slash command name |
| `await ctx.respond(...)` | Send a reply |
| `await ctx.defer(...)` | Acknowledge (15-min window) |
| `await ctx.send_embed(title, description, *, fields, footer, ...)` | Build and send an embed |
| `await ctx.send_file(path, *, filename, content, ephemeral)` | Send a file attachment |
| `await ctx.dm(content, ...)` | Send a DM to the invoking user |
| `await ctx.send_to(channel_id, content, ...)` | Send a message to any channel by ID |
| `await ctx.ask_form(title, **fields)` | Show a modal form; returns `dict` or `None` |
| `await ctx.confirm(prompt, ...)` | Yes/No buttons; returns `True`, `False`, or `None` |
| `await ctx.choose(prompt, options, ...)` | Select-menu; returns chosen string or `None` |
| `await ctx.paginate(pages, ...)` | Multi-page Prev/Next browsing |
| `await ctx.kick(member, *, reason)` | Kick a member |
| `await ctx.ban(member, *, reason, delete_message_days)` | Ban a member |
| `await ctx.timeout(member, duration, *, reason)` | Temporarily mute a member (seconds) |
| `await ctx.unban(user, *, reason)` | Unban a user |
| `await ctx.add_role(member, role_id, *, reason)` | Add a role to a member |
| `await ctx.remove_role(member, role_id, *, reason)` | Remove a role from a member |
| `await ctx.purge(limit)` | Bulk-delete messages; returns count |
| `await ctx.fetch_messages(limit)` | Return N most recent messages |
| `await ctx.create_thread(name, *, auto_archive_minutes, reason)` | Create a thread; returns `discord.Thread` |
| `await ctx.set_nickname(member, nickname, *, reason)` | Set or clear a member's server nickname |
| `await ctx.move_member(member, channel_id, *, reason)` | Move to a voice channel by ID, or disconnect (`None`) |
| `await ctx.create_role(name, *, color, hoist, mentionable, reason)` | Create a role; returns `discord.Role` |
| `await ctx.delete_role(role_id, *, reason)` | Delete a role by ID |
| `await ctx.slowmode(seconds, *, reason)` | Set channel slowmode (0 = off) |
| `await ctx.lock_channel(*, reason)` | Prevent @everyone from sending messages |
| `await ctx.unlock_channel(*, reason)` | Restore @everyone send permission |
| `await ctx.react(message, emoji)` | Add a reaction to a message |
| `await ctx.unreact(message, emoji)` | Remove the bot's own reaction |
| `await ctx.clear_reactions(message)` | Remove all reactions |
| `await ctx.delete_message(message, *, delay)` | Delete a message, optionally after a delay |

### `Plugin`

| Method | Description |
|---|---|
| `async on_load()` | Called when plugin is loaded |
| `async on_unload()` | Called when plugin is unloaded |
| `self.bot` | Back-reference to the `Bot` |

### `ServerConfig`

| Method | Description |
|---|---|
| `set_role(key, role_id)` | Store a role ID under a named key |
| `get_role(key)` | Retrieve a role ID, or `None` |
| `has_role(key)` | Return `True` if the key exists |
| `remove_role(key)` | Delete a role entry |
| `list_roles()` | Return a copy of all role entries |
| `clear_roles()` | Remove all role entries |
| `set_channel(key, channel_id)` | Store a channel ID under a named key |
| `get_channel(key)` | Retrieve a channel ID, or `None` |
| `has_channel(key)` | Return `True` if the key exists |
| `remove_channel(key)` | Delete a channel entry |
| `list_channels()` | Return a copy of all channel entries |
| `clear_channels()` | Remove all channel entries |
| `set_other(key, value)` | Store an arbitrary setting |
| `get_other(key, default)` | Retrieve a setting, or `default` |
| `has_other(key)` | Return `True` if the key exists |
| `remove_other(key)` | Delete a setting |
| `list_other()` | Return a copy of all other settings |
| `clear_other()` | Remove all other settings |
| `reset()` | Wipe all roles, channels, and other settings |
| `merge(other)` | Merge another `ServerConfig` in, overwriting on collision |
| `to_dict()` | Return a deep copy of the raw config data |

### `ServerConfigStore`

| Method | Description |
|---|---|
| `await store.load(guild_id)` | Load a guild's config; returns empty config if none exists |
| `await store.save(config)` | Atomically persist a guild's config to disk |
| `await store.delete(guild_id)` | Remove a guild's config file |
| `await store.exists(guild_id)` | Return `True` if a config file exists for the guild |

---

## Creating a Bot Application

1. Go to [discord.com/developers](https://discord.com/developers/applications) and create a new application.
2. Under **Bot**, enable the intents your bot needs (e.g. "Server Members Intent" for `member_join`).
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, then invite the bot to your server.
4. Copy the token and run:

```bash
DISCORD_TOKEN=your_token python my_bot.py
```

> **Global slash commands** can take up to 1 hour to appear in Discord.
> Use `guild_id=YOUR_SERVER_ID` while developing for instant updates.

---

Additional documentation lives in `docs/`:

- [`docs/index.md`](docs/index.md)
- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/concepts.md`](docs/concepts.md)
- [`docs/api.md`](docs/api.md)
- [`docs/examples.md`](docs/examples.md)
- [`docs/fork-and-expand.md`](docs/fork-and-expand.md)
