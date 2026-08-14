"""Integration: download into output root only (local HTTP server)."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from m3utolocal.downloader import download_file
from m3utolocal.domain.job_builder import build_jobs
from m3utolocal.domain.models import Channel
from m3utolocal.domain.match import find_matches
from m3utolocal.utils import parse_m3u


class _Handler(BaseHTTPRequestHandler):
    payload = b"hello-vod-content-0123456789"

    def do_HEAD(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, format, *args):  # noqa: A003
        return


@pytest.fixture
def http_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/movie.mp4"
    server.shutdown()


def test_download_stays_in_output_root(tmp_path: Path, http_server: str, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cwd = Path.cwd()
    out = tmp_path / "library"
    out.mkdir()
    jobs = build_jobs(
        [Channel("TestVid", "TestVid", http_server)],
        out,
    )
    job = jobs[0]
    download_file(job.channel.url, str(job.final_path))
    assert job.final_path.is_file()
    assert job.final_path.read_bytes() == _Handler.payload
    # No media dumped in CWD
    media = list(cwd.glob("*.mp4"))
    assert media == [] or all(p.parent == out for p in media)
    assert not (cwd / "TestVid.mp4").exists()


def test_skip_when_complete(tmp_path: Path, http_server: str):
    out = tmp_path / "lib"
    out.mkdir()
    jobs = build_jobs([Channel("T", "T", http_server)], out)
    p = jobs[0].final_path
    p.write_bytes(_Handler.payload)
    download_file(jobs[0].channel.url, str(p))
    assert p.read_bytes() == _Handler.payload


def test_parse_filter_integration(tmp_path: Path):
    m3u = tmp_path / "p.m3u"
    m3u.write_text(
        "#EXTM3U\n"
        '#EXTINF:-1 tvg-id="Good" tvg-name="Good",\n'
        "http://x/a.mp4\n"
        '#EXTINF:-1 tvg-id="Live" tvg-name="Live",\n'
        "http://x/live\n",
        encoding="utf-8",
    )
    channels = parse_m3u(str(m3u))
    matches = find_matches(channels, "good")
    assert len(matches) == 1
