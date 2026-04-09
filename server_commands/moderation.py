import discord

from easycord import Plugin, on, slash


class ModerationPlugin(Plugin):
    """Server moderation helpers."""

    async def on_load(self):
        print(f"[ModerationPlugin] Loaded — connected to {self.bot.user}")

    @slash(description="Announce a message to this channel.")
    async def announce(self, ctx, message: str):
        if not ctx.guild:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Posted by {ctx.user.display_name}")
        await ctx.respond(embed=embed)

    @on("member_join")
    async def greet_member(self, member):
        """DM new members a welcome message."""
        try:
            await member.send(
                f"👋 Welcome to **{member.guild.name}**, {member.name}!\n"
                "Feel free to introduce yourself."
            )
        except Exception:
            pass  # DMs may be disabled

