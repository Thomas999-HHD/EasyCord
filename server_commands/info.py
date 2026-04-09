import discord

from easycord import Plugin, slash


class InfoPlugin(Plugin):
    """Informational commands."""

    @slash(description="Display server information.")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        if guild is None:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return

        embed = discord.Embed(title=f"ℹ️ {guild.name}", color=discord.Color.blurple())
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Owner", value=str(guild.owner))
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
        await ctx.respond(embed=embed)

    @slash(description="Show your profile info.")
    async def me(self, ctx):
        user = ctx.user
        await ctx.respond_embed(
            title=f"👤 {user.display_name}",
            description=f"**ID:** `{user.id}`\n**Bot:** {user.bot}",
        )

