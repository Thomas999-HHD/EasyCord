# AI context

> Read this file before reading anything else. It tells you where to look so you don't waste tokens.

## Commands

```bash
pip install -e ".[dev]"        # install with dev deps (one-time)
pytest                          # run all tests
pytest tests/test_foo.py        # single file
```

`asyncio_mode = "auto"` is set in `pyproject.toml` — no `@pytest.mark.asyncio` needed.

## Where to look first

| Task | File(s) |
|------|---------|
| Add a bot command/plugin | `server_commands/` |
| Add a bundled framework plugin | `easycord/plugins/` |
| Moderation (manual or AI) | `easycord/plugins/moderation.py` or `ai_moderator.py` |
| Reaction roles setup | `easycord/plugins/reaction_roles.py` |
| Member audit logging | `easycord/plugins/member_logging.py` |
| Bot core (slash/event/middleware/plugin wiring) | `easycord/bot.py` |
| Response helpers | `easycord/context.py` (imports from `_context_*.py`) |
| Built-in middleware | `easycord/middleware.py` |
| Per-guild config persistence | `easycord/server_config.py` |
| Full API reference | `docs/api.md` |
| Architecture overview | `model.md` |

## Architecture

```
easycord/               framework package
  bot.py                Bot — slash/event/middleware/plugin registration
  context.py            Context — aggregates _context_base/_channels/_moderation/_ui
  _context_base.py      respond, defer, embed, DM, form, confirm, paginate
  _context_channels.py  slowmode, lock/unlock, threads, reactions, messages
  _context_moderation.py kick, ban, timeout, unban, roles, nickname, voice
  _context_ui.py        choose, paginate (select-menu UI)
  decorators.py         @slash @on @task (for Plugin methods)
  plugin.py             Plugin base class
  middleware.py         log_middleware, catch_errors, rate_limit, guild_only
  composer.py           fluent Composer builder
  server_config.py      ServerConfigStore — per-guild atomic JSON
  audit.py              AuditLog — embed logging to a Discord channel
  group.py              SlashGroup — slash command groups
  plugins/              bundled drop-in plugins
    levels.py           LevelsPlugin — XP, leveling, ranks
    polls.py            PollsPlugin
    welcome.py          WelcomePlugin
    moderation.py       ModerationPlugin — manual moderation (kick, ban, timeout, warn, mute)
    ai_moderator.py     AIModeratorPlugin — LLM-powered message analysis
    reaction_roles.py   ReactionRolesPlugin — auto-assign roles via emoji
    member_logging.py   MemberLoggingPlugin — audit trail for member changes
    auto_responder.py   AutoResponderPlugin — keyword/regex-triggered responses
    starboard.py        StarboardPlugin — archive popular messages to channel
    invite_tracker.py   InviteTrackerPlugin — track which invite code brought members
server_commands/        example bot plugins (add new bot features here)
tests/                  pytest suite — mirrors easycord/ structure
docs/                   user-facing documentation
model.md                AI context map (architecture + extension guide)
```

## Non-obvious patterns

- **Context is split.** `context.py` assembles `Context` from four `_context_*.py` mixin files. Edit the right mixin, not `context.py` directly.
- **Middleware only wraps slash commands** — not events. `bot.use(fn)` has no effect on `@bot.on(...)` handlers.
- **`on_load()` timing differs.** Plugins added before `bot.run()` have `on_load()` awaited in `setup_hook`. Plugins added after (bot already ready) get `on_load()` scheduled via `asyncio.create_task`.
- **`auto_sync=True` by default** syncs ALL commands globally on startup. Global commands take ~1 h to appear in Discord. Use `guild_id=YOUR_SERVER_ID` on `@bot.slash` during development for instant registration.
- **ServerConfigStore writes are atomic.** Write-to-temp + rename, protected by per-guild async locks. Don't write config JSON directly.
- **`server_commands/` vs `easycord/plugins/`.** `server_commands/` = example bot-specific plugins (not part of the installable package). `easycord/plugins/` = bundled, reusable plugins shipped with the framework.
- **Moderation plugins compose.** Use ModerationPlugin (manual) + AIModeratorPlugin (AI analysis) + ReactionRolesPlugin (role assignment) + MemberLoggingPlugin (audit) independently or together. All use ServerConfigStore for per-guild config.
- **Rate limiting in plugins.** ToolLimiter and RateLimit classes track per-user/tool execution. Use in plugins to prevent abuse (e.g., max 5 bans/hour, max 10 warns/hour).

## Quick Examples

### Manual Moderation (No AI)

```python
from easycord import Bot
from easycord.plugins import ModerationPlugin

bot = Bot()
bot.add_plugin(ModerationPlugin())

# Slash commands now available:
# /kick <user> <reason>
# /ban <user> <reason> <delete_days>
# /unban <user> <reason>
# /timeout <user> <minutes> <reason>
# /warn <user> <reason>
# /mute <user> <reason>
# /unmute <user> <reason>
# /warnings <user>
# /mod_config
```

### AI-Powered Moderation

```python
from easycord import Bot, Orchestrator, FallbackStrategy
from easycord.plugins import AIModeratorPlugin, ModerationPlugin
from easycord.plugins._ai_providers import AnthropicProvider, OllamaProvider

bot = Bot()

# Setup LLM provider chain
strategy = FallbackStrategy([
    AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY")),
    OllamaProvider(base_url="http://localhost:11434"),
])
orchestrator = Orchestrator(strategy, bot.tool_registry)

# Add moderation plugins
bot.add_plugin(ModerationPlugin())
bot.add_plugin(AIModeratorPlugin(orchestrator=orchestrator))

# AI automatically analyzes messages:
# - Detects spam, abuse, NSFW
# - Configurable confidence thresholds (default 0.85)
# - Configurable action levels (notify_only, warn, auto_delete)
# - Uses conversation memory for user context
```

**Configure in Discord:**
```
/mod_enable true
/mod_threshold 0.90
/mod_action_level warn
/mod_add_rule spam
/mod_add_rule abuse
```

### Reaction Roles (Self-Assign)

```python
from easycord import Bot
from easycord.plugins import ReactionRolesPlugin

bot = Bot()
bot.add_plugin(ReactionRolesPlugin())

# In Discord, setup reaction mappings programmatically:
# Find message ID where rules are posted
# /reaction_role_set <message_id> ✅ <@Member role>
# /reaction_role_set <message_id> 🎮 <@Gamer role>
# /reaction_role_set <message_id> 🎨 <@Artist role>

# Users react with emoji → automatically get role
# Users remove reaction → automatically lose role
```

**Use case - Rules message:**
```
Post to #welcome:
"React to agree to rules ✅"
Then: /reaction_role_set <message_id> ✅ <@Verified>
```

### Member Audit Logging

```python
from easycord import Bot
from easycord.plugins import MemberLoggingPlugin

bot = Bot()
bot.add_plugin(MemberLoggingPlugin())

# Logs all member changes to designated channel:
# - Member joins (with account age)
# - Member leaves (with member duration)
# - Nickname changes
# - Role additions/removals
# - Timeout/unmute events
# - Username changes

# Configure:
# /member_log_channel <#audit-channel>
# /member_log_config (to verify)
```

### Auto-Responder (Keywords)

```python
from easycord import Bot
from easycord.plugins import AutoResponderPlugin

bot = Bot()
bot.add_plugin(AutoResponderPlugin())

# In Discord:
# /responder_add hello "Hello there! 👋"
# /responder_add_regex "^how.*" "I'm doing well, thanks!"
# /responder_list
# /responder_remove hello

# Bot replies to any message containing "hello" or matching regex patterns
```

### Starboard (Popular Messages)

```python
from easycord import Bot
from easycord.plugins import StarboardPlugin

bot = Bot()
bot.add_plugin(StarboardPlugin())

# In Discord:
# /starboard_channel #starboard
# /starboard_emoji ⭐
# /starboard_threshold 5

# When a message gets 5+ ⭐ reactions, bot archives it to #starboard
# Removes from starboard if reactions drop below threshold
```

### Invite Tracker

```python
from easycord import Bot
from easycord.plugins import InviteTrackerPlugin

bot = Bot()
bot.add_plugin(InviteTrackerPlugin())

# In Discord:
# /invite_log_channel #welcome-logs

# Bot logs which invite code was used when members join
# Useful for tracking referral sources and growth
```

### Complete Setup (Moderation + Fun + Growth)

```python
from easycord import Bot, Orchestrator, FallbackStrategy
from easycord.plugins import (
    ModerationPlugin,
    AIModeratorPlugin,
    ReactionRolesPlugin,
    MemberLoggingPlugin,
    AutoResponderPlugin,
    StarboardPlugin,
    InviteTrackerPlugin,
)
from easycord.plugins._ai_providers import AnthropicProvider

bot = Bot()

# AI orchestrator (optional)
orchestrator = Orchestrator(
    FallbackStrategy([AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))]),
    bot.tool_registry,
)

# Moderation + Audit
bot.add_plugin(ModerationPlugin())
bot.add_plugin(AIModeratorPlugin(orchestrator=orchestrator))
bot.add_plugin(MemberLoggingPlugin())

# Community
bot.add_plugin(ReactionRolesPlugin())
bot.add_plugin(AutoResponderPlugin())
bot.add_plugin(StarboardPlugin())

# Analytics
bot.add_plugin(InviteTrackerPlugin())

bot.run("TOKEN")
```

### Testing Moderation Plugins

```bash
# Run moderation tests
pytest tests/test_moderation.py -v
pytest tests/test_ai_moderator.py -v
pytest tests/test_reaction_roles_plugin.py -v
pytest tests/test_member_logging_plugin.py -v

# Run all tests
pytest
```

## v3.7.0 Features (New)

### Helper Libraries

Five production-ready helper classes simplify common operations:

```python
from easycord.helpers import (
    EmbedBuilder,           # Quick embeds with .success(), .error(), .info(), .warning() presets
    ContextHelpers,         # Respond helpers, member listing, bulk operations, pagination
    ConfigHelpers,          # ServerConfigStore shortcuts (load_or_default, update_atomic, load_all_guilds)
    ToolHelpers,            # Tool registry utilities (register_batch, check_permission, list_all_tools)
    RateLimitHelpers,       # Rate limit management (create_limit, check, reset_user/tool, get_stats)
)
```

### Decorator Enhancements

**@slash** now supports `rate_limit` parameter:
```python
@slash(description="Ban user", rate_limit=(3, 60))  # Max 3 calls per hour
async def ban(self, ctx, user: discord.User):
    ...
```

**@on** now supports `on_cleanup` callback for plugin cleanup:
```python
@on("ready", on_cleanup=self.cleanup_resources)
async def on_ready(self):
    ...
```

**@ai_tool** now supports `permissions` parameter:
```python
@ai_tool(description="Ban user", permissions=["ban_members"])
async def ban_user(self, ctx, user_id: int):
    ...
```

### Plugin Lifecycle

All plugins now support:
- `on_load()` — Called once when plugin is added (if bot already ready) or when bot starts
- `on_ready()` — Called every time bot becomes ready (including after reconnects)
- `on_unload()` — Called when plugin is removed

### Chainable Plugin Registration

`bot.add_plugin()` now returns the bot for fluent chaining:
```python
bot.add_plugin(ModPlugin()).add_plugin(RolePlugin()).add_plugin(LogPlugin())
```

## Token discipline

- Check `model.md` for architecture before reading source files.
- Check `docs/api.md` for signatures before reading implementation.
- Read only the `_context_*.py` mixin you need, not all four.
- Run `pytest` before claiming tests pass.
