"""Normalized search semantics for Channel + dict inputs (consensus Phase 3)."""

from __future__ import annotations

from m3utolocal.domain.match import find_matches
from m3utolocal.domain.models import Channel


def test_find_matches_accepts_channel_iterable():
    channels = [
        Channel(tvg_id="A", tvg_name="Matrix", url="http://x/a.mp4"),
        Channel(tvg_id="B", tvg_name="Other", url="http://x/b.mp4"),
    ]
    m = find_matches(channels, "matrix")
    assert len(m) == 1
    assert m[0]["tvg-id"] == "A"
    assert isinstance(m[0], dict)  # mutable for size probing


def test_find_matches_uses_norm_fields_not_joined_key():
    """Query must not false-match across id/name boundary."""
    channels = [
        Channel(tvg_id="foo", tvg_name="bar", url="http://x/a.mp4"),
        Channel(tvg_id="foo bar", tvg_name="x", url="http://x/b.mp4"),
    ]
    m = find_matches(channels, "foo bar")
    assert len(m) == 1
    assert m[0]["tvg-id"] == "foo bar"


def test_find_matches_case_insensitive_channel():
    channels = [Channel(tvg_id="Foo", tvg_name="Bar", url="http://x/a.mp4")]
    assert find_matches(channels, "FOO")
    assert find_matches(channels, "bar")


def test_find_matches_still_accepts_dicts():
    channels = [{"tvg-id": "A", "tvg-name": "Matrix", "url": "http://x/a.mp4"}]
    m = find_matches(channels, "matrix")
    assert len(m) == 1
    m[0]["size"] = 99  # size probing contract
    assert m[0]["size"] == 99


def test_find_matches_vod_filter_on_channel():
    channels = [
        Channel(tvg_id="A", tvg_name="Matrix", url="http://x/a.mp4"),
        Channel(tvg_id="B", tvg_name="Matrix Live", url="http://x/live"),
        Channel(tvg_id="C", tvg_name="Matrix HLS", url="http://x/s.m3u8"),
    ]
    m = find_matches(channels, "matrix")
    assert len(m) == 1
    assert m[0]["tvg-id"] == "A"
