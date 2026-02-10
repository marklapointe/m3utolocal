#!/usr/bin/env python3
# Copyright (c) 2026, Mark LaPointe <mark@cloudbsd.org>
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import os
import re
import sys
import concurrent.futures

from utils import format_size, get_file_size, parse_m3u, sanitize_filename
from tui import tui_select
from download_manager import DownloadManager
from downloader import download_file

def main():
    parser = argparse.ArgumentParser(description="Download files from an M3U file based on search query.")
    parser.add_argument("query", help="Search query for tvg-id or tvg-name")
    parser.add_argument("-y", "--yes", action="store_true", help="Bypass confirmation and download all matches")
    parser.add_argument("-m", "--m3u", default="chans.m3u", help="Path to the M3U file (default: chans.m3u)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of simultaneous downloads (default: 1)")
    
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
    # ANSI colors for cycling dots
    dot_colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    reset = "\033[0m"
    
    try:
        for i, match in enumerate(matches):
            num_dots = (i % 3) + 1
            dots = "." * num_dots
            color = dot_colors[i % len(dot_colors)]
            percent = (i / len(matches)) * 100
            # Print with colorful dots, padded to avoid flickering
            print(f"\r[{percent:5.1f}%] Fetching sizes {color}{dots:<3}{reset}", end="", flush=True)
            match['size'] = get_file_size(match['url'])
        print(f"\r[100.0%] Fetching sizes Done.             ")
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

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
    
    manager = DownloadManager(len(matches)) if args.threads > 1 else None
    
    def process_download(i, channel, final=True):
        tvg_id = channel.get('tvg-id', '')
        tvg_name = channel.get('tvg-name', '')
        url = channel['url']
        
        display_name = tvg_id if tvg_id else tvg_name
        safe_base = sanitize_filename(display_name)
        
        ext_match = re.search(r'(\.[a-zA-Z0-9]{2,4})(\?.*)?$', url)
        extension = ext_match.group(1) if ext_match else ""
        
        if len(matches) > 1:
            target_filename = f"{safe_base}_{i+1}{extension}"
        else:
            target_filename = f"{safe_base}{extension}"
            
        final_path = os.path.join(".", target_filename)
        temp_path = os.path.join(download_dir, target_filename)
        
        try:
            if os.path.exists(final_path):
                download_file(url, final_path, manager=manager, file_id=i, final=final)
            else:
                download_file(url, temp_path, manager=manager, file_id=i, final=final)
                if os.path.exists(temp_path):
                    if manager is None:
                        print(f"Moving '{target_filename}' to current directory.")
                    if os.path.exists(final_path):
                        os.remove(final_path)
                    os.rename(temp_path, final_path)
        except Exception:
            raise # Re-raise to be handled by executor

    try:
        failed_downloads = []
        current_threads = args.threads
        
        if current_threads > 1:
            # Multi-threaded pass with dynamic thread reduction
            manager = DownloadManager(len(matches))
            active_futures = {}
            remaining_to_submit = list(enumerate(matches))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
                while remaining_to_submit or active_futures:
                    # Submit new tasks up to current_threads
                    while remaining_to_submit and len(active_futures) < current_threads:
                        i, channel = remaining_to_submit.pop(0)
                        future = executor.submit(process_download, i, channel, final=False)
                        active_futures[future] = (i, channel)
                    
                    if not active_futures:
                        break
                        
                    done, _ = concurrent.futures.wait(active_futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
                    
                    for future in done:
                        i, channel = active_futures.pop(future)
                        try:
                            future.result()
                        except KeyboardInterrupt:
                            print("\n\nInterrupted by user. Shutting down threads...")
                            executor.shutdown(wait=False, cancel_futures=True)
                            sys.exit(1)
                        except Exception:
                            failed_downloads.append((i, channel))
                            if current_threads > 1:
                                current_threads -= 1
        else:
            # Single threaded pass
            for i, channel in enumerate(matches):
                try:
                    process_download(i, channel, final=True)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    failed_downloads.append((i, channel))

        # Retry failed downloads one by one
        if failed_downloads:
            if not manager:
                print(f"\nRetrying {len(failed_downloads)} failed downloads...")
            
            for i, channel in failed_downloads:
                try:
                    # final=True here to mark it as Failed if it fails again
                    process_download(i, channel, final=True)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    pass

        print("\nAll downloads completed.")
    except KeyboardInterrupt:
        print("\nDownload cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
