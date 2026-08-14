import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("make") is None, reason="make not available")
def test_make_install_prefix_puts_m3utolocal_on_bindir(tmp_path):
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    env = os.environ.copy()
    env["DESTDIR"] = ""
    proc = subprocess.run(
        ["make", "install", f"PREFIX={prefix}", f"PYTHON={sys.executable}"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    exe = prefix / "bin" / "m3utolocal"
    assert exe.is_file(), proc.stdout + proc.stderr
    assert not (prefix / "bin" / "utils.py").exists()
    help_out = subprocess.run([str(exe), "--help"], capture_output=True, text=True)
    assert help_out.returncode == 0, help_out.stdout + help_out.stderr
    assert "usage: m3utolocal" in help_out.stdout
