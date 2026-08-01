"""JSON configuration load/save with XDG + system defaults."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from m3utolocal.infra.paths import (
    config_file,
    default_output_root,
    ensure_dir,
    system_config_file,
)

VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARN", "ERROR"})


@dataclass
class Settings:
    language: str = "en"
    m3u_path: str = "chans.m3u"
    output_dir: str = ""
    threads: int = 1
    retries: int = 1
    auto_clean_parts: bool = False
    log_level: str = "INFO"
    theme: str = "default"

    def resolved_output_dir(self) -> Path:
        if self.output_dir:
            return Path(self.output_dir).expanduser().resolve()
        return default_output_root().resolve()


def default_settings() -> Settings:
    return Settings()


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and v is not None:
            out[k] = v
    return out


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config must be a JSON object: {path}")
    return data


def settings_from_dict(data: dict[str, Any]) -> Settings:
    known = {f.name for f in fields(Settings)}
    filtered = {k: v for k, v in data.items() if k in known}
    s = Settings(**{**asdict(default_settings()), **filtered})
    return s


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if settings.threads < 1:
        errors.append("threads must be >= 1")
    if settings.retries < 0:
        errors.append("retries must be >= 0")
    if settings.log_level.upper() not in VALID_LOG_LEVELS:
        errors.append(f"log_level must be one of {sorted(VALID_LOG_LEVELS)}")
    if not settings.language:
        errors.append("language must be non-empty")
    return errors


def load_settings(
    *,
    cli_overrides: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> Settings:
    """Precedence: CLI overrides > env > user config > system config > defaults."""
    data = asdict(default_settings())

    try:
        data = _merge_dict(data, load_json_file(system_config_file()))
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    user_cfg = config_path or config_file()
    try:
        data = _merge_dict(data, load_json_file(user_cfg))
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    env_lang = os.environ.get("M3UTOLOCAL_LANG")
    if env_lang:
        data["language"] = env_lang
    env_out = os.environ.get("M3UTOLOCAL_OUTPUT_DIR")
    if env_out:
        data["output_dir"] = env_out
    env_m3u = os.environ.get("M3UTOLOCAL_M3U")
    if env_m3u:
        data["m3u_path"] = env_m3u

    if cli_overrides:
        data = _merge_dict(data, {k: v for k, v in cli_overrides.items() if v is not None})

    settings = settings_from_dict(data)
    errors = validate_settings(settings)
    if errors:
        raise ValueError("; ".join(errors))
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    target = path or config_file()
    ensure_dir(target.parent)
    payload = asdict(settings)
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return target


def write_config_template(path: Path | None = None) -> Path:
    """Write default config (m3utolocal init)."""
    return save_settings(default_settings(), path)
