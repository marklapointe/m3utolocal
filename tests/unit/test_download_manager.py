"""Unit tests for global DownloadManager background queue management."""

from __future__ import annotations

from pathlib import Path
import pytest

from m3utolocal.services.download_manager import DownloadManager
from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp

textual = pytest.importorskip("textual")
pytest.importorskip("pytest_asyncio")


def test_download_manager_enqueue(tmp_path: Path):
    mgr = DownloadManager()
    matches = [{"tvg-id": "ch1", "url": "http://example.com/ch1.mp4", "size": 1000}]
    mgr.enqueue(matches, tmp_path)
    assert len(mgr.states) == 1
    assert mgr.states[0].job.channel.tvg_id == "ch1"
    assert mgr.states[0].total == 1000


@pytest.mark.asyncio
async def test_app_navigate_to_queue_screen(tmp_path: Path):
    app = M3UToLocalApp(Settings(m3u_path=str(tmp_path / "chans.m3u")))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.show_downloads_queue([{"tvg-id": "ch1", "url": "http://example.com/1.mp4", "size": 100}])
        await pilot.pause()
        assert "DownloadsScreen" in str(type(app.screen))

        # Navigate back to Home
        await pilot.press("escape")
        await pilot.pause()
        assert "HomeScreen" in str(type(app.screen))

        # Jump back to Active Queue via menu action / key '5'
        await pilot.press("5")
        await pilot.pause()
        assert "DownloadsScreen" in str(type(app.screen))
