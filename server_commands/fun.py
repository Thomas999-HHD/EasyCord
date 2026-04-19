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

    @slash(description="Ask the magic 8-ball a yes/no question.")
    async def eightball(self, ctx, question: str):
        answers = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful.",
        ]
        await ctx.respond(f"🎱 *{question}*\n\n**{random.choice(answers)}**")

    @slash(description="Let the bot choose between your options (comma-separated).")
    async def pick(self, ctx, choices: str):
        options = [c.strip() for c in choices.split(",") if c.strip()]
        if len(options) < 2:
            await ctx.respond("Give me at least 2 comma-separated options!", ephemeral=True)
            return
        await ctx.respond(f"🤔 I choose… **{random.choice(options)}**")

    @slash(description="Play rock-paper-scissors against the bot.")
    async def rps(self, ctx, choice: str):
        moves = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        user_move = choice.lower().strip()
        if user_move not in moves:
            await ctx.respond("Choose **rock**, **paper**, or **scissors**.", ephemeral=True)
            return
        bot_move = random.choice(list(moves.keys()))
        wins_against = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if user_move == bot_move:
            outcome = "It's a tie!"
        elif wins_against[user_move] == bot_move:
            outcome = "You win! 🎉"
        else:
            outcome = "I win! 🤖"
        await ctx.respond(
            f"You: {moves[user_move]} **{user_move}**\n"
            f"Me:  {moves[bot_move]} **{bot_move}**\n\n"
            f"**{outcome}**"
        )
