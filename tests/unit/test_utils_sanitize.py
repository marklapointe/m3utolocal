from m3utolocal.utils import sanitize_filename


def test_sanitize_illegal_chars():
    assert "/" not in sanitize_filename('a/b:c*d?.mp4')
    assert ":" not in sanitize_filename('a/b:c*d?.mp4')


def test_sanitize_empty():
    assert sanitize_filename("???") == "___" or sanitize_filename("???")
    assert sanitize_filename("   ") == "unnamed"
    assert sanitize_filename(None) == "unnamed"


def test_sanitize_max_length():
    long_name = "a" * 300 + ".mp4"
    out = sanitize_filename(long_name, max_length=50)
    assert len(out) <= 50
    assert out.endswith(".mp4")
