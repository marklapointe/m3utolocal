from m3utolocal.domain.match import find_matches, is_vod_url


def test_is_vod_url():
    assert is_vod_url("http://x/movie.mp4") is True
    assert is_vod_url("http://x/live") is False
    assert is_vod_url("http://x/stream.m3u8") is False
    assert is_vod_url("http://x/f.mkv?token=1") is True


def test_find_matches_filters_live():
    channels = [
        {"tvg-id": "A", "tvg-name": "Matrix", "url": "http://x/a.mp4"},
        {"tvg-id": "B", "tvg-name": "Matrix Live", "url": "http://x/live"},
        {"tvg-id": "C", "tvg-name": "Matrix HLS", "url": "http://x/s.m3u8"},
    ]
    m = find_matches(channels, "matrix")
    assert len(m) == 1
    assert m[0]["tvg-id"] == "A"


def test_find_matches_case_insensitive():
    channels = [{"tvg-id": "Foo", "tvg-name": "Bar", "url": "http://x/a.mp4"}]
    assert find_matches(channels, "FOO")
    assert find_matches(channels, "bar")
