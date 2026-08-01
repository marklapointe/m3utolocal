from pathlib import Path

from m3utolocal.domain.job_builder import build_jobs
from m3utolocal.domain.models import Channel


def test_jobs_under_output_root(tmp_path: Path):
    channels = [
        Channel("Movie", "Movie", "http://x/a.mp4"),
        Channel("Movie", "Movie", "http://x/b.mp4"),
    ]
    jobs = build_jobs(channels, tmp_path)
    assert len(jobs) == 2
    names = {j.final_path.name for j in jobs}
    assert "Movie.mp4" in names
    assert "Movie_1.mp4" in names
    for j in jobs:
        assert j.final_path.parent == tmp_path.resolve()
        assert str(j.part_path).endswith(".part")
        assert j.final_path.is_relative_to(tmp_path.resolve()) or str(
            j.final_path
        ).startswith(str(tmp_path.resolve()))


def test_no_cwd_in_paths(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cwd = Path.cwd()
    out = tmp_path / "library"
    jobs = build_jobs(
        [Channel("X", "X", "http://x/z.mkv")],
        out,
    )
    assert jobs[0].final_path.parent == out.resolve()
    assert jobs[0].final_path.parent != cwd
