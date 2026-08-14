# 0002 — Build Status

| Check | Status |
|-------|--------|
| Unit + integration + UI | Local pytest after 1.2.0 packaging fold |
| Command name | `m3utolocal` / `python -m m3utolocal` |
| Default output | `$XDG_DATA_HOME/m3utolocal/library` (not CWD) |
| pyproject sdist/wheel | `python -m build` |
| FreeBSD port | pep517 + autoplist, DISTVERSION 1.2.0 |
| Linux .deb | `packaging/debian` + `scripts/build-deb` |
| macOS Homebrew | `packaging/homebrew/m3utolocal.rb` (head) |
| `make install` | PREFIX `/usr/local`, fallback `~/.local`; no `.py` in bindir |

T0–T9 from 0300 are implemented. Packaging is the 1.2.0 work.
