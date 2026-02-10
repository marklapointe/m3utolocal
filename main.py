#!/usr/bin/env python3
# Copyright (c) 2026, Mark LaPointe <mark@cloudbsd.org>
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import os
import re
import requests
import sys
import tempfile

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

import curses
import time

def tui_select(matches):
    def draw_menu(stdscr, cursor_idx, selected_indices, scroll_offset):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        
        # Calculate total size of selected items
        total_selected_size = sum(matches[idx].get('size', 0) for idx in selected_indices)
        size_str = format_size(total_selected_size)
        
        # Header
        title = f" Found {len(matches)} matches | Total: {size_str} (Space: Toggle, Enter: Confirm, a: All, n: None, q: Quit) "
        stdscr.addstr(0, 0, title[:w], curses.A_REVERSE)
        
        # List items
        list_h = h - 2 # Leaves room for header and footer/status
        for i in range(list_h):
            idx = i + scroll_offset
            if idx >= len(matches):
                break
            
            is_selected = idx in selected_indices
            is_cursor = (idx == cursor_idx)
            
            name = matches[idx].get('tvg-id') or matches[idx].get('tvg-name')
            item_prefix = f" {idx+1}. {name}"
            
            if is_cursor:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(i + 1, 0, " ")
                if is_selected:
                    stdscr.addstr("[", curses.A_REVERSE)
                    stdscr.addstr("✔", curses.A_REVERSE | curses.color_pair(1))
                    stdscr.addstr("]", curses.A_REVERSE)
                else:
                    stdscr.addstr("[ ]", curses.A_REVERSE)
                stdscr.addstr(item_prefix[:w-5], curses.A_REVERSE)
                # Fill the rest of the line with reverse attribute
                remaining = w - (5 + len(item_prefix[:w-5]))
                if remaining > 0:
                    stdscr.addstr(" " * remaining, curses.A_REVERSE)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(i + 1, 0, " ")
                if is_selected:
                    stdscr.addstr("[")
                    stdscr.addstr("✔", curses.color_pair(1))
                    stdscr.addstr("]")
                else:
                    stdscr.addstr("[ ]")
                stdscr.addstr(item_prefix[:w-5])
        
        stdscr.refresh()

    def main_tui(stdscr):
        curses.curs_set(0) # Hide cursor
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            # Define green color pair
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            
        cursor_idx = 0
        selected_indices = set(range(len(matches)))
        scroll_offset = 0
        
        while True:
            h, w = stdscr.getmaxyx()
            list_h = h - 2
            
            # Adjust scroll offset
            if cursor_idx < scroll_offset:
                scroll_offset = cursor_idx
            elif cursor_idx >= scroll_offset + list_h:
                scroll_offset = cursor_idx - list_h + 1
                
            draw_menu(stdscr, cursor_idx, selected_indices, scroll_offset)
            
            try:
                key = stdscr.getch()
            except KeyboardInterrupt:
                return None
            
            if key == ord('q'):
                return None
            elif key == curses.KEY_UP:
                cursor_idx = max(0, cursor_idx - 1)
            elif key == curses.KEY_DOWN:
                cursor_idx = min(len(matches) - 1, cursor_idx + 1)
            elif key == ord(' '):
                if cursor_idx in selected_indices:
                    selected_indices.remove(cursor_idx)
                else:
                    selected_indices.add(cursor_idx)
            elif key == ord('a'):
                selected_indices = set(range(len(matches)))
            elif key == ord('n'):
                selected_indices = set()
            elif key in [curses.KEY_ENTER, 10, 13]: # Enter
                if not selected_indices:
                    stdscr.addstr(h-1, 0, "Error: No items selected. Select at least one or 'q' to quit.", curses.A_BOLD)
                    stdscr.refresh()
                    continue
                return sorted(list(selected_indices))
            elif key == curses.KEY_RESIZE:
                stdscr.erase()
                
    return curses.wrapper(main_tui)

def download_file(url, target_filename):
    try:
        # Get remote file size first
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            accept_ranges = r.headers.get('Accept-Ranges') == 'bytes'
            
            if os.path.exists(target_filename):
                local_size = os.path.getsize(target_filename)
                if total_size > 0 and local_size == total_size:
                    print(f"File '{target_filename}' already exists and size matches. Skipping.")
                    return
                else:
                    print(f"File '{target_filename}' exists but size mismatch (Local: {local_size}, Remote: {total_size}). Redownloading...")

            print(f"Downloading to '{target_filename}' ({total_size} bytes)...")
            
            temp_path = target_filename + ".part"
            initial_pos = 0
            if os.path.exists(temp_path):
                initial_pos = os.path.getsize(temp_path)
                if accept_ranges and initial_pos < total_size:
                    print(f"Resuming download from {initial_pos} bytes...")
                    headers = {'Range': f'bytes={initial_pos}-'}
                    r_gen = requests.get(url, headers=headers, stream=True, timeout=30)
                else:
                    initial_pos = 0
                    r_gen = requests.get(url, stream=True, timeout=30)
            else:
                # Create empty file immediately to ensure it exists for resume
                with open(temp_path, 'wb') as f:
                    pass
                r_gen = requests.get(url, stream=True, timeout=30)

            with r_gen as r:
                r.raise_for_status()
                mode = 'ab' if initial_pos > 0 else 'wb'
                
                with open(temp_path, mode) as tmp_file:
                    downloaded = initial_pos
                    start_time = time.time()
                    last_update_time = start_time
                    downloaded_since_start = 0
                    
                    try:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)
                                downloaded_since_start += len(chunk)
                                
                                current_time = time.time()
                                if current_time - last_update_time >= 0.1 or downloaded == total_size:
                                    if total_size > 0:
                                        percent = downloaded / total_size * 100
                                        
                                        # Terminal width
                                        try:
                                            columns = os.get_terminal_size().columns
                                        except OSError:
                                            columns = 80
                                        
                                        # ANSI colors for percentage
                                        if percent < 33:
                                            color = "\033[91m" # Red
                                        elif percent < 66:
                                            color = "\033[93m" # Yellow
                                        elif percent < 100:
                                            color = "\033[94m" # Blue
                                        else:
                                            color = "\033[92m" # Green
                                        reset = "\033[0m"
                                        
                                        # Download rate
                                        elapsed = current_time - start_time
                                        if elapsed > 0:
                                            rate = downloaded_since_start / elapsed
                                            if rate > 1024 * 1024:
                                                rate_str = f"{rate / (1024 * 1024):.1f} MB/s"
                                            else:
                                                rate_str = f"{rate / 1024:.1f} KB/s"
                                        else:
                                            rate_str = "0.0 B/s"
                                            
                                        prefix = f"Progress: ["
                                        suffix = f"] {percent:5.1f}% {rate_str}"
                                        colored_suffix = f"] {color}{percent:5.1f}%{reset} {rate_str}"
                                        
                                        # Available width for the bar itself
                                        bar_width = columns - len(prefix) - len(suffix) - 2
                                        if bar_width > 0:
                                            full_blocks = int(percent * bar_width / 100)
                                            fraction = (percent * bar_width / 100) - full_blocks
                                            
                                            bar = f"{color}:" * full_blocks
                                            if fraction > 0 and full_blocks < bar_width:
                                                bar += "."
                                                # If we added a dot, we need to fill the rest with spaces
                                                padding = " " * (bar_width - full_blocks - 1)
                                            else:
                                                padding = " " * (bar_width - full_blocks)
                                            
                                            sys.stdout.write(f"\r{prefix}{bar}{reset}{padding}{colored_suffix}")
                                            sys.stdout.flush()
                                            last_update_time = current_time
                    except KeyboardInterrupt:
                        print("\nDownload interrupted by user.")
                        return
                
                print() # Move to next line after progress bar
                if os.path.exists(target_filename):
                    os.remove(target_filename)
                os.rename(temp_path, target_filename)
                print(f"Successfully downloaded '{target_filename}'.")
    except Exception as e:
        print(f"\nFailed to download '{url}': {e}")
def main():
    parser = argparse.ArgumentParser(description="Download files from an M3U file based on search query.")
    parser.add_argument("query", help="Search query for tvg-id or tvg-name")
    parser.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation and download all matches")
    parser.add_argument("-m", "--m3u", default="chans.m3u", help="Path to the M3U file (default: chans.m3u)")
    
    args = parser.parse_args()
    
    search_query = args.query.lower()
    m3u_file = args.m3u
    
    if not os.path.exists(m3u_file):
        print(f"Error: {m3u_file} not found.")
        sys.exit(1)

    print(f"Searching for '{search_query}' in '{m3u_file}'...")
    channels = parse_m3u(m3u_file)
    
    # Filter by search query in tvg-id or tvg-name
    matches = []
    for c in channels:
        # Check both tvg-id and tvg-name for matches
        if search_query in c['tvg-id'].lower() or search_query in c['tvg-name'].lower():
            # Apply extension check to filter out live streams
            # Looking for a dot followed by 2-4 alphanumeric characters at the end of the URL
            if re.search(r'\.[a-zA-Z0-9]{2,4}(\?.*)?$', c['url']):
                matches.append(c)
    
    if not matches:
        print(f"No non-live matches found for '{search_query}'.")
        return

    # Fetch sizes for all matches to display in TUI
    print(f"Fetching file sizes for {len(matches)} matches...")
    for i, match in enumerate(matches):
        dots = "." * ((i % 3) + 1)
        percent = (i / len(matches)) * 100
        print(f"\r[{percent:5.1f}%] Fetching sizes{dots:<3}", end="", flush=True)
        match['size'] = get_file_size(match['url'])
    print(f"\r[100.0%] Fetching sizes... Done.")

    if not args.yes:
        selected_indices = tui_select(matches)
        if selected_indices is None:
            print("Download cancelled.")
            return
    else:
        selected_indices = list(range(len(matches)))

    # Only keep selected matches
    matches = [matches[i] for i in selected_indices]
    
    if not matches:
        print("No items selected for download.")
        return

    total_download_size = sum(match.get('size', 0) for match in matches)
    print(f"\nTotal volume to be downloaded: {format_size(total_download_size)}")

    # Create a downloads directory if it doesn't exist
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    print("\nStarting downloads...")
    for i, channel in enumerate(matches):
        tvg_id = channel.get('tvg-id', '')
        tvg_name = channel.get('tvg-name', '')
        url = channel['url']
        
        # Determine the base name for the file
        # Use tvg-id if available, otherwise fallback to tvg-name
        display_name = tvg_id if tvg_id else tvg_name
        safe_base = sanitize_filename(display_name)
        
        # Extract extension from URL
        ext_match = re.search(r'(\.[a-zA-Z0-9]{2,4})(\?.*)?$', url)
        extension = ext_match.group(1) if ext_match else ""
        
        # If there are multiple matches, we might want to distinguish them
        if len(matches) > 1:
            target_filename = f"{safe_base}_{i+1}{extension}"
        else:
            target_filename = f"{safe_base}{extension}"
            
        final_path = os.path.join(".", target_filename)
        temp_path = os.path.join(download_dir, target_filename)
        
        # Check if file already exists in PWD
        if os.path.exists(final_path):
            # We still call download_file but pass final_path to let it check size
            download_file(url, final_path)
        else:
            # Download to temp space first
            download_file(url, temp_path)
            # If download successful and file exists in temp, move to PWD
            if os.path.exists(temp_path):
                print(f"Moving '{target_filename}' to current directory.")
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_path, final_path)

if __name__ == "__main__":
    main()
