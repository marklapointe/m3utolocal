"""Main application screens."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Static,
)

from m3utolocal.domain.match import find_matches
from m3utolocal.i18n import _, get_language
from m3utolocal.i18n.languages import available_languages
from m3utolocal.services.cleanup import CleanupPolicy, CleanupService
from m3utolocal.services.config import Settings, save_settings
from m3utolocal.ui.modals import (
    CleanupPreviewModal,
    ConfirmModal,
    ErrorModal,
    HelpModal,
    LanguageModal,
)
from m3utolocal.utils import format_size, get_file_size, parse_m3u


class HomeScreen(Screen):
    """Rich dashboard home screen."""

    BINDINGS = [
        Binding("1", "search", "Search", show=True),
        Binding("2", "cleanup", "Cleanup", show=True),
        Binding("3", "settings", "Settings", show=True),
        Binding("4", "language", "Language", show=True),
        Binding("5", "downloads", "Queue", show=True),
        Binding("6", "quit", "Quit", show=True),
        Binding("d", "downloads", "Downloads", show=False),
        Binding("slash", "search", "Search", key_display="/", show=False),
        Binding("s", "settings", "Settings", show=False),
        Binding("c", "cleanup", "Cleanup", show=False),
        Binding("L", "language", "Language", show=False),
        Binding("question_mark", "help", "Help", key_display="?", show=True),
        Binding("q", "quit", "Quit", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(classes="panel", id="home-panel"):
            with Vertical(id="home-banner"):
                yield Static(_("m3utolocal"), id="home-title")
                yield Static(
                    _("M3U Playlist Search & Media Downloader"),
                    id="home-subtitle",
                )
            with Horizontal(classes="stat-grid"):
                with Vertical(classes="stat-card", id="stat-out"):
                    yield Label(_("Library Output"), classes="stat-title")
                    yield Label(
                        _("Output: {path}").format(
                            path=str(self.app.settings.resolved_output_dir())
                        ),
                        classes="stat-val",
                        markup=False,
                    )
                with Vertical(classes="stat-card", id="stat-m3u"):
                    yield Label(_("M3U Playlist"), classes="stat-title")
                    yield Label(
                        _("M3U: {path}").format(path=self.app.settings.m3u_path),
                        classes="stat-val",
                        markup=False,
                    )
                with Vertical(classes="stat-card", id="stat-cfg"):
                    yield Label(_("Settings"), classes="stat-title")
                    yield Label(
                        _("Threads: {threads} · Retries: {retries}").format(
                            threads=self.app.settings.threads,
                            retries=self.app.settings.retries,
                        ),
                        classes="stat-val",
                    )
            yield Static(_("Quick Navigation"), id="home-menu-title")
            with Vertical(id="home-actions"):
                yield Button(_("Search playlist"), variant="primary", id="btn-search", classes="action-btn")
                yield Button(_("Cleanup library"), id="btn-cleanup", classes="action-btn")
                yield Button(_("Settings"), id="btn-settings", classes="action-btn")
                yield Button(_("Language"), id="btn-lang", classes="action-btn")
                yield Button(_("Downloads Queue"), id="btn-dl-queue", classes="action-btn")
                yield Button(_("Quit"), id="btn-quit", classes="action-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-search":
            self.action_search()
        elif bid == "btn-cleanup":
            self.action_cleanup()
        elif bid == "btn-settings":
            self.action_settings()
        elif bid == "btn-lang":
            self.action_language()
        elif bid == "btn-dl-queue":
            self.action_downloads()
        elif bid == "btn-quit":
            self.app.exit()

    def action_search(self) -> None:
        self.app.push_screen(SearchScreen())

    def action_cleanup(self) -> None:
        self.app.push_screen(CleanupScreen())

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_language(self) -> None:
        async def _pick() -> None:
            code = await self.app.push_screen_wait(
                LanguageModal(available_languages(), get_language())
            )
            if code:
                self.app.apply_language(code)
                self.app.switch_screen(HomeScreen())

        self.app.run_worker(_pick())

    def action_downloads(self) -> None:
        self.app.show_downloads_queue()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_quit(self) -> None:
        self.app.exit()


class SearchScreen(Screen):
    """Playlist search and selection screen."""

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", show=True),
        Binding("q", "back", "Back", show=False),
        Binding("space", "toggle", "Toggle", key_display="Space", show=True),
        Binding("t", "toggle_advance", "Toggle & Down", key_display="t", show=True),
        Binding("a", "select_all", "All", show=True),
        Binding("n", "select_none", "None", show=True),
        Binding("i", "select_invert", "Invert", show=True),
        Binding("d", "download", "Download", show=True),
        Binding("question_mark", "help", "Help", key_display="?", show=True),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, initial_query: str = "") -> None:
        super().__init__()
        self.initial_query = initial_query
        self.matches: list[dict[str, Any]] = []
        self.selected: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="panel"):
            yield Input(
                value=self.initial_query,
                placeholder=_("Search tvg-id / tvg-name…"),
                id="query",
            )
            yield Static(
                _("Found 0 matches · 0 selected"),
                id="summary-bar",
                markup=False,
            )
            yield DataTable(id="match-list", cursor_type="row", zebra_stripes=True)
            yield Static(_("Select an item to view details"), id="item-inspector", markup=False)
            yield Static("", id="status", markup=False)
            with Horizontal(classes="action-bar"):
                yield Button(_("Search"), variant="primary", id="btn-go")
                yield Button(_("All"), id="btn-all")
                yield Button(_("None"), id="btn-none")
                yield Button(_("Invert"), id="btn-invert")
                yield Button(_("Download selected"), variant="success", id="btn-dl")
                yield Button(_("Back"), id="btn-back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#match-list", DataTable)
        table.expand = True
        table.add_column("#", key="num")
        table.add_column("✓", key="check")
        table.add_column(_("Name"), key="name")
        table.add_column(_("Size"), key="size")
        table.add_column("URL", key="url")
        if self.initial_query:
            self._start_search_worker(self.initial_query)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._start_search_worker(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-go":
            q = self.query_one("#query", Input).value
            self._start_search_worker(q)
        elif bid == "btn-all":
            self.action_select_all()
            try:
                self.query_one("#match-list", DataTable).focus()
            except Exception:
                pass
        elif bid == "btn-none":
            self.action_select_none()
            try:
                self.query_one("#match-list", DataTable).focus()
            except Exception:
                pass
        elif bid == "btn-invert":
            self.action_select_invert()
            try:
                self.query_one("#match-list", DataTable).focus()
            except Exception:
                pass
        elif bid == "btn-dl":
            self.action_download()
        elif bid == "btn-back":
            self.action_back()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        idx = event.cursor_row
        if idx is not None and 0 <= idx < len(self.matches):
            self._toggle_row_index(idx)

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        idx = event.coordinate.row
        if idx is not None and 0 <= idx < len(self.matches):
            self._toggle_row_index(idx)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        idx = event.cursor_row
        self._update_inspector(idx)

    def _update_inspector(self, idx: int | None) -> None:
        try:
            inspector = self.query_one("#item-inspector", Static)
        except Exception:
            return
        if idx is None or not (0 <= idx < len(self.matches)):
            inspector.update(_("Select an item to view details"))
            return
        m = self.matches[idx]
        name = m.get("tvg-id") or m.get("tvg-name") or "unnamed"
        size = format_size(int(m.get("size") or 0)) if int(m.get("size") or 0) > 0 else _("Unknown")
        url = m.get("url") or "—"
        is_sel = idx in self.selected
        badge = "[✓ SELECTED]" if is_sel else "[  UNSELECTED]"
        text = f"Item #{idx + 1}: {name} ({size}) | {badge}\nURL: {url}"
        inspector.update(text)

    def _start_search_worker(self, query: str) -> None:
        try:
            status = self.query_one("#status", Static)
            status.update(_("Searching…"))
        except Exception:
            pass
        self.run_worker(self._async_search(query), exclusive=True)

    async def _async_search(self, query: str) -> None:
        m3u = Path(self.app.settings.m3u_path)
        try:
            status = self.query_one("#status", Static)
            table = self.query_one("#match-list", DataTable)
            table.clear()
        except Exception:
            return
        self.matches = []
        self.selected = set()

        if not m3u.is_file():
            status.update(_("M3U not found: {path}").format(path=m3u))
            self._update_summary()
            self._update_inspector(None)
            return

        def _do_parse() -> list[dict[str, Any]]:
            channels = parse_m3u(str(m3u))
            return find_matches(channels, query)

        matches = await asyncio.to_thread(_do_parse)
        self.matches = matches
        self.selected = set(range(len(self.matches)))

        for i, m in enumerate(self.matches):
            name = m.get("tvg-id") or m.get("tvg-name") or "?"
            size = format_size(int(m.get("size") or 0)) if int(m.get("size") or 0) > 0 else _("Unknown")
            url = m.get("url") or "—"
            table.add_row(str(i + 1), "[✓]", name, size, url, key=str(i))

        self._update_summary()
        self._update_inspector(0 if self.matches else None)
        status.update("")
        if self.matches:
            try:
                table.focus()
            except Exception:
                pass

        def _probe_sizes():
            for i in range(min(50, len(self.matches))):
                if not self.matches[i].get("size") and self.matches[i].get("url"):
                    try:
                        sz = get_file_size(self.matches[i]["url"])
                        if sz > 0:
                            self.matches[i]["size"] = sz
                    except Exception:
                        pass
            try:
                self.app.call_from_thread(self._refresh_checks)
            except Exception:
                pass

        if self.matches:
            self.run_worker(asyncio.to_thread(_probe_sizes), exclusive=False)

    def _update_summary(self) -> None:
        try:
            summary = self.query_one("#summary-bar", Static)
            status = self.query_one("#status", Static)
        except Exception:
            return
        total_selected_size = sum(
            int(self.matches[i].get("size") or 0)
            for i in self.selected
            if i < len(self.matches)
        )
        size_str = format_size(total_selected_size) if total_selected_size > 0 else _("Unknown total size")
        summary_text = (
            f"{_('Found {n} matches · {sel} selected').format(n=len(self.matches), sel=len(self.selected))}"
            f" ({size_str})"
        )
        summary.update(summary_text)
        status.update(
            _("Found {n} matches · {sel} selected").format(
                n=len(self.matches), sel=len(self.selected)
            )
        )

    def _refresh_checks(self) -> None:
        try:
            table = self.query_one("#match-list", DataTable)
        except Exception:
            return

        if table.row_count == len(self.matches):
            for i, m in enumerate(self.matches):
                mark = "[✓]" if i in self.selected else "[ ]"
                sz_val = int(m.get("size") or 0)
                size_str = format_size(sz_val) if sz_val > 0 else _("Unknown")
                try:
                    table.update_cell(str(i), "check", mark)
                    table.update_cell(str(i), "size", size_str)
                except Exception:
                    pass
        else:
            saved_row = table.cursor_row
            saved_scroll_y = getattr(table.scroll_offset, "y", 0)
            table.clear()
            for i, m in enumerate(self.matches):
                name = m.get("tvg-id") or m.get("tvg-name") or "?"
                size = format_size(int(m.get("size") or 0)) if int(m.get("size") or 0) > 0 else _("Unknown")
                url = m.get("url") or "—"
                mark = "[✓]" if i in self.selected else "[ ]"
                table.add_row(str(i + 1), mark, name, size, url, key=str(i))
            if saved_row is not None and 0 <= saved_row < len(self.matches):
                try:
                    table.move_cursor(row=saved_row)
                    table.scroll_to(y=saved_scroll_y, animate=False)
                except Exception:
                    pass

        self._update_summary()
        if table.cursor_row is not None:
            self._update_inspector(table.cursor_row)

    def _toggle_row_index(self, idx: int) -> None:
        table = self.query_one("#match-list", DataTable)
        if idx in self.selected:
            self.selected.discard(idx)
            mark = "[ ]"
        else:
            self.selected.add(idx)
            mark = "[✓]"
            if not self.matches[idx].get("size"):
                url = self.matches[idx].get("url", "")
                if url:
                    def _probe(target_idx=idx, target_url=url):
                        sz = get_file_size(target_url)
                        self.matches[target_idx]["size"] = sz
                        def _update_row_size():
                            try:
                                t = self.query_one("#match-list", DataTable)
                                size_str = format_size(sz) if sz > 0 else _("Unknown")
                                t.update_cell(str(target_idx), "size", size_str)
                                self._update_summary()
                                if t.cursor_row == target_idx:
                                    self._update_inspector(target_idx)
                            except Exception:
                                pass
                        self.app.call_from_thread(_update_row_size)
                    self.run_worker(asyncio.to_thread(_probe), exclusive=False)

        try:
            table.update_cell(str(idx), "check", mark)
        except Exception:
            self._refresh_checks()
        self._update_summary()
        self._update_inspector(idx)

    def action_toggle(self) -> None:
        table = self.query_one("#match-list", DataTable)
        if table.cursor_row is None or not self.matches:
            return
        self._toggle_row_index(table.cursor_row)

    def action_toggle_advance(self) -> None:
        table = self.query_one("#match-list", DataTable)
        if table.cursor_row is None or not self.matches:
            return
        idx = table.cursor_row
        self._toggle_row_index(idx)
        if idx + 1 < len(self.matches):
            table.move_cursor(row=idx + 1)

    def action_select_all(self) -> None:
        self.selected = set(range(len(self.matches)))
        self._refresh_checks()

    def action_select_none(self) -> None:
        self.selected = set()
        self._refresh_checks()

    def action_select_invert(self) -> None:
        self.selected = set(range(len(self.matches))) - self.selected
        self._refresh_checks()

    def action_download(self) -> None:
        if not self.selected:
            self.app.push_screen(ErrorModal(_("Select at least one item.")))
            return
        chosen = [self.matches[i] for i in sorted(self.selected)]
        total = sum(int(m.get("size") or 0) for m in chosen)

        async def _go() -> None:
            ok = await self.app.push_screen_wait(
                ConfirmModal(
                    _("Download {n} files ({size})?").format(
                        n=len(chosen), size=format_size(total) if total > 0 else _("Unknown total size")
                    )
                )
            )
            if not ok:
                return
            self.app.show_downloads_queue(chosen)

        self.app.run_worker(_go())

    def action_cursor_down(self) -> None:
        self.query_one("#match-list", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#match-list", DataTable).action_cursor_up()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal())

    def action_back(self) -> None:
        self.app.pop_screen()


class DownloadsScreen(Screen):
    """Download queue screen viewing live DownloadManager state."""

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", show=True),
        Binding("q", "back", "Back", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="panel"):
            with Vertical(classes="dl-card"):
                yield Static(_("Downloads"), id="dl-title")
                yield Static(_("Preparing…"), id="dl-status", markup=False)
                yield ProgressBar(total=100, show_eta=True, id="dl-overall")
                yield Static("", id="dl-overall-detail", markup=False)
                yield ProgressBar(total=100, show_eta=True, id="dl-current")
                yield Static("", id="dl-current-detail", markup=False)
            yield DataTable(id="dl-table", zebra_stripes=True)
            with Horizontal(classes="action-bar"):
                yield Button(_("Back"), id="btn-back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#dl-table", DataTable)
        table.expand = True
        table.add_column("#", key="num")
        table.add_column(_("File"), key="file")
        table.add_column(_("Size"), key="size")
        table.add_column(_("Progress"), key="progress")
        table.add_column(_("Rate"), key="rate")
        table.add_column(_("Status"), key="status")
        table.focus()
        
        self.app.download_manager.set_listener(self._on_manager_update)
        self._refresh_all()
        self.set_interval(0.2, self._refresh_all)

    def on_unmount(self) -> None:
        self.app.download_manager.set_listener(None)

    def _on_manager_update(self) -> None:
        try:
            self.app.call_from_thread(self._refresh_all)
        except Exception:
            pass

    def _refresh_all(self) -> None:
        try:
            table = self.query_one("#dl-table", DataTable)
            status = self.query_one("#dl-status", Static)
            overall = self.query_one("#dl-overall", ProgressBar)
            overall_detail = self.query_one("#dl-overall-detail", Static)
            cur = self.query_one("#dl-current", ProgressBar)
            cur_detail = self.query_one("#dl-current-detail", Static)
        except Exception:
            return

        mgr = self.app.download_manager
        if not mgr.states:
            status.update(_("No active download jobs. Search for channels to start downloads."))
            overall.update(progress=0)
            overall_detail.update("")
            cur.update(progress=0)
            cur_detail.update("")
            table.clear()
            return

        # Overall progress
        done_bytes, total_bytes, overall_pct = mgr.overall_progress()
        overall.update(total=100, progress=overall_pct)
        overall_detail.update(
            f"{format_size(done_bytes)} / {format_size(total_bytes)} · {overall_pct:5.1f}%"
        )

        # Active item
        active = mgr.active_job_state()
        if active:
            cur.update(total=100, progress=active.pct)
            cur_detail.update(
                _("{percent:.0f}% · {rate} · {eta}").format(
                    percent=active.pct, rate=active.rate, eta=active.eta
                )
            )
            status.update(_("Downloading {name}…").format(name=active.job.final_path.name))
        elif mgr.is_running:
            status.update(_("Preparing…"))
        else:
            status.update(_("All downloads completed under {path}").format(
                path=self.app.settings.resolved_output_dir()
            ))

        # Re-sync table rows
        if table.row_count != len(mgr.states):
            table.clear()
            for s in mgr.states:
                sz_str = format_size(s.total) if s.total > 0 else _("Unknown")
                table.add_row(
                    str(s.job.id + 1),
                    s.job.final_path.name,
                    sz_str,
                    f"{s.pct:5.1f}%",
                    s.rate,
                    s.status,
                    key=str(s.job.id),
                )
        else:
            for s in mgr.states:
                row_k = str(s.job.id)
                sz_str = format_size(s.total) if s.total > 0 else _("Unknown")
                try:
                    table.update_cell(row_k, "size", sz_str)
                    table.update_cell(row_k, "progress", f"{s.pct:5.1f}%")
                    table.update_cell(row_k, "rate", s.rate)
                    table.update_cell(row_k, "status", s.status)
                except Exception:
                    pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.action_back()

    def action_back(self) -> None:
        self.app.pop_screen()


class CleanupScreen(Screen):
    """Library cleanup screen."""

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", show=True),
        Binding("q", "back", "Back", show=False),
        Binding("enter", "run", "Plan", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="panel"):
            yield Static(_("Cleanup"), id="cu-title", classes="screen-title")
            yield Label(
                _("Library: {path}").format(
                    path=self.app.settings.resolved_output_dir()
                ),
                markup=False,
            )
            yield Static("", id="cu-status", markup=False)
            with Horizontal(classes="action-bar"):
                yield Button(_("Preview"), variant="primary", id="btn-preview")
                yield Button(_("Back"), id="btn-back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-preview":
            self.action_run()
        elif event.button.id == "btn-back":
            self.action_back()

    def action_run(self) -> None:
        root = self.app.settings.resolved_output_dir()
        plan = CleanupService().plan(root, policy=CleanupPolicy())
        lines = [
            f"[{i.kind}] {i.path.name} ({i.size} B) — {i.reason}" for i in plan.items
        ]

        async def _go() -> None:
            ok = await self.app.push_screen_wait(
                CleanupPreviewModal(lines, plan.total_bytes)
            )
            if not ok:
                return
            result = CleanupService().execute(plan, dry_run=False)
            self.query_one("#cu-status", Static).update(
                _("Removed {n} items.").format(n=result["removed"])
            )

        self.app.run_worker(_go())

    def action_back(self) -> None:
        self.app.pop_screen()


class SettingsScreen(Screen):
    """Application settings screen."""

    BINDINGS = [
        Binding("escape", "back", "Back", key_display="Esc", show=True),
        Binding("q", "back", "Back", show=False),
        Binding("L", "language", "Language", show=True),
        Binding("enter", "save", "Save", show=True),
    ]

    def compose(self) -> ComposeResult:
        s = self.app.settings
        yield Header()
        with Vertical(classes="panel"):
            yield Static(_("Settings"), id="set-title", classes="screen-title")
            with Vertical(classes="form-card"):
                yield Label(_("M3U path"), classes="form-label")
                yield Input(value=s.m3u_path, id="in-m3u", classes="form-input")
                yield Label(_("Output directory (empty = XDG library)"), classes="form-label")
                yield Input(value=s.output_dir, id="in-out", classes="form-input")
                yield Label(_("Threads"), classes="form-label")
                yield Input(value=str(s.threads), id="in-threads", classes="form-input")
                yield Label(_("Retries"), classes="form-label")
                yield Input(value=str(s.retries), id="in-retries", classes="form-input")
            with Horizontal(classes="action-bar"):
                yield Button(_("Save"), variant="primary", id="btn-save")
                yield Button(_("Language…"), id="btn-lang")
                yield Button(_("Back"), id="btn-back")
            yield Static("", id="set-status", markup=False)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-lang":
            self.action_language()
        elif event.button.id == "btn-back":
            self.action_back()

    def action_save(self) -> None:
        s = self.app.settings
        s.m3u_path = self.query_one("#in-m3u", Input).value.strip() or s.m3u_path
        s.output_dir = self.query_one("#in-out", Input).value.strip()
        try:
            s.threads = max(1, int(self.query_one("#in-threads", Input).value or "1"))
            s.retries = max(0, int(self.query_one("#in-retries", Input).value or "0"))
        except ValueError:
            self.app.push_screen(ErrorModal(_("Invalid threads/retries")))
            return
        path = save_settings(s)
        self.query_one("#set-status", Static).update(
            _("Saved {path}").format(path=path)
        )

    def action_language(self) -> None:
        async def _pick() -> None:
            code = await self.app.push_screen_wait(
                LanguageModal(available_languages(), get_language())
            )
            if code:
                self.app.apply_language(code)
                self.app.settings.language = code
                save_settings(self.app.settings)

        self.app.run_worker(_pick())

    def action_back(self) -> None:
        self.app.pop_screen()
