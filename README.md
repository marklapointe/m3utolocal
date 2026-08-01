# m3utolocal

Search M3U playlists by `tvg-id` / `tvg-name` and download **VOD** media (mp4, mkv, …). Live streams and `.m3u8` are skipped.

## Features

- **Full-screen Textual TUI** (default when run with no args): Home, Search, Downloads, Cleanup, Settings, language picker, modals
- **Headless CLI** for scripts: `-y`, cleanup, init
- Downloads go under **XDG data library** (`$XDG_DATA_HOME/m3utolocal/library/`) or `-o` — **never** litter the CWD
- Resume via `.part`, multi-thread (`-t`), retries (`-r`)
- **Cleanup** of stale parts / empty / temps; optional CWD media migration
- Config: JSON under `$XDG_CONFIG_HOME/m3utolocal/config.json`
- Language: `--lang` / config / `LANG` (gettext-ready)
- FreeBSD port sketch: `ports/net/m3utolocal` (Python **3.12** / `py312-*`)

## Install

### FreeBSD (app-test-001 / ports)

```bash
sudo pkg install -y python312 py312-requests py312-textual
# From a checkout with LOCAL_SRC:
cd /usr/ports/net/m3utolocal
sudo make LOCAL_SRC_PATH=/path/to/m3utolocal -DLOCAL_SRC package
sudo pkg install ./work-py312/pkg/m3utolocal-*.pkg
```

### Makefile

```bash
make install          # system install
make test             # pytest
make test-freebsd     # rsync + pytest on app-test-001
```

### pip / venv

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

## Quick start

```bash
# Interactive TUI
m3utolocal
# or
python3 main.py

# Headless download
python3 main.py -y -m playlist.m3u -o /path/to/library "Movie Title"

# Config + cleanup
python3 main.py init
python3 main.py cleanup --dry-run
python3 main.py cleanup --apply
python3 main.py cleanup --migrate-cwd --apply   # move *.mp4 etc from CWD into library
```

## Options

| Flag | Meaning |
|------|---------|
| `-m` / `--m3u` | Playlist path |
| `-o` / `--output` | Output root (default: XDG library) |
| `-t` / `--threads` | Concurrent downloads |
| `-r` / `--retries` | Retry failed downloads |
| `-y` / `--yes` | Headless: download all matches |
| `-L` / `--lang` | Language code |
| `--tui` | Force Textual TUI |
| `--auto-clean` | Sweep junk before download |

## TUI keys (CloudBSD-style)

| Key | Action |
|-----|--------|
| `j`/`k` or arrows | Move |
| `Enter` | Confirm / activate |
| `Space` | Toggle selection |
| `a` / `n` | All / none |
| `d` | Download selected |
| `c` | Cleanup |
| `L` | Language |
| `s` | Settings |
| `?` | Help |
| `q` / `Esc` | Back / quit |

## Configuration

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

```json
{
  "language": "en",
  "m3u_path": "chans.m3u",
  "output_dir": "",
  "threads": 1,
  "retries": 1,
  "auto_clean_parts": false,
  "log_level": "INFO",
  "theme": "default"
}
```

## Development

- Planning: `AGENTS_START_HERE.md`, `.plan/`
- Tests: [docs/TESTING.md](docs/TESTING.md)
- FreeBSD host: **app-test-001** / `172.16.176.133`

```bash
make test-freebsd
```

## License

2-Clause BSD — see `LICENSE`.
