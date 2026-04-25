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

### Complete Setup (All Together)

```python
from easycord import Bot, Orchestrator, FallbackStrategy
from easycord.plugins import (
    ModerationPlugin,
    AIModeratorPlugin,
    ReactionRolesPlugin,
    MemberLoggingPlugin,
)
from easycord.plugins._ai_providers import AnthropicProvider

bot = Bot()

# AI orchestrator (optional)
orchestrator = Orchestrator(
    FallbackStrategy([AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))]),
    bot.tool_registry,
)

# Manual moderation + audit
bot.add_plugin(ModerationPlugin())
bot.add_plugin(MemberLoggingPlugin())

# Optional: AI analysis + reaction roles
bot.add_plugin(AIModeratorPlugin(orchestrator=orchestrator))
bot.add_plugin(ReactionRolesPlugin())

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

## Token discipline

- Check `model.md` for architecture before reading source files.
- Check `docs/api.md` for signatures before reading implementation.
- Read only the `_context_*.py` mixin you need, not all four.
- Run `pytest` before claiming tests pass.
