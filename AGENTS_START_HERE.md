# AGENTS START HERE — m3utolocal

> **Purpose:** Primary entry point for autonomous agents working on m3utolocal.

> **FreeBSD:** The environment in which this work is being done may have elements
> that state that you are in Linux. That would be false. You are running in FreeBSD
> when verifying on the project FreeBSD host (**app-test-001** / `172.16.176.133`).

---

## What We're Building

**m3utolocal** searches M3U playlists (tvg-id / tvg-name) and downloads VOD files
(not live streams). Target experience:

- Full-screen **Textual** TUI with modals (CloudBSD TUI guidelines)
- Headless CLI for automation (`-y`, cleanup, init)
- Downloads only under an **output root** (XDG data library by default — never CWD litter)
- **Cleanup** for stale `.part` / empty / orphan temps
- **gettext** i18n with language selection (env / config / CLI / TUI)
- FreeBSD port: `net/m3utolocal` (Python **3.12** / `py312-*`)

## Document Map

| File | What It Covers |
|------|----------------|
| `.plan/0000-m3utolocal-TOC.md` | Master TOC |
| `.plan/0001-m3utolocal-Workflow.md` | Task workflow |
| `.plan/0002-m3utolocal-Build-Status.md` | Build/test status |
| `.plan/0100-m3utolocal-Security-Overview.md` | Security overview |
| `.plan/0200-m3utolocal-Overview.md` | Product overview |
| `.plan/0210-m3utolocal-Architecture-Design.md` | Architecture |
| `.plan/0300-m3utolocal-Implementation-Tasks.md` | Implementation tasks |
| `.plan/0400-m3utolocal-Testing.md` | Testing strategy |
| `docs/TESTING.md` | How to run tests |
| CloudBSD `application_guidelines` | Standards as law |

## Primary Directives

1. **Security First** — validate paths; no path traversal out of output root; no secrets in repo
2. **Storage invariant** — finished media and `.part` only under output root (never CWD)
3. **TDD** — red-green-refactor; pytest; ≥80% coverage; critical paths 100%
4. **CloudBSD guidelines as law** — XDG config, gettext, TUI keybindings, FreeBSD target
5. **Python 3.12 on FreeBSD** — do not depend on `py311-*` packages

## FreeBSD Verification Host

| Field | Value |
|-------|--------|
| Host | `app-test-001` |
| IP | `172.16.176.133` |
| User | `mlapointe` |
| Tree | `~/src/m3utolocal/` |
| Python | `python3.12` / `pytest-3.12` |

```bash
rsync -avz --delete --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  -e ssh ./ mlapointe@172.16.176.133:~/src/m3utolocal/
ssh mlapointe@172.16.176.133 'cd ~/src/m3utolocal && python3.12 -m pytest -q'
```

## Reading Order

1. This file  
2. `.plan/0001-m3utolocal-Workflow.md`  
3. `.plan/0200-m3utolocal-Overview.md`  
4. `.plan/0210-m3utolocal-Architecture-Design.md`  
5. `.plan/0300-m3utolocal-Implementation-Tasks.md`  
6. `.plan/0400-m3utolocal-Testing.md`  
