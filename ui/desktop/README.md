# EasyCord Desktop

Wraps the EasyCord UI in a native window and bundles it as a single executable.

## What you get

- **Windows:** `dist\EasyCord.exe` — one file, no console, no installer required.
- **macOS / Linux:** `dist/EasyCord` — same idea, native binary.

Under the hood: PyWebView hosts an Edge/WebKit2 webview pointed at a localhost
static server that serves `EasyCord.html` and the `easycord-ui/` JSX bundle.
PyInstaller packs Python, the webview runtime, and the assets into one file.

## Build

### Windows

```bat
cd desktop
build.bat
```

Requires Python 3.11+ on PATH. The script creates a venv, installs deps, and
runs PyInstaller against `easycord.spec`. The Edge WebView2 runtime is already
present on Windows 11 and most updated Windows 10 boxes; if it's missing on a
target machine, install the evergreen bootstrapper from Microsoft.

### macOS / Linux

```bash
cd desktop
./build.sh
```

On macOS the binary uses WKWebView (built in). On Linux you need
`libwebkit2gtk-4.0` available at runtime.

## Run from source (no build)

```bash
cd desktop
python -m venv .venv && source .venv/bin/activate     # or .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Layout

```
desktop/
├── main.py             # PyWebView entry point + tiny localhost server
├── easycord.spec       # PyInstaller spec (bundles EasyCord.html + easycord-ui/)
├── requirements.txt    # pywebview + pyinstaller
├── build.bat           # Windows build → dist\EasyCord.exe
├── build.sh            # macOS/Linux build → dist/EasyCord
└── icon.ico            # optional — drop a 256×256 .ico here for the exe icon
```

## Notes

- The HTML loads React + Babel from `unpkg.com`. For fully-offline use, run
  `super_inline_html` (or any inliner) on `EasyCord.html` first and update
  `easycord.spec` to bundle the resulting single file instead.
- The shell is intentionally thin — no IPC, no extras. When the real
  `easycord.dashboard` backend lands, swap the localhost static server in
  `main.py` for the FastAPI app and you have a desktop control plane.
