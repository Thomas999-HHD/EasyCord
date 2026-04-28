# Release notes for 4.1

Release date: 2026-04-28

This release closes the biggest EasyCord Discord Framework parity gaps by adding class-based cogs, extension loading, and a clearer release path while keeping the framework lightweight.

## Highlights

- Added `Cog` and `GroupCog` for class-based command and listener organization.
- Added extension loading with `load_extension()`, `unload_extension()`, and `reload_extension()`.
- Added release automation so tagged versions can publish themselves.
- Added `Bot.add_cog()`, `Bot.get_cog()`, `Bot.remove_cog()`, and cog inspection helpers.
- Added `bot.load_builtin_plugins()` as the obvious way to load the bundled first-party plugin pack.
- Kept the beginner-friendly helpers from the prior release: database auto-config, built-in plugins, embed cards, and localization.

## What changed

- Added a cog layer that mirrors `discord.py` naming and grouping conventions.
- Added extension hooks so modules can define `setup(bot)` and `teardown(bot)` like `discord.py`.
- Added a local `scripts/release.ps1` helper and a GitHub Actions workflow for tagged releases.
- Updated the handoff files so Cloud Code can pick up the current state without rebuilding the story from scratch.

## Why it helps

- Discord.py users get familiar entry points instead of learning a new mental model for everything.
- Extensions and cogs make larger bots easier to split into manageable parts.
- Release automation keeps versioning and publishing more repeatable.
- The model files now carry the latest working context for the next agent.

## How to use the new pieces

- Use `Cog` when you want a class that groups slash commands and listeners.
- Use `GroupCog` when that cog should also act as a slash-command namespace.
- Use `bot.load_extension("my_module")` when you want module-based loading with `setup(bot)`.
- Use `.github/workflows/release.yml` or `scripts/release.ps1` when you are publishing a tagged release.

## Upgrade notes

- Existing bots can adopt cogs and extensions incrementally.
- You do not need to convert existing plugins immediately.
- If you already use plugins, you can treat cogs as the higher-parity option for new feature areas.

## Validation

- `python -m pytest tests/test_group.py tests/test_bot.py tests/test_composer.py tests/test_server_commands.py tests/test_package_exports.py tests/test_decorators.py tests/test_context.py tests/test_i18n.py tests/test_plugin_base.py tests/test_announcements_plugin.py tests/test_autoreply_plugin.py tests/test_cog_and_extensions.py`
- `python -m pytest` (`472 passed`)
- `python -m compileall easycord examples docs tests`

Note: On Windows, pytest may emit temp/cache permission warnings that can be safely ignored if the test slice passes.
