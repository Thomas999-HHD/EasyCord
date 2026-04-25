"""
Minimal bot with NO AI dependencies.

Demonstrates EasyCord core features:
- Slash commands
- Events
- Permissions
- Per-guild configuration
- Error handling

No Orchestrator, no LLM, no AI tools.
Just a production-ready bot.
"""

import os
import logging
from dotenv import load_dotenv
import discord

from easycord import Bot, Composer, Plugin, slash, on, ServerConfigStore

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PLUGIN — Slash commands + events
# ============================================================================

class CorePlugin(Plugin):
    """Bot commands (no AI)."""

    def __init__(self):
        super().__init__()
        self.config = ServerConfigStore(".easycord/config")

    @slash(description="Check your rank")
    async def rank(self, ctx):
        cfg = await self.config.load(ctx.guild_id)
        level = cfg.get_other("user_level", {}).get(str(ctx.user.id), 0)
        await ctx.respond(f"You are level {level}")

    @slash(description="Server info", guild_only=True)
    async def server_info(self, ctx):
        await ctx.defer()
        members = len(ctx.guild.members)
        owner = ctx.guild.owner.mention if ctx.guild.owner else "Unknown"
        await ctx.respond(f"**{ctx.guild.name}**\nMembers: {members}\nOwner: {owner}")

    @on("member_join")
    async def welcome(self, member):
        channel = member.guild.system_channel
        if channel:
            try:
                await channel.send(
                    f"Welcome {member.mention}! 👋\n"
                    f"Account age: <t:{int(member.created_at.timestamp())}:R>"
                )
            except discord.Forbidden:
                logger.warning(f"Can't send to {channel.name}")

# ============================================================================
# BOT
# ============================================================================

bot = (
    Composer()
    .with_members()         # For member join events
    .auto_sync(True)
    .log(level="INFO")
    .catch_errors("An error occurred")
    .rate_limit(limit=10, window=60)
    .add_plugin(CorePlugin())
    .build()
)

@bot.slash(description="Ping")
async def ping(ctx):
    await ctx.respond(f"Pong! ({ctx.bot.latency*1000:.0f}ms)")

@bot.on_error
async def on_error(ctx, error):
    logger.exception(f"Error in {ctx.command_name}", exc_info=error)

@bot.on("ready")
async def on_ready():
    logger.info(f"Ready as {bot.user}")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN not in .env")

    bot.run(token)
