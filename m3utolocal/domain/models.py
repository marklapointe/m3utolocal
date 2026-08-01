"""Domain models for channels and download jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobState(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"


@dataclass(frozen=True)
class Channel:
    tvg_id: str
    tvg_name: str
    url: str
    size: int = 0

    @property
    def display_name(self) -> str:
        return self.tvg_id if self.tvg_id else self.tvg_name


@dataclass
class DownloadJob:
    id: int
    channel: Channel
    final_path: Path
    part_path: Path
    state: JobState = JobState.QUEUED
    error: str | None = None


@dataclass(frozen=True)
class CleanupItem:
    path: Path
    kind: str
    size: int
    mtime: float
    reason: str


@dataclass(frozen=True)
class CleanupPlan:
    items: tuple[CleanupItem, ...] = field(default_factory=tuple)

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.items)

    def __len__(self) -> int:
        return len(self.items)
