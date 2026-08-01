"""Verify gettext catalogs exist and load for every language."""

from pathlib import Path
import re

import gettext

from m3utolocal.i18n import set_language, _
from m3utolocal.i18n.catalog import MESSAGES
from m3utolocal.i18n.complete_maps import (
    IDENTITY_OK,
    expected_keys,
    load_complete_maps,
)
from m3utolocal.i18n.languages import available_languages

LOCALE_DIR = Path(__file__).resolve().parents[2] / "m3utolocal" / "i18n" / "locales"


def _po_msgids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    ids = re.findall(r'^msgid "((?:\\.|[^"\\])*)"', text, re.M)
    out = set()
    for i in ids:
        if not i:
            continue
        out.add(i.encode("utf-8").decode("unicode_escape") if "\\" in i else i)
    return out


def test_every_language_has_mo():
    for li in available_languages():
        mo = LOCALE_DIR / li.code / "LC_MESSAGES" / "m3utolocal.mo"
        assert mo.is_file(), f"missing {mo}"


def test_english_catalog_count():
    assert len(MESSAGES) == 106


def test_all_languages_match_english_key_count():
    """Every language catalog must contain the same msgid set as English."""
    en_po = LOCALE_DIR / "en" / "LC_MESSAGES" / "m3utolocal.po"
    en_ids = _po_msgids(en_po)
    assert len(en_ids) >= len(MESSAGES)
    for li in available_languages():
        po = LOCALE_DIR / li.code / "LC_MESSAGES" / "m3utolocal.po"
        ids = _po_msgids(po)
        assert len(ids) == len(en_ids), (
            f"{li.code}: {len(ids)} msgids != en {len(en_ids)}"
        )
        missing = set(MESSAGES) - ids
        assert not missing, f"{li.code} missing MESSAGES keys: {sorted(missing)[:5]}"


def test_complete_maps_cover_every_language():
    maps = load_complete_maps()
    exp = expected_keys()
    for li in available_languages():
        assert li.code in maps
        assert set(maps[li.code]) == exp


def test_no_untranslated_strings_outside_identity():
    """Non-English catalogs must not leave UI strings as English (except identity)."""
    for li in available_languages():
        if li.code == "en":
            continue
        t = gettext.translation(
            "m3utolocal", localedir=str(LOCALE_DIR), languages=[li.code], fallback=True
        )
        still = []
        for key, en in MESSAGES.items():
            if key in IDENTITY_OK:
                continue
            if t.gettext(key) == en:
                still.append(key)
        assert not still, f"{li.code} still English: {still[:8]}"


def test_spanish_translates_confirm():
    set_language("es")
    assert _("Confirm") == "Confirmar"
    set_language("en")
    assert _("Confirm") == "Confirm"


def test_german_home_dashboard_labels():
    """Home screen titles/stats must not fall back to English in de."""
    set_language("de")
    assert _("Library Output") == "Bibliotheksausgabe"
    assert _("M3U Playlist") == "M3U-Playlist"
    assert _("M3U Playlist Search & Media Downloader") == (
        "M3U-Playlist-Suche und Medien-Downloader"
    )
    assert _("Quick Navigation") == "Schnellnavigation"
    assert _("Downloads Queue") == "Download-Warteschlange"
    assert _("Settings") == "Einstellungen"
    assert _("Threads: {threads} · Retries: {retries}").format(
        threads=1, retries=1
    ) == "Threads: 1 · Wiederholungen: 1"
    assert _("M3U: {path}").format(path="/tmp/x.m3u") == "M3U: /tmp/x.m3u"
    # language code must not be part of the M3U path label
    assert "lang" not in _("M3U: {path}")
    set_language("en")


def test_arabic_home_dashboard_not_english():
    set_language("ar")
    assert _("Library Output") != "Library Output"
    assert _("Quick Navigation") != "Quick Navigation"
    assert _("Settings") != "Settings"
    set_language("en")


def test_catalog_covers_ui_strings():
    # Core UI must be in source catalog
    for key in (
        "Downloads",
        "Overall progress",
        "Cleanup",
        "Settings",
        "Library Output",
        "M3U Playlist",
        "M3U: {path}",
        "Threads: {threads} · Retries: {retries}",
    ):
        assert key in MESSAGES
    assert "M3U: {path} · lang: {lang}" not in MESSAGES


def test_all_catalogs_load_via_gettext():
    for li in available_languages():
        t = gettext.translation(
            "m3utolocal", localedir=str(LOCALE_DIR), languages=[li.code], fallback=True
        )
        assert t.gettext("Confirm")  # non-empty
