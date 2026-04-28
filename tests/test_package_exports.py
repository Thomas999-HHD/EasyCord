from easycord import (
    AnnouncementsPlugin,
    AutoReplyPlugin,
    Cog,
    GuildPlugin,
    JsonConfigPlugin,
    LocalizationManager,
    GroupCog,
    component,
    message_command,
    modal,
    user_command,
)


def test_package_exports_include_beginner_decorators():
    assert component is not None
    assert modal is not None
    assert user_command is not None
    assert message_command is not None


def test_package_exports_include_localization_manager():
    assert LocalizationManager is not None


def test_package_exports_include_plugin_helpers():
    assert GuildPlugin is not None
    assert JsonConfigPlugin is not None
    assert AnnouncementsPlugin is not None
    assert AutoReplyPlugin is not None


def test_package_exports_include_cogs():
    assert Cog is not None
    assert GroupCog is not None
