# Performance Tuning for EasyCord Bots

Guide to optimizing your EasyCord bot for speed, memory, and scalability.

## Overview

Performance optimization focuses on three areas:
1. **Command latency** — time to respond to user interactions
2. **Memory usage** — RAM consumed by the bot process
3. **Throughput** — commands processed per second under load

## Command Latency

### Defer long operations

If a command takes >3 seconds, defer the response:

```python
# ❌ BAD: No defer, Discord times out after 3 seconds
@bot.slash(description="Process data")
async def process(ctx):
    data = await expensive_computation()  # Takes 10 seconds
    await ctx.respond(f"Done: {data}")    # Too late!

# ✅ GOOD: Defer first
@bot.slash(description="Process data")
async def process(ctx):
    await ctx.defer()  # Tell Discord "we're working on it"
    data = await expensive_computation()
    await ctx.respond(f"Done: {data}")
```

### Cache frequently accessed data

```python
# ❌ BAD: Fetch guild config every command
@bot.slash(description="Check config")
async def check_config(ctx):
    cfg = await store.load(ctx.guild_id)  # Disk I/O
    await ctx.respond(f"Enabled: {cfg.get_other('enabled')}")

# ✅ GOOD: Cache with TTL
from functools import lru_cache
import time

config_cache = {}
CACHE_TTL = 300  # 5 minutes

async def get_config_cached(guild_id):
    if guild_id in config_cache:
        cached, timestamp = config_cache[guild_id]
        if time.time() - timestamp < CACHE_TTL:
            return cached
    
    cfg = await store.load(guild_id)
    config_cache[guild_id] = (cfg, time.time())
    return cfg

@bot.slash(description="Check config")
async def check_config(ctx):
    cfg = await get_config_cached(ctx.guild_id)
    await ctx.respond(f"Enabled: {cfg.get_other('enabled')}")
```

### Use database indexes

If using SQLite:

```python
# ✅ GOOD: Index frequently queried columns
import sqlite3

db = sqlite3.connect(".easycord/library.db")
db.execute("CREATE INDEX idx_guild_id ON guilds(guild_id)")
db.execute("CREATE INDEX idx_user_id ON users(user_id)")
db.commit()
```

### Batch operations instead of loops

```python
# ❌ BAD: N+1 queries
@bot.slash(description="Welcome members", permissions=["administrator"])
async def welcome_all(ctx):
    members = await ctx.guild.fetch_members()
    for member in members:
        await member.send("Welcome!")  # One API call per member!

# ✅ GOOD: Batch with concurrent tasks
import asyncio

@bot.slash(description="Welcome members", permissions=["administrator"])
async def welcome_all(ctx):
    await ctx.defer()
    members = [m async for m in ctx.guild.fetch_members()]
    
    # Send DMs concurrently (max 5 at a time to avoid rate limits)
    semaphore = asyncio.Semaphore(5)
    
    async def send_dm(member):
        async with semaphore:
            try:
                await member.send("Welcome!")
            except discord.Forbidden:
                pass
    
    await asyncio.gather(*[send_dm(m) for m in members])
    await ctx.respond(f"Welcomed {len(members)} members")
```

### Paginate large result sets

```python
# ❌ BAD: Load all 1000 members, send as one huge list
@bot.slash(description="List members")
async def list_members(ctx):
    members = await ctx.guild.fetch_members()
    member_names = "\n".join([m.name for m in members])
    await ctx.respond(member_names)  # >2000 chars, fails!

# ✅ GOOD: Paginate with navigation
@bot.slash(description="List members")
async def list_members(ctx):
    await ctx.defer()
    members = [m async for m in ctx.guild.fetch_members()]
    
    # Create pages (20 members per page)
    pages = []
    for i in range(0, len(members), 20):
        chunk = members[i:i+20]
        names = "\n".join([m.name for m in chunk])
        pages.append(f"Members (page {i//20 + 1}):\n{names}")
    
    await ctx.paginate(pages)
```

## Memory Usage

### Use generators instead of lists

```python
# ❌ BAD: Load all messages into memory
async def get_recent_messages(ctx):
    all_messages = await ctx.fetch_messages(limit=10000)  # 10000 in RAM
    for msg in all_messages:
        print(msg.content)

# ✅ GOOD: Iterate without loading all at once
async def get_recent_messages(ctx):
    async for msg in ctx.channel.history(limit=10000):  # Streams, low memory
        print(msg.content)
```

### Clear event handlers on plugin unload

```python
# ❌ BAD: Handler keeps running after plugin unload
class MyPlugin(Plugin):
    @task(hours=1)
    async def periodic_task(self):
        # Runs forever, even if plugin removed
        pass

# ✅ GOOD: Task auto-stops on unload
class MyPlugin(Plugin):
    @task(hours=1)
    async def periodic_task(self):
        # Auto-stopped when plugin.on_unload() called
        pass
    
    async def on_unload(self):
        # Task is automatically cancelled here
        pass
```

### Release resources in plugins

```python
class MyPlugin(Plugin):
    async def on_load(self):
        self.db_connection = await create_db_connection()
        self.cache = {}
    
    async def on_unload(self):
        # ✅ GOOD: Clean up
        if self.db_connection:
            await self.db_connection.close()
        self.cache.clear()
```

### Limit cache sizes

```python
from collections import OrderedDict

class LimitedCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def set(self, key, value):
        self.cache[key] = value
        # Remove oldest items if over limit
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def get(self, key):
        return self.cache.get(key)

cache = LimitedCache(max_size=10000)
```

## Database Optimization

### Use connection pooling

```python
# ❌ BAD: New connection per query
async def fetch_config(guild_id):
    db = sqlite3.connect(".easycord/library.db")
    # Query
    db.close()

# ✅ GOOD: Reuse connections (EasyCord does this internally)
# Use bot.db which handles pooling
@bot.slash()
async def get_config(ctx):
    config = await bot.db.get(ctx.guild_id, "config")
```

### Write batches instead of individual updates

```python
# ❌ BAD: Write each update individually
for user_id in user_ids:
    await bot.db.set(guild_id, f"user_{user_id}", score)

# ✅ GOOD: Batch writes
batch = {}
for user_id in user_ids:
    batch[f"user_{user_id}"] = score
# Pseudo-code: await bot.db.set_batch(guild_id, batch)
```

## Message Throughput

### Handle concurrent commands efficiently

```python
# EasyCord handles this automatically with async/await
# Just make sure operations are truly async:

# ✅ GOOD: All I/O is async
@bot.slash()
async def fetch_user_data(ctx):
    user = await ctx.guild.fetch_member(ctx.user.id)  # Async
    config = await bot.db.get(ctx.guild_id, "config")  # Async
    await ctx.respond(f"Data: {user.name}, {config}")

# ❌ BAD: Blocking operations freeze the bot
import requests
import time

@bot.slash()
async def fetch_external(ctx):
    # Blocking! Freezes entire bot while waiting
    response = requests.get("https://api.example.com/data")
    await ctx.respond(f"Data: {response.json()}")

# ✅ GOOD: Use async HTTP client
import aiohttp

@bot.slash()
async def fetch_external(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as resp:
            data = await resp.json()
    await ctx.respond(f"Data: {data}")
```

### Rate limit aggressively

```python
from easycord import Composer

# ✅ GOOD: Global rate limit with middleware
bot = (
    Composer()
    .rate_limit(limit=10, window=60)  # 10 commands/user/minute
    .build()
)

# ✅ GOOD: Per-command cooldown
@bot.slash(description="...", cooldown=5.0)
async def expensive_command(ctx):
    pass
```

## AI Orchestration Performance

### Limit tool execution steps

```python
from easycord import RunContext

# ❌ BAD: Allow unlimited tool calls
context = RunContext(
    messages=[...],
    ctx=ctx,
    max_steps=100,  # Could run forever
)

# ✅ GOOD: Limit iterations
context = RunContext(
    messages=[...],
    ctx=ctx,
    max_steps=3,    # Max 3 tool calls, then return
    timeout=15.0,   # 15 second timeout
)
```

### Cache LLM responses

```python
import hashlib

llm_cache = {}

async def cached_llm_call(prompt, cache_key=None):
    if cache_key is None:
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
    
    if cache_key in llm_cache:
        return llm_cache[cache_key]
    
    result = await orchestrator.run(...)
    llm_cache[cache_key] = result
    return result
```

## Monitoring & Profiling

### Add timing instrumentation

```python
import time
import logging

logger = logging.getLogger(__name__)

async def timed_operation(name, coro):
    start = time.perf_counter()
    result = await coro
    elapsed = time.perf_counter() - start
    logger.info(f"{name} took {elapsed:.2f}s")
    return result

# Usage
@bot.slash()
async def slow_command(ctx):
    data = await timed_operation("data fetch", expensive_operation())
```

### Monitor memory usage

```python
import psutil
import logging

logger = logging.getLogger(__name__)

@bot.on("ready")
async def log_memory(self):
    process = psutil.Process()
    mem = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Memory usage: {mem:.1f} MB")
```

### Log slow commands

```python
from easycord.middleware import MiddlewareFn

async def log_slow_commands(ctx, proceed):
    start = time.perf_counter()
    try:
        await proceed()
    finally:
        elapsed = time.perf_counter() - start
        if elapsed > 1.0:
            logger.warning(f"{ctx.command_name} took {elapsed:.2f}s (slow)")

bot.use(log_slow_commands)
```

## Scaling Patterns

### Use sharding for large bots (100k+ guilds)

```python
# EasyCord supports discord.py's sharding
from easycord import Bot

bot = Bot(shard_id=0, shard_count=4)  # Run 4 bot instances
bot.run("TOKEN")
```

### Distribute database across regions

For very large bots, consider separating reads/writes:

```python
# Read from read replica
async def get_config(guild_id):
    return await read_db.get(guild_id, "config")

# Write to primary
async def save_config(guild_id, config):
    return await write_db.set(guild_id, "config", config)
```

### Use plugin unloading to reduce memory

```python
# Plugins can be unloaded when not in use
if context.user.is_premium:
    bot.add_plugin(PremiumPlugin())
else:
    await bot.remove_plugin(PremiumPlugin)
```

## Benchmark results

**Example bot (basic setup):**
- Baseline memory: ~50 MB
- Per 1000 cached configs: +1 MB
- Per 10 plugins: +5 MB

**Command latency (deferred):**
- Database read: 50-100ms
- External API call: 200-500ms
- LLM call (via orchestrator): 2-5s

**Throughput:**
- Single bot instance: 100-500 commands/second
- Limited by Discord API rate limits, not EasyCord

## Performance checklist

- [ ] Defer commands that take >1 second
- [ ] Cache frequently accessed data with TTL
- [ ] Batch operations instead of loops
- [ ] Use generators for large result sets
- [ ] Clean up resources in `on_unload()`
- [ ] Limit cache sizes to avoid memory bloat
- [ ] Use async HTTP clients (aiohttp, httpx)
- [ ] Monitor memory and command latency
- [ ] Set rate limits on sensitive commands
- [ ] Log slow commands (>1s) for analysis
- [ ] Profile memory usage periodically
- [ ] Test with realistic guild sizes

## Further reading

- [discord.py performance](https://discordpy.readthedocs.io/en/latest/faq.html)
- [asyncio best practices](https://docs.python.org/3/library/asyncio.html)
- [SQLite optimization](https://www.sqlite.org/bestpractice.html)
