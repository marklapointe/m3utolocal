"""Global background DownloadManager decouple from UI screen lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from m3utolocal.domain.job_builder import DownloadJob, build_jobs
from m3utolocal.utils import format_size


@dataclass
class JobState:
    job: DownloadJob
    status: str = "Queued"
    downloaded: int = 0
    total: int = 0
    pct: float = 0.0
    rate: str = "—"
    eta: str = "—"


class DownloadManager:
    """Manages background download tasks across screen transitions."""

    def __init__(self) -> None:
        self.states: list[JobState] = []
        self.is_running: bool = False
        self._lock = asyncio.Lock()
        self._listener: Callable[[], None] | None = None

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
            # re-index job id if appending
            j.id = start_id + i
            initial_total = max(0, int(j.channel.size or 0))
            self.states.append(JobState(job=j, total=initial_total))

    async def start_downloads(self, threads: int = 1) -> None:
        from m3utolocal.downloader import download_file

        if self.is_running:
            return
        self.is_running = True

        sem = asyncio.Semaphore(max(1, threads))

        async def _worker(state: JobState) -> None:
            async with sem:
                state.status = "Downloading…"
                self._notify()

                def _cb(downloaded: int, total_size: int, rate_str: str, eta_str: str) -> None:
                    state.downloaded = downloaded
                    if total_size > 0:
                        state.total = total_size
                    state.pct = 0.0 if state.total <= 0 else min(100.0, 100.0 * downloaded / state.total)
                    state.rate = rate_str.strip() if rate_str else "0.0 KB/s"
                    state.eta = eta_str or "ETA: --"
                    if state.total > 0 and state.pct >= 100:
                        state.status = "Done"
                    else:
                        state.status = "Downloading…"
                    self._notify()

                try:
                    url = state.job.channel.url
                    path = str(state.job.final_path)

                    def _download():
                        download_file(url, path, on_progress=_cb)

                    await asyncio.to_thread(_download)
                    state.status = "Done"
                    if state.total <= 0:
                        try:
                            sz = state.job.final_path.stat().st_size
                            state.downloaded = sz
                            state.total = sz
                            state.pct = 100.0
                        except OSError:
                            pass
                except Exception as e:
                    state.status = f"Failed: {e}"
                self._notify()

        pending = [s for s in self.states if s.status in ("Queued", "Downloading…")]
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

    def active_job_state(self) -> JobState | None:
        for s in self.states:
            if s.status == "Downloading…":
                return s
        return None
