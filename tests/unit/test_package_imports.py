def test_utils_lives_in_package():
    from m3utolocal.utils import format_size, parse_m3u, sanitize_filename

    assert format_size(1024) == "1.00 KB"
    assert callable(parse_m3u)
    assert sanitize_filename("a/b") == "a_b"


def test_downloader_lives_in_package():
    from m3utolocal.downloader import download_file

    assert callable(download_file)


def test_cli_progress_manager():
    from m3utolocal.cli_progress import DownloadManager

    assert DownloadManager(1) is not None
