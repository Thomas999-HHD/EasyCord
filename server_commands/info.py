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
        await ctx.send_embed(
            title=f"👤 {user.display_name}",
            description=f"**ID:** `{user.id}`\n**Bot:** {user.bot}",
        )

    @slash(description="Show information about a specific role.")
    async def roleinfo(self, ctx, role: discord.Role):
        if ctx.guild is None:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"🏷️ Role: {role.name}",
            color=role.color,
        )
        embed.add_field(name="ID", value=str(role.id), inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        await ctx.respond(embed=embed)

    @slash(description="Show information about this channel.")
    async def channelinfo(self, ctx):
        channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            await ctx.respond("This command only works in a text channel.", ephemeral=True)
            return
        embed = discord.Embed(title=f"#️⃣ #{channel.name}", color=discord.Color.blurple())
        embed.add_field(name="ID", value=str(channel.id), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s", inline=True)
        embed.add_field(name="NSFW", value="Yes" if channel.is_nsfw() else "No", inline=True)
        if channel.topic:
            embed.add_field(name="Topic", value=channel.topic, inline=False)
        await ctx.respond(embed=embed)

    @slash(description="Show the bot's latency.")
    async def ping(self, ctx):
        latency_ms = round(self.bot.latency * 1000)
        await ctx.respond(f"🏓 Pong! Latency: **{latency_ms}ms**")

    @slash(description="Show the top roles in this server.")
    async def roles(self, ctx):
        if ctx.guild is None:
            await ctx.respond("This command only works in a server.", ephemeral=True)
            return
        sorted_roles = sorted(ctx.guild.roles[1:], key=lambda r: r.position, reverse=True)[:15]
        lines = [f"{r.mention} — {len(r.members)} member{'s' if len(r.members) != 1 else ''}" for r in sorted_roles]
        embed = discord.Embed(
            title=f"🏅 Roles in {ctx.guild.name}",
            description="\n".join(lines) or "No roles.",
            color=discord.Color.blurple(),
        )
        await ctx.respond(embed=embed)
