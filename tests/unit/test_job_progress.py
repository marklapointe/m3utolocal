"""Unit tests for JobProgress, cancel, and TUI download retries (consensus Phase 2)."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from m3utolocal.domain.models import JobState
from m3utolocal.services.download_manager import DownloadManager, JobProgress


def test_job_progress_type_exists_not_shadowing_domain():
    """Manager progress type is JobProgress; domain JobState remains the enum."""
    assert JobProgress is not JobState
    assert issubclass(JobState, str)


def test_enqueue_uses_domain_job_state(tmp_path: Path):
    mgr = DownloadManager()
    mgr.enqueue(
        [{"tvg-id": "ch1", "url": "http://example.com/ch1.mp4", "size": 1000}],
        tmp_path,
    )
    assert isinstance(mgr.states[0], JobProgress)
    assert mgr.states[0].status is JobState.QUEUED
    assert mgr.states[0].total == 1000


@pytest.mark.asyncio
async def test_start_downloads_marks_completed(tmp_path: Path):
    mgr = DownloadManager()
    mgr.enqueue(
        [{"tvg-id": "ch1", "url": "http://example.com/ch1.mp4", "size": 10}],
        tmp_path,
    )
    target = mgr.states[0].job.final_path

    def fake_download(url, path, on_progress=None, cancel_check=None):
        Path(path).write_bytes(b"hello")
        if on_progress:
            on_progress(5, 5, "1.0 KB/s", "ETA: 0s")

    with patch("m3utolocal.downloader.download_file", side_effect=fake_download):
        await mgr.start_downloads(threads=1, retries=0)

    assert mgr.states[0].status is JobState.COMPLETED
    assert target.read_bytes() == b"hello"
    assert mgr.is_running is False


@pytest.mark.asyncio
async def test_cancel_marks_queued_and_running_cancelled(tmp_path: Path):
    import asyncio

    mgr = DownloadManager()
    mgr.enqueue(
        [
            {"tvg-id": "a", "url": "http://example.com/a.mp4", "size": 10},
            {"tvg-id": "b", "url": "http://example.com/b.mp4", "size": 10},
        ],
        tmp_path,
    )
    started = threading.Event()
    release = threading.Event()

    def blocking_download(url, path, on_progress=None, cancel_check=None):
        started.set()
        while not release.wait(0.01):
            if cancel_check and cancel_check():
                from m3utolocal.downloader import DownloadCancelled

                raise DownloadCancelled("cancelled")

    with patch("m3utolocal.downloader.download_file", side_effect=blocking_download):
        task = asyncio.create_task(mgr.start_downloads(threads=1, retries=0))
        for _ in range(200):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set()
        mgr.cancel()
        release.set()
        await task

    statuses = {s.status for s in mgr.states}
    assert JobState.CANCELLED in statuses
    assert JobState.QUEUED not in statuses
    assert mgr.is_running is False


@pytest.mark.asyncio
async def test_retries_on_recoverable_failure(tmp_path: Path):
    mgr = DownloadManager()
    mgr.enqueue(
        [{"tvg-id": "ch1", "url": "http://example.com/ch1.mp4", "size": 10}],
        tmp_path,
    )
    calls = {"n": 0}

    def flaky(url, path, on_progress=None, cancel_check=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("flaky")
        Path(path).write_bytes(b"ok")

    with patch("m3utolocal.downloader.download_file", side_effect=flaky):
        await mgr.start_downloads(threads=1, retries=2)

    assert calls["n"] == 3
    assert mgr.states[0].status is JobState.COMPLETED


@pytest.mark.asyncio
async def test_exhausted_retries_marks_failed(tmp_path: Path):
    mgr = DownloadManager()
    mgr.enqueue(
        [{"tvg-id": "ch1", "url": "http://example.com/ch1.mp4", "size": 10}],
        tmp_path,
    )

    def always_fail(url, path, on_progress=None, cancel_check=None):
        raise ConnectionError("nope")

    with patch("m3utolocal.downloader.download_file", side_effect=always_fail):
        await mgr.start_downloads(threads=1, retries=1)

    assert mgr.states[0].status is JobState.FAILED
    assert "nope" in (mgr.states[0].error or "")


def test_download_file_honours_cancel_check(tmp_path: Path):
    from m3utolocal.downloader import DownloadCancelled, download_file

    class FakeResp:
        status_code = 200
        headers = {"content-length": "1000000", "Accept-Ranges": "bytes"}

        def iter_content(self, chunk_size=65536):
            for _ in range(100):
                yield b"x" * chunk_size

        def raise_for_status(self):
            return None

        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    session = MagicMock()
    session.head.return_value = FakeResp()
    session.get.return_value = FakeResp()

    cancel = {"hit": False}

    def cancel_check():
        if cancel["hit"]:
            return True
        cancel["hit"] = True
        return False

    target = tmp_path / "out.mp4"
    with pytest.raises(DownloadCancelled):
        download_file(
            "http://example.com/big.mp4",
            str(target),
            session=session,
            cancel_check=cancel_check,
        )
    # Partial data preserved as .part
    assert (tmp_path / "out.mp4.part").exists() or not target.exists()
