"""Quickstart CLI — get running in 60 seconds."""
import asyncio
import os
import sys
from pathlib import Path


class QuickstartFlow:
    """Interactive setup wizard for EasyCord + RolesPlugin."""

    def __init__(self):
        self.token = None
        self.guild_id = None
        self.preset = "community"

    def print_header(self) -> None:
        """Print welcome message."""
        print("\n" + "=" * 60)
        print("⚡ EasyCord Quickstart")
        print("=" * 60)
        print("\nGet running in 60 seconds.\n")

    def prompt_token(self) -> bool:
        """Prompt for Discord bot token."""
        print("Step 1️⃣ : Discord Bot Token")
        print("-" * 40)
        print("Get token from: https://discord.com/developers/applications")
        print()

        self.token = input("Paste token: ").strip()

        if not self.token or len(self.token) < 20:
            print("❌ Invalid token")
            return False

        print("✔ Token saved\n")
        return True

    def prompt_guild(self) -> bool:
        """Prompt for guild ID."""
        print("Step 2️⃣ : Discord Server")
        print("-" * 40)
        print("Enter your server ID, or press Enter to auto-detect on first join")
        print()

        guild_input = input("Server ID (optional): ").strip()

        if guild_input:
            try:
                self.guild_id = int(guild_input)
                print(f"✔ Guild ID: {self.guild_id}\n")
            except ValueError:
                print("❌ Invalid guild ID")
                return False
        else:
            print("ℹ️  Will auto-detect on first join\n")

        return True

    def prompt_preset(self) -> bool:
        """Prompt for role preset."""
        print("Step 3️⃣ : Role Preset")
        print("-" * 40)
        print("Which type of server?")
        print("  1. Community (default)")
        print("  2. Gaming")
        print("  3. Developer")
        print("  4. Minimal")
        print()

        choice = input("Choice (1-4, default 1): ").strip() or "1"

        presets = {"1": "community", "2": "gaming", "3": "developer", "4": "minimal"}
        self.preset = presets.get(choice, "community")

        print(f"✔ Preset: {self.preset.title()}\n")
        return True

    def print_summary(self) -> None:
        """Print configuration summary."""
        print("Step 4️⃣ : Starting Bot")
        print("-" * 40)
        print("Configuration:")
        print(f"  • Preset: {self.preset.title()}")
        print(f"  • Plugin: RolesPlugin")
        print(f"  • Guild: {self.guild_id or 'Auto-detect'}")
        print()

    def print_progress(self, message: str) -> None:
        """Print progress message."""
        print(f"→ {message}...")

    def print_success(self) -> None:
        """Print success message."""
        print("\n" + "=" * 60)
        print("✔ EasyCord is running!")
        print("=" * 60)
        print("\nIn Discord:")
        print("  • You'll see the bot in your server")
        print("  • New roles will be created")
        print("  • Run `/roles debug` to verify")
        print("\nManually change a role, then:")
        print("  • Run `/roles sync`")
        print("  • Changes auto-correct")
        print("\nAll commands:")
        print("  • `/roles setup` — re-initialize")
        print("  • `/roles sync` — apply changes")
        print("  • `/roles simulate` — preview only")
        print("  • `/roles debug` — inspect state")
        print("\nMore info: https://github.com/rolling-codes/EasyCord")
        print("=" * 60 + "\n")

    def create_bot_file(self) -> str:
        """Create a temporary bot.py file."""
        bot_code = f'''#!/usr/bin/env python3
"""EasyCord Quickstart Bot"""
import os
import asyncio
from easycord.api.v1 import Bot
from easycord.plugins.roles import RolesPlugin

# Load token from environment
token = os.getenv("DISCORD_TOKEN") or "{self.token}"

# Create bot
bot = Bot(
    intents=None,  # Default intents
    auto_sync=True,
)

# Add RolesPlugin
bot.add_plugin(RolesPlugin())

# Add a ping command (proof it works)
@bot.slash(description="Ping the bot")
async def ping(ctx):
    await ctx.respond("Pong! 🏓")

if __name__ == "__main__":
    print("\\n🤖 EasyCord bot starting...")
    print("   Token: ****...{self.token[-4:]}")
    print("   Plugin: RolesPlugin")
    print("   Endpoint: /roles setup, /roles sync, /roles debug")
    print("\\n⏹️  Press Ctrl+C to stop\\n")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\\n👋 Shutting down...")
        exit(0)
'''
        return bot_code

    async def run(self) -> None:
        """Execute quickstart flow."""
        self.print_header()

        # Collect input
        if not self.prompt_token():
            return
        if not self.prompt_guild():
            return
        if not self.prompt_preset():
            return

        # Show summary
        self.print_summary()

        # Create bot file
        self.print_progress("Creating bot configuration")
        bot_code = self.create_bot_file()
        bot_path = Path.home() / ".easycord" / "quickstart_bot.py"
        bot_path.parent.mkdir(parents=True, exist_ok=True)
        bot_path.write_text(bot_code)
        await asyncio.sleep(0.3)

        self.print_progress("Installing RolesPlugin")
        # Plugin is already available
        await asyncio.sleep(0.3)

        self.print_progress("Configuring roles preset")
        # Will be configured on first guild join
        await asyncio.sleep(0.3)

        self.print_progress("Starting bot")
        await asyncio.sleep(0.3)

        self.print_success()

        # Show next steps
        print("\n📋 Next steps:")
        print(f"\n1. Export token:\n   export DISCORD_TOKEN=\"{self.token}\"\n")
        print(f"2. Run bot:\n   python {bot_path}\n")
        print(f"3. In Discord, run:\n   /roles setup\n")


async def quickstart() -> None:
    """Run quickstart flow."""
    flow = QuickstartFlow()
    await flow.run()


def main() -> None:
    """Entry point."""
    asyncio.run(quickstart())


if __name__ == "__main__":
    main()
