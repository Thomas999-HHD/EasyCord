# Release notes for 3.1.2

This version is about getting back to the framework’s original job: taking the things you normally do the long way in `discord.py` and shrinking them down to the smallest practical function call.

## What changed

- Simplified the starter and plugin examples so the default path is easier to copy.
- Added bulk helpers for loading plugins and slash command groups in one call.
- Expanded command registration to support more `discord.py` app command options with less boilerplate.
- Broke repeated plugin logic into shared helpers so the bundled features read more like usage examples.
- Tightened the docs so the shortest path to a working bot is obvious first.

## Why

Most beginners do not need more abstraction; they need less work between an idea and a working command. This release leans into that by removing repeated setup, grouping related actions together, and making the common path feel direct.

## User impact

- Less code to write for the same command or feature.
- Easier plugin integration for modular bots.
- A clearer path from raw `discord.py` habits to framework-style code.

## Validation

- `python -m pytest tests/test_group.py tests/test_bot.py tests/test_composer.py tests/test_server_commands.py tests/test_package_exports.py tests/test_decorators.py`
- `python -m compileall easycord examples docs tests`
