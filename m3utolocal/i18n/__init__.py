"""Locale detection and gettext-backed translation (English & RTL support)."""

from __future__ import annotations

import gettext
import os
import unicodedata
from pathlib import Path

from m3utolocal.i18n.languages import LanguageInfo, available_languages, language_codes

_DOMAIN = "m3utolocal"
_locale_dir = Path(__file__).resolve().parent / "locales"
_current_lang = "en"
_translation: gettext.NullTranslations = gettext.NullTranslations()

RTL_LANGUAGES: set[str] = {"ar", "he", "fa", "ur", "ps", "yi", "sd"}

# Unicode bidi isolates — applied per *run*, never as one wrap for the whole line.
_LRI = "\u2066"  # Left-to-Right Isolate
_RLI = "\u2067"  # Right-to-Left Isolate
_FSI = "\u2068"  # First Strong Isolate
_PDI = "\u2069"  # Pop Directional Isolate
_RLE = "\u202b"  # Right-to-Left Embedding (legacy; strip if present)
_LRE = "\u202a"
_PDF = "\u202c"
_RLO = "\u202e"
_LRO = "\u202d"

# Strip any previous directional formatting before re-isolating.
_BIDI_CONTROLS = frozenset(
    {
        _LRI,
        _RLI,
        _FSI,
        _PDI,
        _RLE,
        _LRE,
        _PDF,
        _RLO,
        _LRO,
        "\u200e",  # LRM
        "\u200f",  # RLM
        "\u061c",  # ALM
    }
)


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


# Path/URL glue counted as LTR so ``/home/user`` is one LRI box.
_PATH_GLUE = frozenset("/\\._-~@+?=&#%")


def _strip_bidi_controls(text: str) -> str:
    return "".join(ch for ch in text if ch not in _BIDI_CONTROLS)


def _bidi_class(ch: str) -> str:
    """Map character to coarse run class: 'R', 'L', or 'N' (neutral)."""
    # Path/URL glue must be LTR so ``/home/user`` is one LRI box, not
    # ``/`` + ``home`` + ``/`` + ``user`` with bare slashes between.
    if ch in _PATH_GLUE:
        return "L"
    b = unicodedata.bidirectional(ch)
    if b in ("R", "AL"):
        return "R"
    if b == "NSM":
        # Marks attach to previous strong; caller handles with context.
        return "M"
    if b in ("L", "EN", "AN", "LRE", "LRO"):
        # Digits (EN/AN) behave as LTR for paths/sizes in this UI.
        return "L"
    return "N"


def _segment_bidi_runs(text: str) -> list[tuple[str, str]]:
    """Split *text* into maximal (class, substring) runs: R / L / N.

    Marks attach to the preceding strong run (or to following if at start).
    Neutrals stay as their own runs so they are never absorbed across an
    R|L boundary (that was reordering colons/paths). Path separators like
    ``/`` are later reclassified as L when adjacent to LTR so
    ``/home/user`` stays one LRI box.
    """
    if not text:
        return []
    runs: list[tuple[str, str]] = []
    buf: list[str] = []
    cur: str | None = None

    def flush() -> None:
        nonlocal buf, cur
        if buf and cur is not None:
            runs.append((cur, "".join(buf)))
        buf = []
        cur = None

    for ch in text:
        cls = _bidi_class(ch)
        if cls == "M":
            # Combining mark: stick to current strong run if any.
            if cur in ("R", "L"):
                buf.append(ch)
            elif runs and runs[-1][0] in ("R", "L"):
                prev_c, prev_s = runs[-1]
                runs[-1] = (prev_c, prev_s + ch)
            else:
                # Orphan mark — treat as neutral
                if cur != "N":
                    flush()
                    cur = "N"
                buf.append(ch)
            continue
        if cur is None:
            cur = cls
            buf.append(ch)
            continue
        if cls == cur:
            buf.append(ch)
            continue
        flush()
        cur = cls
        buf.append(ch)
    flush()

    # Reclassify path-glue neutrals (/, ., _, …) as L when next to LTR.
    glued: list[tuple[str, str]] = []
    for i, (cls, s) in enumerate(runs):
        if cls == "N" and s and all(ch in _PATH_GLUE for ch in s):
            prev_c = glued[-1][0] if glued else None
            next_c = runs[i + 1][0] if i + 1 < len(runs) else None
            if prev_c == "L" or next_c == "L":
                cls = "L"
        if glued and glued[-1][0] == cls:
            glued[-1] = (cls, glued[-1][1] + s)
        else:
            glued.append((cls, s))
    return glued


def format_bidi(text: str, code: str | None = None) -> str:
    """Hard-isolate bidi runs for terminal/Textual RTL UI.

    Never wraps the whole line in one RLI…PDI. Instead:

    * each strong **RTL** run → ``RLI … PDI``
    * each strong **LTR** run (Latin, paths, digits) → ``LRI … PDI``
    * neutrals (spaces, ``:``, ``·``, punctuation) stay *outside* isolates
      so they cannot pull a path into an RTL embedding

    Pure-LTR strings in an RTL UI language still get LRI isolation so a
    surrounding RTL terminal context cannot reorder them.
    """
    if not text or not is_rtl(code):
        return text

    text = _strip_bidi_controls(text)
    if not text:
        return text

    runs = _segment_bidi_runs(text)
    has_rtl = any(c == "R" for c, _ in runs)
    has_ltr = any(c == "L" for c, _ in runs)

    # Pure LTR while UI is RTL: isolate the whole string as LTR.
    if has_ltr and not has_rtl:
        return f"{_LRI}{text}{_PDI}"

    # Pure RTL: hard-isolate each RTL run; leave bare neutrals outside.
    if has_rtl and not has_ltr:
        out: list[str] = []
        for cls, s in runs:
            if cls == "R":
                out.append(f"{_RLI}{s}{_PDI}")
            else:
                out.append(s)
        return "".join(out)

    # Mixed: isolate every strong run hard; neutrals stay bare between them.
    out = []
    for cls, s in runs:
        if cls == "R":
            out.append(f"{_RLI}{s}{_PDI}")
        elif cls == "L":
            out.append(f"{_LRI}{s}{_PDI}")
        else:
            out.append(s)
    return "".join(out)


def format_bidi_template(template: str, code: str | None = None, **kwargs: object) -> str:
    """Translate-friendly: ``format`` first, then hard-isolate the result.

    Prefer this over ``format_bidi(template).format(...)`` when placeholders
    expand to paths/numbers — isolation must see the final string.
    """
    filled = template.format(**kwargs)
    return format_bidi(filled, code=code)


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


class BidiString(str):
    """Translated string with deferred hard bidi isolation.

    * Display (no placeholders): content is already ``format_bidi``'d.
    * ``.format()`` / ``%``: strip prior isolates, fill placeholders, then
      re-isolate the *final* text so ``{path}`` is not split into
      ``{\\u2066path\\u2069}`` (which breaks ``str.format``).
    """

    def format(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
        raw = _strip_bidi_controls(str.__str__(self))
        return format_bidi(raw.format(*args, **kwargs))

    def __mod__(self, other: object) -> str:  # type: ignore[override]
        raw = _strip_bidi_controls(str.__str__(self))
        return format_bidi(raw % other)


def _(message: str) -> str:
    translated = _translation.gettext(message)
    if not is_rtl():
        return translated
    # Isolate now for display; .format() strips + re-isolates after fill.
    return BidiString(format_bidi(translated))


def ngettext(singular: str, plural: str, n: int) -> str:
    translated = _translation.ngettext(singular, plural, n)
    if not is_rtl():
        return translated
    return BidiString(format_bidi(translated))


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
