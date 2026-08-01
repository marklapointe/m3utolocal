"""Unit tests for Right-to-Left (RTL) language handling and i18n coverage."""

from __future__ import annotations

import pytest

from m3utolocal.i18n import is_rtl, format_bidi, set_language, get_language, _
from m3utolocal.i18n.catalog import MESSAGES
from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp


def test_is_rtl_detection():
    assert is_rtl("ar") is True
    assert is_rtl("he") is True
    assert is_rtl("ur") is True
    assert is_rtl("en") is False
    assert is_rtl("es") is False


def test_format_bidi_isolates():
    set_language("ar")
    formatted = format_bidi("Test String")
    assert formatted.startswith("\u2067")
    assert formatted.endswith("\u2069")

    set_language("en")
    assert format_bidi("Test String") == "Test String"


def test_rtl_translation_wrapped():
    set_language("ar")
    translated = _("Confirm")
    assert "\u2067" in translated
    set_language("en")


def test_all_catalog_messages_non_empty():
    for msgid, msgstr in MESSAGES.items():
        assert msgid, "Empty msgid in catalog"
        assert msgstr, f"Empty msgstr for msgid '{msgid}'"


@pytest.mark.asyncio
async def test_app_applies_rtl_class():
    textual = pytest.importorskip("textual")
    pytest.importorskip("pytest_asyncio")

    app = M3UToLocalApp(Settings(language="ar"))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "rtl" in app.classes
        app.apply_language("en")
        await pilot.pause()
        assert "rtl" not in app.classes
