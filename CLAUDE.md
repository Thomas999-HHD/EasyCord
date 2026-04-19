# EasyCord — AI context

> Read this file before reading anything else. It tells you where to look so you don't waste tokens.

## Commands

```bash
pip install -e ".[dev]"        # install with dev deps (one-time)
pytest                          # run all tests
pytest tests/test_foo.py        # single file
```

`asyncio_mode = "auto"` is set in `pyproject.toml` — no `@pytest.mark.asyncio` needed.

## Where to look first

| Task | File(s) |
|------|---------|
| Add a bot command/plugin | `server_commands/` |
| Add a bundled framework plugin | `easycord/plugins/` |
| Bot core (slash/event/middleware/plugin wiring) | `easycord/bot.py` |
| Response helpers | `easycord/context.py` (imports from `_context_*.py`) |
| Built-in middleware | `easycord/middleware.py` |
| Per-guild config persistence | `easycord/server_config.py` |
| Full API reference | `docs/api.md` |
| Architecture overview | `model.md` |

## Architecture

```
easycord/               framework package
  bot.py                Bot — slash/event/middleware/plugin registration
  context.py            Context — aggregates _context_base/_channels/_moderation/_ui
  _context_base.py      respond, defer, embed, DM, form, confirm, paginate
  _context_channels.py  slowmode, lock/unlock, threads, reactions, messages
  _context_moderation.py kick, ban, timeout, unban, roles, nickname, voice
  _context_ui.py        choose, paginate (select-menu UI)
  decorators.py         @slash @on @task (for Plugin methods)
  plugin.py             Plugin base class
  middleware.py         log_middleware, catch_errors, rate_limit, guild_only
  composer.py           fluent Composer builder
  server_config.py      ServerConfigStore — per-guild atomic JSON
  audit.py              AuditLog — embed logging to a Discord channel
  group.py              SlashGroup — slash command groups
  plugins/              bundled drop-in plugins
    levels.py           LevelsPlugin — XP, leveling, ranks
    polls.py            PollsPlugin
    welcome.py          WelcomePlugin
server_commands/        example bot plugins (add new bot features here)
tests/                  pytest suite — mirrors easycord/ structure
docs/                   user-facing documentation
model.md                AI context map (architecture + extension guide)
```

## Non-obvious patterns

- **Context is split.** `context.py` assembles `Context` from four `_context_*.py` mixin files. Edit the right mixin, not `context.py` directly.
- **Middleware only wraps slash commands** — not events. `bot.use(fn)` has no effect on `@bot.on(...)` handlers.
- **`on_load()` timing differs.** Plugins added before `bot.run()` have `on_load()` awaited in `setup_hook`. Plugins added after (bot already ready) get `on_load()` scheduled via `asyncio.create_task`.
- **`auto_sync=True` by default** syncs ALL commands globally on startup. Global commands take ~1 h to appear in Discord. Use `guild_id=YOUR_SERVER_ID` on `@bot.slash` during development for instant registration.
- **ServerConfigStore writes are atomic.** Write-to-temp + rename, protected by per-guild async locks. Don't write config JSON directly.
- **`server_commands/` vs `easycord/plugins/`.** `server_commands/` = example bot-specific plugins (not part of the installable package). `easycord/plugins/` = bundled, reusable plugins shipped with the framework.

## Token discipline

- Check `model.md` for architecture before reading source files.
- Check `docs/api.md` for signatures before reading implementation.
- Read only the `_context_*.py` mixin you need, not all four.
- Run `pytest` before claiming tests pass.
