import time
from pathlib import Path

from m3utolocal.services.cleanup import CleanupPolicy, CleanupService


def test_plan_stale_part_and_empty(tmp_path: Path):
    part = tmp_path / "a.mp4.part"
    part.write_bytes(b"partial")
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    good = tmp_path / "done.mp4"
    good.write_bytes(b"data")

    old = time.time() - 10 * 24 * 3600
    # set mtime old
    import os

    os.utime(part, (old, old))

    plan = CleanupService().plan(
        tmp_path, policy=CleanupPolicy(part_max_age_seconds=7 * 24 * 3600, now=time.time())
    )
    kinds = {i.kind for i in plan.items}
    assert "stale_part" in kinds
    assert "empty" in kinds
    paths = {i.path.name for i in plan.items}
    assert "done.mp4" not in paths


def test_execute_dry_run_keeps_files(tmp_path: Path):
    f = tmp_path / "x.part"
    f.write_bytes(b"abc")
    plan = CleanupService().plan(
        tmp_path, policy=CleanupPolicy(part_max_age_seconds=0, now=time.time())
    )
    CleanupService().execute(plan, dry_run=True)
    assert f.exists()
    CleanupService().execute(plan, dry_run=False)
    assert not f.exists()


def test_migrate_cwd(tmp_path: Path):
    cwd = tmp_path / "cwd"
    out = tmp_path / "lib"
    cwd.mkdir()
    out.mkdir()
    media = cwd / "clip.mp4"
    media.write_bytes(b"vid")
    (cwd / "notes.txt").write_text("no")
    moves = CleanupService().migrate_cwd_media(cwd, out, dry_run=False)
    assert len(moves) == 1
    assert (out / "clip.mp4").exists()
    assert not media.exists()
