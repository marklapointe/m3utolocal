"""Pytest fixtures and path setup."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_m3u(tmp_path: Path) -> Path:
    content = """#EXTM3U
#EXTINF:-1 tvg-id="Matrix Reloaded" tvg-name="The Matrix Reloaded",The Matrix Reloaded
http://example.com/vod/matrix.mp4
#EXTINF:-1 tvg-id="LiveNews" tvg-name="Live News"
http://example.com/live/news
#EXTINF:-1 tvg-id="HLS Stream" tvg-name="HLS"
http://example.com/live/stream.m3u8
#EXTINF:-1 tvg-id="Other Movie" tvg-name="Comedy Night"
http://example.com/vod/comedy.mkv?token=abc
#EXTINF:-1,Bare Name Only
http://example.com/files/bare.avi
"""
    path = tmp_path / "sample.m3u"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def xdg_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "config"
    data = tmp_path / "data"
    cache = tmp_path / "cache"
    cfg.mkdir()
    data.mkdir()
    cache.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(cfg))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.delenv("M3UTOLOCAL_LANG", raising=False)
    monkeypatch.delenv("M3UTOLOCAL_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("M3UTOLOCAL_M3U", raising=False)
    return tmp_path
