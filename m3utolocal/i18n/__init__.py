"""Locale detection and gettext-backed translation (English & RTL support)."""

from __future__ import annotations

import gettext
import os
from pathlib import Path

from m3utolocal.i18n.languages import LanguageInfo, available_languages, language_codes

_DOMAIN = "m3utolocal"
_locale_dir = Path(__file__).resolve().parent / "locales"
_current_lang = "en"
_translation: gettext.NullTranslations = gettext.NullTranslations()

RTL_LANGUAGES: set[str] = {"ar", "he", "fa", "ur", "ps", "yi", "sd"}


def _normalize_lang(code: str | None) -> str:
    if not code:
        return "en"
    code = code.replace("-", "_").strip()
    if not code or code.lower() in ("c", "posix"):
        return "en"
    base = code.split(".")[0]
    codes = language_codes()
    if base in codes:
        return base
    short = base.split("_")[0]
    if short in codes:
        return short
    if short.lower() in codes:
        return short.lower()
    return "en"


def is_rtl(code: str | None = None) -> bool:
    """Return True if language code (or current language) is Right-to-Left."""
    lang = _normalize_lang(code) if code else _current_lang
    return lang in RTL_LANGUAGES


def format_bidi(text: str, code: str | None = None) -> str:
    """Format string for bidirectional/RTL rendering in terminal UIs."""
    if not text:
        return text
    if is_rtl(code):
        # Use Unicode RLI (Right-to-Left Isolate U+2067) and PDI (Pop Directional Isolate U+2069)
        return f"\u2067{text}\u2069"
    return text


def detect_language(
    *,
    cli_lang: str | None = None,
    config_lang: str | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    """Precedence: CLI > config > LC_ALL/LC_MESSAGES/LANG > en."""
    if cli_lang:
        return _normalize_lang(cli_lang)
    if config_lang:
        return _normalize_lang(config_lang)
    env = environ if environ is not None else os.environ
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = env.get(key)
        if val:
            return _normalize_lang(val)
    return "en"


def set_language(code: str) -> str:
    """Install translation for *code*; returns normalized code actually used."""
    global _current_lang, _translation
    lang = _normalize_lang(code)
    _current_lang = lang
    try:
        _translation = gettext.translation(
            _DOMAIN,
            localedir=str(_locale_dir),
            languages=[lang, "en"],
            fallback=True,
        )
    except Exception:
        _translation = gettext.NullTranslations()
    return lang


def get_language() -> str:
    return _current_lang


def _(message: str) -> str:
    translated = _translation.gettext(message)
    if is_rtl():
        return format_bidi(translated)
    return translated


def ngettext(singular: str, plural: str, n: int) -> str:
    translated = _translation.ngettext(singular, plural, n)
    if is_rtl():
        return format_bidi(translated)
    return translated


class LocaleService:
    def detect(
        self,
        *,
        cli_lang: str | None = None,
        config_lang: str | None = None,
        environ: dict[str, str] | None = None,
    ) -> str:
        return detect_language(
            cli_lang=cli_lang, config_lang=config_lang, environ=environ
        )

    def set_language(self, code: str) -> str:
        return set_language(code)

    def available_languages(self) -> list[LanguageInfo]:
        return available_languages()

    def translate(self, msgid: str) -> str:
        return _(msgid)

    def ntranslate(self, singular: str, plural: str, n: int) -> str:
        return ngettext(singular, plural, n)

    def is_rtl(self, code: str | None = None) -> bool:
        return is_rtl(code)
