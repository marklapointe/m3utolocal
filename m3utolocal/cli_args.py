"""CLI argument parsing — isolated for unit tests.

Subcommands (cleanup / init) are dispatched by the first argv token so a
search query like ``SVT`` is never mistaken for a subcommand.
"""

from __future__ import annotations

import argparse
from typing import Sequence


SUBCOMMANDS = frozenset({"cleanup", "init"})


def build_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m3utolocal",
        description="Download files from an M3U file based on search query.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Search query for tvg-id or tvg-name",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Bypass confirmation and download all matches",
    )
    parser.add_argument(
        "-m",
        "--m3u",
        default=None,
        help="Path to the M3U file (default: from config or chans.m3u)",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=None,
        help="Number of simultaneous downloads (default: 1)",
    )
    parser.add_argument(
        "-r",
        "--retries",
        type=int,
        default=None,
        help="Number of times to retry failed downloads (default: 1)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory for downloads (default: XDG library)",
    )
    parser.add_argument(
        "-L",
        "--lang",
        default=None,
        help="UI language code (e.g. en, es, fr)",
    )
    parser.add_argument(
        "--auto-clean",
        action="store_true",
        help="Remove stale .part files before download",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Force full-screen Textual TUI",
    )
    return parser


def build_cleanup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m3utolocal cleanup",
        description="Clean stale parts / empty files under output dir",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Only list what would be removed (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete planned files",
    )
    parser.add_argument("--parts-only", action="store_true")
    parser.add_argument(
        "--migrate-cwd",
        action="store_true",
        help="Move media litter from CWD into output dir",
    )
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-m", "--m3u", default=None, help=argparse.SUPPRESS)
    parser.add_argument("-t", "--threads", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("-r", "--retries", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("-L", "--lang", default=None, help=argparse.SUPPRESS)
    parser.add_argument("-y", "--yes", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--auto-clean", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tui", action="store_true", help=argparse.SUPPRESS)
    return parser


def build_init_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m3utolocal init",
        description="Write default XDG config.json",
    )
    parser.add_argument("-m", "--m3u", default=None, help=argparse.SUPPRESS)
    parser.add_argument("-t", "--threads", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("-r", "--retries", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("-o", "--output", default=None, help=argparse.SUPPRESS)
    parser.add_argument("-L", "--lang", default=None, help=argparse.SUPPRESS)
    parser.add_argument("-y", "--yes", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--auto-clean", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tui", action="store_true", help=argparse.SUPPRESS)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse argv. First token cleanup/init selects that subcommand only."""
    if argv is None:
        argv = sys_argv_without_prog()

    argv = list(argv)
    if argv and argv[0] in SUBCOMMANDS:
        command = argv[0]
        rest = argv[1:]
        if command == "cleanup":
            args = build_cleanup_parser().parse_args(rest)
        else:
            args = build_init_parser().parse_args(rest)
        args.command = command
        # Main-mode fields defaulted for shared settings loading
        if not hasattr(args, "query"):
            args.query = None
        if not hasattr(args, "yes"):
            args.yes = False
        if not hasattr(args, "tui"):
            args.tui = False
        if not hasattr(args, "auto_clean"):
            args.auto_clean = False
        return args

    args = build_main_parser().parse_args(argv)
    args.command = None
    return args


def sys_argv_without_prog() -> list[str]:
    import sys

    return sys.argv[1:]
