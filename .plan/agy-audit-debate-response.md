### 1. Verification and Critique Resolution

Each peer critique point was verified directly against the live codebase:

1. **`Channel` Immutability ([`m3utolocal/domain/models.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L19-L24))**  
   * **Verdict:** **Conceded**. [`Channel`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L20) is already decorated with `@dataclass(frozen=True)`. Treating immutability as a missing feature in the audit was an oversight; only `slots=True` is missing.
2. **"Flyweight" Mislabeled ([`docs/CODE_QUALITY_AUDIT.md`](file:///home/mlapointe/secure/git/m3uToLocal/docs/CODE_QUALITY_AUDIT.md#L29))**  
   * **Verdict:** **Conceded**. Slotted fields and per-instance precomputed search strings do not share intrinsic state across instances. It is memory layout and cached computation, not a GoF Flyweight.
3. **Undocumented Scale Claims ([`README.md`](file:///home/mlapointe/secure/git/m3uToLocal/README.md), [`docs/CONFIGURATION.md`](file:///home/mlapointe/secure/git/m3uToLocal/docs/CONFIGURATION.md))**  
   * **Verdict:** **Conceded**. Scale figures (100k–200k channels, 100MB playlists) were hypothetical worst-case benchmarks and are not documented project performance requirements.
4. **Defective `dict(ch)` Compat & No-Op Dual Branch ([`docs/CODE_QUALITY_AUDIT.md`](file:///home/mlapointe/secure/git/m3uToLocal/docs/CODE_QUALITY_AUDIT.md#L131-L146), [#L209](file:///home/mlapointe/secure/git/m3uToLocal/docs/CODE_QUALITY_AUDIT.md#L209))**  
   * **Verdict:** **Conceded**. `__getitem__` and `get` without `keys()` / `__iter__` raise `TypeError: 'Channel' object is not iterable` when passed to `dict()`. Furthermore, line 209 (`dict(c) if isinstance(c, Channel) else dict(c)`) was an erroneous no-op dual branch.
5. **Frozen `Channel` vs. In-Place Size Probing ([`m3utolocal/cli.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/cli.py#L162), [`m3utolocal/ui/screens.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L323))**  
   * **Verdict:** **Conceded**. Both [`main()`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/cli.py#L27) and [`_probe_sizes()`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L317) mutate `match["size"]` in place. Returning frozen [`Channel`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L20) instances directly from [`find_matches`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/match.py#L22) breaks existing callers unless matches remain mutable mappings or dict records.
6. **False-Match Boundary in `_norm_key` ([`m3utolocal/domain/match.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/match.py#L33))**  
   * **Verdict:** **Conceded**. Concatenating `f"{id} {name}"` false-matches any query spanning the delimiter boundary (e.g. `tvg_id="xfoo"`, `tvg_name="barx"`, query `"foo bar"`). Precomputing separate `_norm_id` and `_norm_name` is mandatory.
7. **`JobState` Inconsistency & Shadowing ([`m3utolocal/domain/models.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10), [`m3utolocal/services/download_manager.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L15))**  
   * **Verdict:** **Conceded**. [`download_manager.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L15) defines an ad-hoc dataclass also named `JobState` using arbitrary strings (`"Done"`, `"Downloading…"`), shadowing the canonical [`JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) enum. The audit's proposed `IJobState` hierarchy omitted `Skipped` and exacerbated the divergence.
8. **Over-Engineered GoF State / Command ([`docs/CODE_QUALITY_AUDIT.md`](file:///home/mlapointe/secure/git/m3uToLocal/docs/CODE_QUALITY_AUDIT.md#L280-L320))**  
   * **Verdict:** **Conceded**. An abstract class hierarchy (`IJobState`, `DownloadCommand`) adds needless indirection. The actual gap is that [`DownloadManager`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L25) lacks cancellation and retries (which [`cli.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/cli.py#L208) already supports).
9. **Streaming `iter_m3u` Limitations ([`m3utolocal/ui/screens.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L298-L306))**  
   * **Verdict:** **Conceded**. [`DataTable`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L306) and `self.matches` materialize all filtered rows regardless. Streaming benefits headless CLI filtering on sparse queries, but has minimal impact on the interactive search table.
10. **`NameRegistry` Over-Engineering ([`m3utolocal/domain/job_builder.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/job_builder.py#L18-L34))**  
    * **Verdict:** **Conceded**. [`unique_filename`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/job_builder.py#L18) does an $O(1)$ set lookup in a short while-loop. Because collision counts in user downloads are minimal, [`unique_filename`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/job_builder.py#L18) is sufficient.
11. **EMA Rate Discrepancies & Framing ([`m3utolocal/downloader.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/downloader.py#L273), [`docs/CODE_QUALITY_AUDIT.md`](file:///home/mlapointe/secure/git/m3uToLocal/docs/CODE_QUALITY_AUDIT.md#L260))**  
    * **Verdict:** **Conceded**. The audit snippet checked `dt < 0.2` while the test spec and existing code used `0.1`.
12. **Missing-File Behavior Regression ([`m3utolocal/utils.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/utils.py#L56-L58))**  
    * **Verdict:** **Conceded**. [`parse_m3u`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/utils.py#L52) prints `Error: {file_path} not found.` on non-existent files. Silent generation in `iter_m3u` would break caller expectations if `parse_m3u` blindly delegated without retaining the error output.

---

### 2. Defended Core Components (With Evidence)

1. **EMA Throughput Estimator in [`downloader.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/downloader.py#L294):**
   * *Evidence:* [`_write_body`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/downloader.py#L241) computes `rate = downloaded_since_start / elapsed`. On multi-gigabyte files, `elapsed` grows into hundreds of seconds. When bandwidth fluctuates or stalls, the cumulative average takes minutes to adjust, rendering `eta_str` inaccurate. An exponential moving average ($\alpha = 0.15$, $dt \ge 0.1\text{s}$) resolves inertia while preventing tick jitter.
2. **Unifying Job State and Bridging TUI Feature Parity:**
   * *Evidence:* Currently, [`DownloadManager`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L25) sets `state.status = "Done"` and `state.status = "Downloading…"`, bypassing [`JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) (`COMPLETED = "Completed"`, `RUNNING = "Downloading"`). It also lacks cancellation and retry handling. Renaming the manager's dataclass to `JobProgress`, binding it to [`domain.models.JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10), and introducing an `asyncio.Event` cancellation flag + retry loop closes the real operational gap between the CLI and TUI.
3. **Eliminating Allocation Spikes in Channel Search:**
   * *Evidence:* [`find_matches`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/match.py#L33) executes `q not in tvg_id.lower() and q not in tvg_name.lower()` on every channel per keystroke. Caching pre-lowercased identifiers (`_norm_id` and `_norm_name`) avoids repetitive allocations across keystrokes without introducing space-boundary false matches.

---

### 3. Consensus Implementation Plan

#### Phase Breakdown

* **Phase 1: Rate Estimator & Progress Smoothing (High Priority)**
  * Implement `RateEstimator` in [`m3utolocal/downloader.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/downloader.py) using an EMA ($\alpha = 0.15$, threshold $dt \ge 0.1\text{s}$).
  * Replace the cumulative average calculation in [`_write_body`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/downloader.py#L294).
  * *Status:* **Implement**.

* **Phase 2: Job Progress Unification & TUI Cancellation / Retries (High Priority)**
  * In [`m3utolocal/services/download_manager.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py):
    * Rename `@dataclass class JobState` to `JobProgress` to remove shadowing.
    * Use canonical [`domain.models.JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) enum values (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`).
    * Add `cancel()` using `asyncio.Event` and wire retry attempts matching `settings.retries`.
  * In [`m3utolocal/ui/screens.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L489):
    * Add Cancel binding/action to [`DownloadsScreen`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L489).
  * *Status:* **Implement**.

* **Phase 3: Search Caching & Model Hygiene (Medium Priority)**
  * Add `slots=True` to [`Channel`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L20).
  * Add `_norm_id: str` and `_norm_name: str` fields to [`Channel`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L20) computed in `__post_init__` via `object.__setattr__`.
  * Update [`find_matches`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/match.py#L22) to evaluate `q in c._norm_id or q in c._norm_name` when iterating [`Channel`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L20) objects, preserving exact substring semantics.
  * Keep [`find_matches`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/match.py#L22) returning `list[dict[str, Any]]` to preserve in-place size probing in [`cli.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/cli.py#L162) and [`screens.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L323).
  * *Status:* **Implement**.

* **Phase 4: Streaming Parser (Low Priority)**
  * Implement `iter_m3u(file_path)` in [`m3utolocal/utils.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/utils.py) as an optional streaming generator.
  * Keep [`parse_m3u`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/utils.py#L52) printing `Error: {file_path} not found.` and returning `[]` on missing files to prevent regressions.
  * *Status:* **Implement as Low Priority / Defer if time-constrained**.

* **Dropped / Cut Items:**
  * **Drop** `NameRegistry` class; retain [`unique_filename`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/job_builder.py#L18).
  * **Drop** polymorphic `IJobState` class hierarchy; use [`JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) enum and `JobProgress`.
  * **Drop** `DownloadCommand` hierarchy; keep task coordination in [`DownloadManager`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L25).

---

### 4. Concrete Acceptance Criteria

1. **Non-Regression Baseline:**
   * All 102 existing tests in `pytest tests/` pass without modification.
2. **Rate Estimator:**
   * Instantaneous rate spikes do not cause abrupt ETA jumps; rate stabilizes within $\pm 10\%$ on constant byte streams.
   * Calls with $\Delta t < 0.1\text{s}$ return cached rate without recalculating.
3. **State & Cancellation:**
   * Triggering cancellation on [`DownloadManager`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L25) transitions active jobs to `JobState.CANCELLED` and halts background workers.
   * Failed downloads retry up to `settings.retries` before transitioning to `JobState.FAILED`.
   * [`JobProgress.status`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/services/download_manager.py#L17) strictly reflects [`JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) enum values.
4. **Search Semantics:**
   * Query `"foo bar"` matches channel where `tvg_id="foo bar"` or `tvg_name="foo bar"`, but does NOT match `tvg_id="foo"` and `tvg_name="bar"`.
   * Size probing in [`cli.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/cli.py#L162) and [`screens.py`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/ui/screens.py#L323) runs without `FrozenInstanceError` or `TypeError`.
5. **Missing File Handling:**
   * `parse_m3u("nonexistent.m3u")` prints error to stdout and returns `[]`.

---

### 5. Explicit Corrections for `docs/CODE_QUALITY_AUDIT.md`

1. **Section 1.1:** Retitle "Factory / Flyweight" to "Channel Memory Optimization"; remove claim that `Channel` lacks immutability.
2. **Section 1.3:** Replace proposed `IJobState` polymorphic hierarchy and `DownloadCommand` with unified [`JobState`](file:///home/mlapointe/secure/git/m3uToLocal/m3utolocal/domain/models.py#L10) enum wiring, `JobProgress` renaming, and `asyncio.Event` cancellation.
3. **Section 2.1:** Remove 100k–200k channel SLA claims; frame streaming and slots around memory reduction for large playlists.
4. **Section 2.2:** Correct $dt$ threshold in snippet from `0.2` to `0.1` to match implementation and test specifications.
5. **Section 2.3:** Replace single joined `_norm_key` with separate `_norm_id` and `_norm_name` fields. Remove `NameRegistry` class proposal.
6. **Section 4 & 5:**
   * Remove `test_channel_immutable_frozen` (already implemented).
   * Fix `test_channel_dict_mapping_compat` specification (require `collections.abc.Mapping` / `keys()`).
   * Remove `test_name_registry.py` and `test_job_state_transitions.py` polymorphic tests; replace with tests for `JobProgress`, cancellation, and retries.
   * Update `iter_m3u` / `parse_m3u` spec to ensure missing-file error printing is preserved.

---

CONSENSUS: AGREED
