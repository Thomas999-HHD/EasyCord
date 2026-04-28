# AGENTS.md

## Commands
```bash
pytest
pytest tests/test_endpoint_integration.py tests/test_bot.py tests/test_package_exports.py tests/test_plugin_base.py
```

## Current state
- Project name/positioning: EasyCord Discord Framework
- Current working version: `3.2.0`
- Full test suite is green: `472 passed`
- Handoff files to keep current: `model.md`, `CHANGELOG.md`, `docs/release-notes.md`, `docs/api.md`

## Core extension points
- `easycord/cog.py` -> `Cog`, `GroupCog`, listener helpers
- `easycord/plugins/base.py` -> `IntegrationPlugin`, `GuildPlugin`, `JsonConfigPlugin`
- `easycord/_bot_plugins.py` -> plugin loading, cogs, extensions, endpoint registry
- `easycord/decorators.py` -> `slash`, `on`, `task`, `endpoint`, component/modal decorators

## Token-saving practices
- Prefer the smallest relevant file set when editing or testing.
- Reuse existing helpers and plugin patterns instead of inventing parallel APIs.
- Update `model.md` after large feature changes so future work can start from context, not archaeology.
- Keep docs short and example-driven; avoid repeating the same feature in every doc.

## Integration notes
- `Bot.load_builtin_plugins()` loads the first-party plugin pack once.
- `@bot.endpoint` / `@endpoint` can be used in bare or named form for reusable plugin integrations.
- `IntegrationPlugin` is the best base class when a plugin needs to call other plugins or shared endpoints.
