"""Unit tests for slotted Channel with precomputed search keys (consensus Phase 3)."""

from __future__ import annotations

import pytest

from m3utolocal.domain.models import Channel


def test_channel_has_slots_no_dict():
    ch = Channel(tvg_id="id1", tvg_name="Name 1", url="http://x/1.mp4")
    assert hasattr(Channel, "__slots__")
    assert not hasattr(ch, "__dict__")


def test_channel_precomputes_norm_fields():
    ch = Channel(tvg_id="CNN-HD", tvg_name="Cable News", url="http://x/stream.mp4")
    assert ch._norm_id == "cnn-hd"
    assert ch._norm_name == "cable news"


def test_channel_mapping_compat():
    ch = Channel(tvg_id="id1", tvg_name="Name 1", url="http://x/1.mp4", size=1024)
    assert ch["tvg-id"] == "id1"
    assert ch["tvg-name"] == "Name 1"
    assert ch["url"] == "http://x/1.mp4"
    assert ch["size"] == 1024
    assert ch.get("tvg-id") == "id1"
    assert ch.get("unknown_key", "default") == "default"
    d = dict(ch)
    assert d["tvg-id"] == "id1"
    assert d["size"] == 1024


def test_channel_still_frozen():
    ch = Channel(tvg_id="id1", tvg_name="Name 1", url="http://x/1.mp4")
    with pytest.raises((AttributeError, TypeError)):
        ch.url = "http://modified"  # type: ignore[misc]
