"""Build unique DownloadJob paths under an output root."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from m3utolocal.domain.models import Channel, DownloadJob
from utils import sanitize_filename


def extension_from_url(url: str) -> str:
    m = re.search(r"(\.[a-zA-Z0-9]{2,4})(\?.*)?$", url)
    return m.group(1) if m else ""


def unique_filename(base: str, ext: str, used: set[str]) -> str:
    """Return a unique basename (with extension), mutating *used*."""
    name = f"{base}{ext}" if ext else base
    if not name or name in (".", ".."):
        name = f"unnamed{ext}"
    if name not in used:
        used.add(name)
        return name
    stem = base or "unnamed"
    n = 1
    while True:
        candidate = f"{stem}_{n}{ext}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        n += 1


class DownloadJobBuilder:
    def __init__(self) -> None:
        self._channel: Channel | None = None
        self._root: Path | None = None
        self._used: set[str] | None = None
        self._job_id: int = 0

    def with_channel(self, channel: Channel | Mapping[str, Any]) -> DownloadJobBuilder:
        if isinstance(channel, Channel):
            self._channel = channel
        else:
            self._channel = Channel(
                tvg_id=str(channel.get("tvg-id") or channel.get("tvg_id") or ""),
                tvg_name=str(channel.get("tvg-name") or channel.get("tvg_name") or ""),
                url=str(channel.get("url") or ""),
                size=int(channel.get("size") or 0),
            )
        return self

    def under(self, root: Path | str) -> DownloadJobBuilder:
        self._root = Path(root)
        return self

    def with_unique_name(self, used: set[str]) -> DownloadJobBuilder:
        self._used = used
        return self

    def with_id(self, job_id: int) -> DownloadJobBuilder:
        self._job_id = job_id
        return self

    def build(self) -> DownloadJob:
        if self._channel is None:
            raise ValueError("channel is required")
        if self._root is None:
            raise ValueError("output root is required")
        used = self._used if self._used is not None else set()
        base = sanitize_filename(self._channel.display_name) or "unnamed"
        ext = extension_from_url(self._channel.url)
        filename = unique_filename(base, ext, used)
        final_path = (self._root / filename).resolve()
        root_resolved = self._root.resolve()
        if not str(final_path).startswith(str(root_resolved)):
            raise ValueError("path escapes output root")
        part_path = Path(str(final_path) + ".part")
        return DownloadJob(
            id=self._job_id,
            channel=self._channel,
            final_path=final_path,
            part_path=part_path,
        )


def build_jobs(
    channels: list[Channel | Mapping[str, Any]],
    output_root: Path | str,
) -> list[DownloadJob]:
    used: set[str] = set()
    jobs: list[DownloadJob] = []
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    for i, ch in enumerate(channels):
        job = (
            DownloadJobBuilder()
            .with_id(i)
            .with_channel(ch)
            .under(root)
            .with_unique_name(used)
            .build()
        )
        jobs.append(job)
    return jobs
