# API reference

This reference is derived from the actual EasyCord source in this codebase.

## `easycord.EasyCord`

### Constructor

`EasyCord(*, intents: discord.Intents | None = None, sync_commands: bool = True, **kwargs)`

- **intents**: passed to `discord.Client`. Defaults to `discord.Intents.default()`.
- **sync_commands**: if true, `setup_hook()` runs `await tree.sync()`.
- **kwargs**: forwarded to `discord.Client`.

### Slash commands

`EasyCord.slash(name: str | None = None, *, description: str = "No description provided.", guild_id: int | None = None) -> Callable`

Decorator that registers a top-level slash command.

- **name**: defaults to the function name.
- **description**: shown in Discord UI.
- **guild_id**:
  - `None` registers globally
  - `int` registers to a specific guild (instant)

Handler shape:

- `async def cmd(ctx, ...)`

### Events

`EasyCord.on(event: str) -> Callable`

Decorator that registers an event listener for `event` (without the `on_` prefix).

Example:

```python
@bot.on("message")
async def on_message(message): ...
```

### Middleware

`EasyCord.use(middleware: MiddlewareFn) -> MiddlewareFn`

Registers a middleware function. Middleware runs for slash commands only.

Middleware signature:

`async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None`

### Plugins

`EasyCord.load_plugin(plugin: Plugin) -> None`

Loads a plugin instance:

- assigns the bot reference (`plugin._bot`)
- registers all plugin slash commands and event handlers
- calls `on_load()`:
  - in `setup_hook()` for plugins loaded before `run()`
  - or scheduled immediately if the bot is already ready

`EasyCord.unload_plugin(plugin: Plugin) -> Awaitable[None]`

Unloads a plugin instance:

- removes the plugin’s registered slash commands from the command tree (best-effort)
- deregisters the plugin’s event handlers
- awaits `plugin.on_unload()`

Raises:

- `ValueError` if the plugin is not loaded.

### Lifecycle hooks

EasyCord overrides:

- `setup_hook()`:
  - syncs commands (if enabled)
  - awaits `on_load()` for all loaded plugins
- `dispatch(event, *args, **kwargs)`:
  - calls `discord.Client.dispatch`
  - schedules all EasyCord event handlers for `event`
- `on_ready()`:
  - logs ready information

### Convenience

`EasyCord.run(token: str, **kwargs) -> None`

Configures basic logging and calls `discord.Client.run(...)`.

## `easycord.Context`

### Constructor

`Context(interaction: discord.Interaction)`

### Core attributes

- `ctx.interaction`: the underlying `discord.Interaction`
- `ctx.user`: `discord.User | discord.Member`
- `ctx.guild`: `discord.Guild | None`
- `ctx.channel`: channel from the interaction
- `ctx.command_name`: slash command name or `None`

### Responding

`await ctx.respond(content: str | None = None, *, ephemeral: bool = False, embed: discord.Embed | None = None, **kwargs) -> None`

Behavior:

- first response uses `interaction.response.send_message(...)`
- subsequent responses use `interaction.followup.send(...)`

`await ctx.defer(*, ephemeral: bool = False) -> None`

Defers the response and marks the context as responded.

`await ctx.respond_embed(title: str, description: str | None = None, *, color: discord.Color = discord.Color.blue(), ephemeral: bool = False, **kwargs) -> None`

Builds a `discord.Embed` and sends it via `respond()`.

### Helpers

- `ctx.author`: alias for `ctx.user`
- `ctx.data`: raw `interaction.data`

## Decorators for plugins (`easycord.decorators`)

### `slash(...)`

`slash(name: str | None = None, *, description: str = "No description provided.", guild_id: int | None = None) -> Callable`

Marks a plugin method as a slash command. Intended use:

```python
from easycord import Plugin, slash

class MyPlugin(Plugin):
    @slash(description="Hello")
    async def hello(self, ctx, name: str): ...
```

### `on(event)`

`on(event: str) -> Callable`

Marks a plugin method as an event handler.

## `easycord.Plugin`

Base class for plugins.

- `plugin.bot -> EasyCord`: back-reference (only valid after `load_plugin()`)
- `async plugin.on_load()`: optional async setup hook
- `async plugin.on_unload()`: optional async teardown hook

## Built-in middleware factories (`easycord.middleware`)

All return a `MiddlewareFn`.

### `logging_middleware(level=logging.INFO, fmt="/{command} invoked by {user} in {guild}")`

Logs every slash command invocation using `logging.getLogger("easycord")`.

Format placeholders:

- `{command}`: `ctx.command_name`
- `{user}`: `ctx.user`
- `{guild}`: `ctx.guild` or `"DM"`

### `guild_only_middleware()`

Blocks commands invoked in DMs and responds ephemerally with an error message.

### `rate_limit_middleware(max_calls=5, window_seconds=10.0)`

Simple per-user sliding-window rate limiter using timestamps from `time.monotonic()`.

When limited, responds ephemerally with a “try again in Xs” message.

### `error_handler_middleware(message="💥 Something went wrong. Please try again.")`

Catches exceptions thrown by later middleware/handlers, logs them, and attempts to send an ephemeral error response.

