"""
examples/basic_bot.py
~~~~~~~~~~~~~~~~~~~~~
The simplest possible EasyCord bot.

Run:
    pip install "discord.py>=2.0"
    python examples/basic_bot.py
"""

import os

from easycord import EasyCord
from easycord.middleware import error_handler_middleware, logging_middleware

bot = EasyCord()

bot.use(logging_middleware())
bot.use(error_handler_middleware())


@bot.use
async def timing_middleware(ctx, next):
    import time

    start = time.monotonic()
    await next()
    elapsed = (time.monotonic() - start) * 1000
    print(f"  /{ctx.command_name} finished in {elapsed:.1f}ms")


@bot.slash(description="Ping the bot and see its latency.")
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.respond(f"🏓 Pong!  Latency: **{latency_ms}ms**")


@bot.slash(description="Echo your message back to you.")
async def echo(ctx, message: str, times: int = 1):
    if times < 1 or times > 5:
        await ctx.respond("⚠️ `times` must be between 1 and 5.", ephemeral=True)
        return
    await ctx.respond("\n".join([message] * times))


@bot.slash(description="Show info about a user.")
async def userinfo(ctx, member: str = None):
    user = ctx.user
    await ctx.respond_embed(
        title=f"👤 {user.display_name}",
        description=f"ID: `{user.id}`\nBot: {user.bot}",
    )


@bot.on("message")
async def on_message(message):
    if message.author.bot:
        return
    if "hello bot" in message.content.lower():
        await message.reply("👋 Hello there!")


@bot.on("member_join")
async def on_member_join(member):
    print(f"New member: {member.name} joined {member.guild.name}")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    bot.run(token)

