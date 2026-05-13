# EasyCord v6.1.0

Desktop Command Center integration release.

## Highlights

- Packages the `ui` and `ui/easycord-ui` assets into the Python distribution so the desktop Command Center can launch from installed EasyCord packages.
- Adds the `easycord-desktop` console script for direct Command Center startup.
- Exposes `easycord.launch_command_center()` as a first-class EasyCord API entry point.
- Exposes `ui.desktop.launch()` as a lazy launcher so normal EasyCord imports stay dependency-light when `pywebview` is not installed.
- Aligns desktop runtime and visible UI version labels with `6.1.0`.
- Keeps memory telemetry mockable and optional through `psutil`.

## Install

```bash
pip install "easycord[desktop]"
```

## Launch

```bash
easycord-desktop
```

Or from Python:

```python
import easycord

easycord.launch_command_center()
```

## Verification

Expected focused checks:

```bash
python -m compileall -q easycord ui tests
pytest tests/test_desktop_bridge.py tests/test_desktop_integration.py
```
