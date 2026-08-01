from utils import parse_m3u


def test_parse_sample(sample_m3u):
    channels = parse_m3u(str(sample_m3u))
    assert len(channels) >= 4
    ids = {c["tvg-id"] for c in channels}
    assert "Matrix Reloaded" in ids


def test_parse_missing_file(tmp_path):
    assert parse_m3u(str(tmp_path / "nope.m3u")) == []


def test_bare_name_fallback(sample_m3u):
    channels = parse_m3u(str(sample_m3u))
    bare = [c for c in channels if c["url"].endswith("bare.avi")]
    assert bare
    assert bare[0]["tvg-name"] == "Bare Name Only"
