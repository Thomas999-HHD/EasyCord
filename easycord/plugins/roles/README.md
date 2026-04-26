# RolesPlugin — v4.0 Flagship Reference Implementation

**Status:** Production-ready | **v4.0 foundation release** | **No lock-in architecture**

---

## Overview

RolesPlugin is the **reference implementation** for EasyCord v4.0. It demonstrates:

- ✅ **Declarative blueprints** — role definitions as typed config
- ✅ **Deterministic reconciliation** — idempotent diff + apply
- ✅ **Safety policies** — prevent self-escalation, protect admin roles
- ✅ **EventBus integration** — all state changes emit events
- ✅ **Capability enforcement** — fine-grained permission control
- ✅ **Cross-plugin API** — other plugins integrate cleanly
- ✅ **Full observability** — debug commands, audit trails
- ✅ **Zero lock-in** — escape hatches to raw discord.py

Every design choice here is a template for v4.0 plugins.

---

## Quick Start

### Installation

```python
from easycord.api.v1 import Bot
from easycord.plugins import RolesPlugin

bot = Bot()
bot.add_plugin(RolesPlugin())
bot.run("TOKEN")
```

### Setup

In Discord:

```
/roles setup       # Create default roles (Bot, Admin, Moderator, Member)
/roles sync        # Apply blueprint to guild
/roles debug       # Inspect current state
```

---

## Architecture

### 1. Blueprint System

Source of truth for all role definitions. Typed, validated, versioned.

```python
from easycord.plugins.roles.blueprint import RoleBlueprint, BlueprintSet

admin = RoleBlueprint(
    name="Admin",
    permissions=["ban_members", "kick_members"],
    color=0xFF0000,
    hoist=True,
    inherits=None,
)

moderator = RoleBlueprint(
    name="Moderator",
    permissions=["kick_members", "manage_messages"],
    inherits="admin",  # Inherit from Admin
)

blueprint_set = BlueprintSet(
    guild_id=12345,
    blueprints={"admin": admin, "moderator": moderator}
)
```

**Features:**
- Permission inheritance
- Explicit deny overrides
- Color, hoist, mentionable control
- Full validation (names, perms, cycles)

### 2. Diff Engine

Compare desired state (blueprint) to actual state (Discord). Produce minimal change set.

```python
from easycord.plugins.roles.diff import DiffEngine

engine = DiffEngine()
diff = await engine.compute_diff(guild, blueprint_set, stored_ids)

# diff.summary() → human-readable output
# diff.is_clean() → check if sync needed
# diff.changes → list of RoleDiff objects
```

**Change types:**
- `CREATE` — role doesn't exist yet
- `UPDATE_PERMS` — permissions mismatch
- `UPDATE_COLOR` — color mismatch
- `UPDATE_HOIST` — hoist status mismatch
- `UPDATE_MENTIONABLE` — mentionable mismatch
- `DELETE` — remove unmanaged roles (optional)

### 3. Policy Engine

Enforce safety rules before applying changes.

```python
from easycord.plugins.roles.policy import PolicyEngine, PolicyConfig

config = PolicyConfig(
    prevent_self_escalation=True,  # User can't upgrade own role
    protect_admin_role=True,        # Warn on admin changes
    prevent_dangerous_perms=True,   # Block administrator perm
)

engine = PolicyEngine(config)
violations = await engine.validate(guild, diff_result, ctx.member)

if violations:
    # Handle policy violations
    pass
```

### 4. Reconciliation Engine

Apply changes idempotently to Discord.

```python
from easycord.plugins.roles.reconcile import ReconciliationEngine

engine = ReconciliationEngine()

# Dry-run (preview)
result = await engine.apply_diff(guild, diff_result, dry_run=True)

# Apply changes
result = await engine.apply_diff(guild, diff_result, dry_run=False)

if result.success:
    print(f"Applied {result.changes_applied} changes")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

**Properties:**
- Non-destructive by default
- Partial failure tolerant
- Full error logging

### 5. Storage Layer

Persist blueprints and role ID mappings via ServerConfigStore.

```python
from easycord.plugins.roles.storage import RoleStorage

storage = RoleStorage(config_store)

# Save blueprints
await storage.save_blueprints(blueprint_set)

# Load blueprints
blueprints = await storage.load_blueprints(guild_id)

# Track role IDs
await storage.set_role_id(guild_id, "admin", 999)
role_ids = await storage.load_role_ids(guild_id)
```

### 6. Public API

Other plugins use this to assign/remove roles.

```python
from easycord.plugins.roles.plugin import RolesPlugin

roles_plugin = bot.get_plugin(RolesPlugin)
api = roles_plugin.get_api()

# Assign role to user
await api.assign(user_id, guild_id, "moderator")

# Remove role
await api.remove(user_id, guild_id, "moderator")

# Check if user has role
has_mod = await api.has(user_id, guild_id, "moderator")

# Get Discord role object
role = await api.get_role(guild_id, "admin")

# List all managed roles
roles = await api.list_roles(guild_id)
```

---

## Execution Pipeline

All actions flow through the **v4.0 execution pipeline**:

```
Command
  ↓
EventBus (emit "interaction.received")
  ↓
Middleware (run plugins, log, rate limit)
  ↓
Capability Check (user has required permission)
  ↓
Policy Engine (safety validation)
  ↓
Handler (execute command logic)
  ↓
Response + Event Emission
```

**In code:**

```python
# User invokes command
@slash(description="Sync roles", capabilities=["roles.manage"])
async def roles_sync(self, ctx: Context) -> None:
    # EventBus already emitted "interaction.received"
    # Capabilities already checked
    
    # Load and validate
    blueprint_set = await self.storage.load_blueprints(ctx.guild_id)
    diff = await self.diff_engine.compute_diff(guild, blueprint_set)
    
    # Policy validation
    violations = await self.policy_engine.validate(guild, diff, ctx.member)
    if violations:
        await ctx.respond("Policy violation")
        return
    
    # Apply
    result = await self.reconcile_engine.apply_diff(guild, diff)
    
    # Emit audit event
    await self.bot.events.emit(
        self._event("sync", {"changes_applied": result.changes_applied})
    )
    
    await ctx.respond("✅ Synced")
```

---

## Observability

### Debug Command

```
/roles debug
```

Output:
```
Managed Roles:
  ✅ `admin` → Admin (ID: 999)
  ✅ `moderator` → Moderator (ID: 998)
  ⚠️ `bot` → Bot (not created)
```

### Simulation

```
/roles simulate
```

Preview all changes without applying:
```
Changes for guild 12345:
  + CREATE Bot
  ~ UPDATE_PERMS Admin: permissions changed
  ~ UPDATE_COLOR Moderator: color changed

⚠️ Unmanaged roles (not in blueprint):
  - Legacy (ID: 997)
```

### Events

All state changes emit EventBus events. Other plugins listen:

```python
@bot.events.on("roles.sync")
async def on_role_sync(event):
    print(f"Roles synced: {event.data}")
```

Event names:
- `roles.plugin_loaded` — plugin initialized
- `roles.plugin_ready` — bot ready
- `roles.sync` — roles synchronized
- `roles.plugin_unloaded` — plugin removed

---

## Capabilities

Plugin defines five granular capabilities:

```python
"roles.manage"   # Sync blueprints, reset config
"roles.create"   # Create new roles (future)
"roles.assign"   # Assign roles to members
"roles.simulate" # Dry-run preview
"roles.debug"    # View state
```

Commands check capabilities:

```python
@slash(description="Sync roles", capabilities=["roles.manage"])
async def roles_sync(self, ctx):
    # User lacks `roles.manage` → ephemeral error, handler skipped
    ...
```

---

## Commands

### `/roles setup`

Initialize default blueprints:
- `bot` — send messages, manage roles, manage channels
- `admin` — ban members, kick members, manage messages
- `moderator` — kick members, manage messages (inherits from member)
- `member` — send messages, read history

### `/roles sync`

Apply blueprint changes to this guild. Policy-gated.

```
✅ Sync completed:
  + CREATE Bot
  ~ UPDATE_PERMS Admin: permissions changed

Use `/roles debug` to inspect state.
```

### `/roles simulate`

Dry-run. Show what would change without applying.

### `/roles debug`

Inspect current state. Show managed vs unmanaged roles.

### `/roles export`

Export blueprints as JSON (for backup or sharing).

```json
{
  "version": "1.0",
  "blueprints": {
    "admin": {
      "name": "Admin",
      "permissions": ["ban_members"],
      ...
    }
  }
}
```

### `/roles reset`

Delete all blueprints (confirmation required).

---

## Testing

Run tests:

```bash
pytest tests/test_roles_plugin.py -v
```

Test coverage:
- ✅ Blueprint validation (names, permissions, cycles)
- ✅ Diff computation (create, update, delete detection)
- ✅ Policy enforcement (self-escalation, dangerous perms)
- ✅ Reconciliation idempotency (apply twice = same result)
- ✅ Storage persistence (save/load)
- ✅ Public API (assign, remove, has, list)
- ✅ Integration (plugin lifecycle, capability registration)

---

## Design Decisions

### Why Blueprints?

- **Declarative** — define intent, not imperative steps
- **Reviewable** — diffs show exactly what will change
- **Versionable** — track config changes in git
- **Safe** — can preview before applying

### Why Idempotent Reconciliation?

- **Recoverable** — crash during apply? Just run sync again
- **Non-destructive** — never deletes unless explicitly enabled
- **Observable** — can diff without applying
- **Testable** — predictable, deterministic behavior

### Why Policy Enforcement?

- **Prevent escalation** — user can't upgrade own permissions
- **Protect admin** — require confirmation for admin changes
- **Block dangerous** — prevent granting `administrator` perm
- **Audit** — all decisions logged and reversible

### Why EventBus?

- **Decoupled** — other plugins listen without knowing implementation
- **Observable** — every state change is traceable
- **Extensible** — plugins can react to role changes
- **Non-blocking** — listeners run concurrently

### Why Public API?

- **No coupling** — other plugins don't call internals
- **Stable contract** — API is versioned, can change internals
- **Type-safe** — full type hints for IDE autocomplete
- **Capability-gated** — can't bypass permissions

---

## v4.0 Design Template

This plugin exemplifies the v4.0 design:

1. **Modular** — separate blueprint, diff, policy, reconcile, storage
2. **Deterministic** — no hidden state or magic
3. **Observable** — EventBus events, debug commands, audit trails
4. **Safe** — policy enforcement, non-destructive defaults
5. **Capable** — fine-grained capability system
6. **Testable** — comprehensive unit + integration tests
7. **Documented** — every class/method has docstrings
8. **Type-safe** — full type hints, dataclasses
9. **Escape-hatchable** — can drop to discord.py anytime
10. **Removable** — plugin can be unloaded cleanly

Every v4.0 plugin should follow this pattern.

---

## License

MIT. See LICENSE file.
