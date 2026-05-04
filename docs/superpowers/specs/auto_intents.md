# Auto-Intents Resolution — Design Spec

Part of v3.3 (DX + Automation Core). This doc covers the intent declaration contract, Composer aggregation algorithm, conflict resolution policy, and observable warning behavior.

---

## Problem

Every plugin that uses privileged gateway events needs specific Discord intents enabled. Today developers must know which intents each plugin requires, set them manually on `discord.Intents`, and pass them to `Composer`. If they miss one, the bot silently receives no events — no error, just broken behavior.

Auto-resolution eliminates this: plugins declare what they need, Composer merges it all, and developers only see warnings when something requires their action (portal approval for privileged intents).

---

## Intent Declaration Contract

Plugins and SlashGroup subclasses declare their required intents via a class attribute:

```python
class InviteTrackerPlugin(SlashGroup, name="invite"):
    intents = {"members", "guild_invites"}
```

The value must be a `set[str]` where each string matches a `discord.Intents` flag name (e.g. `"members"`, `"message_content"`, `"guild_scheduled_events"`).

### Optional override method

Plugins that need dynamic intent resolution (rare) may override `get_intents()`:

```python
def get_intents(self) -> set[str]:
    return self.intents
```

This is the extension point. The default implementation returns `cls.intents`. Composers call `get_intents()` — never `intents` directly — so the override is always honored.

### Inheritance

The attribute is resolved by walking the full MRO, collecting from every class that declares it:

```python
def collect_intents(obj: object) -> set[str]:
    if hasattr(obj, "get_intents"):
        return obj.get_intents()
    result: set[str] = set()
    for cls in type(obj).__mro__:
        if "intents" in cls.__dict__:
            result |= set(cls.__dict__["intents"])
    return result
```

This means:
- `Plugin` base class can declare shared intents all subclasses inherit.
- `SlashGroup` subclasses work identically.
- Mixin classes with their own `intents` declarations are automatically picked up.

Plugins without an `intents` attribute contribute nothing (no error).

---

## Composer Aggregation Algorithm

`Composer.build()` runs intent resolution after all plugins and groups are registered, immediately before constructing the `Bot`:

```python
def build(self) -> Bot:
    self._resolve_plugin_intents()
    bot = Bot(intents=self._intents, ...)
    ...
    return bot
```

`_resolve_plugin_intents()`:

```python
PRIVILEGED_INTENTS = {"members", "presences", "message_content"}

def _resolve_plugin_intents(self) -> None:
    base = self._ensure_intents()
    added: set[str] = set()

    for obj in (*self._plugins, *self._groups):
        for flag in collect_intents(obj):
            if not getattr(base, flag, None):
                setattr(base, flag, True)
                added.add(flag)

    for flag in added:
        if flag in PRIVILEGED_INTENTS:
            logging.getLogger("easycord").warning(
                "Plugin %s requested privileged intent %r. "
                "Ensure this is enabled in the Discord Developer Portal.",
                type(obj).__name__,
                flag,
            )
        else:
            logging.getLogger("easycord").debug(
                "Auto-enabled intent %r from plugin %s.",
                flag,
                type(obj).__name__,
            )
```

**Order of operations:**

1. Start from `self._intents` (user-set or `discord.Intents.default()`).
2. Walk every registered plugin and group, collect their declared intents.
3. For each declared intent not already set: set it, record it as added.
4. Post-pass: emit `logging.warning` for any privileged intent added automatically; emit `logging.debug` for non-privileged ones.
5. `self._intents` is now the fully resolved intents object — passed to `Bot.__init__`.

---

## Conflict Resolution Policy

### Non-privileged intents

Silently merged. No warning, no friction. If the plugin needs it and the developer didn't set it, it gets set.

### Privileged intents (`members`, `presences`, `message_content`)

Merged + `logging.warning`. Example:

```
[easycord] WARNING: Plugin InviteTrackerPlugin requested privileged intent 'members'.
Ensure this is enabled in the Discord Developer Portal.
```

The bot still starts. EasyCord cannot validate portal approval — Discord rejects the connection at login time if the intent isn't approved. The warning tells developers what to check.

### User explicitly set intents then adds a plugin requiring more

If the user called `.intents(discord.Intents.none())` and then adds `InviteTrackerPlugin`, the resolution still merges:

```
[easycord] WARNING: Auto-expanding user-provided intents to include 'members'
required by InviteTrackerPlugin. Ensure this is enabled in the Developer Portal.
```

The warning message changes to mention "user-provided intents" so it's clear the auto-resolution overrode an explicit choice.

### Never raise

Do not raise `ValueError` or `RuntimeError` on intent conflicts. Discord's own connection handshake is the enforcement point. Raising here makes the framework feel brittle and provides no benefit over Discord's clear "Privileged Intents not enabled" error at startup.

---

## Observability

Intent resolution should always be inspectable:

- `logging.warning` for privileged auto-additions (always visible at default log level).
- `logging.debug` for non-privileged auto-additions (visible with `DEBUG` logging).
- Final resolved intents object is available as `bot._intents` after `build()`.

Future: a `.debug_intents()` method on `Composer` that prints the full resolution trace before building. Not v3.3 scope — note it as a possible v3.5 DX addition.

---

## Examples

### Standard setup (no plugins)

```python
bot = Composer().with_members().log().build()
# bot._intents.members == True, set explicitly
```

### Auto-resolution via plugin

```python
bot = Composer().add_group(InviteTrackerPlugin()).build()
# Composer sees InviteTrackerPlugin.intents = {"members", "guild_invites"}
# Warning logged for "members" (privileged)
# Debug logged for "guild_invites" (non-privileged)
# bot._intents.members == True, bot._intents.guild_invites == True
```

### Mixed: explicit + plugin

```python
bot = (
    Composer()
    .with_members()                  # explicit, no warning
    .add_group(InviteTrackerPlugin()) # also needs guild_invites
    .build()
)
# members already set → no duplicate warning
# guild_invites added quietly via debug log
```

### Inheritance

```python
class BaseTrackerPlugin(Plugin):
    intents = {"guilds"}

class RichTrackerPlugin(BaseTrackerPlugin):
    intents = {"members"}

# collect_intents(RichTrackerPlugin()) → {"guilds", "members"}
# both collected via MRO walk
```

---

## What Not to Do

**Do not store a string list in `intents`** — use a `set[str]` so union operations work cleanly and duplicates are free.

**Do not call `getattr(discord.Intents, flag)` to validate flag names** — let Discord raise a clear `AttributeError` at build time if a flag name is wrong. Adding validation here would require maintaining a flag allowlist.

**Do not merge intents after `Bot.__init__`** — the `intents` object must be final before the bot is constructed; modifying it post-construction has no effect on the gateway connection.

---

## Files to Modify

- `easycord/composer.py` — `_resolve_plugin_intents()`, `_ensure_intents()`, `with_*()` shortcuts, updated `build()`
- `easycord/plugin.py` — document `intents` class attribute in base class docstring (no code change needed)
- `tests/test_composer.py` — tests for shortcut flags, auto-resolution, MRO walk, privileged warning emission
