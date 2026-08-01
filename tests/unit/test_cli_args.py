"""Regression: search queries must never be eaten by subcommands."""

from __future__ import annotations

import pytest

from m3utolocal.cli_args import parse_args, SUBCOMMANDS


def test_pycharm_tui_query_svt_not_a_command():
    """Exact failure mode from broken run config / argparse subparsers."""
    args = parse_args(
        ["-m", "/home/mlapointe/chans.m3u", "--tui", "SVT"]
    )
    assert args.command is None
    assert args.query == "SVT"
    assert args.tui is True
    assert args.m3u == "/home/mlapointe/chans.m3u"
    assert args.yes is False


def test_query_before_flags():
    args = parse_args(["SVT", "-m", "/tmp/x.m3u", "--tui"])
    assert args.query == "SVT"
    assert args.tui is True
    assert args.command is None


def test_query_after_all_flags():
    args = parse_args(["-m", "/tmp/x.m3u", "-y", "-t", "2", "movie title"])
    assert args.query == "movie title"
    assert args.yes is True
    assert args.threads == 2
    assert args.command is None


def test_tui_only_with_m3u_no_query():
    """Default: open UI with playlist, no search string."""
    args = parse_args(["-m", "/home/mlapointe/chans.m3u"])
    assert args.command is None
    assert args.query is None
    assert args.m3u == "/home/mlapointe/chans.m3u"
    assert args.tui is False  # still opens TUI because no -y and no query


def test_empty_argv_is_tui_home():
    args = parse_args([])
    assert args.command is None
    assert args.query is None


def test_cleanup_subcommand():
    args = parse_args(["cleanup", "--apply", "-o", "/tmp/lib"])
    assert args.command == "cleanup"
    assert args.apply is True
    assert args.output == "/tmp/lib"
    assert args.query is None


def test_cleanup_dry_run_default():
    args = parse_args(["cleanup"])
    assert args.command == "cleanup"
    assert args.apply is False


def test_init_subcommand():
    args = parse_args(["init"])
    assert args.command == "init"
    assert args.query is None


def test_svt_is_never_a_subcommand():
    args = parse_args(["SVT"])
    assert args.command is None
    assert args.query == "SVT"
    assert "SVT" not in SUBCOMMANDS


def test_cleanup_not_confused_with_query_named_cleanup_as_flag_order():
    # If user searches for the word "cleanup" they must put it after flags
    # or as sole query without it being first token as subcommand.
    # First token cleanup IS the subcommand (documented).
    args = parse_args(["cleanup", "--apply"])
    assert args.command == "cleanup"

    # Searching for "cleanup" as query:
    args = parse_args(["-m", "x.m3u", "cleanup"])
    assert args.command is None
    assert args.query == "cleanup"


def test_unknown_flag_raises():
    with pytest.raises(SystemExit):
        parse_args(["--not-a-real-flag"])


def test_headless_yes_with_query():
    args = parse_args(["-y", "-m", "/tmp/p.m3u", "foo"])
    assert args.yes is True
    assert args.query == "foo"
    assert args.command is None
