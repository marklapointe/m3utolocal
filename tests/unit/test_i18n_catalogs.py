"""Verify gettext catalogs exist and load for every language."""

from pathlib import Path

import gettext

from m3utolocal.i18n import set_language, _
from m3utolocal.i18n.catalog import MESSAGES
from m3utolocal.i18n.languages import available_languages

LOCALE_DIR = Path(__file__).resolve().parents[2] / "m3utolocal" / "i18n" / "locales"


def test_every_language_has_mo():
    for li in available_languages():
        mo = LOCALE_DIR / li.code / "LC_MESSAGES" / "m3utolocal.mo"
        assert mo.is_file(), f"missing {mo}"


def test_spanish_translates_confirm():
    set_language("es")
    assert _("Confirm") == "Confirmar"
    set_language("en")
    assert _("Confirm") == "Confirm"


def test_catalog_covers_ui_strings():
    # Core UI must be in source catalog
    for key in ("Downloads", "Overall progress", "Cleanup", "Settings"):
        assert key in MESSAGES


def test_all_catalogs_load_via_gettext():
    for li in available_languages():
        t = gettext.translation(
            "m3utolocal", localedir=str(LOCALE_DIR), languages=[li.code], fallback=True
        )
        assert t.gettext("Confirm")  # non-empty
