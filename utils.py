import os
import re
import requests
import time

def format_size(size_bytes):
    if size_bytes < 0:
        return "0 B"
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
    try:
        # Try HEAD request first as it's faster
        response = requests.head(url, allow_redirects=True, timeout=5)
        size = int(response.headers.get('content-length', 0))
        if size > 0:
            return size
        
        # If HEAD doesn't give size, try GET with stream=True
        with requests.get(url, stream=True, timeout=5) as r:
            return int(r.headers.get('content-length', 0))
    except Exception:
        return 0

def parse_m3u(file_path):
    channels = []
    current_channel = {}
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Extract tvg-id
                tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
                tvg_id = tvg_id_match.group(1) if tvg_id_match else ""
                
                # Extract tvg-name if available, otherwise use everything after the last comma
                tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
                if tvg_name_match:
                    tvg_name = tvg_name_match.group(1)
                else:
                    parts = line.split(',')
                    tvg_name = parts[-1] if len(parts) > 1 else ""
                
                current_channel['tvg-id'] = tvg_id
                current_channel['tvg-name'] = tvg_name
            elif line and not line.startswith('#'):
                current_channel['url'] = line
                # Only keep channels that have either tvg-id or tvg-name
                if current_channel.get('tvg-id') or current_channel.get('tvg-name'):
                    channels.append(current_channel)
                current_channel = {}
    return channels

def sanitize_filename(filename):
    # Remove characters that are not allowed in filenames
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

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
