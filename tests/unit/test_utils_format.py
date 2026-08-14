from m3utolocal.utils import format_size, format_time


def test_format_size_bytes():
    assert format_size(0) == "Unknown"
    assert format_size(-1) == "Unknown"
    assert format_size(1023) == "1023 B"


def test_format_size_kb_mb():
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"


def test_format_time():
    assert format_time(-5) == "0s"
    assert format_time(59) == "59s"
    assert format_time(60) == "1m 0s"
    assert format_time(3661) == "1h 1m"
