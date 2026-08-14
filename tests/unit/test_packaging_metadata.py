import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_debian_control_package_name():
    text = (ROOT / "packaging" / "debian" / "control").read_text(encoding="utf-8")
    assert "Package: m3utolocal" in text
    assert "python3-textual" in text
    assert "pybuild-plugin-pyproject" in text


def test_homebrew_formula_bin_name():
    text = (ROOT / "packaging" / "homebrew" / "m3utolocal.rb").read_text(encoding="utf-8")
    assert "virtualenv_install_with_resources" in text
    assert "m3utolocal" in text
    assert "python@3.12" in text
    for name, sha in re.findall(r'resource "([^"]+)".*?sha256 "([0-9a-f]+)"', text, re.S):
        assert len(sha) == 64, f"{name} sha256 length {len(sha)}"


def test_pyproject_console_script():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'm3utolocal = "m3utolocal.cli:main"' in text
    assert 'version = "1.2.0"' in text
