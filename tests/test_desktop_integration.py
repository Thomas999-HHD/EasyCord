import easycord
import ui.desktop


def test_command_center_public_api_exported():
    assert easycord.__version__ == "6.1.0"
    assert "launch_command_center" in easycord.__all__
    assert callable(easycord.launch_command_center)


def test_desktop_package_exposes_lazy_launcher():
    assert "launch" in ui.desktop.__all__
    assert callable(ui.desktop.launch)
