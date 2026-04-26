# Migration Guide: v3.8 → v3.9

**Good news:** v3.9 is 100% backwards compatible. Your v3.8 bots will run unchanged.

This guide shows how to adopt v3.9 patterns (recommended for new code).

---

## What Changed in v3.9

| Feature | v3.8 | v3.9 | Breaking? |
|---------|------|------|-----------|
| Imports | `from easycord import Bot` | `from easycord.api.v1 import Bot` (recommended) | ❌ No |
| Middleware | `@bot.use` | `@bot.middleware` (alias added) | ❌ No |
| Event bus | Implicit dispatch | `bot.events` (opt-in, additive) | ❌ No |
| Capabilities | Discord perms only | Discord perms + plugin grants + custom | ❌ No |
| Escape hatches | None | `ctx.client`, `ctx.raw_interaction` | N/A (new feature) |

---

## 1. Update Imports (Recommended)

### v3.8 style (still works)
```python
from easycord import Bot, Context, slash
```

### v3.9 style (recommended)
```python
from easycord.api.v1 import Bot, Context, slash
```

**Why?** Signals that you want stable API. If you pin v3.x, you get guaranteed compat through v4.x (unless using internal APIs).

**Change:** Add `from easycord.api.v1` instead of `from easycord`. Everything else is identical.

---

## 2. Use Escape Hatches for Raw Access

### v3.8 style (discord.py directly)
```python
# Had to bypass EasyCord completely
import discord
discord_client = ctx.interaction.client
```

### v3.9 style (recommended)
```python
# Drop down from high-level helpers anytime
await ctx.ban(user, reason="spam")  # High-level
await ctx.client.http.ban(user.id, ctx.guild.id)  # Low-level, same time
```

**Available escape hatches:**
- `ctx.client` — the `discord.Client` (which is your `Bot`)
- `ctx.raw_interaction` — the raw `discord.Interaction`
- `bot` — is a `discord.Client` (Bot extends it)

---

## 3. Opt Into EventBus (Optional)

### v3.8 style
```python
@bot.on("member_join")
async def on_member_join(member):
    await member.send("Welcome!")
```

### v3.9 style (new, opt-in)
```python
from easycord.kernel import Event

@bot.events.on("bot.member.join")  # or wildcards: bot.member.*
async def on_member_join(event):
    member = event.data["member"]
    await member.send("Welcome!")
```

**Note:** Old `@bot.on()` still works. EventBus is additive, not replacing.

**When to use:**
- Old style: familiar, works fine
- New style: wildcards (`bot.member.*`), priority ordering, better isolation
- Mix: both styles work side-by-side

---

## 4. Use Capabilities in Commands (Optional)

### v3.8 style
```python
@slash(description="Ban user", permissions=["ban_members"])
async def ban(ctx, user):
    ...
```

### v3.9 style (new, backwards compatible)
```python
@slash(
    description="Ban user",
    capabilities=["ban_members"],  # New parameter, optional
)
async def ban(ctx, user):
    ...
```

**Effect:** Same as `permissions=`. But capabilities can be:
- Discord permissions (`ban_members`)
- Plugin-defined (`custom.export`)
- Granted at runtime by other plugins

**v3.8 code works as-is.** New capability system is opt-in.

---

## 5. Update Middleware (Optional)

### v3.8 style
```python
@bot.use
async def my_mw(ctx, proceed):
    print("before")
    await proceed()
    print("after")
```

### v3.9 style (equivalent)
```python
@bot.middleware
async def my_mw(ctx, proceed):
    print("before")
    await proceed()
    print("after")
```

**No functional difference.** Both work. `middleware` is the v4.0 spelling.

---

## 6. No Breaking Changes

If you have a v3.8 bot, **do nothing.** It will run on v3.9 unchanged.

### Checklist
- ✅ `from easycord import Bot` still works
- ✅ `@bot.use` still works
- ✅ `@bot.on()` still works
- ✅ `@slash(permissions=...)` still works
- ✅ All plugins work unchanged
- ✅ All commands work unchanged
- ✅ All configuration persists

**Zero breaking changes.**

---

## v3.9 → v4.0 Preview

v4.0 will introduce major changes (plugin v2, modular architecture). v3.9 is intentionally a light release to:

1. Introduce stable API namespace
2. Reduce lock-in concerns
3. Prepare infrastructure

**To prepare for v4.0:**
- Use `from easycord.api.v1 import ...` (your code survives the rename)
- Avoid private APIs (imports starting with `_`)
- Read [PLUGIN_V2_SPEC.md](PLUGIN_V2_SPEC.md) to understand the direction

---

## Support

- **Questions?** Open an issue on GitHub
- **Found a bug?** Report it on GitHub
- **Want to help?** Contributions welcome!
