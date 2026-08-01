"""Scan output root and plan/execute cleanup of litter."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from m3utolocal.domain.models import CleanupItem, CleanupPlan

MEDIA_SUFFIXES = frozenset(
    {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".ts",
        ".mpg",
        ".mpeg",
    }
)


@dataclass
class CleanupPolicy:
    part_max_age_seconds: float = 7 * 24 * 3600
    include_empty: bool = True
    include_stale_parts: bool = True
    include_orphan_temps: bool = True
    now: float | None = None


class CleanupService:
    def plan(self, root: Path, *, policy: CleanupPolicy | None = None) -> CleanupPlan:
        policy = policy or CleanupPolicy()
        now = policy.now if policy.now is not None else time.time()
        root = Path(root)
        if not root.is_dir():
            return CleanupPlan(())

        items: list[CleanupItem] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            # Skip soft-trash if present
            if Path(dirpath).name == ".trash":
                continue
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                size = st.st_size
                mtime = st.st_mtime
                age = now - mtime

                if policy.include_empty and size == 0:
                    items.append(
                        CleanupItem(
                            path=path,
                            kind="empty",
                            size=size,
                            mtime=mtime,
                            reason="zero-byte file",
                        )
                    )
                    continue

                if policy.include_stale_parts and name.endswith(".part"):
                    if age >= policy.part_max_age_seconds:
                        items.append(
                            CleanupItem(
                                path=path,
                                kind="stale_part",
                                size=size,
                                mtime=mtime,
                                reason="stale partial download",
                            )
                        )
                    continue

                if policy.include_orphan_temps and (
                    name.endswith(".tmp")
                    or ".tmp_" in name
                    or name.startswith("tmp_")
                ):
                    items.append(
                        CleanupItem(
                            path=path,
                            kind="orphan_temp",
                            size=size,
                            mtime=mtime,
                            reason="orphan temporary file",
                        )
                    )

        items.sort(key=lambda i: str(i.path))
        return CleanupPlan(tuple(items))

    def execute(self, plan: CleanupPlan, *, dry_run: bool = True) -> dict[str, int]:
        removed = 0
        bytes_freed = 0
        for item in plan.items:
            if dry_run:
                continue
            try:
                size = item.path.stat().st_size if item.path.exists() else item.size
                item.path.unlink(missing_ok=True)
                removed += 1
                bytes_freed += size
            except OSError:
                continue
        return {"removed": removed, "bytes_freed": bytes_freed, "planned": len(plan)}

    def migrate_cwd_media(
        self,
        cwd: Path,
        output_root: Path,
        *,
        dry_run: bool = True,
    ) -> list[tuple[Path, Path]]:
        """Move media files from *cwd* into *output_root* (idempotent names)."""
        cwd = Path(cwd)
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        moves: list[tuple[Path, Path]] = []
        for path in sorted(cwd.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in MEDIA_SUFFIXES:
                continue
            dest = output_root / path.name
            n = 1
            while dest.exists():
                dest = output_root / f"{path.stem}_{n}{path.suffix}"
                n += 1
            moves.append((path, dest))
            if not dry_run:
                shutil.move(str(path), str(dest))
        return moves
