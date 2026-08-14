"""Download resume / recovery regression tests."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from m3utolocal.downloader import download_file


class _RangeServer:
    """HTTP server that optionally honors Range and Accept-Ranges."""

    def __init__(
        self,
        payload: bytes,
        *,
        advertise_ranges: bool = True,
        honor_ranges: bool = True,
    ):
        self.payload = payload
        self.advertise_ranges = advertise_ranges
        self.honor_ranges = honor_ranges
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):  # noqa: N802
                outer.requests.append({"method": "HEAD", "range": self.headers.get("Range")})
                self.send_response(200)
                self.send_header("Content-Length", str(len(outer.payload)))
                if outer.advertise_ranges:
                    self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

            def do_GET(self):  # noqa: N802
                rng = self.headers.get("Range")
                outer.requests.append({"method": "GET", "range": rng})
                if rng and outer.honor_ranges and rng.startswith("bytes="):
                    spec = rng.split("=", 1)[1]
                    start_s, _, end_s = spec.partition("-")
                    start = int(start_s) if start_s else 0
                    end = int(end_s) if end_s else len(outer.payload) - 1
                    end = min(end, len(outer.payload) - 1)
                    chunk = outer.payload[start : end + 1]
                    self.send_response(206)
                    self.send_header(
                        "Content-Range",
                        f"bytes {start}-{end}/{len(outer.payload)}",
                    )
                    self.send_header("Content-Length", str(len(chunk)))
                    if outer.advertise_ranges:
                        self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    self.wfile.write(chunk)
                    return
                # Full body (either no range or ignore range)
                self.send_response(200)
                self.send_header("Content-Length", str(len(outer.payload)))
                if outer.advertise_ranges:
                    self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(outer.payload)

            def log_message(self, *a):
                return

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/file.bin"

    def stop(self):
        self._server.shutdown()


@pytest.fixture
def payload() -> bytes:
    return bytes(range(256)) * 400  # 100 KiB pattern


def test_resume_appends_with_206(tmp_path: Path, payload: bytes):
    srv = _RangeServer(payload, advertise_ranges=True, honor_ranges=True)
    try:
        target = tmp_path / "vid.mp4"
        part = Path(str(target) + ".part")
        # Pretend first 30% already downloaded
        cut = len(payload) // 3
        part.write_bytes(payload[:cut])
        download_file(srv.url, str(target))
        assert target.read_bytes() == payload
        assert not part.exists()
        # At least one ranged GET was used
        ranged = [r for r in srv.requests if r["method"] == "GET" and r["range"]]
        assert ranged, "expected a Range GET for resume"
        assert ranged[0]["range"] == f"bytes={cut}-"
    finally:
        srv.stop()


def test_resume_when_server_ignores_range_no_corruption(tmp_path: Path, payload: bytes):
    """If server returns 200 for a Range request, rewrite from scratch — never append full body."""
    srv = _RangeServer(payload, advertise_ranges=True, honor_ranges=False)
    try:
        target = tmp_path / "vid.mp4"
        part = Path(str(target) + ".part")
        cut = len(payload) // 2
        part.write_bytes(payload[:cut])
        download_file(srv.url, str(target))
        data = target.read_bytes()
        assert data == payload
        assert len(data) == len(payload)  # not cut + full
        assert not part.exists()
    finally:
        srv.stop()


def test_resume_tries_range_without_accept_ranges_header(tmp_path: Path, payload: bytes):
    """HEAD may omit Accept-Ranges; still attempt Range when .part exists."""
    srv = _RangeServer(payload, advertise_ranges=False, honor_ranges=True)
    try:
        target = tmp_path / "vid.mp4"
        part = Path(str(target) + ".part")
        cut = 10000
        part.write_bytes(payload[:cut])
        download_file(srv.url, str(target))
        assert target.read_bytes() == payload
        ranged = [r for r in srv.requests if r["method"] == "GET" and r["range"]]
        assert ranged, "should still try Range even without Accept-Ranges on HEAD"
    finally:
        srv.stop()


def test_complete_part_finalized_without_redownload(tmp_path: Path, payload: bytes):
    srv = _RangeServer(payload, advertise_ranges=True, honor_ranges=True)
    try:
        target = tmp_path / "vid.mp4"
        part = Path(str(target) + ".part")
        part.write_bytes(payload)  # already complete
        download_file(srv.url, str(target))
        assert target.read_bytes() == payload
        assert not part.exists()
        # No GET needed if we finalize complete part after HEAD size match
        gets = [r for r in srv.requests if r["method"] == "GET"]
        assert gets == [] or True  # allow HEAD-only finalize
        # Prefer: no GET at all
        assert gets == []
    finally:
        srv.stop()


def test_oversized_part_truncated_and_redownloads(tmp_path: Path, payload: bytes):
    srv = _RangeServer(payload, advertise_ranges=True, honor_ranges=True)
    try:
        target = tmp_path / "vid.mp4"
        part = Path(str(target) + ".part")
        part.write_bytes(payload + b"EXTRA_CORRUPT")
        download_file(srv.url, str(target))
        assert target.read_bytes() == payload
        assert not part.exists()
    finally:
        srv.stop()


def test_fresh_download_creates_and_removes_part(tmp_path: Path, payload: bytes):
    srv = _RangeServer(payload, advertise_ranges=True, honor_ranges=True)
    try:
        target = tmp_path / "vid.mp4"
        download_file(srv.url, str(target))
        assert target.read_bytes() == payload
        assert not Path(str(target) + ".part").exists()
    finally:
        srv.stop()
