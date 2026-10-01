"""Global background DownloadManager decoupled from UI screen lifecycle."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from m3utolocal.domain.job_builder import DownloadJob, build_jobs
from m3utolocal.domain.models import JobState


@dataclass
class JobProgress:
    """Live progress for one queued download (not the domain JobState enum)."""

    job: DownloadJob
    status: JobState = JobState.QUEUED
    downloaded: int = 0
    total: int = 0
    pct: float = 0.0
    rate: str = "—"
    eta: str = "—"
    error: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)


class DownloadManager:
    """Manages background download tasks across screen transitions."""

    def __init__(self) -> None:
        self.states: list[JobProgress] = []
        self.is_running: bool = False
        self._lock = asyncio.Lock()
        self._listener: Callable[[], None] | None = None
        self._cancel_all = threading.Event()

    def set_listener(self, listener: Callable[[], None] | None) -> None:
        self._listener = listener

    def _notify(self) -> None:
        if self._listener:
            try:
                self._listener()
            except Exception:
                pass

    def enqueue(self, matches: list[dict[str, Any]], output_dir: Path, threads: int = 1) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        jobs = build_jobs(matches, output_dir)
        start_id = len(self.states)
        for i, j in enumerate(jobs):
            j.id = start_id + i
            initial_total = max(0, int(j.channel.size or 0))
            self.states.append(JobProgress(job=j, total=initial_total))

    def cancel(self) -> None:
        """Request cancellation of queued and in-flight downloads."""
        self._cancel_all.set()
        for state in self.states:
            if state.status in (JobState.QUEUED, JobState.RUNNING):
                state.cancel_event.set()
                if state.status is JobState.QUEUED:
                    state.status = JobState.CANCELLED
        self._notify()

    async def start_downloads(self, threads: int = 1, retries: int = 0) -> None:
        from m3utolocal.downloader import DownloadCancelled, download_file

        if self.is_running:
            return
        self.is_running = True
        self._cancel_all.clear()

        sem = asyncio.Semaphore(max(1, threads))

        async def _worker(state: JobProgress) -> None:
            if state.cancel_event.is_set() or self._cancel_all.is_set():
                state.status = JobState.CANCELLED
                self._notify()
                return

            async with sem:
                if state.cancel_event.is_set() or self._cancel_all.is_set():
                    state.status = JobState.CANCELLED
                    self._notify()
                    return

                state.status = JobState.RUNNING
                self._notify()

                def _cb(downloaded: int, total_size: int, rate_str: str, eta_str: str) -> None:
                    state.downloaded = downloaded
                    if total_size > 0:
                        state.total = total_size
                    state.pct = (
                        0.0
                        if state.total <= 0
                        else min(100.0, 100.0 * downloaded / state.total)
                    )
                    state.rate = rate_str.strip() if rate_str else "0.0 KB/s"
                    state.eta = eta_str or "ETA: --"
                    if state.status is not JobState.CANCELLED:
                        state.status = JobState.RUNNING
                    self._notify()

                def _cancel_check() -> bool:
                    return state.cancel_event.is_set() or self._cancel_all.is_set()

                url = state.job.channel.url
                path = str(state.job.final_path)
                max_attempts = max(0, retries) + 1
                last_error: Exception | None = None

                for attempt in range(max_attempts):
                    if _cancel_check():
                        state.status = JobState.CANCELLED
                        self._notify()
                        return
                    try:

                        def _download() -> None:
                            download_file(
                                url,
                                path,
                                on_progress=_cb,
                                cancel_check=_cancel_check,
                            )

                        await asyncio.to_thread(_download)
                        state.status = JobState.COMPLETED
                        if state.total <= 0:
                            try:
                                sz = state.job.final_path.stat().st_size
                                state.downloaded = sz
                                state.total = sz
                                state.pct = 100.0
                            except OSError:
                                pass
                        self._notify()
                        return
                    except DownloadCancelled:
                        state.status = JobState.CANCELLED
                        self._notify()
                        return
                    except Exception as e:
                        last_error = e
                        if attempt + 1 < max_attempts and not _cancel_check():
                            await asyncio.sleep(1)
                            continue
                        state.status = JobState.FAILED
                        state.error = str(e)
                        self._notify()
                        return

                if last_error is not None:
                    state.status = JobState.FAILED
                    state.error = str(last_error)
                self._notify()

        pending = [s for s in self.states if s.status is JobState.QUEUED]
        if pending:
            await asyncio.gather(*[_worker(s) for s in pending])
        self.is_running = False
        self._notify()

    def overall_progress(self) -> tuple[int, int, float]:
        if not self.states:
            return 0, 0, 0.0
        done = sum(s.downloaded for s in self.states)
        total = sum(s.total if s.total > 0 else s.downloaded for s in self.states)
        pct = 0.0 if total <= 0 else min(100.0, 100.0 * done / total)
        return done, total, pct

    def active_job_state(self) -> JobProgress | None:
        for s in self.states:
            if s.status is JobState.RUNNING:
                return s
        return None
