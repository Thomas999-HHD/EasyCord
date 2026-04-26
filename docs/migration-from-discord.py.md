# Migrating from discord.py to EasyCord

EasyCord is built on discord.py but removes boilerplate and unifies patterns scattered across discord.py's API. This guide shows concrete side-by-side examples and a migration checklist.

## Side-by-side comparison

### Slash commands

**discord.py:**
```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)

@bot.tree.command()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

bot.run("TOKEN")
```

**EasyCord:**
```python
from easycord import Bot

bot = Bot()

@bot.slash(description="Ping the bot")
async def ping(ctx):
    await ctx.respond("Pong!")

bot.run("TOKEN")
```

**What changed:**
- Removes intent boilerplate (defaults sensible, auto-detected from plugins)
- Single decorator `@bot.slash()` vs `@bot.tree.command()` + manual sync
- Context object handles both first/followup responses automatically
- Command sync automatic on startup (no manual `tree.sync()` calls)

### Events

**discord.py:**
```python
@bot.event
async def on_member_join(member):
    await member.send(f"Welcome {member.name}!")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
```

**EasyCord:**
```python
@bot.on("member_join")
async def on_member_join(member):
    await member.send(f"Welcome {member.name}!")

@bot.on("ready")
async def on_ready():
    print(f"Logged in as {bot.user}")
```

**What changed:**
- Single `@bot.on("event_name")` decorator (no `@bot.event` vs cog listeners confusion)
- Event names without `on_` prefix reduce typos
- Same parameters, consistent with slash command style

### Permission checks

**discord.py:**
```python
@bot.tree.command()
@app_commands.checks.has_permissions(administrator=True)
async def admin_command(interaction: discord.Interaction):
    await interaction.response.send_message("Admin only")
```

**EasyCord:**
```python
@bot.slash(description="...", permissions=["administrator"])
async def admin_command(ctx):
    await ctx.respond("Admin only")
```

**What changed:**
- Single parameter instead of decorator chain (no `@app_commands.checks.has_permissions()` stacking)
- Permission names as strings (less discord.py import ceremony)

### Moderation

**discord.py:**
```python
member = interaction.user
await member.kick(reason="Spamming")
await member.ban(reason="Rule violation", delete_message_days=7)
await member.timeout(timedelta(hours=1), reason="Timeout")
```

**EasyCord:**
```python
# Same in context, even simpler
await ctx.kick(member, reason="Spamming")
await ctx.ban(member, reason="Rule violation", delete_message_days=7)
await ctx.timeout(member, 3600, reason="Timeout")  # seconds, not timedelta
```

**Difference:**
- Duration as seconds (easier) instead of timedelta
- All on context object

### Roles & members

**discord.py:**
```python
role = await guild.create_role(name="Custom Role")
await member.add_roles(role)
await member.remove_roles(role)
```

**EasyCord:**
```python
role = await ctx.create_role("Custom Role")
await ctx.add_role(member, role.id)
await ctx.remove_role(member, role.id)
```

### Responses with embeds

**discord.py:**
```python
embed = discord.Embed(
    title="User Info",
    description="Details",
    color=discord.Color.blue()
)
embed.add_field(name="Status", value="Active", inline=False)
await interaction.response.send_message(embed=embed)
```

**EasyCord:**
```python
from easycord import EmbedBuilder

embed = (
    EmbedBuilder()
    .title("User Info")
    .description("Details")
    .field("Status", "Active", inline=False)
    .build()
)
await ctx.respond(embed=embed)
```

**Differences:**
- Fluent builder (chainable) instead of method calls
- Automatic blue color default
- `.respond()` handles both first and followup sends

### Modal forms

**discord.py:**
```python
class FeedbackModal(discord.ui.Modal, title="Feedback"):
    name = discord.ui.TextInput(label="Name")
    feedback = discord.ui.TextInput(label="Feedback", style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Thanks {self.name}!")

@bot.tree.command()
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal())
```

**EasyCord:**
```python
@bot.slash(description="Open feedback form")
async def feedback(ctx):
    form_data = await ctx.ask_form(
        "Feedback Form",
        name="Your name",
        feedback="Your feedback"
    )
    if form_data:
        await ctx.respond(f"Thanks {form_data['name']}!")
```

**Differences:**
- No class needed — inline form definition
- Auto-handles cancellation
- Returns dict of field values

### Buttons & select menus

**discord.py:**
```python
class ApprovalView(discord.ui.View):
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Approved!")
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Rejected!")

@bot.tree.command()
async def approve_request(interaction: discord.Interaction):
    view = ApprovalView()
    await interaction.response.send_message("Approve?", view=view)
```

**EasyCord:**
```python
@bot.slash(description="Approve request")
async def approve_request(ctx):
    embed = (
        EmbedBuilder()
        .title("Approve?")
        .build()
    )
    await ctx.respond(
        embed=embed,
        buttons=[
            ("Approve", "approve", "success"),
            ("Reject", "reject", "danger"),
        ]
    )

@bot.component("approve")
async def on_approve(ctx):
    await ctx.respond("Approved!", ephemeral=True)

@bot.component("reject")
async def on_reject(ctx):
    await ctx.respond("Rejected!", ephemeral=True)
```

**Differences:**
- Buttons defined inline in respond call
- Handlers registered separately via `@bot.component()`
- Cleaner logic flow

### Configuration per guild

**discord.py:**
```python
# Manual JSON or database
import json

config_file = f"config_{guild_id}.json"
with open(config_file) as f:
    config = json.load(f)
config["moderation_enabled"] = True
with open(config_file, "w") as f:
    json.dump(config, f)
```

**EasyCord:**
```python
from easycord import ServerConfigStore

store = ServerConfigStore()
cfg = await store.load(ctx.guild_id)
cfg.set_other("moderation_enabled", True)
await store.save(cfg)
```

**Differences:**
- Atomic writes (safe for concurrency)
- Per-guild async locks
- Automatic JSON serialization

### Background tasks

**discord.py:**
```python
from discord.ext import tasks

@bot.event
async def on_ready():
    periodic_check.start()

@tasks.loop(hours=1)
async def periodic_check():
    # ...
```

**EasyCord:**
```python
from easycord import Plugin, task

class MyPlugin(Plugin):
    @task(hours=1)
    async def periodic_check(self):
        # Auto-starts on load, auto-stops on unload
        pass

bot.add_plugin(MyPlugin())
```

### Cogs (plugins)

**discord.py:**
```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Ready!")
    
    @app_commands.command()
    async def my_command(self, interaction: discord.Interaction):
        pass

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

**EasyCord:**
```python
from easycord import Plugin, on, slash

class MyPlugin(Plugin):
    async def on_load(self):
        print("Loaded!")
    
    async def on_ready(self):
        print("Ready!")
    
    @slash(description="...")
    async def my_command(self, ctx):
        pass

bot.add_plugin(MyPlugin())
```

**Differences:**
- `Plugin` base class (no multiple inheritance)
- `@on("ready")` instead of `@commands.Cog.listener()`
- `on_load()` and `on_unload()` for setup/teardown
- No async setup function needed

## After migrating: What you can delete

Once your bot is running on EasyCord, you can remove:

- [ ] **Manual intent configuration** — EasyCord auto-detects from plugins
- [ ] **Command sync boilerplate** — `await bot.tree.sync()` (auto on startup)
- [ ] **Decorator chains** — `@app_commands.checks.has_permissions()` → `permissions=...` param
- [ ] **Custom permission checking** — middleware handles it
- [ ] **Rate limit wrappers** — `@app_commands.cooldowns.dynamic_cooldown()` → `cooldown=...` param
- [ ] **Modal form classes** — `ctx.ask_form()` replaces View scaffolding
- [ ] **Button/select View subclasses** — `@bot.component()` and inline buttons in respond
- [ ] **Cog setup boilerplate** — `async def setup(bot)` (plugin auto-wires)
- [ ] **Manual response state tracking** — Context handles first/followup automatically
- [ ] **Custom rate limit classes** — bot.use(rate_limit_middleware(...)) or per-command cooldown

This isn't "adding a layer on top." You're deleting complexity.

## Migration checklist

- [ ] Replace `intents` with `.with_members()`, `.with_messages()`, etc. in Composer
- [ ] Replace `@bot.event` with `@bot.on("event_name")`
- [ ] Replace `@app_commands.command()` with `@bot.slash(description="...")`
- [ ] Replace `discord.Interaction` with `Context` — use `ctx.respond()` instead of `interaction.response.send_message()`
- [ ] Replace permission decorators with `permissions=["..."]` parameter
- [ ] Replace `discord.Embed` with `EmbedBuilder`
- [ ] Replace modal classes with `ctx.ask_form()`
- [ ] Replace View/Button/Select classes with inline button/select in `ctx.respond()` and `@bot.component()`
- [ ] Move Cogs to Plugins with `on_load()` / `on_unload()`
- [ ] Replace `@tasks.loop()` with `@task()` in plugins
- [ ] Replace manual JSON config with `ServerConfigStore`
- [ ] Test all commands with `/` prefix
- [ ] Verify intent requirements are met (check logs for warnings)

## Common pitfalls

### Command sync timing

discord.py: Global commands take up to 1 hour to appear.
**EasyCord:** Same, but you can use `guild_id=` for instant testing:

```python
@bot.slash(description="...", guild_id=YOUR_SERVER_ID)
async def test_command(ctx):
    pass
```

Remove `guild_id` before deploying globally.

### Middleware only on slash commands

discord.py: Decorators work on any command.
**EasyCord:** Middleware (`@bot.use()`) only wraps slash commands, NOT events.

For event-based checks, add logic inside the handler:

```python
@bot.on("member_join")
async def on_join(self, member):
    if member.bot:  # Add check here
        return
```

### Context availability in events

Events don't have a `Context` object — you work with discord.py objects directly:

```python
@bot.on("message")
async def on_message(message):
    # No ctx here, use message/guild/etc.
    if message.author.bot:
        return
```

If you need moderation helpers, use the discord.py API directly or create a context manually in plugins.

## Next steps

1. Start with the simplest commands and migrate them first.
2. Test each command in Discord before moving to the next.
3. Use the `/` prefix (slash commands) — text prefixes are not the focus.
4. Check `docs/examples.md` for patterns.
5. Read `docs/fork-and-expand.md` for structuring a larger bot.
