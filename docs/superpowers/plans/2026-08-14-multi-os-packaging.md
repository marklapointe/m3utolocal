# Multi-OS Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship m3utolocal 1.2.0 as the command `m3utolocal` from one sdist, with a FreeBSD port, Homebrew formula, Linux `.deb`, and a single `make install`.

**Architecture:** Fold root modules into the `m3utolocal` package, add PEP 621 `pyproject.toml` with `[project.scripts] m3utolocal = "m3utolocal.cli:main"`, fix `default_output_root()` to the XDG library, then wrap the same sdist in port / brew / deb.

**Tech Stack:** Python 3.12+, setuptools, requests, textual, GNU make, FreeBSD ports, dpkg/pybuild, Homebrew.

**Spec:** `docs/superpowers/specs/2026-08-14-multi-os-packaging-design.md`

## Global Constraints

- Installed command name is exactly `m3utolocal` on linux, freebsd, and darwin.
- `requires-python = ">=3.12"`. Dependencies: `requests>=2.31.0`, `textual>=0.80.0`.
- Single `make install`. PREFIX default `/usr/local`. If PREFIX is not writable and DESTDIR is empty, fall back to `$(HOME)/.local`. DESTDIR staging never falls back.
- Supported OS set is `{linux, freebsd, darwin}`; anything else prints `unsupported OS: <name>` and exits 1.
- GNU make required (`gmake` on FreeBSD/macOS).
- No `.py` files in bindir. No `install-user` target. No playlist/media in packages.
- Default download root is `$XDG_DATA_HOME/m3utolocal/library`.
- License stays BSD-2-Clause. Version is `1.2.0`.
- TDD: failing test first for behavior changes.

## File map

| Path | Role |
|------|------|
| `pyproject.toml` | Create — PEP 621 + console script |
| `m3utolocal/cli.py` | Create — move `main()` from `main.py` |
| `m3utolocal/__main__.py` | Create — `python -m m3utolocal` |
| `m3utolocal/utils.py` | Create — fold root `utils.py` |
| `m3utolocal/downloader.py` | Create — fold root `downloader.py` |
| `m3utolocal/tui.py` | Create — fold root `tui.py` |
| `m3utolocal/cli_progress.py` | Create — fold root `download_manager.py` |
| `m3utolocal/infra/paths.py` | Modify — XDG library default |
| `m3utolocal/__init__.py` | Modify — version 1.2.0 |
| `main.py` | Modify — 4-line shim |
| `Makefile` | Rewrite — commandments + package targets |
| `ports/net/m3utolocal/*` | Modify — pep517/autoplist, 1.2.0 |
| `packaging/debian/*` | Create — dh/pybuild |
| `packaging/homebrew/m3utolocal.rb` | Create — formula |
| `scripts/make_distinfo.sh` | Rewrite — `python -m build --sdist` |
| `tests/unit/test_config_xdg.py` | Modify — XDG library assert |
| `tests/unit/test_entry_points.py` | Create — command name / help |
| `tests/unit/test_distinfo.py` | Modify — 1.2.0 names |
| import sites listed in Task 2 | Modify — `m3utolocal.*` |
| `README.md`, `man/m3utolocal.1`, `docs/TESTING.md`, `.plan/*` | Modify — document `m3utolocal` |

---

### Task 1: Default output is the XDG library

**Files:**
- Modify: `m3utolocal/infra/paths.py`
- Modify: `tests/unit/test_config_xdg.py`

**Interfaces:**
- Consumes: `data_dir()` → `xdg_data_home() / "m3utolocal"`
- Produces: `default_output_root() -> Path` equal to `data_dir() / "library"`

- [ ] **Step 1: Write the failing test**

Replace `test_default_output_is_cwd` in `tests/unit/test_config_xdg.py`:

```python
def test_default_output_is_xdg_library(xdg_env):
    root = default_output_root()
    assert root == xdg_env / "data" / "m3utolocal" / "library"
    assert root.resolve() != Path.cwd().resolve()
```

Keep `xdg_env` — it sets `XDG_DATA_HOME` to `tmp_path / "data"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_config_xdg.py::test_default_output_is_xdg_library -v`

Expected: FAIL — function still returns `Path.cwd()`.

- [ ] **Step 3: Write minimal implementation**

In `m3utolocal/infra/paths.py` replace `default_output_root`:

```python
def default_output_root() -> Path:
    """Default library for downloads (XDG data, never CWD)."""
    return data_dir() / "library"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_config_xdg.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add m3utolocal/infra/paths.py tests/unit/test_config_xdg.py
git commit -m "fix: default download root to XDG library, not CWD"
```

---

### Task 2: Fold root modules into the package

**Files:**
- Create: `m3utolocal/utils.py` (copy of root `utils.py`)
- Create: `m3utolocal/downloader.py` (copy; change import)
- Create: `m3utolocal/tui.py` (copy; change import)
- Create: `m3utolocal/cli_progress.py` (copy of root `download_manager.py`)
- Modify imports in: `m3utolocal/domain/job_builder.py`, `m3utolocal/services/download_manager.py`, `m3utolocal/ui/screens.py`, `m3utolocal/ui/modals.py`, `tests/unit/test_utils_format.py`, `tests/unit/test_utils_parse_m3u.py`, `tests/unit/test_utils_sanitize.py`, `tests/unit/test_download_resume.py`, `tests/unit/test_download_progress_cb.py`, `tests/integration/test_download_pipeline.py`, `tests/ui/test_tui_enhanced.py`
- Delete after green: root `utils.py`, `downloader.py`, `tui.py`, `download_manager.py`

**Interfaces:**
- Consumes: existing public functions (`format_size`, `parse_m3u`, `sanitize_filename`, `download_file`, `tui_select`)
- Produces: same names under `m3utolocal.utils`, `m3utolocal.downloader`, `m3utolocal.tui`, `m3utolocal.cli_progress.DownloadManager`

- [ ] **Step 1: Write the failing import test**

Create `tests/unit/test_package_imports.py`:

```python
def test_utils_lives_in_package():
    from m3utolocal.utils import format_size, parse_m3u, sanitize_filename
    assert format_size(1024) == "1.00 KB"


def test_downloader_lives_in_package():
    from m3utolocal.downloader import download_file
    assert callable(download_file)


def test_cli_progress_manager():
    from m3utolocal.cli_progress import DownloadManager
    assert DownloadManager(1) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_package_imports.py -v`

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Copy modules and fix internal imports**

Copy the four root files into the package. Change:

- `m3utolocal/downloader.py`: `from m3utolocal.utils import format_time`
- `m3utolocal/tui.py`: `from m3utolocal.utils import format_size`

Update existing package/test imports:

```python
from m3utolocal.utils import sanitize_filename  # job_builder
from m3utolocal.utils import format_size        # services/download_manager, ui
from m3utolocal.downloader import download_file
from m3utolocal.tui import tui_select
from m3utolocal.cli_progress import DownloadManager  # only CLI; TUI keeps services.download_manager
```

In `m3utolocal/services/download_manager.py` change `from downloader import download_file` to `from m3utolocal.downloader import download_file`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/unit tests/integration tests/ui -q`

Expected: PASS. Then delete the four root modules and re-run. If anything still imports the root names, fix it.

- [ ] **Step 5: Commit**

```bash
git add m3utolocal tests
git rm utils.py downloader.py tui.py download_manager.py
git commit -m "refactor: fold root modules into the m3utolocal package"
```

---

### Task 3: `m3utolocal` console entry

**Files:**
- Create: `m3utolocal/cli.py` (body of today's `main.py` with package imports)
- Create: `m3utolocal/__main__.py`
- Create: `pyproject.toml`
- Create: `tests/unit/test_entry_points.py`
- Modify: `main.py` (shim)
- Modify: `m3utolocal/__init__.py` (`__version__ = "1.2.0"`)

**Interfaces:**
- Consumes: `m3utolocal.cli_args.parse_args`, folded modules
- Produces: `m3utolocal.cli.main(argv=None) -> None`; console script `m3utolocal`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_entry_points.py
import subprocess
import sys

from m3utolocal import __version__


def test_version_is_120():
    assert __version__ == "1.2.0"


def test_module_help_uses_prog_m3utolocal():
    proc = subprocess.run(
        [sys.executable, "-m", "m3utolocal", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "usage: m3utolocal" in proc.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_entry_points.py -v`

Expected: FAIL (`__version__` is 1.1.0; `-m m3utolocal` has no `__main__`)

- [ ] **Step 3: Implement entry points**

`m3utolocal/__init__.py`: `__version__ = "1.2.0"`

`m3utolocal/__main__.py`:

```python
from m3utolocal.cli import main

if __name__ == "__main__":
    main()
```

`m3utolocal/cli.py`: move `main()` from `main.py`. Imports:

```python
from m3utolocal.utils import format_size, get_file_size, parse_m3u
from m3utolocal.tui import tui_select
from m3utolocal.cli_progress import DownloadManager
from m3utolocal.downloader import download_file
from m3utolocal.cli_args import parse_args
# remaining m3utolocal.* imports unchanged
```

`main.py`:

```python
#!/usr/bin/env python3
from m3utolocal.cli import main

if __name__ == "__main__":
    main()
```

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "m3utolocal"
version = "1.2.0"
description = "Search M3U playlists and download VOD files to a local library"
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.12"
authors = [{ name = "Mark LaPointe", email = "mark@cloudbsd.org" }]
dependencies = [
  "requests>=2.31.0",
  "textual>=0.80.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-cov>=5.0.0",
  "pytest-asyncio>=0.24.0",
  "responses>=0.25.0",
]

[project.scripts]
m3utolocal = "m3utolocal.cli:main"

[tool.setuptools.packages.find]
include = ["m3utolocal*"]

[tool.setuptools.package-data]
m3utolocal = [
  "i18n/locales/**/*.mo",
  "i18n/locales/**/*.po",
  "i18n/locales/*.pot",
  "i18n/complete_maps.json",
  "ui/css/*.tcss",
]
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/unit/test_entry_points.py tests/integration/test_cli_regression.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml m3utolocal/cli.py m3utolocal/__main__.py m3utolocal/__init__.py main.py tests/unit/test_entry_points.py
git commit -m "feat: install as the m3utolocal console script"
```

---

### Task 4: Makefile install commandments

**Files:**
- Modify: `Makefile`
- Create: `tests/unit/test_makefile_install.py` (or a shell check in `tests/integration/test_make_install.py`)

**Interfaces:**
- Consumes: wheel from `python -m build`
- Produces: `$(PREFIX)/bin/m3utolocal`, sitelib package, man page

- [ ] **Step 1: Write the failing install test**

```python
# tests/integration/test_make_install.py
import os
import subprocess
from pathlib import Path


def test_make_install_prefix_puts_m3utolocal_on_bindir(tmp_path):
    root = Path(__file__).resolve().parents[2]
    prefix = tmp_path / "prefix"
    env = os.environ.copy()
    env["DESTDIR"] = ""
    subprocess.run(
        ["make", "install", f"PREFIX={prefix}", f"PYTHON={env.get('PYTHON', 'python3')}"],
        cwd=root,
        check=True,
        env=env,
    )
    exe = prefix / "bin" / "m3utolocal"
    assert exe.is_file()
    assert not (prefix / "bin" / "utils.py").exists()
    help_out = subprocess.run([str(exe), "--help"], capture_output=True, text=True)
    assert help_out.returncode == 0
    assert "usage: m3utolocal" in help_out.stdout
```

Note: `make install` must work with DESTDIR empty and an explicit PREFIX (no ~/.local fallback when PREFIX is a writable tmp path).

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/integration/test_make_install.py -v`

Expected: FAIL — current Makefile copies `.py` into bindir and does not build a console script.

- [ ] **Step 3: Rewrite Makefile**

Required behavior (implement with portable POSIX recipes; GNU make is the documented tool):

```make
PREFIX ?= /usr/local
PYTHON ?= python3.12
BINNAME := m3utolocal
UNAME_S := $(shell uname -s)
DESTDIR ?=

ifeq ($(UNAME_S),Linux)
FRAGMENT_OS := linux
else ifeq ($(UNAME_S),FreeBSD)
FRAGMENT_OS := freebsd
else ifeq ($(UNAME_S),Darwin)
FRAGMENT_OS := darwin
else
$(error unsupported OS: $(UNAME_S))
endif

.PHONY: all build install uninstall test package

all: build

build:
	$(PYTHON) -m build

# install: if PREFIX not writable and DESTDIR empty → HOME/.local
# DESTDIR set → never fall back
# pip install the wheel with --prefix; also install man/m3utolocal.1
```

Install implementation sketch:

```make
install: build
	@prefix="$(PREFIX)"; \
	if [ -z "$(DESTDIR)" ] && [ ! -w "$$prefix" ] && [ ! -w "$$prefix/.." ]; then \
		prefix="$(HOME)/.local"; \
	fi; \
	wheel=$$(ls -1 dist/m3utolocal-*.whl | tail -1); \
	$(PYTHON) -m pip install --prefix="$$prefix" --root="$(DESTDIR)" --no-deps --force-reinstall "$$wheel"; \
	mkdir -p "$(DESTDIR)$$prefix/share/man/man1"; \
	cp man/m3utolocal.1 "$(DESTDIR)$$prefix/share/man/man1/"
```

Remove the old `cp utils.py tui.py … $(BINDIR)` rules.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/integration/test_make_install.py -v`

Expected: PASS. Also `python3 -m pytest -q` stays green.

- [ ] **Step 5: Commit**

```bash
git add Makefile tests/integration/test_make_install.py
git commit -m "build: single make install that ships the m3utolocal command"
```

---

### Task 5: FreeBSD port pep517

**Files:**
- Modify: `ports/net/m3utolocal/Makefile`
- Modify: `ports/net/m3utolocal/pkg-descr` (command is `m3utolocal`)
- Delete or empty: hand-maintained `pkg-plist` if switching to `autoplist`
- Modify: `scripts/make_distinfo.sh` to run `python -m build --sdist`
- Modify: `tests/unit/test_distinfo.py` for `m3utolocal-1.2.0.tar.gz`

**Interfaces:**
- Consumes: sdist `m3utolocal-1.2.0.tar.gz`
- Produces: `/usr/local/bin/m3utolocal` via `USE_PYTHON=pep517 autoplist`

- [ ] **Step 1: Update distinfo test for 1.2.0**

```python
assert "SHA256 (m3utolocal-1.2.0.tar.gz)" in text
```

Skip the tarball byte-match until the sdist exists; split into `test_distinfo_names_120` (always) and `test_release_tarball_matches_distinfo` (skip if missing, or run after `scripts/make_distinfo.sh`).

- [ ] **Step 2: Run test — expect FAIL on 1.1.0 strings**

- [ ] **Step 3: Port Makefile**

```make
PORTNAME=	m3utolocal
DISTVERSION=	1.2.0
CATEGORIES=	net
# ...
BUILD_DEPENDS=	${PYTHON_PKGNAMEPREFIX}setuptools>=0:devel/py-setuptools@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}wheel>=0:devel/py-wheel@${PY_FLAVOR}
RUN_DEPENDS=	${PYTHON_PKGNAMEPREFIX}requests>=2.31.0:www/py-requests@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}textual>=0.80.0:textproc/py-textual@${PY_FLAVOR}
USES=		python
USE_PYTHON=	pep517 autoplist concurrent flavors
NO_ARCH=	yes
```

Remove `do-install` hand copies of `utils.py` / `tui.py`. Keep `LOCAL_SRC` override. Install man via `PLIST_FILES= share/man/man1/m3utolocal.1.gz` plus a one-line `post-install` or `MAKE_ENV`.

Rewrite `scripts/make_distinfo.sh` to `python3 -m build --sdist` and write `ports/net/m3utolocal/distinfo` from that tarball.

- [ ] **Step 4: On app-test-001 (when reachable)**

```bash
make test-freebsd
# then LOCAL_SRC package + pkg info -l m3utolocal | grep bin/m3utolocal
```

If the host is down, leave the port files ready and record that FreeBSD package-install is unverified.

- [ ] **Step 5: Commit**

```bash
git add ports/net/m3utolocal scripts/make_distinfo.sh tests/unit/test_distinfo.py
git commit -m "packaging: FreeBSD port uses pep517 and autoplist for 1.2.0"
```

---

### Task 6: Linux .deb and Homebrew formula

**Files:**
- Create: `packaging/debian/control`, `packaging/debian/rules`, `packaging/debian/changelog`, `packaging/debian/copyright`, `packaging/debian/source/format`, `packaging/debian/manpages`
- Create: `packaging/homebrew/m3utolocal.rb`
- Create: `scripts/build-deb`
- Modify: `Makefile` `package` target

**Interfaces:**
- Consumes: same sdist / pyproject
- Produces: `.deb` with `/usr/bin/m3utolocal`; formula that installs `m3utolocal`

- [ ] **Step 1: Test that package metadata names the command**

```python
# tests/unit/test_packaging_metadata.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_debian_control_package_name():
    text = (ROOT / "packaging" / "debian" / "control").read_text()
    assert "Package: m3utolocal" in text
    assert "python3-textual" in text


def test_homebrew_formula_bin_name():
    text = (ROOT / "packaging" / "homebrew" / "m3utolocal.rb").read_text()
    assert 'virtualenv_install_with_resources' in text
    assert "m3utolocal" in text
```

- [ ] **Step 2: Run — expect FAIL (files missing)**

- [ ] **Step 3: Add debian + brew + `scripts/build-deb`**

`packaging/debian/control`:

```
Source: m3utolocal
Section: net
Priority: optional
Maintainer: Mark LaPointe <mark@cloudbsd.org>
Build-Depends: debhelper-compat (= 13), dh-python, python3-all, python3-setuptools, python3-wheel
Standards-Version: 4.7.0
Homepage: https://github.com/marklapointe/m3utolocal

Package: m3utolocal
Architecture: all
Depends: ${python3:Depends}, ${misc:Depends}, python3-requests, python3-textual
Description: Search M3U playlists and download VOD files
 m3utolocal searches M3U playlists and downloads VOD media to an XDG library.
```

`packaging/debian/rules`:

```make
#!/usr/bin/make -f
export PYBUILD_NAME=m3utolocal
%:
	dh $@ --with python3 --buildsystem=pybuild
```

Homebrew formula: `class M3utolocal < Formula`, `depends_on "python@3.12"`, resource blocks for requests and textual (pin versions from a lock comment), `virtualenv_install_with_resources`. `make package` on Darwin prints `brew install --formula packaging/homebrew/m3utolocal.rb`.

`scripts/build-deb` copies `packaging/debian` to a sdist extract (or the repo root) and runs `dpkg-buildpackage -us -uc -b` when `dpkg-buildpackage` exists; otherwise exits 0 with a skip message so Linux CI without Debian tooling does not false-fail unit tests.

- [ ] **Step 4: Run unit metadata tests; run `scripts/build-deb` if dpkg tools exist**

- [ ] **Step 5: Commit**

```bash
git add packaging scripts/build-deb Makefile tests/unit/test_packaging_metadata.py
git commit -m "packaging: add Debian package and Homebrew formula"
```

---

### Task 7: Docs, man, plan status

**Files:**
- Modify: `README.md` — install via `m3utolocal`, drop `python3 main.py` as primary
- Modify: `man/m3utolocal.1` — version 1.2.0
- Modify: `docs/TESTING.md`, `docs/CONFIGURATION.md`
- Modify: `.plan/0002-m3utolocal-Build-Status.md`, `.plan/0300-m3utolocal-Implementation-Tasks.md`
- Modify: `AGENTS_START_HERE.md` if it still says CWD-safe while code was not

- [ ] **Step 1: Grep for `python3 main.py` and `1.1.0` in docs/man/README**

- [ ] **Step 2: Update every user-facing invocation to `m3utolocal`**

- [ ] **Step 3: Mark T0–T9 complete where the code exists; add packaging tasks as done in 0002**

- [ ] **Step 4: `python3 -m pytest -q` green**

- [ ] **Step 5: Commit**

```bash
git add README.md man/m3utolocal.1 docs .plan AGENTS_START_HERE.md
git commit -m "docs: document m3utolocal as the only user command"
```

---

## Self-review

1. Spec coverage: XDG fix, fold, console script, Makefile, FreeBSD, deb, brew, docs — each has a task.
2. No TBD/TODO placeholders.
3. Names: `m3utolocal.cli:main`, `cli_progress.DownloadManager`, version `1.2.0` consistent.

## Execution

This plan is ready. User already said to proceed (approach A, command `m3utolocal`, "get to it"). Execute inline in this session, task by task, TDD, frequent commits.
