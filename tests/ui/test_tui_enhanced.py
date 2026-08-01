"""Enhanced TUI interactive screen and modal tests."""

from __future__ import annotations

from pathlib import Path
import pytest

textual = pytest.importorskip("textual")
pytest.importorskip("pytest_asyncio")

from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp
from m3utolocal.ui.modals import ErrorModal, CleanupPreviewModal
from m3utolocal.ui.screens import SearchScreen, SettingsScreen
from tui import tui_select


@pytest.mark.asyncio
async def test_tui_navigation_flow(tmp_path: Path):
    m3u_file = tmp_path / "test.m3u"
    m3u_file.write_text(
        '#EXTINF:-1 tvg-id="Movie 1" tvg-name="Movie 1",Movie 1\nhttp://example.com/movie1.mp4\n',
        encoding="utf-8",
    )

    settings = Settings(m3u_path=str(m3u_file), output_dir=str(tmp_path / "out"))
    app = M3UToLocalApp(settings)

    async with app.run_test() as pilot:
        await pilot.pause()
        # Home screen loaded
        assert "HomeScreen" in str(type(app.screen))

        # Push SearchScreen
        await pilot.press("slash")
        await pilot.pause()
        assert "SearchScreen" in str(type(app.screen))

        # Perform search query
        search_screen = app.screen
        assert isinstance(search_screen, SearchScreen)
        search_screen._start_search_worker("Movie 1")
        await pilot.pause()

        # Check search items found and selected
        assert len(search_screen.matches) == 1
        assert len(search_screen.selected) == 1

        # Test selection toggles
        search_screen.action_select_none()
        assert len(search_screen.selected) == 0

        # Double-click / RowSelected simulation
        search_screen._toggle_row_index(0)
        assert 0 in search_screen.selected

        search_screen.action_select_all()
        assert len(search_screen.selected) == 1

        search_screen.action_select_invert()
        assert len(search_screen.selected) == 0

        # Press back
        await pilot.press("escape")
        await pilot.pause()
        assert "HomeScreen" in str(type(app.screen))


@pytest.mark.asyncio
async def test_settings_screen_save(tmp_path: Path):
    settings = Settings(m3u_path=str(tmp_path / "chan.m3u"), output_dir=str(tmp_path / "out"))
    app = M3UToLocalApp(settings)

    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(SettingsScreen())
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, SettingsScreen)
        screen.action_save()
        await pilot.pause()

        # Verify status widget exists
        status_widget = screen.query_one("#set-status")
        assert status_widget is not None


@pytest.mark.asyncio
async def test_modals_interaction(tmp_path: Path):
    app = M3UToLocalApp(Settings())
    async with app.run_test() as pilot:
        await pilot.pause()

        # Error Modal
        app.push_screen(ErrorModal("Sample Error"))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        # Cleanup Modal
        app.push_screen(CleanupPreviewModal(["[part] file.part (100 B)"], 100))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()


def test_tui_select_fallback():
    matches = [
        {"tvg-id": "Ch1", "url": "http://ex.com/1", "size": 1024},
        {"tvg-id": "Ch2", "url": "http://ex.com/2", "size": 2048},
    ]

    class FakeStdScr:
        def getmaxyx(self):
            return 24, 80

        def erase(self):
            pass

        def refresh(self):
            pass

        def addstr(self, *args, **kwargs):
            pass

        def attron(self, *args):
            pass

        def attroff(self, *args):
            pass

        def getch(self):
            return 10  # Enter key

    import curses
    old_wrapper = curses.wrapper
    old_has_colors = getattr(curses, "has_colors", None)
    try:
        curses.wrapper = lambda fn: fn(FakeStdScr())
        curses.has_colors = lambda: False
        result = tui_select(matches)
        assert result == [0, 1]
    finally:
        curses.wrapper = old_wrapper
        if old_has_colors:
            curses.has_colors = old_has_colors
