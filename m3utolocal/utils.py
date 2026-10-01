from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterator

import requests

from m3utolocal.domain.models import Channel


def format_size(size_bytes):
    if size_bytes is None or size_bytes <= 0:
        return "Unknown"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    units = ("KB", "MB", "GB", "TB", "PB")
    size = size_bytes / 1024
    unit_idx = 0
    
    while size >= 1024 and unit_idx < len(units) - 1:
        size /= 1024
        unit_idx += 1
        
    return f"{size:.2f} {units[unit_idx]}"

def get_file_size(url):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) VLC/3.0.18"}
    try:
        response = requests.head(url, allow_redirects=True, headers=headers, timeout=5)
        if response.status_code < 400:
            size = int(response.headers.get('content-length', 0) or 0)
            if size > 0:
                return size
            cr = response.headers.get('content-range', '')
            if '/' in cr:
                try:
                    return int(cr.split('/')[-1])
                except ValueError:
                    pass
        
        with requests.get(url, headers=headers, stream=True, timeout=5) as r:
            if r.status_code < 400:
                size = int(r.headers.get('content-length', 0) or 0)
                if size > 0:
                    return size
                cr = r.headers.get('content-range', '')
                if '/' in cr:
                    try:
                        return int(cr.split('/')[-1])
                    except ValueError:
                        pass
    except Exception:
        pass
    return 0

def iter_m3u(file_path: str | Path) -> Iterator[Channel]:
    """Yield Channel entities lazily from an M3U playlist."""
    path = Path(file_path)
    if not path.is_file():
        return

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        tvg_id = ""
        tvg_name = ""
        for line in f:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                id_m = re.search(r'tvg-id="([^"]*)"', line)
                name_m = re.search(r'tvg-name="([^"]*)"', line)
                tvg_id = id_m.group(1) if id_m else ""
                if name_m:
                    tvg_name = name_m.group(1)
                else:
                    parts = line.split(",")
                    tvg_name = parts[-1] if len(parts) > 1 else ""
            elif line and not line.startswith("#"):
                if tvg_id or tvg_name:
                    yield Channel(tvg_id=tvg_id, tvg_name=tvg_name, url=line)
                tvg_id = ""
                tvg_name = ""


def parse_m3u(file_path: str | Path) -> list[Channel]:
    """Parse an M3U into a list of Channel entities.

    Prints an error and returns ``[]`` when the file is missing (legacy contract).
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return []
    return list(iter_m3u(file_path))

def sanitize_filename(filename, max_length=200):
    """Sanitize a filename for cross-platform safety.

    Removes path separators and reserved characters. Empty results become
    ``"unnamed"``. Length is capped while trying to preserve a short extension.
    """
    if filename is None:
        return "unnamed"
    name = str(filename).strip()
    name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", name)
    name = name.strip(" .")
    # If only underscores/noise remain after stripping, treat as empty
    if not name or re.fullmatch(r"[_.]+", name):
        # Keep pure-underscore replacements of illegal-only strings as underscores
        # when original had non-space content that became underscores
        if name and set(name) <= {"_"}:
            return name if name else "unnamed"
        return "unnamed"
    if len(name) > max_length:
        # Preserve short extension if present
        if "." in name[1:]:
            stem, ext = name.rsplit(".", 1)
            if len(ext) <= 8:
                keep = max_length - len(ext) - 1
                name = f"{stem[:keep]}.{ext}" if keep > 0 else name[:max_length]
            else:
                name = name[:max_length]
        else:
            name = name[:max_length]
    return name

def format_time(seconds):
    if seconds < 0:
        return "0s"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"
