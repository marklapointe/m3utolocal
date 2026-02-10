import os
import sys
import time
import requests
from utils import format_time

def download_file(url, target_filename, manager=None, file_id=None, final=True):
    display_name = os.path.basename(target_filename)
    try:
        # Get remote file size first
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            accept_ranges = r.headers.get('Accept-Ranges') == 'bytes'
            
            if os.path.exists(target_filename):
                local_size = os.path.getsize(target_filename)
                if total_size > 0 and local_size == total_size:
                    if manager:
                        manager.complete_download(file_id, display_name, "Skipped", final=final)
                    else:
                        print(f"File '{target_filename}' already exists and size matches. Skipping.")
                    return
                else:
                    if not manager:
                        print(f"File '{target_filename}' exists but size mismatch (Local: {local_size}, Remote: {total_size}). Redownloading...")

            if not manager:
                print(f"Downloading to '{target_filename}' ({total_size} bytes)...")
            
            temp_path = target_filename + ".part"
            initial_pos = 0
            if os.path.exists(temp_path):
                initial_pos = os.path.getsize(temp_path)
                if accept_ranges and initial_pos < total_size:
                    headers = {'Range': f'bytes={initial_pos}-'}
                    r_gen = requests.get(url, headers=headers, stream=True, timeout=30)
                else:
                    initial_pos = 0
                    r_gen = requests.get(url, stream=True, timeout=30)
            else:
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
                            # In multi-threaded mode, chunk iteration might be blocking.
                            # KeyboardInterrupt is handled in main thread, but individual threads 
                            # should also check if they should exit if possible.
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)
                                downloaded_since_start += len(chunk)
                                
                                current_time = time.time()
                                if current_time - last_update_time >= 0.1 or downloaded == total_size:
                                    if total_size > 0:
                                        percent = downloaded / total_size * 100
                                        elapsed = current_time - start_time
                                        if elapsed > 0:
                                            rate = downloaded_since_start / elapsed
                                            if rate > 1024 * 1024:
                                                rate_val = rate / (1024 * 1024)
                                                rate_unit = "MB/s"
                                            else:
                                                rate_val = rate / 1024
                                                rate_unit = "KB/s"
                                            rate_str = f"{rate_val:5.1f} {rate_unit}"
                                            
                                            remaining_bytes = total_size - downloaded
                                            if rate > 0:
                                                eta_seconds = remaining_bytes / rate
                                                eta_val = format_time(eta_seconds)
                                            else:
                                                eta_val = "--"
                                            eta_str = f"ETA: {eta_val}"
                                        else:
                                            rate_str = "  0.0 KB/s"
                                            eta_str = "ETA: --"
                                        
                                        if manager:
                                            manager.update_progress(file_id, display_name, percent, rate_str, eta_str)
                                        else:
                                            # Standard single-line progress bar logic...
                                            try:
                                                columns = os.get_terminal_size().columns
                                            except OSError:
                                                columns = 80
                                            
                                            # Scroll filename if too long (single-threaded mode)
                                            display_name_scrolled = display_name
                                            if len(display_name) > 20:
                                                # Use time to calculate scroll offset for single thread
                                                offset = int(time.time() * 3) % (len(display_name) + 5)
                                                padded_name = display_name + "     "
                                                display_name_scrolled = (padded_name[offset:] + padded_name[:offset])[:20]

                                            if percent < 33: color = "\033[91m"
                                            elif percent < 66: color = "\033[93m"
                                            elif percent < 100: color = "\033[94m"
                                            else: color = "\033[92m"
                                            reset = "\033[0m"
                                            
                                            percent_str = f"{percent:6.1f}%"
                                            rate_str_fixed = f"{rate_str:>10}"
                                            eta_str_fixed = f"{eta_str:<15}"
                                            
                                            prefix = f"{display_name_scrolled:<20} ["
                                            suffix = f"] {percent_str} {rate_str_fixed} {eta_str_fixed}"
                                            colored_suffix = f"] {color}{percent_str}{reset} {rate_str_fixed} {eta_str_fixed}"
                                            
                                            bar_width = columns - len(prefix) - len(suffix) - 2
                                            if bar_width > 0:
                                                full_blocks = int(percent * bar_width / 100)
                                                fraction = (percent * bar_width / 100) - full_blocks
                                                bar = f"{color}:" * full_blocks
                                                if fraction > 0 and full_blocks < bar_width:
                                                    bar += "."
                                                    padding = " " * (bar_width - full_blocks - 1)
                                                else:
                                                    padding = " " * (bar_width - full_blocks)
                                                sys.stdout.write(f"\r{prefix}{bar}{reset}{padding}{colored_suffix}")
                                                sys.stdout.flush()
                                        last_update_time = current_time
                    except KeyboardInterrupt:
                        if manager:
                             manager.complete_download(file_id, display_name, "0.0 KB/s", error="Interrupted", final=final)
                        else:
                             # For single thread, this is caught by the loop in main()
                             pass
                        raise
                
                if not manager:
                    print() # Move to next line after progress bar
                
                if os.path.exists(target_filename):
                    os.remove(target_filename)
                os.rename(temp_path, target_filename)
                
                if manager:
                    manager.complete_download(file_id, display_name, rate_str, final=final)
                else:
                    print(f"Successfully downloaded '{target_filename}'.")
                    
    except KeyboardInterrupt:
        # Re-raise KeyboardInterrupt to be handled by the main thread
        raise
    except Exception as e:
        if manager:
            manager.complete_download(file_id, display_name, "0.0 KB/s", error=str(e), final=final)
        else:
            print(f"\nFailed to download '{url}': {e}")
        raise # Re-raise to let main know it failed
