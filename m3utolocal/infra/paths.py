"""XDG and FreeBSD-friendly path helpers."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "m3utolocal"
SYSTEM_CONFIG_DIR = Path("/usr/local/etc/cloudbsd/m3utolocal")


def _home() -> Path:
    return Path.home()


def xdg_config_home() -> Path:
    raw = os.environ.get("XDG_CONFIG_HOME")
    return Path(raw) if raw else _home() / ".config"


def xdg_data_home() -> Path:
    raw = os.environ.get("XDG_DATA_HOME")
    return Path(raw) if raw else _home() / ".local" / "share"


def xdg_cache_home() -> Path:
    raw = os.environ.get("XDG_CACHE_HOME")
    return Path(raw) if raw else _home() / ".cache"


def config_dir() -> Path:
    return xdg_config_home() / APP_NAME


def data_dir() -> Path:
    return xdg_data_home() / APP_NAME


def cache_dir() -> Path:
    return xdg_cache_home() / APP_NAME


def default_output_root() -> Path:
    """Default library for downloads (present working directory)."""
    return Path.cwd()


def config_file() -> Path:
    return config_dir() / "config.json"


def system_config_file() -> Path:
    return SYSTEM_CONFIG_DIR / "config.json"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
