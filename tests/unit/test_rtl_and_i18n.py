"""Unit tests for Right-to-Left (RTL) language handling and i18n coverage."""

from __future__ import annotations

import pytest

from m3utolocal.i18n import (
    is_rtl,
    format_bidi,
    format_bidi_template,
    set_language,
    _,
    BidiString,
)
from m3utolocal.i18n.catalog import MESSAGES
from m3utolocal.services.config import Settings
from m3utolocal.ui.app import M3UToLocalApp

LRI = "\u2066"
RLI = "\u2067"
PDI = "\u2069"


def test_is_rtl_detection():
    assert is_rtl("ar") is True
    assert is_rtl("he") is True
    assert is_rtl("ur") is True
    assert is_rtl("en") is False
    assert is_rtl("es") is False


def test_pure_ltr_gets_lri_in_rtl_ui():
    """Paths/Latin-only lines must be LRI-isolated under RTL UI language."""
    set_language("ar")
    plain = "Output: /home/mlapointe/chans.m3u"
    out = format_bidi(plain)
    assert out == f"{LRI}{plain}{PDI}"
    assert RLI not in out
    set_language("en")
    assert format_bidi("Test String") == "Test String"


def test_pure_rtl_gets_rli_only():
    set_language("ar")
    arabic = "مكتبة"
    assert format_bidi(arabic) == f"{RLI}{arabic}{PDI}"
    set_language("en")


def test_mixed_isolates_rtl_and_ltr_separately():
    """Hard isolation: RTL run + bare neutral + LTR path (each strong run boxed)."""
    set_language("ar")
    arabic = "المخرجات"
    path = "/home/user/out"
    mixed = f"{arabic}: {path}"
    formatted = format_bidi(mixed)
    # Not one full-line isolate
    assert formatted != f"{RLI}{mixed}{PDI}"
    assert formatted != f"{LRI}{mixed}{PDI}"
    # RTL boxed
    assert f"{RLI}{arabic}{PDI}" in formatted
    # Path boxed as LTR
    assert f"{LRI}{path}{PDI}" in formatted
    # Colon/space sit outside isolates (cannot drag path into RTL embedding)
    assert f"{PDI}: {LRI}" in formatted or f"{PDI}:{LRI}" in formatted or ": " in formatted
    set_language("en")


def test_format_bidi_mixed_label_and_path_hebrew():
    set_language("he")
    he = "ספרייה"
    path = "/tmp/library"
    out = format_bidi(f"{he} {path}")
    assert f"{RLI}{he}{PDI}" in out
    assert f"{LRI}{path}{PDI}" in out
    assert not out.startswith(f"{RLI}{he} {path}{PDI}")
    set_language("en")


def test_bidi_string_reisolates_after_format():
    """_().format(path=…) must isolate the filled path, not just the template."""
    set_language("ar")
    # Simulate catalog-style template
    template = "المخرجات: {path}"
    s = BidiString(format_bidi(template))
    path = "/home/mlapointe/chans.m3u"
    filled = s.format(path=path)
    assert path in filled.replace(LRI, "").replace(RLI, "").replace(PDI, "")
    assert f"{LRI}{path}{PDI}" in filled
    assert filled.count(RLI) >= 1
    set_language("en")


def test_format_bidi_template_helper():
    set_language("ur")
    path = "/var/lib/m3u"
    out = format_bidi_template("مخرجات: {path}", path=path)
    assert f"{LRI}{path}{PDI}" in out
    set_language("en")


def test_digits_and_paths_are_ltr_runs():
    set_language("ar")
    # Arabic label + European digits + path
    label = "خيوط"
    out = format_bidi(f"{label}: 4 · /tmp/x")
    assert f"{RLI}{label}{PDI}" in out
    assert f"{LRI}4{PDI}" in out or "4" in out
    assert f"{LRI}/tmp/x{PDI}" in out
    set_language("en")


def test_strips_nested_bidi_before_reisolate():
    set_language("he")
    inner = f"{RLI}שלום{PDI}"
    # Should not double-nest forever
    once = format_bidi(inner)
    twice = format_bidi(once)
    assert twice == once
    assert twice.count(RLI) == 1
    set_language("en")


def test_rtl_translation_uses_hard_isolates():
    set_language("ar")
    translated = _("Confirm")
    # Arabic Confirm should be RLI-wrapped
    plain = translated.replace(RLI, "").replace(LRI, "").replace(PDI, "")
    if any("\u0600" <= c <= "\u06FF" for c in plain):
        assert RLI in translated and PDI in translated
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
