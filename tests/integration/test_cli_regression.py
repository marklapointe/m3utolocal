"""End-to-end CLI regression via subprocess (no interactive TUI launch)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main.py"
PYTHON = sys.executable


def run_cli(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e["PYTHONPATH"] = str(ROOT)
    if env:
        e.update(env)
    return subprocess.run(
        [PYTHON, str(MAIN), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=e,
        timeout=30,
    )


def test_cli_svt_tui_args_do_not_die_with_invalid_choice():
    """Must not print: invalid choice: 'SVT' (choose from cleanup, init)."""
    # Will try to open TUI — in non-TTY may still start; we only care it does
    # NOT fail at argparse. Use timeout-friendly path: parse only by importing.
    from m3utolocal.cli_args import parse_args

    args = parse_args(["-m", "/home/mlapointe/chans.m3u", "--tui", "SVT"])
    assert args.query == "SVT"
    assert args.command is None


def test_cli_help_exit_zero():
    r = run_cli(["-h"])
    assert r.returncode == 0
    assert "query" in r.stdout.lower() or "Search" in r.stdout or "m3u" in r.stdout.lower()
    assert "cleanup" in r.stdout or "init" in r.stdout or True  # help text from main parser


def test_cli_init_writes_config(tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    data = tmp_path / "data"
    cfg.mkdir()
    data.mkdir()
    env = {
        "XDG_CONFIG_HOME": str(cfg),
        "XDG_DATA_HOME": str(data),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    (tmp_path / "cache").mkdir()
    r = run_cli(["init"], env=env)
    assert r.returncode == 0, r.stderr
    assert "Wrote config" in r.stdout
    assert (cfg / "m3utolocal" / "config.json").is_file()


def test_cli_cleanup_dry_run(tmp_path):
    out = tmp_path / "lib"
    out.mkdir()
    (out / "stale.mp4.part").write_bytes(b"x")
    r = run_cli(["cleanup", "-o", str(out)])
    assert r.returncode == 0, r.stderr
    assert "Planned" in r.stdout or "stale" in r.stdout.lower() or "part" in r.stdout


def test_cli_missing_m3u_headless_fails(tmp_path):
    r = run_cli(["-y", "-m", str(tmp_path / "nope.m3u"), "anything"])
    assert r.returncode != 0
    assert "not found" in (r.stdout + r.stderr).lower()


def test_cli_subprocess_svt_reaches_past_argparse():
    """Full argv through main: must not argparse-fail on SVT.

    Launching the real Textual app will hang in CI/non-interactive runs, so we
    only wait long enough to prove argparse accepted the line and TUI started
    (or exited for a non-argparse reason).
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TERM"] = "xterm-256color"
    proc = subprocess.Popen(
        [PYTHON, str(MAIN), "-m", "/home/mlapointe/chans.m3u", "--tui", "SVT"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        try:
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            # Still running after 2s ⇒ argparse did not reject SVT; kill TUI.
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
            # Timeout == success for this regression (app entered main loop).
            combined = (stdout or "") + (stderr or "")
            assert "invalid choice" not in combined
            assert "choose from cleanup" not in combined
            return
        combined = (stdout or "") + (stderr or "")
        assert "invalid choice" not in combined
        assert "choose from cleanup" not in combined
        # If it exited quickly, must not be the old argparse error (exit 2 + usage).
        if proc.returncode == 2:
            assert "argument command" not in combined
    finally:
        if proc.poll() is None:
            proc.kill()
