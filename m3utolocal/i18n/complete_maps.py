"""Complete per-language message maps (parity with English catalog).

Loaded from complete_maps.json generated for all supported languages.
Every language has the same key set as English MESSAGES + PLURALS forms.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from m3utolocal.i18n.catalog import MESSAGES, PLURALS

_JSON = Path(__file__).with_name("complete_maps.json")

# May remain identical to English (brand, units, shared loanwords)
IDENTITY_OK = frozenset({
    "m3utolocal",
    "ETA",
    "URL",
    "M3U: {path}",
    "{percent:.0f}% · {rate} · {eta}",
    # Same word in multiple languages (not a missing translation)
    "No",
})


@lru_cache(maxsize=1)
def load_complete_maps() -> dict[str, dict[str, str]]:
    data = json.loads(_JSON.read_text(encoding="utf-8"))
    return {str(k): {str(mk): str(mv) for mk, mv in v.items()} for k, v in data.items()}


def expected_keys() -> set[str]:
    keys = set(MESSAGES)
    for s, p in PLURALS:
        keys.add(s)
        keys.add(p)
    return keys


def map_for(code: str) -> dict[str, str]:
    maps = load_complete_maps()
    if code not in maps:
        raise KeyError(f"no complete map for language {code!r}")
    return dict(maps[code])
