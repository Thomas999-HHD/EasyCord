# Interactions

EasyCord v5.2 keeps `discord.app_commands.CommandTree` as the Discord sync
backend, but `InteractionRegistry` is the framework inventory. It tracks slash
commands, context menu commands, components, modals, and autocomplete callbacks
with owner, scope, metadata, enabled state, and sync state.

```python
from easycord import Bot, slash_command

bot = Bot(auto_sync=False)

@slash_command(description="Ping the bot")
async def ping(ctx):
    await ctx.respond("Pong!")

inventory = bot.inspect_interactions()
```

`@slash` and `@slash_command` are the same decorator. Existing bots can keep
using `@slash`; new code can use `@slash_command` when migrating from Pycord,
Nextcord, Disnake, or discord.py examples that use longer command names.

## Inspector

`bot.inspect_interactions()` returns grouped lists:

- `slash`
- `context_menu`
- `component`
- `modal`
- `autocomplete`

Each entry includes the interaction type, name or route pattern, callback name,
source plugin, guild scope, metadata, enabled state, sync state, and registration
time.

For live diagnostics, opt into the built-in developer command:

```python
bot.enable_interaction_inspector(owner_ids={123456789012345678})
```

This registers `/easycord interactions` and returns a compact grouped count of
the current registry.

## Autocomplete

Autocomplete callbacks receive EasyCord context, the current input, and partial
options supplied by Discord:

```python
from easycord import Plugin, autocomplete, slash_command

class FruitPlugin(Plugin):
    @autocomplete("fruit", command="pick")
    async def fruit_choices(self, ctx, current: str, options: dict):
        return [name for name in ["apple", "banana"] if current in name]

    @slash_command(description="Pick fruit")
    async def pick(self, ctx, fruit: str):
        await ctx.respond(fruit)
```

Tests can call `easycord.testing.invoke_autocomplete(...)` without a live bot.
