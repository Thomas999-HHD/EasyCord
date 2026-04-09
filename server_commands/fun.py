import random

from easycord import Plugin, slash


class FunPlugin(Plugin):
    """Silly fun commands."""

    @slash(description="Roll a dice with N sides.")
    async def roll(self, ctx, sides: int = 6):
        result = random.randint(1, sides)
        await ctx.respond(f"🎲 You rolled a **{result}** (d{sides})")

    @slash(description="Flip a coin.")
    async def flip(self, ctx):
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        await ctx.respond(result)

    @slash(description="Pick a random number in a range.")
    async def random_number(self, ctx, minimum: int = 1, maximum: int = 100):
        if minimum >= maximum:
            await ctx.respond("⚠️ `minimum` must be less than `maximum`.", ephemeral=True)
            return
        await ctx.respond(f"🔢 Your number: **{random.randint(minimum, maximum)}**")

