from pathlib import Path

from m3utolocal.infra.paths import config_file, default_output_root
from m3utolocal.services.config import load_settings, save_settings, validate_settings, Settings


def test_default_output_is_cwd(xdg_env):
    root = default_output_root()
    assert root.resolve() == Path.cwd().resolve()


def test_save_and_load(xdg_env):
    s = Settings(language="es", threads=2, m3u_path="/tmp/a.m3u")
    path = save_settings(s)
    assert path == config_file()
    loaded = load_settings()
    assert loaded.language == "es"
    assert loaded.threads == 2


def test_cli_overrides_config(xdg_env):
    save_settings(Settings(language="es", threads=1))
    loaded = load_settings(cli_overrides={"language": "de", "threads": 4})
    assert loaded.language == "de"
    assert loaded.threads == 4


def test_validate_threads():
    errs = validate_settings(Settings(threads=0))
    assert any("threads" in e for e in errs)
