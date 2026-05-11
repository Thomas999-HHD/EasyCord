"""Tests for guild structure adaptation helpers."""
from __future__ import annotations

from types import SimpleNamespace

from easycord import Bot, ServerConfigStore, plan_guild_adaptation


def _channel(channel_id: int, name: str) -> SimpleNamespace:
    return SimpleNamespace(id=channel_id, name=name)


def _role(role_id: int, name: str) -> SimpleNamespace:
    return SimpleNamespace(id=role_id, name=name)


def _guild() -> SimpleNamespace:
    return SimpleNamespace(
        id=123,
        name="Example Guild",
        text_channels=[
            _channel(10, "general"),
            _channel(11, "mod-logs"),
            _channel(12, "welcome"),
            _channel(13, "announcements"),
            _channel(14, "rules"),
            _channel(15, "ticket-support"),
        ],
        roles=[
            _role(1, "@everyone"),
            _role(20, "Admin"),
            _role(21, "Moderator"),
            _role(22, "Verified Member"),
        ],
    )


def test_plan_guild_adaptation_infers_channels_and_roles() -> None:
    plan = plan_guild_adaptation(_guild())

    assert plan["ok"] is True
    assert plan["guild_id"] == 123
    assert plan["channels"]["logging"] == 11
    assert plan["channels"]["welcome"] == 12
    assert plan["channels"]["announcements"] == 13
    assert plan["channels"]["rules"] == 14
    assert plan["channels"]["support"] == 15
    assert plan["roles"]["admin"] == 20
    assert plan["roles"]["moderator"] == 21
    assert plan["roles"]["member"] == 22
    assert all({"kind", "key", "id", "name", "confidence"} <= set(match) for match in plan["matches"])


def test_plan_guild_adaptation_warns_when_core_structure_is_missing() -> None:
    guild = SimpleNamespace(
        id=456,
        name="Small Guild",
        text_channels=[_channel(1, "chat")],
        roles=[_role(2, "Member")],
    )

    plan = plan_guild_adaptation(guild)

    assert plan["channels"]["general"] == 1
    assert any("No logging channel" in warning for warning in plan["warnings"])
    assert any("admin or moderator role" in warning for warning in plan["warnings"])


async def test_apply_guild_adaptation_saves_server_config(tmp_path) -> None:
    store = ServerConfigStore(str(tmp_path / "config"))
    bot = Bot(
        auto_sync=False,
        db_backend="memory",
        auto_adapt_guilds=True,
        guild_config_store=store,
    )
    try:
        saved = await bot.apply_guild_adaptation(_guild())
        cfg = await store.load(123)

        assert saved["applied_channels"]["logging"] == 11
        assert cfg.get_channel("logging") == 11
        assert cfg.get_channel("welcome") == 12
        assert cfg.get_role("admin") == 20
        assert cfg.get_other("guild_adaptation")["guild_name"] == "Example Guild"
    finally:
        await bot.close()


async def test_apply_guild_adaptation_preserves_existing_config_by_default(tmp_path) -> None:
    store = ServerConfigStore(str(tmp_path / "config"))
    cfg = await store.load(123)
    cfg.set_channel("logging", 999)
    cfg.set_role("admin", 888)
    await store.save(cfg)

    bot = Bot(auto_sync=False, db_backend="memory", guild_config_store=store)
    try:
        saved = await bot.apply_guild_adaptation(_guild())
        loaded = await store.load(123)

        assert loaded.get_channel("logging") == 999
        assert loaded.get_role("admin") == 888
        assert saved["preserved_channels"]["logging"] == 999
        assert saved["preserved_roles"]["admin"] == 888
    finally:
        await bot.close()


async def test_on_guild_join_auto_adapts_when_enabled(tmp_path) -> None:
    store = ServerConfigStore(str(tmp_path / "config"))
    bot = Bot(
        auto_sync=False,
        db_backend="memory",
        auto_adapt_guilds=True,
        guild_config_store=store,
    )
    try:
        await bot.on_guild_join(_guild())
        cfg = await store.load(123)
        guild_record = await bot.db.get_guild(123)

        assert cfg.get_channel("logging") == 11
        assert guild_record is not None
    finally:
        await bot.close()
