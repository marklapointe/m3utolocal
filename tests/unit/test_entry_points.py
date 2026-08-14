import subprocess
import sys

from m3utolocal import __version__


def test_version_is_120():
    assert __version__ == "1.2.0"


def test_prefix_launcher_extends_path():
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "scripts" / "m3utolocal"
    text = src.read_text(encoding="utf-8")
    assert "site-packages" in text
    assert "from m3utolocal.cli import main" in text


def test_module_help_uses_prog_m3utolocal():
    proc = subprocess.run(
        [sys.executable, "-m", "m3utolocal", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "usage: m3utolocal" in proc.stdout
