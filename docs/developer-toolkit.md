# Developer Toolkit

EasyCord v5.3 adds a small, dependency-free toolkit for local bot development.

## Create a bot

```bash
easycord new my-bot
cd my-bot
pip install -e ".[dev]"
pytest
```

The scaffold includes `bot.py`, one plugin under `plugins/`, `.env.example`,
`pyproject.toml`, and a starter pytest file using `easycord.testing.invoke()`.
Generated code uses `Bot(auto_sync=False)` so local imports and tests do not
touch Discord.

## Check your setup

Run `doctor` before launching a bot or debugging a new environment:

```bash
easycord doctor
easycord doctor bot:bot
easycord doctor bot:bot --json
```

The command checks Python version support, the installed `discord.py` package,
whether `DISCORD_TOKEN` is configured, and optionally imports a bot target. When
a target is supplied, it also reports how many EasyCord interactions are
registered and warns if local imports would auto-sync commands.

The same output formatter is available in Python:

```python
from easycord import format_doctor_report

print(format_doctor_report(report))
```

## Inspect interactions

Point the CLI at a bot object using `module:object` syntax:

```bash
easycord inspect bot:bot
easycord inspect bot:bot --json
```

This imports the bot and prints `bot.inspect_interactions()` in a readable
format. The same formatter is available in Python:

```python
from easycord import format_interaction_inventory

print(format_interaction_inventory(bot.inspect_interactions()))
```

## Preview command sync

```bash
easycord sync-plan bot:bot --remote old_ping
easycord sync-plan bot:bot --remote old_ping --json
```

`sync-plan` never contacts Discord. It compares local registered command names
with remote names you pass manually and prints the same plan shape returned by
`bot.plan_command_sync(...)`.

## Generate a test

```bash
easycord test-template greetings
easycord test-template greetings --output tests/test_greetings.py
```

The template uses `Bot(auto_sync=False, db_backend="memory")`, adds the plugin,
and invokes a command without connecting to Discord.

## Offline interaction tests

Use the testing helpers for command, autocomplete, context menu, component, and
modal flows:

```python
from easycord.testing import invoke, invoke_autocomplete
from easycord.testing import invoke_component, invoke_message_command
from easycord.testing import invoke_modal, invoke_user_command

ctx = await invoke(bot, "hello")
choices = await invoke_autocomplete(bot, "search", "query", "ea")
profile = await invoke_user_command(bot, "Profile", target_id=42)
quote = await invoke_message_command(bot, "Quote", content="Ship it")
clicked = await invoke_component(bot, "ticket:close:42")
submitted = await invoke_modal(bot, "feedback", message="Great bot")
```
