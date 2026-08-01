"""Supported languages: English first, then native-name sort."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    native_name: str
    english_name: str


# Deduplicated CloudBSD-oriented list. English first; others by native name.
_RAW: list[tuple[str, str, str]] = [
    ("en", "English", "English"),
    ("ar", "العربية", "Arabic"),
    ("bg", "Български", "Bulgarian"),
    ("ca", "Català", "Catalan"),
    ("cs", "Čeština", "Czech"),
    ("de", "Deutsch", "German"),
    ("el", "Ελληνικά", "Greek"),
    ("eo", "Esperanto", "Esperanto"),
    ("es", "Español", "Spanish"),
    ("fi", "Suomi", "Finnish"),
    ("fr", "Français", "French"),
    ("he", "עברית", "Hebrew"),
    ("hi", "हिन्दी", "Hindi"),
    ("hr", "Hrvatski", "Croatian"),
    ("hu", "Magyar", "Hungarian"),
    ("id", "Bahasa Indonesia", "Indonesian"),
    ("it", "Italiano", "Italian"),
    ("ja", "日本語", "Japanese"),
    ("ko", "한국어", "Korean"),
    ("lt", "Lietuvių", "Lithuanian"),
    ("lv", "Latviešu", "Latvian"),
    ("nb", "Norsk", "Norwegian"),
    ("nl", "Nederlands", "Dutch"),
    ("pa", "ਪੰਜਾਬੀ", "Punjabi"),
    ("pl", "Polski", "Polish"),
    ("pt", "Português", "Portuguese"),
    ("pt_BR", "Português (Brasil)", "Portuguese (Brazil)"),
    ("ro", "Română", "Romanian"),
    ("ru", "Русский", "Russian"),
    ("sk", "Slovenčina", "Slovak"),
    ("sl", "Slovenščina", "Slovenian"),
    ("sr", "Српски", "Serbian"),
    ("sv", "Svenska", "Swedish"),
    ("sw", "Kiswahili", "Swahili"),
    ("tlh", "tlhIngan Hol", "Klingon"),
    ("tr", "Türkçe", "Turkish"),
    ("uk", "Українська", "Ukrainian"),
    ("ur", "اردو", "Urdu"),
    ("yo", "Yorùbá", "Yoruba"),
    ("zh_CN", "中文", "Chinese"),
]


def available_languages() -> list[LanguageInfo]:
    english = LanguageInfo(*_RAW[0])
    rest = sorted(
        (LanguageInfo(c, n, e) for c, n, e in _RAW[1:]),
        key=lambda li: li.native_name.casefold(),
    )
    return [english, *rest]


def language_codes() -> set[str]:
    return {c for c, _, _ in _RAW}
