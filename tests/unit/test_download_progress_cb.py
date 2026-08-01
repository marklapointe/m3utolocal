"""Progress callback for TUI bars."""

from pathlib import Path

import pytest

from downloader import download_file


class _Handler:
    payload = b"x" * 50_000


@pytest.fixture
def http_server():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class H(BaseHTTPRequestHandler):
        def do_HEAD(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Length", str(len(_Handler.payload)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Length", str(len(_Handler.payload)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(_Handler.payload)

        def log_message(self, *a):
            return

    srv = HTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/f.bin"
    srv.shutdown()


def test_on_progress_receives_updates(tmp_path: Path, http_server: str):
    events = []

    def cb(downloaded, total, rate, eta):
        events.append((downloaded, total, rate, eta))

    target = tmp_path / "out.bin"
    download_file(http_server, str(target), on_progress=cb)
    assert target.read_bytes() == _Handler.payload
    assert events, "expected progress callbacks"
    assert events[-1][0] >= len(_Handler.payload)
    assert "Done" in events[-1][3] or events[-1][0] == events[-1][1]
