# pyrefly: ignore [missing-import]
import pytest
import threading
import time
import asyncio
import re
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add ui/desktop to path so we can import main
sys.path.append(str(Path(__file__).parent.parent / "ui" / "desktop"))

try:
    # pyrefly: ignore [missing-import]
    import webview
    # pyrefly: ignore [missing-import]
    from main import BotAPI
    WEBVIEW_AVAILABLE = True
except ImportError:
    WEBVIEW_AVAILABLE = False
    BotAPI = None

pytestmark = pytest.mark.skipif(not WEBVIEW_AVAILABLE, reason="pywebview not installed")

class MockBot:
    def __init__(self):
        self.latency = 0.05
        self.guilds = [1, 2, 3]
        self._start_time = time.time()
        self.loop = MagicMock()
    
    def is_ready(self):
        return True
    
    async def close(self):
        pass

@pytest.fixture
def api():
    return BotAPI()

def test_status_reporting_offline(api):
    status = api.get_status()
    assert status["status"] == "offline"
    assert status["uptime"] == 0

def test_invalid_snowflake_validation(api):
    # Invalid guild IDs
    assert "error" in api.start_bot("token", "abc")
    assert "error" in api.start_bot("token", "123") # too short

def test_missing_token_rejection(api):
    assert "error" in api.start_bot("", "123456789012345678")

def test_stop_before_start_graceful(api):
    # Should not crash
    resp = api.stop_bot()
    assert resp["status"] == "stopped"

@patch("main.threading.Thread")
def test_lifecycle_flow_success(mock_thread, api):
    token = "MTE.test.token"
    guild = "123456789012345678"
    
    # Start
    resp = api.start_bot(token, guild)
    assert resp["status"] == "starting"
    assert api._state == "starting"
    
    # Mock bot being ready
    api._bot = MockBot()
    status = api.get_status()
    assert status["status"] == "online"
    assert status["guilds"] == 3
    
    # Stop
    with patch("main.asyncio.run_coroutine_threadsafe") as mock_run:
        resp = api.stop_bot()
        assert resp["status"] == "stopped"
        assert api._bot is None

def test_prevent_double_start(api):
    api._state = "online"
    resp = api.start_bot("token", "123456789012345678")
    assert "error" in resp

def test_log_buffer_max_size_rotation(api):
    # Fill buffer beyond 100
    for i in range(150):
        api._logs.append({"msg": f"test {i}"})
    
    # Let's mock a log record
    record = MagicMock()
    record.levelname = "INFO"
    record.getMessage.return_value = "hello"
    
    import logging
    logger = logging.getLogger("easycord")
    
    for i in range(150):
        logger.info(f"log {i}")
    
    assert len(api._logs) <= 100

def test_exception_masking_security(api):
    # Ensure tokens are not in logs even if bot fails
    token = "SECRET_TOKEN_123"
    
    with patch("main.Bot") as mock_bot_class:
        mock_bot_class.side_effect = Exception(f"Failed with {token}")
        
        def run_sync(target, daemon=True):
            target()
        
        with patch("main.threading.Thread", side_effect=run_sync):
            api.start_bot(token, "123456789012345678")
    
    # Check logs
    assert len(api._logs) > 0
    for log in api._logs:
        assert token not in log["msg"]

def test_memory_usage_reporting(api):
    with patch("main.psutil") as mock_psutil:
        mock_process = MagicMock()
        mock_process.memory_info().rss = 100 * 1024 * 1024 # 100 MB
        mock_psutil.Process.return_value = mock_process
        
        mem = api._get_memory_usage()
        assert mem == 100
