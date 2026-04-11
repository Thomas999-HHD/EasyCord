import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from easycord import Bot, Plugin
from easycord.decorators import task


@pytest.fixture
def bot():
    mock_tree = MagicMock()
    mock_tree.sync = AsyncMock()

    with patch("discord.Client.__init__", return_value=None), \
         patch("easycord.bot.app_commands.CommandTree", return_value=mock_tree):
        b = Bot(intents=MagicMock(), auto_sync=False)
        b.is_ready = MagicMock(return_value=False)
        return b


def test_task_decorator_stamps_attributes():
    class MyPlugin(Plugin):
        @task(seconds=30)
        async def my_task(self):
            pass

    p = MyPlugin()
    assert p.my_task._is_task is True
    assert p.my_task._task_interval == 30.0


def test_task_decorator_minutes():
    class MyPlugin(Plugin):
        @task(minutes=2)
        async def my_task(self):
            pass

    assert MyPlugin().my_task._task_interval == 120.0


def test_task_decorator_hours():
    class MyPlugin(Plugin):
        @task(hours=1)
        async def my_task(self):
            pass

    assert MyPlugin().my_task._task_interval == 3600.0


def test_task_decorator_combined():
    class MyPlugin(Plugin):
        @task(hours=1, minutes=30, seconds=15)
        async def my_task(self):
            pass

    assert MyPlugin().my_task._task_interval == 3600 + 1800 + 15


def test_task_zero_interval_raises():
    with pytest.raises(ValueError, match="greater than zero"):
        task(seconds=0)


def test_add_plugin_does_not_start_tasks_before_ready(bot):
    class MyPlugin(Plugin):
        @task(seconds=1)
        async def my_task(self):
            pass

    plugin = MyPlugin()
    bot.add_plugin(plugin)
    # Bot is not ready, so no tasks should have been started
    assert id(plugin) not in bot._task_handles


async def test_start_plugin_tasks_creates_asyncio_tasks(bot):
    ran = []

    class MyPlugin(Plugin):
        @task(seconds=100)
        async def my_task(self):
            ran.append(True)

    plugin = MyPlugin()
    plugin._bot = bot
    bot._plugins.append(plugin)
    bot._start_plugin_tasks(plugin)

    assert id(plugin) in bot._task_handles
    assert len(bot._task_handles[id(plugin)]) == 1

    # Cancel the task so it doesn't keep running
    for handle in bot._task_handles[id(plugin)]:
        handle.cancel()
        try:
            await handle
        except asyncio.CancelledError:
            pass


async def test_remove_plugin_cancels_tasks(bot):
    class MyPlugin(Plugin):
        @task(seconds=100)
        async def my_task(self):
            pass

    plugin = MyPlugin()
    plugin._bot = bot
    bot._plugins.append(plugin)
    bot._start_plugin_tasks(plugin)

    assert id(plugin) in bot._task_handles
    await bot.remove_plugin(plugin)
    assert id(plugin) not in bot._task_handles
