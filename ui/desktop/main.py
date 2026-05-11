"""
EasyCord Desktop — PyWebView shell.

Wraps the EasyCord UI (HTML + JSX) in a native Windows window.
Build to a single .exe via build.bat / build.sh (see README).
"""
from __future__ import annotations

import os
import sys
import threading
import time
import asyncio
import http.server
import socketserver
import socket
from pathlib import Path

# pyrefly: ignore [missing-import]
import webview
import json
import logging
from . import bot  # Assuming we can import from parent or local context

logger = logging.getLogger("easycord.desktop")

APP_TITLE = "EasyCord"
APP_VERSION = "6.0.0"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820
PREFERRED_PORT = 17317


def resource_root() -> Path:
    """Locate bundled assets (works both in dev and inside PyInstaller --onefile)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "web"
    # dev: this file lives in desktop/, assets live one level up
    return Path(__file__).resolve().parent.parent


def find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def serve(root: Path, port: int) -> None:
    """Tiny localhost-only static server. JSX <script type="text/babel"> needs http://, not file://."""
    os.chdir(root)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_a, **_kw):
            pass  # silence

    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever()


from enum import Enum
import re
import atexit

class State(Enum):
    OFFLINE = "offline"
    STARTING = "starting"
    ONLINE = "online"
    STOPPING = "stopping"

class BotAPI:
    def __init__(self):
        self._bot = None
        self._bot_thread = None
        self._logs = []
        self._lock = threading.Lock()
        self._state = State.OFFLINE.value
        self._setup_logging()
        atexit.register(self.stop_bot)

    def _setup_logging(self):
        class UIHandler(logging.Handler):
            def __init__(self, logs):
                super().__init__()
                self.logs = logs
            def emit(self, record):
                # Sanitize: prevent tokens or secrets from leaking into UI logs
                msg = record.getMessage()
                # Basic mask for common token patterns (MTE... or similar)
                msg = re.sub(r"[a-zA-Z0-9_-]{24,}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27,}", "[REDACTED TOKEN]", msg)
                
                self.logs.append({
                    "time": time.strftime("%H:%M:%S"),
                    "level": record.levelname,
                    "msg": msg
                })
                if len(self.logs) > 100:
                    self.logs.pop(0)

        handler = UIHandler(self._logs)
        # Use easycord logger to capture framework events
        logging.getLogger("easycord").addHandler(handler)
        logging.getLogger("easycord").setLevel(logging.INFO)

    def get_status(self):
        if not self._bot or not self._bot.is_ready():
            return {"status": self._state, "uptime": 0, "latency": 0, "guilds": 0}
        
        return {
            "status": State.ONLINE.value,
            "uptime": time.time() - self._bot._start_time,
            "latency": self._bot.latency * 1000 if self._bot.latency else 0,
            "guilds": len(self._bot.guilds),
            "memory": self._get_memory_usage(),
        }

    def _get_memory_usage(self):
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except (ImportError, Exception):
            return 0

    def start_bot(self, token, guild_id=None):
        with self._lock:
            if self._state != State.OFFLINE.value:
                return {"error": f"Bot is already in {self._state} state"}
            
            if not token or len(token) < 20:
                return {"error": "Invalid or missing bot token"}
            
            if guild_id and not re.match(r"^\d{17,20}$", str(guild_id).strip()):
                return {"error": "Guild ID must be a 17-20 digit snowflake"}

            self._state = State.STARTING.value
        
        def run():
            try:
                from easycord import Bot
                gid = int(str(guild_id).strip()) if guild_id and str(guild_id).strip() else None
                self._bot = Bot(sync_guild_id=gid)
                self._bot.run(token)
            except Exception as e:
                err_msg = str(e)
                # Ensure no secrets in the error message
                err_msg = re.sub(r"[a-zA-Z0-9_-]{24,}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27,}", "[REDACTED]", err_msg)
                logger.error(f"Bot failed: {err_msg}")
                with self._lock:
                    self._state = State.OFFLINE.value
                    self._bot = None

        self._bot_thread = threading.Thread(target=run, daemon=True)
        self._bot_thread.start()
        return {"status": "starting"}

    def stop_bot(self):
        with self._lock:
            if not self._bot:
                self._state = State.OFFLINE.value
                return {"status": "stopped"}
            
            self._state = State.STOPPING.value
            
            try:
                if self._bot.loop and self._bot.loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._bot.close(), self._bot.loop)
            except Exception as e:
                logger.error(f"Error closing bot: {e}")
            finally:
                self._bot = None
                self._state = State.OFFLINE.value
                
        return {"status": "stopped"}

    def get_logs(self, limit=50):
        return self._logs[-limit:]


def main() -> None:
    root = resource_root()
    entry = root / "EasyCord.html"
    if not entry.exists():
        raise SystemExit(f"Missing UI bundle at {entry}")

    port = find_free_port(PREFERRED_PORT)
    # FOR SECURITY: Bind only to localhost
    threading.Thread(target=serve, args=(root, port), daemon=True).start()

    api = BotAPI()
    url = f"http://127.0.0.1:{port}/EasyCord.html"
    webview.create_window(
        f"{APP_TITLE} {APP_VERSION}",
        url=url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(960, 600),
        background_color="#1a1326",
        resizable=True,
        js_api=api
    )
    webview.start()


if __name__ == "__main__":
    main()
