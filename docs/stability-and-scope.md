# Stability & Scope

## What "v3.7.0 complete" means

EasyCord v3.7.0 is production-ready, with explicit guarantees and intentional gaps.

## API Stability

### Frozen (won't break)

These APIs are stable. Upgrades within v3.x won't break them:

- **Bot** — slash commands, events, middleware, plugins, component routing
- **Context** — respond, defer, moderation (kick/ban/timeout), member/role operations, channel operations
- **Plugin** — on_load, on_unload, on_ready lifecycle
- **Decorators** — @slash, @on, @task, @component, @modal, @ai_tool
- **ServerConfigStore** — load, save, atomic writes per guild
- **Builders** — EmbedBuilder, ButtonRowBuilder, SelectMenuBuilder, ModalBuilder
- **Helpers** — ConfigHelpers, ContextHelpers, ToolHelpers, RateLimitHelpers
- **AI** — Orchestrator, ToolRegistry, @ai_tool, ToolSafety levels, FallbackStrategy

Breaking changes (if any) require major version bump (4.0.0).

### Evolving (may change semantics, not signatures)

These may change in v3.x but not in breaking ways:

- **Orchestrator internals** — tool execution order, retry logic, timeout enforcement
- **Middleware behavior** — rate limit windows, error handler invocation
- **Database schema** — internal storage format (data migrated automatically on upgrade)
- **Plugin loading order** — command registration sequence

Apps using public APIs won't break. Internal details may shift.

### Implementation details (may change anytime)

These are not public contracts:

- EasyCordDatabase internal storage
- Event dispatch order (if not documented)
- Plugin.__dict__ contents
- Middleware internal state

Don't rely on these across upgrades.

## What's included (v3.7.0)

**Core framework:**
- Slash commands, context menus, buttons, selects, modals
- Event listeners with auto-wiring
- Middleware stack (logging, error handling, rate limits, permission checks)
- Plugin architecture with lifecycle hooks
- Per-guild configuration (ServerConfigStore)
- Background tasks (@task)

**Bundled plugins:**
- ModerationPlugin (manual kick/ban/timeout/warn/mute)
- AIModeratorPlugin (LLM-powered message analysis)
- ReactionRolesPlugin (auto-assign via emoji)
- MemberLoggingPlugin (audit trail for joins/leaves/roles)
- AutoResponderPlugin (keyword/regex triggers)
- StarboardPlugin (popular message archival)
- InviteTrackerPlugin (which code brought members)
- WelcomePlugin (new member messages)
- PollsPlugin (emoji voting)
- LevelsPlugin (XP/leveling system)
- TagsPlugin (snippet storage)

**AI orchestration:**
- Orchestrator with multi-provider routing (Anthropic, OpenAI, Groq, Gemini, Ollama, etc.)
- FallbackStrategy for provider chains
- Tool registry with SAFE/CONTROLLED/RESTRICTED safety levels
- @ai_tool decorator for exposing functions to AI
- Conversation memory for multi-turn context
- RunContext for bounded execution (max_steps, timeout)

**Developer experience:**
- Fluent Composer builder for declarative setup
- EmbedBuilder and helpers for common patterns
- Localization support (multi-language per guild)
- Async-first design (no blocking operations)
- Comprehensive error handling defaults

**Production readiness:**
- Atomic per-guild configuration writes
- Rate limiting (per-user, per-tool, per-guild)
- Permission enforcement
- Audit logging
- Graceful error handling
- Monitoring hooks (logging integration)

## What's not included (intentional gaps)

### Deferred to v3.5+

These are designed but not shipped:

- **Thread management** — ctx.create_thread, archive, add_members
- **Voice/audio** — connect_voice, audio playback abstraction
- **Advanced scheduling** — beyond @task (cron-like patterns)
- **Custom providers** — template for integrating non-standard LLMs
- **Event RSVP tracking** — plugin extending InviteTracker for scheduled events

Not implemented because:
- Require careful design (threading complexity)
- Have lower adoption (voice is edge case)
- Can be added without breaking changes

### Out of scope (won't ship)

**Text commands (prefix-based)** — focus is slash commands (better UX, Discord platform direction).

**Database abstraction beyond ServerConfigStore** — use bot.db (SQLite) directly or bring your own. EasyCord doesn't pretend to be an ORM.

**Authentication/OAuth** — bots authenticate with token, not OAuth. Use discord.py directly if you need webhook OAuth.

**Rich media handling** — video/audio processing. Compose with ffmpeg/moviepy yourself.

**Web server hosting** — bots are async services, not web apps. If you need HTTP endpoints, run separate service.

**Distributed tracing** — defer to operator (instrument with OpenTelemetry yourself if needed).

## Extension surface

Places you're expected to customize:

### Write custom plugins

```python
class YourPlugin(Plugin):
    @slash(description="...")
    async def your_command(self, ctx):
        pass

bot.add_plugin(YourPlugin())
```

### Write custom middleware

```python
async def custom_check(ctx, proceed):
    if some_check:
        await proceed()

bot.use(custom_check)
```

### Write custom AI providers

Inherit from AIProvider, implement _init_client() and query():

```python
class YourProvider(AIProvider):
    def _init_client(self):
        self.client = your_llm_client()
    
    async def query(self, prompt: str) -> str:
        return await self.client.generate(prompt)

strategy = FallbackStrategy([YourProvider(), ...])
```

### Write custom event handlers

```python
@bot.on("message")
async def analyze(message):
    # Custom logic
    pass
```

### Use bot.db for custom data

```python
await bot.db.set(guild_id, "my_key", {"nested": "data"})
value = await bot.db.get(guild_id, "my_key")
```

These are supported. We test them. They're stable.

## Upgrading safely

### v3.x to v3.y (minor bumps)

```bash
pip install --upgrade easycord
# No migration needed, all APIs frozen
python bot.py
```

### Check logs for deprecation warnings

If upgrading and bot emits:

```
[WARNING] DeprecatedAPI: @on_cleanup is deprecated, use on_unload instead
```

You have until 4.0.0 to migrate. Not urgent.

### Database upgrades automatic

If bot.db schema changes, migration runs on startup:

```
[INFO] Migrating database from v1 to v2...
[INFO] Migration complete
```

No manual steps.

## Support windows

- **v3.7.0** — latest, fully supported
- **v3.6.x** — security fixes only
- **v3.5.x and earlier** — EOL, no support

Upgrade to latest for new plugins and features.

## Philosophy

EasyCord v3.7.0 is **batteries-included but not all-encompassing**.

We ship:

✅ Complete bot framework (commands, events, moderation, plugins)
✅ Production-ready bundled plugins (moderation, logging, leveling)
✅ AI orchestration (multi-provider, sandboxed, auditable)
✅ Configuration management (per-guild, atomic, safe)
✅ Error handling (graceful, logged, user-friendly)

We don't ship:

❌ Every conceivable feature (voice, video, OAuth, database)
❌ Infinite extensibility (if it's out of scope, you use discord.py directly)
❌ Alpha/beta experiments (what ships is stable)

This focus makes EasyCord adoptable for production use while leaving room for custom features.

## Getting involved

### Report bugs

Found a regression? File an issue on GitHub with:
- Exact version (python bot.py outputs it)
- Minimal reproducer
- Actual vs expected behavior

### Suggest features

New plugin? New AI provider? Use GitHub discussions.

Features in scope:
- Things that fit the framework philosophy (unified, batteries-included)
- Things with clear demand (multiple people asking)

Features out of scope:
- Things better as separate packages
- Niche use cases (fork and extend)

### Contribute

Pull requests welcome. See CONTRIBUTING.md.

Priorities:
1. Bug fixes
2. Test coverage (every feature has tests)
3. Documentation (docs guide users)
4. Performance (v3.x → faster, not slower)
5. New plugins (bundled, stable, tested)

Non-priorities:
- Scope creep (if it's out of scope, it's out)
- Experimental features (ship stable or don't ship)
- Dependency hell (don't add heavy dependencies)
