import os
import sys
import time
import threading

class DownloadManager:
    def __init__(self, total_files):
        self.total_files = total_files
        self.downloads = {} # file_id -> info
        self.lock = threading.Lock()
        self.start_line = 0
        self.last_draw_time = 0
        self.scroll_offsets = {} # file_id -> current offset
        self.last_scroll_time = 0
        self.prev_width = 0
        self.first_draw = True

    def update_progress(self, file_id, filename, percent, rate_str, eta_str, status="Downloading"):
        with self.lock:
            if file_id not in self.scroll_offsets:
                self.scroll_offsets[file_id] = 0
                
            self.downloads[file_id] = {
                'file_id': file_id,
                'filename': filename,
                'percent': percent,
                'rate': rate_str,
                'eta': eta_str,
                'status': status
            }
            self._draw()

    def complete_download(self, file_id, filename, rate_str, error=None, final=True):
        with self.lock:
            if file_id in self.downloads:
                info = self.downloads[file_id]
                if file_id in self.scroll_offsets:
                    del self.scroll_offsets[file_id]
                if error:
                    if final:
                        info['status'] = "Failed"
                    else:
                        info['status'] = "Queued"
                    info['percent'] = 0
                    info['rate'] = "0.0 KB/s"
                    info['eta'] = "--"
                else:
                    info['status'] = "Completed"
                    info['percent'] = 100
                    info['rate'] = rate_str
                    info['eta'] = "Done"
            self._draw()

    def _draw(self):
        current_time = time.time()
        
        # Update scroll offsets every 0.3 seconds
        if current_time - self.last_scroll_time >= 0.3:
            for file_id, info in self.downloads.items():
                filename = info['filename']
                if len(filename) > 20:
                    self.scroll_offsets[file_id] = (self.scroll_offsets.get(file_id, 0) + 1) % (len(filename) + 5)
            self.last_scroll_time = current_time

        active_count = sum(1 for info in self.downloads.values() if info['status'] == "Downloading")
        if current_time - self.last_draw_time < 0.1 and active_count > 0:
             return
        self.last_draw_time = current_time

        # Sort: Downloading on top, then Queued, then Completed/Failed/Skipped
        # Within each group, sort by file_id
        def sort_key(item):
            info = item[1]
            status = info['status']
            if status == "Downloading":
                priority = 0
            elif status == "Queued":
                priority = 1
            else: # Completed, Failed, Skipped
                priority = 2
            return (priority, item[0])

        sorted_items = sorted(self.downloads.items(), key=sort_key)
        
        try:
            terminal_size = os.get_terminal_size()
            terminal_height = terminal_size.lines
            terminal_width = terminal_size.columns
        except OSError:
            terminal_height = 24
            terminal_width = 80

        # Detect terminal resize
        resized = False
        if terminal_width != self.prev_width:
            resized = True
            self.prev_width = terminal_width

        if self.first_draw:
            # Add an extra newline on the first draw to "move everything down a bit"
            sys.stdout.write("\n")
            self.first_draw = False

        # Leave more room at the bottom to avoid issues with terminal height
        # and cursor positioning. Using -3 instead of -1.
        max_display = terminal_height - 3
        
        display_items = sorted_items[:max_display]
        
        output = []
        for file_id, info in display_items:
            is_done = info['status'] in ["Completed", "Failed", "Skipped"]
            output.append(self._format_line(info, file_id=file_id, is_completed=is_done))
            
        # Move up by the number of lines we previously drew
        if hasattr(self, 'prev_lines') and self.prev_lines > 0:
            if resized:
                # If width changed, move up and clear everything below to remove artifacts
                sys.stdout.write(f"\033[{self.prev_lines}F\033[J")
            else:
                sys.stdout.write(f"\033[{self.prev_lines}F")
            
        for line in output:
            # Clear line and print
            sys.stdout.write("\033[K" + line + "\n")
            
        # If we truncated, add a line indicating more
        if len(sorted_items) > max_display:
            sys.stdout.write(f"\033[K... and {len(sorted_items) - max_display} more items\n")
            self.prev_lines = len(output) + 1
        else:
            self.prev_lines = len(output)
        sys.stdout.flush()

    def _format_line(self, info, file_id=None, is_completed=False):
        filename = info['filename']
        percent = info['percent']
        rate_str = info['rate']
        eta_str = info['eta']
        status = info['status']
        
        # Scroll filename
        display_filename = filename
        if len(filename) > 20:
            offset = self.scroll_offsets.get(file_id, 0)
            # Padding filename with spaces for smooth loop
            padded_name = filename + "     "
            display_filename = (padded_name[offset:] + padded_name[:offset])[:20]
        
        # Truncate filename if too long for simple fallback
        try:
            columns = os.get_terminal_size().columns
        except OSError:
            columns = 80
            
        # ANSI colors for percentage and status
        if status == "Failed":
            color = "\033[91m" # Red
        elif status == "Queued":
            color = "\033[93m" # Yellow
        elif status == "Skipped":
            color = "\033[95m" # Magenta
        elif percent < 33:
            color = "\033[91m" # Red
        elif percent < 66:
            color = "\033[93m" # Yellow
        elif percent < 100:
            color = "\033[94m" # Blue
        else:
            color = "\033[92m" # Green
        reset = "\033[0m"
        
        percent_str = f"{percent:6.1f}%"
        if status == "Queued":
            percent_str = "QUEUED"
        elif status == "Failed":
            percent_str = "FAILED"
        elif status == "Skipped":
            percent_str = "SKIPPED"
        elif status == "Completed":
            percent_str = " DONE "
            
        rate_str_fixed = f"{rate_str:>10}"
        eta_str_fixed = f"{eta_str:<15}"
        
        prefix = f"{display_filename:<20} ["
        suffix = f"] {percent_str} {rate_str_fixed} {eta_str_fixed}"
        
        # Adjust colored_suffix based on status
        if status in ["Queued", "Failed", "Skipped", "Completed"]:
            colored_suffix = f"] {color}{percent_str:^6}{reset} {rate_str_fixed} {eta_str_fixed}"
        else:
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
            return f"{prefix}{bar}{reset}{padding}{colored_suffix}"
        else:
            return f"{display_filename[:10]} {percent_str} {rate_str_fixed}"
