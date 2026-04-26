# EasyCord v4.0 Execution Pipeline

Complete definition of how interactions flow through the system.

---

## Overview

```
Discord Gateway
       ↓
Adapter (discord.py)
       ↓
EventBus::emit("interaction_create", event)
       ↓
Middleware Chain
       ↓
Capability Check
       ↓
Handler (slash command / event listener / plugin)
       ↓
Response → Discord API
```

All stages are synchronous checkpoint. Failures cascade predictably.

---

## Stage 1: Discord Adapter

**Input:** Raw Discord event or interaction

**Responsibility:**
- Receive from discord.py
- Convert to internal format (Interaction → Context)
- Emit to EventBus

**Code:**
```python
# In discord.py callback
async def callback(interaction: discord.Interaction, **kwargs):
    ctx = Context(interaction)
    
    # Emit pre-middleware event (for logging, metrics, inspection)
    event = Event("interaction.received", {
        "ctx": ctx,
        "interaction_type": "slash" | "component" | "modal",
        "command_name": ctx.command_name,
        "user_id": ctx.user.id,
        "guild_id": ctx.guild.id if ctx.guild else None,
    })
    await bot.events.emit(event)
    
    # Continue to middleware
    ...
```

---

## Stage 2: EventBus (Pre-Middleware)

**Event:** `interaction.received`

**Subscribers:** logging, metrics, plugins (read-only inspection)

**Guarantees:**
- Runs before middleware
- Cannot cancel execution (informational only)
- Failures logged, not fatal
- All handlers run concurrently

**Plugin Hook:**
```python
@bot.events.on("interaction.received")
async def log_command(event):
    ctx = event.data["ctx"]
    print(f"Command: {ctx.command_name} by {ctx.user}")
```

---

## Stage 3: Middleware Chain

**Responsibility:**
- Permission checks (guild_only, admin_only, etc.)
- Rate limiting
- Logging
- Custom user-defined logic

**Execution Order:**
```
Middleware 1 → Middleware 2 → ... → Handler
```

Middlewares registered via:
```python
@bot.middleware
async def my_mw(ctx, proceed):
    print("before")
    await proceed()  # Continue to next middleware or handler
    print("after")
```

**Guarantees:**
- Synchronous ordering (first registered = outermost)
- Can call `ctx.respond()` to short-circuit
- Exceptions bubble up

**Extension Points:**
- `bot.middleware(fn)` - register global middleware
- `@slash(...middleware=[fn])` - command-specific middleware
- Plugin can register middleware in `on_load()`

---

## Stage 4: Capability Check

**Responsibility:**
- Verify declared capabilities are granted
- Map to Discord permissions
- Consult plugin grants

**Integration:**
Capability check happens in middleware OR as part of the `invoke()` function.

**Example:**
```python
@slash(
    description="Ban user",
    capabilities=["ban_members"],  # ← required capability
)
async def ban(ctx, user):
    # Bot checks: does ctx.user have "ban_members" permission?
    # + does plugin define this capability?
    ...
```

**Execution:**
```python
# In _build_slash_callback, before func() call
if capabilities:
    granted = await bot.capability_registry.check_async(
        ctx.interaction,
        *capabilities,
        plugin_name=plugin_name,  # optional
    )
    if not granted:
        await ctx.respond("Missing capabilities", ephemeral=True)
        return
```

---

## Stage 5: Handler Invocation

**Responsibility:**
- Execute the actual command or event listener
- Produce response or side effects

**Types:**
1. Slash command handler
2. Event listener
3. Component callback
4. Modal callback

**Context Access:**
- `ctx.raw_interaction` - raw discord.Interaction
- `ctx.client` - raw discord.Client
- All high-level helpers (kick, ban, respond, etc.)

---

## Stage 6: Response

**Responsibility:**
- Send message back to Discord
- Emit completion events

**Guarantees:**
- One response per interaction (defer then follow-up, or respond)
- Timeout = automatic defer

**Post-Handler Event:**
```python
# After handler completes successfully
event = Event("interaction.completed", {
    "ctx": ctx,
    "status": "success" | "error" | "cancelled",
    "duration_ms": elapsed,
})
await bot.events.emit(event)
```

---

## Error Handling Flow

```
Exception in handler
       ↓
Caught by middleware catch_errors() OR _build_slash_callback
       ↓
EventBus::emit("interaction.error")
       ↓
bot.on_error(func) called (if registered)
       ↓
Ephemeral error message sent (or custom handler takes over)
```

**Event:** `interaction.error`

```python
@bot.events.on("interaction.error")
async def handle_error(event):
    ctx = event.data["ctx"]
    exc = event.data["exception"]
    print(f"Error in {ctx.command_name}: {exc}")
```

---

## Event Naming Convention

**Format:** `domain.action` or `domain.event_type`

### Core Events

| Event | When | Data | Cancellable |
|-------|------|------|-------------|
| `interaction.received` | Interaction received, before middleware | `{ctx, interaction_type, command_name, user_id, guild_id}` | No |
| `interaction.completing` | After middleware, before handler | `{ctx}` | **Yes** (skip handler) |
| `interaction.completed` | Handler returned successfully | `{ctx, duration_ms}` | No |
| `interaction.error` | Unhandled exception in handler | `{ctx, exception}` | No |
| `plugin.loaded` | Plugin loaded | `{plugin_name, plugin}` | No |
| `plugin.unloaded` | Plugin unloaded | `{plugin_name}` | No |

### Plugin-Defined Events

Plugins can emit custom events:

```python
# In plugin
event = Event("moderation.warn", {
    "user_id": user_id,
    "reason": reason,
    "moderator_id": ctx.user.id,
})
await bot.events.emit(event)

# Other plugins listen
@bot.events.on("moderation.warn")
async def notify_user(event):
    user_id = event.data["user_id"]
    # ...
```

**Convention:** Use `plugin_name.event_type` format.

---

## Capability Resolution

### Capabilities Definition

```python
# In registry init or plugin on_load
registry.define(
    name="ban_members",
    discord_perm="ban_members",  # maps to Discord.Permissions
    description="Ban server members"
)

registry.define(
    name="custom.export",
    discord_perm=None,  # No Discord equivalent
    description="Export custom data"
)
```

### Check Order

1. **Overrides** (testing): `registry.override("ban_members", False)`
2. **Plugin Grants** (runtime): `registry.grant("moderation_plugin", "ban_members")`
3. **Discord Permissions** (authority): Member has `ban_members` perm in guild
4. **Deny** (default): If none match, capability not granted

### Enforcement Points

- Slash command decorator: `@slash(..., capabilities=[...])`
- Plugin handler: `@plugin.require("moderation.warn")`
- Runtime check: `await registry.check_async(ctx, "ban_members")`

---

## Plugin Integration Points

Plugins hook at these stages:

```python
class MyPlugin(Plugin):
    async def on_load(self):
        # Register capabilities
        self.bot.capability_registry.grant("my_plugin", "custom.action")
        
        # Register event listeners
        @self.bot.events.on("interaction.received")
        async def on_cmd(event):
            ...
        
        # Register middleware
        @self.bot.middleware
        async def my_mw(ctx, proceed):
            ...
    
    @slash(description="Do thing")
    async def do_thing(ctx):
        # Handler runs here
        ...
```

---

## Multi-Stage Execution Example

User invokes `/ban @user reason:spam`:

```
1. Discord.py receives interaction
2. ADAPTER: Create Context, emit interaction.received event
3. EVENTBUS: Logging plugin logs the invocation
4. MIDDLEWARE: Log middleware logs details
5. MIDDLEWARE: Guild-only middleware checks ctx.guild
6. MIDDLEWARE: Rate limit middleware checks per-user limits
7. CAPABILITY CHECK: Verify "ban_members" capability (check Discord perms)
8. HANDLER: ban_cmd(ctx, user, reason) executes
   - Calls ctx.ban(user, reason)
   - Sends kick message to user
   - Logs to mod channel
9. RESPONSE: ctx.respond("Banned {user}") sent
10. EVENTBUS: Emit interaction.completed event
11. EVENTBUS: Emit custom moderation.ban event
12. PLUGINS: Moderation plugin sees ban event, updates stats
```

---

## Design Principles

### 1. Explicit Over Implicit

- No hidden behavior
- All hooks declared in code
- Failures fast and loud

### 2. Fail-Closed

- Missing permission → deny
- Missing capability → deny
- Exceptions → error response

### 3. Observable

- EventBus logs key transitions
- Middleware can inspect/log
- Plugins can hook any event

### 4. Extensible

- Plugins register at every stage
- Custom capabilities possible
- Event wildcards allow broad listening

### 5. Reversible (Anti-Lock-In)

- Raw `ctx.client` always available
- Raw `ctx.raw_interaction` always available
- No magic, no hidden state
- Easy to drop to discord.py directly

---

## Testing Implications

```python
# Test a command in isolation
async def test_ban_command():
    ctx = create_mock_context(guild=guild, user=moderator)
    
    # Capability override for testing
    bot.capability_registry.override("ban_members", True)
    
    await ban_cmd(ctx, user=target, reason="test")
    
    # Verify response
    assert ctx.messages_sent == ["Banned ..."]
```

---

## Migration from v3.x

v3.x: Implicit event dispatch via `dispatch()` → handlers
v4.0: Explicit EventBus → middleware → capability check → handler

**Compatibility:**
- Old `@bot.on()` still works (re-mapped to EventBus)
- Old `bot.use()` still works (middleware chain unchanged)
- New plugins use explicit EventBus subscription

---

## Future Extensions

**Phase 4 (Roadmap):**
- Distributed event bus (Redis, gRPC)
- Middleware async queue (for long-running ops)
- Capability delegation (admin grants capability to user)
- Conditional middleware (only run if event matches predicate)
