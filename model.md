# Project model (agent context)

This file is a **single-source context map** for agents (and humans) who want to expand this project. It summarizes the purpose, structure, and extension points of the entire codebase.

## What this project is

**EasyCord** is a small, decorator-first Python framework for building Discord bots on top of `discord.py>=2.0`.

Key features:

- **Slash commands**: register via `bot.slash(...)` with permission guards, cooldowns, and autocomplete
- **Events**: register via `bot.on(event)` (supports multiple handlers per event)
- **Middleware**: wraps every slash-command invocation
- **Plugins**: group commands/events into `Plugin` subclasses using `@slash` / `@on`
- **Context helpers**: respond, embed, DM, confirm, choose (select-menu), paginate, moderation, role management, purge, file sending, threads, message history
- **Bot presence**: `bot.set_status()` to set status and activity
- **Optional integrations**:
  - `ServerConfigStore` for per-guild config persisted to disk
  - `AuditLog` for structured embed logging to a Discord channel

## Runtime expectations

- **Python**: 3.10+ (uses `X | Y` typing)
- **Dependency**: `discord.py>=2.0.0` (see `requirements.txt`)
- **Secrets**: use environment variables, never hardcode tokens.
  - Typical: `DISCORD_TOKEN`
  - Optional: `DISCORD_WEBHOOK_URL`, external API tokens, etc.

## Repository layout (current)

Framework package:

- `easycord/__init__.py`: public exports (framework + integrations)
- `easycord/bot.py`: `EasyCord` implementation (slash commands, events, middleware, plugins)
- `easycord/context.py`: `Context` wrapper for `discord.Interaction`
- `easycord/decorators.py`: plugin decorators `slash`, `on`
- `easycord/plugin.py`: `Plugin` base class
- `easycord/middleware.py`: built-in middleware factories
- `easycord/server_config.py`: `ServerConfigStore` for per-guild disk-backed settings (JSON)

Command/plugin folder:

- `server_commands/`: example “real bot” command plugins as separate modules
  - `fun.py`, `moderation.py`, `info.py`
  - `__init__.py` re-exports plugin classes for convenient imports

Docs:

- `docs/`: codebase-derived documentation pages (`index.md`, `api.md`, etc.)

Examples:

- `examples/basic_bot.py`: minimal bot example (inline commands + middleware)
- `examples/plugin_bot.py`: loads plugins from `server_commands/`

## Public API surface (what other code should import)

From the package root (`from easycord import ...`):

- **Core**: `Bot`, `Context`, `Plugin`, `slash`, `on`, `task`, `SlashGroup`, `Composer`
- **Server config**: `ServerConfig`, `ServerConfigStore`
- **Audit**: `AuditLog`

## How core execution works (important mechanics)

### Slash commands

- User code writes handlers like `async def cmd(ctx, ...)`.
- EasyCord registers an internal callback compatible with `discord.app_commands`:
  - builds `Context(interaction)`
  - runs middleware chain
  - calls the original handler with `ctx` + parsed options
- **Signature rewriting** happens so `discord.py` can infer options from the callback signature.

### Middleware

- Only wraps **slash commands** (not events).
- Middleware signature:
  - `async def middleware(ctx: Context, next: Callable[[], Awaitable[None]]) -> None`
- Runs in registration order; can short-circuit by not calling `await next()`.

### Events

- `EasyCord.on("message")` registers handlers for that event key (no `on_` prefix).
- EasyCord overrides `dispatch` and schedules handlers with `asyncio.ensure_future(...)`.

### Plugins

- Plugin methods are tagged by decorators in `decorators.py`.
- `EasyCord.load_plugin(plugin)` scans attributes and registers:
  - slash commands (tagged with `_easycord_slash`)
  - event handlers (tagged with `_easycord_event`)
- Lifecycle:
  - `setup_hook()` syncs commands (if enabled) and awaits `plugin.on_load()` for plugins loaded pre-run
  - if bot is already ready, `load_plugin()` schedules `plugin.on_load()` via `asyncio.create_task(...)`
  - `unload_plugin()` best-effort removes commands, deregisters handlers, then awaits `plugin.on_unload()`

## Persistence model (server configuration)

`ServerConfigStore` writes per-guild JSON files here:

- `.easycord/server-config/<guild_id>.json`

Schema:

- `roles`: `dict[str, int]` (purpose key → role id)
- `channels`: `dict[str, int]` (purpose key → channel id)
- `other`: `dict[str, Any]` JSON-serializable free-form settings

Writes are **atomic** and protected by **per-guild async locks**.

## How to expand safely (conventions)

- **Prefer plugins** for feature work: add a new `server_commands/<feature>.py` plugin module.
- **Keep secrets out of source**: read tokens/URLs from environment variables.
- **Store per-guild settings** using `ServerConfigStore` rather than hardcoding IDs.
- **Don’t block the event loop**: use async I/O, `await`, and background tasks when appropriate.
- **Avoid global side effects on import**: instantiate clients/stores in your bot entrypoint or plugin `on_load()`.

## Where to look first for changes

- Adding commands/events: `server_commands/` modules + `examples/plugin_bot.py`
- Framework behavior: `easycord/bot.py` (slash/event/middleware/plugin mechanics)
- Response helpers: `easycord/context.py`
- Built-in middleware: `easycord/middleware.py`
- Persistence: `easycord/server_config.py`

