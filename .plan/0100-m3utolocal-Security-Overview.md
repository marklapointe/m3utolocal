# 0100 — Security Overview

## Threats

| Threat | Mitigation |
|--------|------------|
| Path traversal via M3U titles | `sanitize_filename` + resolve paths under output root only |
| Arbitrary URL fetch | User-initiated search only; no SSRF to internal nets by design (document risk) |
| Overwrite of unrelated files | Unique job names under output root; no CWD writes |
| Cleanup deleting user data | Dry-run by default; confirm in TUI; only classified items |

## Secrets

No API keys required for core download path. Optional future Honcho key via env only.
