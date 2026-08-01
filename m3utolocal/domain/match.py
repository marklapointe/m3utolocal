"""Pure match / VOD filter helpers."""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

# Extensions treated as live / non-VOD even though they match the general pattern.
_DENY_EXTENSIONS = re.compile(r"\.(m3u8|m3u)(\?.*)?$", re.IGNORECASE)
_VOD_EXTENSION = re.compile(r"\.[a-zA-Z0-9]{2,4}(\?.*)?$")


def is_vod_url(url: str) -> bool:
    """Return True if URL looks like a static VOD file (not live/HLS playlist)."""
    if not url:
        return False
    if _DENY_EXTENSIONS.search(url):
        return False
    return bool(_VOD_EXTENSION.search(url))


def find_matches(
    channels: Iterable[Mapping[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Case-insensitive substring match on tvg-id / tvg-name; VOD URLs only."""
    q = (query or "").lower()
    matches: list[dict[str, Any]] = []
    for c in channels:
        tvg_id = str(c.get("tvg-id") or c.get("tvg_id") or "")
        tvg_name = str(c.get("tvg-name") or c.get("tvg_name") or "")
        url = str(c.get("url") or "")
        if q and q not in tvg_id.lower() and q not in tvg_name.lower():
            continue
        if not is_vod_url(url):
            continue
        matches.append(dict(c))
    return matches
