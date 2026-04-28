from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from easycord import Bot, Cog
from easycord.decorators import slash


def test_cog_listener_and_inspection():
    class SampleCog(Cog):
        @slash(description="Say hi")
        async def hello(self, ctx):
            pass

        @Cog.listener()
        async def on_message(self, message):
            pass

    cog = SampleCog()
    assert cog.qualified_name == "SampleCog"
    assert [cmd.__name__ for cmd in cog.get_commands()] == ["hello"]
    assert cog.get_app_commands()[0].__name__ == "hello"
    assert cog.get_listeners()[0][0] == "message"


def test_add_cog_get_cog_and_cogs(bot):
    class SampleCog(Cog):
        @slash(description="Ping")
        async def ping(self, ctx):
            pass

    cog = SampleCog()
    bot.add_cog(cog)

    assert bot.get_cog("SampleCog") is cog
    assert bot.cogs["SampleCog"] is cog


@pytest.mark.asyncio
async def test_remove_cog(bot):
    class SampleCog(Cog):
        @slash(description="Ping")
        async def ping(self, ctx):
            pass

    cog = SampleCog()
    bot.add_cog(cog)

    await bot.remove_cog("SampleCog")

    assert bot.get_cog("SampleCog") is None


@pytest.mark.asyncio
async def test_load_unload_and_reload_extension(bot):
    root = Path(".extension-test-data")
    root.mkdir(exist_ok=True)
    module_dir = root / f"ext_{uuid4().hex}"
    module_dir.mkdir()
    module_name = f"ext_{uuid4().hex}"
    module_path = module_dir / f"{module_name}.py"
    module_path.write_text(
        "from easycord import Cog, slash\n"
        "\n"
        "class SampleCog(Cog):\n"
        "    @slash(description='Ping')\n"
        "    async def ping(self, ctx):\n"
        "        pass\n"
        "\n"
        "async def setup(bot):\n"
        "    bot.add_cog(SampleCog())\n"
        "\n"
        "async def teardown(bot):\n"
        "    pass\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(module_dir))
    importlib.invalidate_caches()
    try:
        module = await bot.load_extension(module_name)
        assert module.__name__ == module_name
        assert bot.get_cog("SampleCog") is not None
        assert module_name in bot.extensions

        await bot.reload_extension(module_name)
        assert bot.get_cog("SampleCog") is not None

        await bot.unload_extension(module_name)
        assert bot.get_cog("SampleCog") is None
        assert module_name not in bot.extensions
    finally:
        if str(module_dir) in sys.path:
            sys.path.remove(str(module_dir))
        shutil.rmtree(module_dir, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)

