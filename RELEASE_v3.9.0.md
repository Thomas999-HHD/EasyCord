# EasyCord v3.9.0 Release Notes

**Release Date:** 2026-04-26

**Version:** 3.9.0 (Foundation Release)

**Status:** Stable. Production ready. Zero breaking changes.

---

## Overview

v3.9.0 is a **foundation release** establishing structural groundwork for v4.0's modular architecture while maintaining 100% backwards compatibility with v3.8.

**Goal:** Reduce lock-in perception, introduce async event bus and permission gates, and build developer trust through transparency.

---

## What's New

### 1. No Lock-In Guarantee

Direct escape hatches to raw discord.py at any time:

```python
# High-level (easy)
await ctx.ban(user, reason="spam")

# Drop down anytime (low-level)
await ctx.client.http.ban(user.id, ctx.guild.id, reason="spam")

# Both work equally. Your choice.
```

**New properties:**
- `ctx.raw_interaction` — raw `discord.Interaction`
- `ctx.client` — raw `discord.Client` (which is your `Bot`)

### 2. Public API Namespace

Stable, versioned public API:

```python
# Recommended (v3.9+)
from easycord.api.v1 import Bot, Context, Plugin

# Still works, but recommend migrating
from easycord import Bot, Context, Plugin
```

`easycord.api.v1` is **frozen** and follows SemVer through v4.x.

### 3. EventBus (Async Pub/Sub)

Decouple components with a first-class event bus:

```python
# Emit events
event = Event("moderation.warned", {"user_id": 123})
await bot.events.emit(event)

# Listen to events (with priority ordering)
@bot.events.on("moderation.*", priority=10)
async def on_moderation(event):
    print(f"Event: {event.name}")

# Wildcards, concurrency, error isolation — all built-in
```

**Features:**
- Priority ordering (handlers execute by priority, then registration order)
- Wildcard subscriptions (`moderation.*`, `*`)
- Async concurrent execution
- Exception isolation (one handler crash doesn't break others)
- Backwards compatible with v3 `@bot.on()` style

### 4. CapabilityRegistry (Permission Gates)

Declarative permission model for moderation, AI tools, and custom actions:

```python
# Define capabilities
bot.capability_registry.define(
    name="ban_members",
    discord_perm="ban_members",
    description="Ban server members"
)

# Use in commands
@slash(description="Ban user", capabilities=["ban_members"])
async def ban(ctx, user):
    # Automatically checked before handler runs
    # Missing capability → ephemeral error, handler skipped
    ...

# Grant capabilities at runtime
bot.capability_registry.grant("my_plugin", "custom.export")

# Override for testing
bot.capability_registry.override("ban_members", True)
```

**Features:**
- Maps Discord permissions to custom capabilities
- Plugin-defined capabilities (no Discord equivalent needed)
- Fail-closed (deny by default)
- Used by v4.0 plugin system

### 5. Middleware Alias

New v4.0-style naming (v3 style still works):

```python
# v4.0 naming
@bot.middleware
async def my_mw(ctx, proceed):
    await proceed()

# v3.x naming (still works)
@bot.use
async def my_mw(ctx, proceed):
    await proceed()
```

---

## Architecture Changes

### Execution Pipeline

All interactions now flow through a predictable 6-stage pipeline:

```
Adapter → EventBus → Middleware → Capability Check → Handler → Response
```

**See:** [docs/EXECUTION_PIPELINE.md](docs/EXECUTION_PIPELINE.md)

### New Kernel Subsystems

```
easycord/kernel/
  ├── event_bus.py         (EventBus — async pub/sub)
  └── capability.py        (CapabilityRegistry — permission gates)
```

These are **internal** subsystems but fully replaceable via Protocol-based design.

### Module Structure

```
easycord/
  ├── api/v1/              (NEW: stable public API namespace)
  ├── kernel/              (NEW: internal subsystems)
  └── [existing modules]   (unchanged)
```

---

## Documentation

**New:**
- [docs/EXECUTION_PIPELINE.md](docs/EXECUTION_PIPELINE.md) — 6-stage flow, event naming, testing patterns
- [docs/PLUGIN_V2_SPEC.md](docs/PLUGIN_V2_SPEC.md) — v4.0 plugin system specification
- [docs/MIGRATION.md](docs/MIGRATION.md) — v3.8 → v3.9 adoption guide

**Updated:**
- README.md — Added "No Lock-In Guarantee" section
- CHANGELOG.md — Complete v3.9 release notes

---

## Backwards Compatibility

✅ **100% compatible with v3.8.**

| Feature | v3.8 | v3.9 | Breaking? |
|---------|------|------|-----------|
| `from easycord import Bot` | ✅ | ✅ Works | ❌ No |
| `@bot.use(mw)` | ✅ | ✅ Works | ❌ No |
| `@bot.on("event")` | ✅ | ✅ Works | ❌ No |
| `@slash(permissions=[...])` | ✅ | ✅ Works | ❌ No |
| All plugins | ✅ | ✅ Work | ❌ No |
| All commands | ✅ | ✅ Work | ❌ No |
| Config persistence | ✅ | ✅ Persists | ❌ No |

**Zero breaking changes. Drop-in upgrade.**

---

## Testing

**All 578 tests passing.**

- Added: EventBus unit tests (priority, wildcard, cancellation)
- Added: CapabilityRegistry unit tests (permission mapping, grants, overrides)
- Added: Execution pipeline integration tests
- Existing: v3.8 test suite still passes (100% compat verified)

```bash
pytest tests/ -q
# 578 passed in 1.48s
```

---

## Performance

- **EventBus:** ~1-2ms per interaction (negligible; async concurrent processing)
- **CapabilityRegistry:** <1ms per check (HashMap lookup + Discord perm check)
- **No changes to:** command latency, memory usage, startup time

---

## Deprecations

**Informational only. No code changes required.**

- `from easycord import ...` → recommend `from easycord.api.v1 import ...`
  - Still works in v3.9 and v4.x
  - Will warn in v5.0 (if released)

---

## Roadmap (v4.0)

See [docs/PLUGIN_V2_SPEC.md](docs/PLUGIN_V2_SPEC.md):

- **Plugin v2 system:** explicit lifecycle, dependency resolution, hot reload
- **TypedStore:** per-guild config with type validation and migrations
- **Storage backends:** JSON, SQLite, Postgres (pluggable via Protocol)
- **AI decoupling:** optional `easycord[ai]` extra (currently in core)
- **CLI tools:** `easycord init`, `easycord dev`, `easycord migrate`
- **Feature flags:** dynamic feature toggling
- **Distributed event bus:** Redis/gRPC backends (stretch goal)

---

## Installation

### From GitHub

```bash
pip install git+https://github.com/rolling-codes/EasyCord.git@v3.9.0
```

### From GitHub (development)

```bash
git clone https://github.com/rolling-codes/EasyCord.git
cd EasyCord
git checkout v3.9.0
pip install -e .
```

### With dev dependencies

```bash
pip install -e ".[dev]"
pytest
```

---

## Upgrade Guide

See [docs/MIGRATION.md](docs/MIGRATION.md) for:

- How to adopt `easycord.api.v1` imports
- How to use EventBus listeners (optional)
- How to use capabilities (optional)
- How to prepare for v4.0

---

## Known Limitations

Intentionally deferred to v4.0:

- ❌ Plugin v2 (explicit isolation, dependency resolution)
- ❌ Hot reload (plugin code reloading without restart)
- ❌ TypedStore (per-guild typed config with migrations)
- ❌ Storage adapter system (pluggable backends)
- ❌ AI decoupling (separate `easycord[ai]` extra)
- ❌ CLI tools (`easycord init`, etc.)

These are intentional; v3.9 is a foundation release.

---

## Contributors

- EasyCord Team
- Community feedback on lock-in concerns

---

## License

MIT. See LICENSE file.

---

## Support

- **Documentation:** https://github.com/rolling-codes/EasyCord
- **Issues:** https://github.com/rolling-codes/EasyCord/issues
- **Discussions:** https://github.com/rolling-codes/EasyCord/discussions

---

## Summary

v3.9.0 is **production-ready** and **100% backwards compatible**. It establishes trust through transparency (escape hatches), introduces modular infrastructure (EventBus, CapabilityRegistry), and paves the way for v4.0's plugin system.

**No action required to upgrade from v3.8. Just install and run.**

Recommended: Adopt `from easycord.api.v1` imports for new code to signal stability intent.
