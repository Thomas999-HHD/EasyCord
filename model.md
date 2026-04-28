# Agent context map

> Read CLAUDE.md first. This file covers architecture and extension points.

## What it is

EasyCord Discord Framework is a beginner-friendly Python framework for Discord bots on `discord.py>=2.0`. Removes boilerplate: decorators register slash commands, middleware wraps every invocation, plugins group commands/events into classes.

Current roadmap state: release automation, database auto-configuration, bundled plugins, embed-card helpers, a lightweight localization manager, and the new cog/extension parity layer are now in place. `Context.t(...)` can resolve translated strings through `Bot.localization` / `Bot.i18n`.

Release notes now emphasize the practical uses of each feature, especially `Bot.db`, `bot.load_builtin_plugins()`, `EmbedCard`, `LocalizationManager`, `IntegrationPlugin`, `GuildPlugin`, `JsonConfigPlugin`, `Cog`, `GroupCog`, and extension loading, so they can guide the next implementation pass instead of only recording history.

Recent QoL additions:
- `Context.send(...)` and `Context.reply(...)` now mirror `Context.respond(...)`
- `Context.author` and `Context.me` mirror common `discord.py` naming
- `Context.bot` mirrors `interaction.client`
- `Context.fetch_message(message_id)` fetches a single channel message
- `Bot.listen(...)` provides a discord.py-style event decorator, including bare `@bot.listen` inference
- `GuildPlugin` and `JsonConfigPlugin` now provide lighter-weight authoring helpers for first-party plugins
- `IntegrationPlugin` now provides cross-plugin and endpoint lookup helpers
- `Bot.endpoint(...)` and `@endpoint` now support both named and bare decorator forms for reusable plugin endpoints
- `AnnouncementsPlugin` and `AutoReplyPlugin` were added as reference plugins that use the new helper classes
- `.github/workflows/release.yml` now publishes tagged releases automatically
- `scripts/release.ps1` mirrors the release workflow for local publishing
- `Cog`, `GroupCog`, and extension loading now cover the biggest discord.py parity gaps
- Full test suite is green again: `472 passed`

## Handoff notes

- The current code version is `4.1` in `pyproject.toml`.
- `CHANGELOG.md` now contains the `4.1` release entry.
- `docs/release-notes.md` is the body source the release workflow uses for GitHub Releases.
- Cloud Code should start by reading `model.md`, `CHANGELOG.md`, `docs/release-notes.md`, and `docs/api.md`.

## Layout

| Path | Purpose |
| --- | --- |
| `easycord/bot.py` | `Bot` — slash/event/middleware/plugin wiring |
| `easycord/context.py` | `Context` — assembles four `_context_*.py` mixins |
| `easycord/_context_base.py` | respond, defer, embed, dm, send_to, file, edit, properties |
| `easycord/_context_channels.py` | slowmode, lock/unlock, threads, reactions, messages |
| `easycord/_context_moderation.py` | kick, ban, timeout, unban, roles, nickname, voice |
| `easycord/_context_ui.py` | choose, paginate (select-menu UI) |
| `easycord/decorators.py` | `@slash` `@on` `@task` for Plugin methods |
| `easycord/plugin.py` | `Plugin` base class |
| `easycord/middleware.py` | built-in middleware factories |
| `easycord/composer.py` | fluent `Composer` builder |
| `easycord/server_config.py` | `ServerConfigStore` — per-guild atomic JSON |
| `easycord/audit.py` | `AuditLog` — embed logging to Discord channel |
| `easycord/group.py` | `SlashGroup` — slash subcommand groups |
| `easycord/plugins/levels.py` | `LevelsPlugin` — XP, leveling, ranks |
| `easycord/plugins/polls.py` | `PollsPlugin` |
| `easycord/plugins/welcome.py` | `WelcomePlugin` |
| `.github/workflows/release.yml` | tag-triggered GitHub release workflow |
| `scripts/release.ps1` | local release helper for build + publish |
| `easycord/cog.py` | `Cog` / `GroupCog` parity layer and listener helpers |
| `server_commands/` | example bot plugins — add new bot features here |
| `tests/` | pytest suite (`asyncio_mode = "auto"`) |
| `docs/api.md` | full API reference |

## Public API (`from easycord import ...`)

`Bot`, `Context`, `Plugin`, `Cog`, `GroupCog`, `SlashGroup`, `Composer`, `slash`, `on`, `task`, `ServerConfig`, `ServerConfigStore`, `AuditLog`

## Key mechanics

**Slash commands** — `Bot.slash(...)` registers an `app_commands.Command`. Internally: build `Context(interaction)` → run middleware chain → call handler with `ctx` + parsed options. Signature rewriting: first param swapped to `interaction: discord.Interaction` for discord.py, `ctx` stripped and forwarded.

**Middleware** — wraps slash commands only (not events). Runs in registration order. Short-circuit by not calling `await next()`.

**Events** — `Bot.on("message")` supports multiple handlers. Dispatched via `asyncio.create_task` — one failure doesn't block others.

**Plugins** — `add_plugin()` and `add_plugins()` scan attributes for `_is_slash` / `_is_event` / `_is_task` tags. `on_load()` awaited in `setup_hook` if pre-run; `create_task` if bot already ready.

**ServerConfigStore** — atomic writes (write-to-temp + rename), per-guild `asyncio.Lock`.

**Release automation** — `CHANGELOG.md` tracks the release summary, `docs/release-notes.md` feeds the GitHub Release body, and `.github/workflows/release.yml` publishes tagged releases with the built artifacts.

**Discord.py parity** — `Cog`, `GroupCog`, `load_extension()`, `unload_extension()`, `reload_extension()`, `add_cog()`, `get_cog()`, and cog inspection helpers are now the main class-based compatibility layer.

## Extension conventions

- New bot features → `server_commands/<feature>.py` plugin
- New bundled plugins → `easycord/plugins/<feature>.py`
- Keep secrets in env vars (`DISCORD_TOKEN`, etc.)
- Use `async` I/O; never block the event loop
- `auto_sync=True` by default — use `guild_id=` during development for instant command registration
