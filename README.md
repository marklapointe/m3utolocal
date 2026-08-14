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

The installed command is **`m3utolocal`** on FreeBSD, Linux, and macOS.

### FreeBSD (ports)

```bash
sudo pkg install -y python312 py312-requests py312-textual
# From a checkout with LOCAL_SRC:
cd /usr/ports/net/m3utolocal
sudo make LOCAL_SRC_PATH=/path/to/m3utolocal -DLOCAL_SRC package
sudo pkg install ./work-py312/pkg/m3utolocal-*.pkg
```

### Linux (.deb)

```bash
# Debian 13 / Ubuntu 24.04+
./scripts/build-deb
sudo apt install ./dist/m3utolocal_*.deb
```

### macOS (Homebrew)

```bash
brew install --HEAD --formula packaging/homebrew/m3utolocal.rb
```

### Makefile / pip

GNU make is required (`gmake` on FreeBSD and macOS).

```bash
make                  # sdist + wheel
make install          # PREFIX=/usr/local, or ~/.local if not writable
make test             # pytest
make test-freebsd     # rsync + pytest on app-test-001
```

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install .
.venv/bin/m3utolocal --help
```

## Quick start

```bash
# Interactive TUI
m3utolocal

# Headless download
m3utolocal -y -m playlist.m3u -o /path/to/library "Movie Title"

# Config + cleanup
m3utolocal init
m3utolocal cleanup --dry-run
m3utolocal cleanup --apply
m3utolocal cleanup --migrate-cwd --apply   # move *.mp4 etc from CWD into library
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
