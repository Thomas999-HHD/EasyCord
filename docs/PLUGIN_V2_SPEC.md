# Plugin System v2 Specification

Complete definition of plugin architecture, lifecycle, isolation, and integration points.

**Status:** Specification only (no implementation code yet).

---

## Overview

Plugin v2 is a **modular, isolated, composable** system built on:

1. **EventBus** — pub/sub for inter-plugin communication
2. **CapabilityRegistry** — permission gates for sensitive operations
3. **ConfigStore** — per-guild typed configuration (atomic writes)
4. **Dependency Resolution** — version constraints, cycle detection
5. **Hot Reload** — unload → reload without losing state

---

## Plugin Class Definition

```python
from easycord.api.v1 import Plugin, slash, on, task, Capability

class MyPlugin(Plugin):
    """A modular plugin with declared capabilities and dependencies."""

    name = "my_plugin"
    version = "2.1.0"
    description = "Does cool things"
    
    # Plugin dependencies (resolved by PluginLoader)
    requires = [
        "core>=1.0",           # Must have core plugin v1.0 or higher
        "moderation>=2.0",     # Depends on moderation plugin v2.0+
    ]
    
    # Capabilities this plugin provides/requires
    capabilities = [
        "moderation.warn",          # Can warn users
        "moderation.timeout",       # Can timeout users
        "custom.export",            # Custom capability (no Discord equiv)
    ]

    # ── Lifecycle ──────────────────────────────────────────

    async def on_load(self):
        """Called once when plugin is added to bot.
        
        Initialize state, register event handlers, grant capabilities.
        """
        # Register capabilities with the registry
        self.bot.capability_registry.define(
            name="moderation.warn",
            discord_perm="moderate_members",
            description="Issue warnings to members"
        )
        
        # Register event listeners
        @self.bot.events.on("interaction.received")
        async def on_command(event):
            pass
        
        # Initialize config
        self.config = self.load_config()
        
        # Start background tasks
        self.loop_task = asyncio.create_task(self.background_loop())

    async def on_ready(self):
        """Called every time the bot becomes ready.
        
        Good place to validate config, reconnect to external services.
        Called after each reconnect.
        """
        print(f"{self.name} ready")

    async def on_unload(self):
        """Called when plugin is removed from bot.
        
        Cleanup: cancel tasks, close connections, snapshot state.
        """
        if hasattr(self, "loop_task"):
            self.loop_task.cancel()
        
        # Snapshot state for reload
        self._snapshot = {
            "users_warned": self.warned_users.copy(),
        }

    # ── Configuration ──────────────────────────────────────

    def load_config(self):
        """Load per-guild configuration with type validation."""
        from easycord.storage import TypedStore
        from dataclasses import dataclass
        
        @dataclass
        class WarnConfig:
            max_warnings: int = 3
            ban_on_nth: int | None = None
            log_channel_id: int | None = None
        
        # TypedStore handles atomic writes, per-guild isolation, migrations
        return TypedStore(WarnConfig, backend=self.bot.storage_backend)

    async def save_config(self, guild_id: int, config_dict: dict):
        """Atomically update guild config."""
        await self.config.set(guild_id, config_dict)

    # ── Commands ───────────────────────────────────────────

    @slash(
        description="Warn a user",
        capabilities=["moderation.warn"],  # Requires this capability
    )
    async def warn(self, ctx, user: discord.Member, reason: str):
        """Issue a warning to a user."""
        if ctx.guild is None:
            await ctx.respond("Guild-only command")
            return
        
        cfg = await self.config.get(ctx.guild.id)
        warns = self.warned_users.get(user.id, 0) + 1
        
        # Check if auto-ban threshold reached
        if cfg.ban_on_nth and warns >= cfg.ban_on_nth:
            await ctx.ban(user, reason=f"Exceeded warn threshold (#{warns})")
            await ctx.respond(f"{user.mention} banned after {warns} warnings")
            return
        
        self.warned_users[user.id] = warns
        await ctx.respond(f"⚠️ {user.mention} warned ({warns} total)")
        
        # Emit custom event for other plugins to listen
        event = Event("moderation.warned", {
            "user_id": user.id,
            "reason": reason,
            "warns": warns,
            "guild_id": ctx.guild.id,
        })
        await self.bot.events.emit(event)

    # ── Event Listeners ────────────────────────────────────

    @on("moderation.warned")
    async def on_user_warned(self, event):
        """React to warnings (from any source)."""
        user_id = event.data["user_id"]
        warns = event.data["warns"]
        guild_id = event.data["guild_id"]
        
        # Broadcast to mod log channel
        guild = self.bot.get_guild(guild_id)
        if guild:
            cfg = await self.config.get(guild_id)
            if cfg.log_channel_id:
                channel = guild.get_channel(cfg.log_channel_id)
                if channel:
                    await channel.send(f"User {user_id} warned (total: {warns})")

    @on("plugin.loaded")
    async def on_plugin_loaded(self, event):
        """React to other plugins being loaded."""
        plugin = event.data["plugin"]
        print(f"Plugin loaded: {plugin.name}")

    # ── Background Tasks ───────────────────────────────────

    @task(every="1h")
    async def reset_warns_weekly(self):
        """Reset warnings every week."""
        # This task runs on a schedule
        pass

    async def background_loop(self):
        """Custom background loop (not decorator-based)."""
        while True:
            try:
                await asyncio.sleep(60)
                # Do periodic work
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.logger.exception("Error in background loop", exc_info=exc)

    # ── Utilities ──────────────────────────────────────────

    def get_logger(self):
        """Get plugin-scoped logger."""
        return logging.getLogger(f"easycord.plugin.{self.name}")
```

---

## Plugin Lifecycle Details

### 1. Plugin Registration

```python
# In user bot code
bot.add_plugin(MyPlugin())
```

**Steps:**
1. PluginLoader checks `requires` against loaded plugins
2. If cycle detected or missing dependency → error
3. Register capabilities with CapabilityRegistry
4. If bot already ready: call `on_load()` immediately + `on_ready()`
5. If bot not ready: call `on_load()` in `setup_hook`, before sync

### 2. Plugin Lifecycle

```
add_plugin()
   ↓
resolve_dependencies()  ← Check versions, detect cycles
   ↓
on_load()  ← Init state, register handlers, define capabilities
   ↓
setup_hook() or on_ready_event
   ↓
on_ready()  ← Validate connections, etc.
   ↓
[Running...]
   ↓
remove_plugin() or bot.stop()
   ↓
on_unload()  ← Cleanup, snapshot state
   ↓
[Done]
```

### 3. Hot Reload Flow

```python
await bot.reload_plugin("my_plugin")
```

**Steps:**
1. Call `on_unload()` on old instance → get snapshot
2. Reimport module (Python reimport)
3. Instantiate new plugin class
4. Check dependencies again
5. Call `on_load()` on new instance
   - Restore snapshot if available
   - Re-register handlers
6. Call `on_ready()` on new instance
7. Old event handlers unregistered (disconnected from EventBus)

**Guarantees:**
- State loss is intentional (developer chooses what to snapshot)
- No double-handler registration (old handlers auto-disconnected)
- Transactions at plugin level, not granular

---

## Configuration System

### Pattern 1: Typed Per-Guild Config

```python
from easycord.storage import TypedStore
from dataclasses import dataclass

@dataclass
class ModerationConfig:
    warn_limit: int = 3
    log_channel: int | None = None
    roles_to_protect: list[int] = field(default_factory=list)

# In plugin
self.config = TypedStore(ModerationConfig, backend=...)

# Load per guild
cfg = await self.config.get(guild_id, default=ModerationConfig())

# Update atomically
await self.config.set(guild_id, {"warn_limit": 5})

# Bulk operations
all_configs = await self.config.all()
```

### Pattern 2: Global Plugin State

```python
# In on_load()
self.state = {
    "user_warns": {},
    "muted_users": {},
}

# Access anytime
self.state["user_warns"][user_id] = 2

# On unload, snapshot for hot reload
async def on_unload(self):
    self._snapshot = self.state.copy()

# On load, restore
async def on_load(self):
    self.state = getattr(self, "_snapshot", {
        "user_warns": {},
        "muted_users": {},
    })
```

### Pattern 3: Database (Future)

```python
# v4.0 ships with JSON/SQLite
# v4.1+ will support Postgres backend via StorageAdapter

class MyPlugin(Plugin):
    async def on_load(self):
        # Automatic: use whatever storage backend bot has
        self.db = self.bot.storage.get_connection()
```

---

## Capability Declaration

### Define

```python
async def on_load(self):
    # Tell the system this plugin can do these things
    self.bot.capability_registry.define(
        name="moderation.warn",
        discord_perm="moderate_members",
        description="Issue warnings"
    )
    
    self.bot.capability_registry.define(
        name="moderation.export_logs",
        discord_perm=None,  # No Discord equivalent
        description="Export moderation logs"
    )
```

### Use in Commands

```python
@slash(
    description="Warn user",
    capabilities=["moderation.warn"],
)
async def warn(ctx, user):
    # Automatically checked before handler runs
    # Missing capability → ephemeral error, handler skipped
    ...
```

### Grant at Runtime

```python
# Plugin A grants plugin B a capability (for testing or delegation)
self.bot.capability_registry.grant("other_plugin", "moderation.warn")

# Override for testing
self.bot.capability_registry.override("moderation.warn", False)
```

### Check Manually

```python
# In a plugin, check if another plugin has capability
granted = await self.bot.capability_registry.check_async(
    ctx.interaction,
    "moderation.warn",
    plugin_name="my_plugin",
)

if not granted:
    await ctx.respond("Missing capability")
    return
```

---

## EventBus Integration

### Emit Custom Events

```python
async def on_user_warned(self, ctx, user):
    event = Event("moderation.warned", {
        "user_id": user.id,
        "guild_id": ctx.guild.id,
        "reason": "spam",
    })
    await self.bot.events.emit(event)
```

### Listen to Events

```python
async def on_load(self):
    @self.bot.events.on("moderation.warned", priority=10)
    async def on_warn(event):
        user_id = event.data["user_id"]
        # React to warn event
```

### Event Naming Convention

- **Prefix:** `plugin_name.event_type`
- **Example:** `moderation.warned`, `levels.leveled_up`, `welcome.member_joined`
- **Core events:** `interaction.*`, `plugin.*`, `bot.*`

### Wildcard Subscriptions

```python
# Listen to all moderation events
@self.bot.events.on("moderation.*")
async def on_any_moderation(event):
    print(f"Moderation event: {event.name}")
```

---

## Dependency Resolution

### Manifest (via class attributes)

```python
class MyPlugin(Plugin):
    name = "my_plugin"
    version = "2.1.0"
    requires = [
        "core>=1.0",            # At least v1.0
        "moderation>=2.0,<3.0", # v2.x only
        "logging",              # Any version
    ]
```

### Resolution Algorithm

1. **Topological Sort** — determine load order
2. **Version Matching** — check each requirement against loaded plugins
3. **Cycle Detection** — reject circular dependencies
4. **Snapshot Restoration** — if reloading, restore old plugin state first

**Example Resolution:**

```
Input: Want to load [moderation, logging]

Moderation requires: [core>=1.0]
Logging requires: [core>=1.0]

Topological order: core → moderation, logging

Check versions:
  - core >= 1.0 ✓ (core v1.2.0 loaded)
  - moderation v2.0 available ✓
  - logging v1.0 available ✓

Load order: core (already loaded) → moderation → logging
```

**Failure Handling:**

| Scenario | Behavior |
|----------|----------|
| Missing dependency | Error: "Required plugin X not found" |
| Version mismatch | Error: "Required core>=2.0 but have v1.5" |
| Circular dependency | Error: "Circular: A→B→A" |
| Already loaded | Skip (idempotent) |
| Load fails (exception) | Rollback, leave previous state intact |

---

## Plugin Isolation

### No Global State Sharing

```python
# BAD: Plugins share global dict (leaks state, hard to reload)
GLOBAL_STATE = {}

class MyPlugin(Plugin):
    async def on_load(self):
        GLOBAL_STATE["data"] = []  # ← Shared!

# GOOD: Each plugin owns its state
class MyPlugin(Plugin):
    async def on_load(self):
        self.data = []  # ← Isolated to this instance
```

### ConfigStore Isolation

Each plugin gets its own slice of per-guild config:

```python
# Plugin A
await self.config.set(guild_id, {"prefix": "!"})

# Plugin B (different config, same guild)
await self.config.set(guild_id, {"language": "en"})

# Configs don't conflict (different keys)
cfg_a = await self.config.get(guild_id)  # {"prefix": "!"}
cfg_b = await self.config.get(guild_id)  # {"language": "en"}
```

### Namespace EventBus Events

Convention: `plugin_name.event_type`

```python
# Plugin A emits
await self.bot.events.emit(Event("levels.leveled_up", {...}))

# Plugin B emits
await self.bot.events.emit(Event("moderation.warned", {...}))

# No naming collisions
```

---

## Testing Patterns

### Test Plugin in Isolation

```python
import pytest
from easycord.api.v1 import Bot

@pytest.fixture
async def bot():
    bot = Bot(token="test", db_path=":memory:")
    yield bot
    # Cleanup

@pytest.fixture
def plugin(bot):
    plugin = MyPlugin()
    bot.add_plugin(plugin)
    return plugin

@pytest.mark.asyncio
async def test_warn_command(bot, plugin):
    # Create mock context
    ctx = create_mock_context(guild=guild, user=moderator)
    
    # Override capability check
    bot.capability_registry.override("moderation.warn", True)
    
    # Call plugin command
    await plugin.warn(ctx, user=target, reason="spam")
    
    # Verify state changed
    assert plugin.state["warned_users"][target.id] == 1
```

### Test with Full Bot

```python
@pytest.mark.asyncio
async def test_with_full_bot():
    bot = Bot(...)
    bot.add_plugin(MyPlugin())
    bot.add_plugin(OtherPlugin())
    
    # Simulate interaction
    event = Event("interaction.received", {...})
    await bot.events.emit(event)
    
    # Verify both plugins received it
```

---

## Migration from v3.x

v3.x: Plugins based on `easycord.Plugin` (loose coupling)
v4.0: Plugins explicitly declare requirements, capabilities, config

**Compatibility:**

```python
# Old v3 plugin (mostly works, no new features)
class OldPlugin(Plugin):
    @slash(description="Do thing")
    async def do_thing(ctx):
        ...

# v4.0 plugin (new structure)
class NewPlugin(Plugin):
    name = "new_plugin"
    version = "1.0.0"
    requires = ["core>=1.0"]
    capabilities = ["custom.thing"]
    
    async def on_load(self):
        # Explicit init
        ...
    
    @slash(description="Do thing", capabilities=["custom.thing"])
    async def do_thing(ctx):
        ...
```

Old plugins work with minimal changes. New plugins unlock isolation + reload.

---

## Future Extensions (v4.1+)

- **Plugin Marketplace:** Registry of published plugins
- **Permission Delegation:** Admin grants capability to user
- **Distributed Plugins:** Load plugin code from external registry
- **Plugin Sandboxing:** Run untrusted plugins in restricted mode
- **Config Validation Hooks:** Custom validation in TypedStore
- **Metrics Per Plugin:** Track execution time, errors, event counts
