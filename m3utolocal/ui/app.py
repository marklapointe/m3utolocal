"""Textual application entry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App

from m3utolocal.i18n import LocaleService, set_language, is_rtl
from m3utolocal.services.config import Settings, load_settings, save_settings
from m3utolocal.services.download_manager import DownloadManager
from m3utolocal.ui.screens import HomeScreen, SearchScreen


class M3UToLocalApp(App[None]):
    """Full-screen m3utolocal TUI."""

    CSS_PATH = Path(__file__).parent / "css" / "app.tcss"
    TITLE = "m3utolocal"
    BINDINGS = []

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        initial_query: str | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings or load_settings()
        self.initial_query = initial_query or ""
        self.locale = LocaleService()
        self.download_manager = DownloadManager()

    def _apply_rtl_class(self, lang: str) -> None:
        if is_rtl(lang):
            self.add_class("rtl")
        else:
            self.remove_class("rtl")

    def on_mount(self) -> None:
        lang = self.locale.detect(config_lang=self.settings.language)
        set_language(lang)
        self._apply_rtl_class(lang)
        if self.initial_query:
            self.push_screen(SearchScreen(self.initial_query))
        else:
            self.push_screen(HomeScreen())

    def show_downloads_queue(self, matches: list[dict[str, Any]] | None = None) -> None:
        from m3utolocal.ui.screens import DownloadsScreen

        if matches:
            self.download_manager.enqueue(
                matches, self.settings.resolved_output_dir(), self.settings.threads
            )
            self.run_worker(
                self.download_manager.start_downloads(self.settings.threads),
                exclusive=False,
            )
        self.push_screen(DownloadsScreen())

    def apply_language(self, code: str) -> None:
        set_language(code)
        self.settings.language = code
        self._apply_rtl_class(code)
        try:
            save_settings(self.settings)
        except OSError:
            pass
        # Keep header clean — language is visible in Settings / Language UI only.
        self.sub_title = ""


def run_tui(
    settings: Settings | None = None,
    *,
    initial_query: str | None = None,
) -> None:
    M3UToLocalApp(settings, initial_query=initial_query).run()
