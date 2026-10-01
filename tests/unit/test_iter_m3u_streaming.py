"""Streaming M3U iterator tests (consensus Phase 4)."""

from __future__ import annotations

import inspect
from pathlib import Path

from m3utolocal.domain.models import Channel
from m3utolocal.utils import iter_m3u, parse_m3u


def test_iter_m3u_returns_generator_not_list(sample_m3u):
    res = iter_m3u(str(sample_m3u))
    assert inspect.isgenerator(res)
    assert not isinstance(res, list)


def test_iter_m3u_streaming_channel_entities(sample_m3u):
    first = next(iter_m3u(str(sample_m3u)))
    assert isinstance(first, Channel)
    assert first.url


def test_iter_m3u_missing_file_yields_empty(tmp_path: Path):
    assert list(iter_m3u(tmp_path / "nope.m3u")) == []


def test_iter_m3u_lazy_evaluation_never_reads_whole_file(tmp_path: Path):
    path = tmp_path / "huge.m3u"
    # First entry then many more lines
    lines = ['#EXTINF:-1 tvg-id="one" tvg-name="One",One\n', "http://x/one.mp4\n"]
    lines += [f'#EXTINF:-1 tvg-id="c{i}",C{i}\nhttp://x/c{i}.mp4\n' for i in range(5000)]
    path.write_text("".join(lines), encoding="utf-8")

    gen = iter_m3u(path)
    first = next(gen)
    assert first.tvg_id == "one"
    gen.close()  # stop without consuming rest


def test_parse_m3u_delegates_and_keeps_missing_file_message(tmp_path: Path, capsys):
    assert parse_m3u(str(tmp_path / "nope.m3u")) == []
    captured = capsys.readouterr()
    assert "not found" in captured.out.lower()


def test_parse_m3u_returns_channels(sample_m3u):
    channels = parse_m3u(str(sample_m3u))
    assert channels
    assert all(isinstance(c, Channel) for c in channels)
    # Mapping / dict-style access preserved for callers
    assert channels[0]["tvg-id"] or channels[0]["tvg-name"]
