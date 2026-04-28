from __future__ import annotations

import pytest

from easycord import IntegrationPlugin, Plugin, endpoint, slash


def test_bot_endpoint_register_and_lookup(bot):
    @bot.endpoint("greet")
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    assert bot.get_endpoint("greet") is greet
    assert bot.require_endpoint("greet") is greet


def test_bot_endpoint_supports_bare_decorator(bot):
    @bot.endpoint
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    assert bot.get_endpoint("greet") is greet


@pytest.mark.asyncio
async def test_bot_endpoint_call(bot):
    @bot.endpoint("greet")
    async def greet(name: str) -> str:
        return f"Hello, {name}!"

    result = await bot.call_endpoint("greet", "Tom")
    assert result == "Hello, Tom!"


def test_plugin_endpoint_registration_and_removal(bot):
    class EndpointPlugin(Plugin):
        @endpoint("ping")
        async def ping(self, value: str) -> str:
            return value.upper()

    plugin = EndpointPlugin()
    bot.add_plugin(plugin)
    assert bot.get_endpoint("ping") is not None

    import asyncio

    asyncio.run(bot.remove_plugin(plugin))
    assert bot.get_endpoint("ping") is None


def test_plugin_endpoint_supports_bare_decorator(bot):
    class EndpointPlugin(Plugin):
        @endpoint
        async def ping(self, value: str) -> str:
            return value.upper()

    plugin = EndpointPlugin()
    bot.add_plugin(plugin)
    assert bot.get_endpoint("ping") is not None


def test_integration_plugin_can_access_plugins_and_endpoints(bot):
    class SharedPlugin(Plugin):
        @endpoint("tag.line")
        async def line(self, value: str) -> str:
            return f"[{value}]"

    class ConsumerPlugin(IntegrationPlugin):
        @slash(description="Call shared endpoint", guild_only=True)
        async def use(self, ctx, text: str):
            return await self.call_endpoint("tag.line", text)

    shared = SharedPlugin()
    consumer = ConsumerPlugin()
    bot.add_plugins(shared, consumer)

    assert consumer.get_plugin("SharedPlugin") is shared
    assert consumer.require_endpoint("tag.line") is not None
