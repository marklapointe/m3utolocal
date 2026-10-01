"""Domain models for channels and download jobs."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class JobState(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    CANCELLED = "Cancelled"


@dataclass(frozen=True, slots=True)
class Channel(Mapping[str, Any]):
    tvg_id: str
    tvg_name: str
    url: str
    size: int = 0
    _norm_id: str = field(init=False, repr=False, compare=False)
    _norm_name: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_norm_id", self.tvg_id.lower())
        object.__setattr__(self, "_norm_name", self.tvg_name.lower())

    @property
    def display_name(self) -> str:
        return self.tvg_id if self.tvg_id else self.tvg_name

    def __getitem__(self, key: str) -> Any:
        if key in ("tvg-id", "tvg_id"):
            return self.tvg_id
        if key in ("tvg-name", "tvg_name"):
            return self.tvg_name
        if key == "url":
            return self.url
        if key == "size":
            return self.size
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(("tvg-id", "tvg-name", "url", "size"))

    def __len__(self) -> int:
        return 4


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
