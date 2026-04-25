# Troubleshooting Guide

Common issues and solutions.

## Bot won't start

### "Cannot find token"

```python
# ❌ BAD: Token not set
os.getenv("DISCORD_TOKEN")  # Returns None
bot.run(None)  # Fails

# ✅ FIX: Set environment variable
export DISCORD_TOKEN="your_token_here"
python bot.py

# Or use python-dotenv
from dotenv import load_dotenv
load_dotenv()
bot.run(os.getenv("DISCORD_TOKEN"))
```

**Also check:**
- Is `.env` file in project root?
- Is `.env` file git-ignored?
- Did you regenerate the token in Discord Developer Portal?

### "Invalid token"

Token may be corrupted or expired. Regenerate it:
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot application
3. Click "Reset Token" under Bot settings
4. Update `.env` file with new token

### "Missing intents"

```python
# ❌ BAD: Missing required intents
bot = Bot()  # Default intents may not include what you need

# ✅ FIX: Enable intents
from easycord import Composer

bot = (
    Composer()
    .with_members()      # For member_join, member_remove events
    .with_messages()     # For message content access
    .build()
)

# Or see warning in logs
# [WARNING] MissingIntent: guild_invites required for InviteTrackerPlugin
```

Check logs for `[WARNING] MissingIntent` messages and enable accordingly.

### "Bot already has task running"

If you start the bot twice in the same process:

```python
# ❌ BAD: Running bot twice
bot1 = Bot()
bot1.run("TOKEN")  # Blocks forever

# ✅ FIX: Only run once
bot = Bot()
@bot.slash()
async def ping(ctx):
    await ctx.respond("Pong!")

bot.run("TOKEN")  # Run at the very end
```

## Commands don't appear

### Global commands not syncing

Global commands take up to 1 hour to appear. Test with guild-specific commands first:

```python
# ❌ BAD: Global command (slow)
@bot.slash(description="Hello")
async def hello(ctx):
    pass

# ✅ GOOD: Guild-specific during dev (instant)
@bot.slash(description="Hello", guild_id=YOUR_SERVER_ID)
async def hello(ctx):
    pass

# Remove guild_id before deploying globally
```

**Also check:**
- Is `auto_sync=True` in Bot or Composer?
- Check logs for sync errors
- Bot must have been invited with `applications.commands` scope

### Command appears but error when invoked

```
Error: "Unknown interaction"
```

Bot was restarted after command appeared. Restart the bot if you modified code.

## Commands not responding

### "No response within 3 seconds"

Command takes longer than 3 seconds. Defer first:

```python
# ❌ BAD: Long-running command
@bot.slash(description="Process data")
async def process(ctx):
    await expensive_operation()  # >3 seconds
    await ctx.respond("Done")

# ✅ FIX: Defer
@bot.slash(description="Process data")
async def process(ctx):
    await ctx.defer()
    await expensive_operation()
    await ctx.respond("Done")
```

### "Interaction not found" after responding

You already responded once. Can't respond twice:

```python
# ❌ BAD: Responding twice
@bot.slash()
async def test(ctx):
    await ctx.respond("First")
    await ctx.respond("Second")  # Error! Already responded

# ✅ FIX: Use followup instead
@bot.slash()
async def test(ctx):
    await ctx.respond("First")
    await ctx.respond("Second", followup=True)  # ctx.respond() auto-handles this

# Or edit the original
@bot.slash()
async def test(ctx):
    await ctx.respond("Loading...")
    await ctx.edit_response("Done!")
```

### Bot has no permission to respond

```
Error: discord.Forbidden
```

Bot missing `send_messages` permission in channel.

**Fix:**
1. Go to channel permissions
2. Add bot to role with `send_messages` permission
3. Or give `Administrator` permission temporarily for testing

### Button/component not responding

```python
# ❌ BAD: Button custom_id wrong
@bot.slash()
async def vote(ctx):
    await ctx.respond("Vote!", buttons=[("Yes", "vote_yes", "primary")])

@bot.component("vote_yes")  # Wait for button click
async def on_vote_yes(ctx):
    await ctx.respond("You voted yes!")

# ✅ FIX: Button clicked, should work
# If not responding, check:
# 1. Is bot in guild?
# 2. Did you restart bot after adding handler?
# 3. Is bot online?
```

## Moderation commands fail

### Can't kick/ban/timeout user

```python
@bot.slash(permissions=["kick_members"])
async def kick(ctx, member: discord.Member):
    try:
        await ctx.kick(member, reason="Spam")
    except discord.Forbidden as e:
        await ctx.respond(f"Can't kick: {e}", ephemeral=True)
```

**Common causes:**
- Bot role is below member's role (hierarchy)
- Bot missing `Kick Members` permission
- Target user is server owner
- Member is not in guild

**Fix:**
1. Check bot role position (must be above target)
2. Grant bot `Kick Members` permission
3. Try kicking a lower-ranked member first to test

### Timeout command says "Can't timeout bot"

You're timing out the bot, not the user:

```python
# ❌ BAD: Typo, timing out self
await ctx.timeout(ctx.bot.user, 3600)

# ✅ FIX: Timeout the member
await ctx.timeout(member, 3600)
```

## Database issues

### "Database locked" errors

Multiple bots writing simultaneously. Use file locking:

```python
# ✅ GOOD: EasyCord handles this
# bot.db uses per-guild async locks internally
await bot.db.set(guild_id, "key", value)  # Safe!

# If using ServerConfigStore manually, it also locks
store = ServerConfigStore()
cfg = await store.load(guild_id)  # Locked
cfg.set_other("key", value)
await store.save(cfg)  # Unlocked
```

### "Database file is empty"

SQLite database corrupted or zero bytes. Regenerate:

```bash
# Delete old database
rm .easycord/library.db

# Restart bot (creates new database)
python bot.py
```

**Warning:** This loses all data. Back up before deleting.

### Can't read guild config

```python
# ❌ BAD: Config doesn't exist yet
store = ServerConfigStore()
cfg = await store.load(guild_id)
value = cfg.get_other("key")  # KeyError if key missing

# ✅ FIX: Use defaults
value = cfg.get_other("key", default="fallback")

# Or create config first
cfg = ServerConfig()
cfg.set_other("key", "value")
await store.save(cfg)
```

## Event handlers not firing

### Member join event not triggering

Did you enable the `members` intent?

```python
# ❌ BAD: Default intents don't include members
bot = Bot()

@bot.on("member_join")
async def welcome(member):
    pass  # Never called!

# ✅ FIX: Enable members intent
from easycord import Composer

bot = (
    Composer()
    .with_members()
    .build()
)

@bot.on("member_join")
async def welcome(member):
    print("Member joined!")  # Now works!
```

### Message event not triggering

Did you enable `messages` intent and message_content?

```python
# ❌ BAD: Can't read message content
bot = Bot().with_messages()

@bot.on("message")
async def log_message(message):
    print(message.content)  # Empty!

# ✅ FIX: Need message_content intent
from easycord import Composer

bot = (
    Composer()
    .with_messages()
    .build()
)

@bot.on("message")
async def log_message(message):
    print(message.content)  # Now has content!
```

### Plugin event handlers not registering

Did you call `bot.add_plugin()` before `bot.run()`?

```python
# ❌ BAD: Plugin added after bot starts
bot = Bot()

@bot.slash()
async def test(ctx):
    pass

bot.run("TOKEN")

# ... later in code, never executed
bot.add_plugin(MyPlugin())

# ✅ FIX: Add plugins before run()
bot = Bot()
bot.add_plugin(MyPlugin())
bot.add_plugin(AnotherPlugin())

@bot.slash()
async def test(ctx):
    pass

bot.run("TOKEN")
```

## Permissions and middleware

### "Missing permissions" even with admin

Middleware checks aren't being run on this command:

```python
# ❌ BAD: Middleware only runs on slash commands
@bot.on("message")
async def on_message(message):
    # No middleware here, manually check
    if not message.author.guild_permissions.administrator:
        return

# ✅ GOOD: Use slash command with permission
@bot.slash(description="...", permissions=["administrator"])
async def admin_command(ctx):
    # Permission checked automatically
    pass
```

### Command requires permission but user can invoke

Permission check is decorative but not enforced:

```python
# ⚠️ WARNING: This doesn't actually block unpermissioned users
@bot.slash(description="...", permissions=["kick_members"])
async def kick(ctx):
    # User without permission can still invoke
    # Check manually if needed
    if not ctx.member.guild_permissions.kick_members:
        await ctx.respond("No permission", ephemeral=True)
        return
```

## AI Orchestration issues

### LLM provider doesn't respond

```python
from easycord import Orchestrator, FallbackStrategy, RunContext
from easycord.plugins import AnthropicProvider, GroqProvider

# Create fallback chain
orchestrator = Orchestrator(
    strategy=FallbackStrategy([
        AnthropicProvider(),  # Try Anthropic first
        GroqProvider(),       # Fallback to Groq
    ]),
    tools=bot.tool_registry,
)

try:
    result = await orchestrator.run(RunContext(...))
except Exception as e:
    await ctx.respond(f"LLM error: {e}", ephemeral=True)
```

**Check:**
1. API keys set (ANTHROPIC_API_KEY, GROQ_API_KEY)?
2. API rate limits exceeded?
3. Network connection?
4. Provider API status?

### Tool not callable by AI

Tool not registered or missing permission:

```python
# ✅ GOOD: Tool properly registered
@ai_tool(description="Get user level", safety=ToolSafety.SAFE)
async def get_level(self, ctx, user_id: int):
    return f"User {user_id} is level 5"

# ✅ GOOD: Tool with permission requirement
@ai_tool(
    description="Kick user",
    safety=ToolSafety.CONTROLLED,
    require_admin=True,
)
async def kick_user(self, ctx, user_id: int):
    member = await ctx.guild.fetch_member(user_id)
    await member.kick()
    return f"Kicked {member.name}"

# AI won't call it if invoker isn't admin
```

## Performance issues

### Bot slow, commands taking >1 second

Enable timing logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now check logs for slow commands and database queries
```

See [performance tuning guide](performance-tuning.md) for optimization steps.

### Memory constantly increasing

Likely memory leak. Check:
1. Are plugins cleaning up in `on_unload()`?
2. Are event handlers registered multiple times?
3. Is cache growing without bounds?

```python
# ✅ FIX: Clean up in on_unload
class MyPlugin(Plugin):
    async def on_load(self):
        self.cache = {}
        self.connection = await connect_db()
    
    async def on_unload(self):
        self.cache.clear()  # Clear cache
        await self.connection.close()  # Close DB
```

## Getting help

### Debugging checklist

When something breaks:

1. **Check logs** for `[ERROR]` or `[WARNING]` messages
2. **Enable debug logging** `logging.basicConfig(level=logging.DEBUG)`
3. **Reduce to minimal example** — does the issue happen in a blank bot?
4. **Check Discord status** — is Discord API having issues?
5. **Test with fresh token** — regenerate bot token
6. **Check bot permissions** — is bot invited with right scopes?
7. **Verify environment variables** — `echo $DISCORD_TOKEN`

### Report issues

Found a bug? Report on GitHub:

```
Title: [Short description]

Reproduce:
1. Do X
2. Do Y
3. See Z

Expected: [What should happen]
Actual: [What happens instead]

Logs:
[Full error message with traceback]

Environment:
- Python: 3.10
- EasyCord: 3.7.0
- discord.py: 2.0.0
```

### Ask questions

Before asking:
- Check this guide
- Check [API reference](api.md)
- Check [examples](examples.md)
- Run `pytest` to verify basic functionality

## Common error codes

| Error | Cause | Fix |
|-------|-------|-----|
| `discord.Forbidden` | Missing permissions | Add permission to bot role |
| `discord.NotFound` | Resource doesn't exist | Check ID, user in guild, etc. |
| `asyncio.TimeoutError` | Operation took >3s | Defer command |
| `discord.HTTPException` | API error, rate limit, or invalid data | Check logs, wait, retry |
| `RuntimeError: Tried to use ctx in DM` | Using guild-only feature in DM | Use `guild_only=True` |
| `ValueError: Cannot create Embed` | Embed missing required field | Add title to embed |

## Further reading

- [discord.py troubleshooting](https://discordpy.readthedocs.io/en/latest/faq.html)
- [Discord API docs](https://discord.com/developers/docs)
- [EasyCord GitHub issues](https://github.com/rolling-codes/EasyCord/issues)
