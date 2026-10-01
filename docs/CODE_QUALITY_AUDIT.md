# Code Quality Audit: Consensus Refactor Plan

**Project:** `m3utolocal`  
**Version:** 1.2.0  
**Date:** 2026-09-30  
**Authors:** Antigravity / Mark LaPointe · Cursor agent (consensus revision)  
**Repository:** `marklapointe/m3utolocal`  
**Status:** Consensus AGREED and implemented (TDD red-green-refactor)

---

## Executive Summary

Peer review of the original GoF/TAOCP audit corrected several factual errors
(Channel already frozen; Flyweight mislabeled; undocumented 100k-channel SLAs;
incomplete Mapping compat; dual `JobState` types; over-engineered State/Command
hierarchies). This document records the **negotiated plan** and what shipped.

---

## Consensus Priority Order

| Phase | Change | Priority | Status |
| :--- | :--- | :--- | :--- |
| **1** | EMA `RateEstimator` in downloader (`α=0.15`, `dt≥0.1s`) | High | Done |
| **2** | Rename manager progress type → `JobProgress`; use domain `JobState`; TUI cancel + retries | High | Done |
| **3** | `Channel(slots=True)` + `_norm_id` / `_norm_name`; `find_matches` returns mutable dicts | Medium | Done |
| **4** | `iter_m3u` streaming generator; `parse_m3u` keeps missing-file print | Low | Done |
| — | `NameRegistry`, polymorphic `IJobState`, `DownloadCommand` | Dropped | Cut |

---

## Corrections From Original Audit

1. **Channel immutability** — already `@dataclass(frozen=True)`; only `slots=True` was missing.
2. **“Flyweight”** — mislabeled; shipped as slotted value object + cached lowercased fields.
3. **Scale claims** — 100k–200k / 100MB figures removed as product SLAs; treated as optional headroom.
4. **`dict(ch)`** — Channel implements `collections.abc.Mapping` (`__getitem__`, `__iter__`, `__len__`).
5. **Size probing** — `find_matches` always returns **mutable dicts**; frozen Channel is never mutated in place.
6. **Norm keys** — separate `_norm_id` and `_norm_name` (no joined key false-match across spaces).
7. **JobState** — domain enum is canonical; manager dataclass renamed to `JobProgress`.
8. **Phase 4 original** — State/Command hierarchies dropped; cancel token + retries wired into `DownloadManager`.
9. **EMA `dt`** — threshold is `0.1s` (aligned with UI update throttle).
10. **Missing file** — `parse_m3u` still prints `Error: … not found.` and returns `[]`.

---

## Implemented Design

### Phase 1 — `RateEstimator`

```python
# m3utolocal/downloader.py
class RateEstimator:
    def __init__(self, alpha: float = 0.15) -> None: ...
    def update(self, current_bytes: int, now: float) -> float: ...
```

Wired into `_write_body` for rate/ETA display. Tests: `tests/unit/test_rate_estimator.py`.

### Phase 2 — `JobProgress` + cancel + retries

- `services/download_manager.py`: `JobProgress` holds `status: JobState`, `cancel_event`.
- `DownloadManager.cancel()` sets cancel flags; queued jobs → `CANCELLED`.
- `start_downloads(threads, retries=…)` retries recoverable failures; cooperative
  `cancel_check` in `download_file` raises `DownloadCancelled` (`.part` preserved).
- TUI `DownloadsScreen`: Cancel binding (`c`) + button.
- App passes `settings.retries` into `start_downloads`.

Tests: `tests/unit/test_job_progress.py`.

### Phase 3 — Slotted Channel + normalized search

```python
@dataclass(frozen=True, slots=True)
class Channel(Mapping[str, Any]):
    tvg_id: str
    tvg_name: str
    url: str
    size: int = 0
    _norm_id: str = field(init=False, ...)
    _norm_name: str = field(init=False, ...)
```

`find_matches` accepts `Channel | Mapping`, uses `_norm_*` for Channel inputs,
returns `list[dict]` for size probing.

Tests: `tests/unit/test_channel_slotted.py`, `tests/unit/test_find_matches_normalized.py`.

### Phase 4 — Streaming parser

- `iter_m3u(path) -> Iterator[Channel]`
- `parse_m3u(path) -> list[Channel]` (missing file: print + `[]`)

Tests: `tests/unit/test_iter_m3u_streaming.py`.

---

## Acceptance Criteria

| Invariant | Pass criteria |
| :--- | :--- |
| Non-regression | Full `pytest tests/` green |
| ETA smoothing | Micro-intervals (`dt < 0.1`) reuse cached rate; spikes dampened |
| Cancel | Active/queued jobs → `JobState.CANCELLED`; workers halt |
| Retries | Up to `settings.retries` before `JobState.FAILED` |
| Search semantics | `"foo bar"` does not match `id=foo` + `name=bar` |
| Size probing | CLI/TUI may assign `match["size"]` without `FrozenInstanceError` |
| Missing file | `parse_m3u` prints error and returns `[]` |

---

## Dropped From Original Plan

- `NameRegistry` / O(1) collision counter — `unique_filename` sufficient
- Polymorphic `IJobState` ABC hierarchy
- `DownloadCommand` command objects
- Single joined `_norm_key`
- Claiming Flyweight / 100k-channel memory SLAs as product requirements
