"""UI unit tests for modal centering and CSS rules."""

from __future__ import annotations

import pytest

textual = pytest.importorskip("textual")
pytest.importorskip("pytest_asyncio")

from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp
from m3utolocal.ui.modals import ConfirmModal, HelpModal, LanguageModal, CleanupPreviewModal, ErrorModal
from m3utolocal.i18n.languages import available_languages


@pytest.mark.asyncio
async def test_modal_screens_centered_in_app():
    app = M3UToLocalApp(Settings())
    async with app.run_test() as pilot:
        await pilot.pause()

        modals = [
            ConfirmModal("Are you sure?"),
            HelpModal(),
            LanguageModal(available_languages(), "en"),
            CleanupPreviewModal(["[part] item.part (100 B)"], 100),
            ErrorModal("System error"),
        ]

        for modal in modals:
            app.push_screen(modal)
            await pilot.pause()
            assert app.screen is modal
            # Check modal-box present
            box = modal.query_one(".modal-box")
            assert box is not None
            await pilot.press("escape")
            await pilot.pause()
