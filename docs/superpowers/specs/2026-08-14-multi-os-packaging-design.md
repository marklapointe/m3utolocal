# m3utolocal multi-OS packaging design

**Date:** 2026-08-14  
**Status:** Approved (approach A; command name `m3utolocal`)  
**Version target:** 1.2.0

## Problem

m3utolocal 1.1.0 is a working TUI/CLI, but it is not shippable on FreeBSD, Linux, and macOS.

- There is no `pyproject.toml`, so there is no sdist/wheel source of truth.
- Root modules (`utils.py`, `tui.py`, `downloader.py`, `download_manager.py`) sit outside the package and are imported by it. `make install` copies those files into `/usr/local/bin`.
- The documented command is mixed (`python3 main.py` vs `m3utolocal`).
- `default_output_root()` returns `Path.cwd()` while README, man, and AGENTS promise `$XDG_DATA_HOME/m3utolocal/library/`. That is why media files land in the checkout.
- The FreeBSD port is a hand-copied file list. There is no Homebrew formula and no Linux `.deb`.

## Goals

1. The installed program is always the command `m3utolocal` on FreeBSD, Linux, and macOS.
2. One sdist from `pyproject.toml` is the source of truth for every OS package.
3. Native packages: FreeBSD port → `.pkg`, Homebrew formula, Linux `.deb`.
4. `make install` is the single install interface (PREFIX `/usr/local`, fallback `$HOME/.local`, DESTDIR never falls back).
5. Fix the CWD storage invariant so default downloads go under the XDG library.
6. Fold the dual module layout into one package so installed sitelib is self-contained.

Non-goals: Windows, frozen PyInstaller binaries, RPM for this release, changing the BSD-2-Clause license, adding features.

## Command name

| Interface | Required |
|-----------|----------|
| `m3utolocal` | Yes — the only documented user command after install |
| `python -m m3utolocal` | Yes — same `main()` |
| `python3 main.py` | Checkout-only shim during transition; not installed, not documented |

`BINNAME` is `m3utolocal` for system and userspace. Console script:

```toml
[project.scripts]
m3utolocal = "m3utolocal.cli:main"
```

## Package layout

```
m3utolocal/
  __init__.py              # __version__ = "1.2.0"
  __main__.py              # python -m m3utolocal
  cli.py                   # today's main() (argparse + headless + TUI dispatch)
  utils.py                 # folded from repo root
  downloader.py            # folded from repo root
  tui.py                   # curses fallback, folded from repo root
  cli_progress.py          # CLI terminal DownloadManager (today's root download_manager.py)
  cli_args.py
  domain/
  services/                # includes async TUI DownloadManager (unchanged name)
  infra/paths.py           # default_output_root → XDG library
  i18n/                    # locales as package data
  ui/                      # Textual app + css/app.tcss
```

Root `main.py` becomes a four-line shim calling `m3utolocal.cli.main` so a dirty checkout still runs. It is not part of the installed file set.

Root `utils.py`, `tui.py`, `downloader.py`, `download_manager.py` are deleted after the fold. All imports become `from m3utolocal.utils import …` (and the matching new modules).

The two `DownloadManager` types stay separate:

- `m3utolocal.cli_progress.DownloadManager` — threaded ANSI progress for headless CLI
- `m3utolocal.services.download_manager.DownloadManager` — asyncio queue for the Textual app

## pyproject.toml

PEP 621 + setuptools (widest FreeBSD port coverage).

- name: `m3utolocal`
- version: `1.2.0`
- requires-python: `>=3.12`
- dependencies: `requests>=2.31.0`, `textual>=0.80.0`
- optional-dev: pytest, pytest-cov, pytest-asyncio, responses
- package-data: `i18n/locales/**/*.mo`, `i18n/locales/**/*.po`, `i18n/locales/*.pot`, `i18n/complete_maps.json`, `ui/css/*.tcss`
- license: BSD-2-Clause (existing `LICENSE`)

`python -m build` produces `dist/m3utolocal-1.2.0.tar.gz` and the wheel. The FreeBSD `distinfo` and GitHub release tarball are this sdist (not a hand-rolled rsync tree). `scripts/make_distinfo.sh` is rewritten to build via `python -m build --sdist`.

## Makefile (Make Commandments)

Supported OS set: `{linux, freebsd, darwin}`. Anything else: `unsupported OS: <name>` and exit 1.

GNU make is required (`gmake` on FreeBSD/macOS). Document that; do not chase bmake parse-time syntax.

| Target | Behavior |
|--------|----------|
| `all` (bare `make`) | Build sdist + wheel into `dist/` |
| `install` | Build if missing; install wheel with `--prefix=$(PREFIX)`. If PREFIX is not writable and `DESTDIR` is empty, PREFIX becomes `$(HOME)/.local`. DESTDIR staging never falls back. Same `BINNAME`. |
| `uninstall` | Remove `$(PREFIX)/bin/m3utolocal`, the sitelib package, and the man page |
| `test` | pytest |
| `package` | OS-specific package (`pkg`, `.deb`, or echo Homebrew tap path) |

Install layout:

```
$(PREFIX)/bin/m3utolocal
$(PREFIX)/lib/python3.X/site-packages/m3utolocal/   # or dist-packages on Debian
$(PREFIX)/share/man/man1/m3utolocal.1
$(PREFIX)/etc/cloudbsd/m3utolocal/                  # optional system config dir, not required at install
```

Do not copy `.py` files into `bindir`. Do not invent `install-user`.

## OS packages

All three consume the same sdist.

### FreeBSD — `ports/net/m3utolocal`

Switch from `NO_BUILD` + `COPYTREE_SHARE` to:

```
USES=        python shebangfix
USE_PYTHON=  pep517 autoplist concurrent flavors
```

RUN_DEPENDS stay `py-requests` and `py-textual`. BUILD_DEPENDS add setuptools + wheel. Man page via `USE_PYTHON` plus `MAN1` or `PLIST_FILES`. Drop the hand-maintained `pkg-plist` of every locale file; `autoplist` owns it. Keep `LOCAL_SRC` / `LOCAL_SRC_PATH` for lab builds. Python 3.12 (`py312-*`).

### Linux — Debian package in `packaging/debian/`

`dh` + `pybuild`. Binary package `m3utolocal`. Depends: `python3-requests`, `python3-textual`. Installs `/usr/bin/m3utolocal` (Debian policy prefix) and the man page. `make package` on Linux runs `dpkg-buildpackage -us -uc` or a documented `scripts/build-deb` that uses the sdist.

Minimum: Debian 13 / Ubuntu 24.04+ (textual in distro). Document that.

### macOS — Homebrew formula `packaging/homebrew/m3utolocal.rb`

Standard Python formula: `depends_on "python@3.12"`, `virtualenv_install_with_resources` for `requests` and `textual`. Installs `m3utolocal` into the formula prefix (Homebrew then links into `$(brew --prefix)/bin`). `make package` on Darwin prints the `brew install --formula` command.

## Storage invariant (must-fix)

```python
def default_output_root() -> Path:
    return data_dir() / "library"
```

That is `$XDG_DATA_HOME/m3utolocal/library`, or `~/.local/share/m3utolocal/library` when unset.

Flip `test_default_output_is_cwd` to assert the XDG library path under the `xdg_env` fixture. Headless and TUI downloads write only under that root unless `-o` / config `output_dir` is set.

`cleanup --migrate-cwd` stays: it is the recovery path for the existing CWD litter.

## Testing

- Unit: path default, console-script metadata, import of folded modules.
- Integration: `python -m m3utolocal --help` and installed `m3utolocal --help` both print `usage: m3utolocal`.
- `make install PREFIX=$tmpdir` produces `$tmpdir/bin/m3utolocal` and does not place `utils.py` in `bindir`.
- Existing unit/integration/UI suite stays green.
- Per-OS package claim requires a real install check on that OS (Honcho ship-acceptance). Linux agent may dry-run `dpkg-deb --info` / formula audit; FreeBSD verification stays on app-test-001.

## Error handling

- Unsupported `uname -s` → exit 1 with `unsupported OS: <name>`.
- `make install` with no wheel and failed build → fail, do not copy source trees into bindir.
- Missing textual: TUI path exits 1 with install hint; headless `-y` still works if `requests` is present.
- Port/deb/brew must not ship playlists, `.part`, or media.

## Key Decisions

1. **Approach A** — native packages from one sdist. Users get OS-native install; we do not maintain three source trees.
2. **Command is `m3utolocal`** — console script + `__main__.py`. Matches BINNAME commandment.
3. **setuptools, not hatchling** — FreeBSD `USE_PYTHON=pep517` + `py-setuptools` is the well-trodden path.
4. **Fold, do not re-export from sitelib root** — loose `utils.py` in sitelib pollutes every Python process. Everything lives under `m3utolocal.*`.
5. **Rename root DownloadManager to `cli_progress`** — avoids colliding with `services.download_manager`.
6. **XDG library default** — docs already promised it; the implementation was wrong.
7. **Keep BSD-2-Clause** — existing project license; do not switch to CloudBSD 3-Clause unless asked.
8. **Version 1.2.0** — 1.1.0 tarball/distinfo already exist; packaging + bugfix is a minor bump.

## PR Plan

1. **fix: default output to XDG library** — `paths.py` + tests. No packaging yet.
2. **refactor: fold root modules into `m3utolocal` package** — moves, import updates, `cli.py`, `__main__.py`, checkout shim.
3. **build: pyproject.toml + Makefile install commandments** — sdist/wheel, `make`/`make install`, man page, no bindir `.py`.
4. **packaging: FreeBSD port pep517 + autoplist** — drop hand plist, update distinfo against 1.2.0 sdist.
5. **packaging: Debian + Homebrew** — `packaging/debian/*`, `packaging/homebrew/m3utolocal.rb`, `make package`.
6. **docs: README, man, TESTING, .plan status** — document `m3utolocal` only; mark T0–T9 done where true.

## Open Questions

None. Approach A, command name, and three-OS set are decided.
