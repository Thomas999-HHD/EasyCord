"""Public package export smoke tests."""
from __future__ import annotations


def test_public_exports_import_from_easycord() -> None:
    import easycord
    from easycord import (
        BotConfig,
        command_error,
        cooldown,
        describe,
        install_type,
        premium_required,
        require_permissions,
    )

    for name in (
        "BotConfig",
        "command_error",
        "cooldown",
        "describe",
        "install_type",
        "premium_required",
        "require_permissions",
    ):
        assert name in easycord.__all__

    assert BotConfig is easycord.BotConfig
    assert callable(command_error)
    assert callable(cooldown)
    assert callable(describe)
    assert callable(install_type)
    assert callable(premium_required)
    assert callable(require_permissions)


def test_no_private_modules_in_public_api() -> None:
    import easycord

    private_names = [
        name
        for name in easycord.__all__
        if name.startswith("_") and not (name.startswith("__") and name.endswith("__"))
    ]
    assert private_names == []
