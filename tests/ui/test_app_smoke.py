"""Textual app smoke tests (Pilot)."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")

pytest.importorskip("pytest_asyncio")

from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp
from m3utolocal.ui.modals import ConfirmModal, HelpModal


@pytest.mark.asyncio
async def test_app_opens_home():
    app = M3UToLocalApp(Settings(m3u_path="chans.m3u", language="en"))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen is not None


@pytest.mark.asyncio
async def test_help_modal():
    app = M3UToLocalApp(Settings())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(HelpModal())
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_confirm_modal_dismiss():
    app = M3UToLocalApp(Settings())
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(ConfirmModal("Go?"))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
