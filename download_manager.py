import os
import sys
import time
import threading

class DownloadManager:
    def __init__(self, total_files):
        self.total_files = total_files
        self.active_downloads = {} # file_id -> info
        self.completed_downloads = []
        self.lock = threading.Lock()
        self.start_line = 0
        self.last_draw_time = 0
        self.scroll_offsets = {} # file_id -> current offset
        self.last_scroll_time = 0

    def update_progress(self, file_id, filename, percent, rate_str, eta_str, status="Downloading"):
        with self.lock:
            if file_id not in self.scroll_offsets:
                self.scroll_offsets[file_id] = 0
                
            self.active_downloads[file_id] = {
                'filename': filename,
                'percent': percent,
                'rate': rate_str,
                'eta': eta_str,
                'status': status
            }
            self._draw()

    def complete_download(self, file_id, filename, rate_str, error=None):
        with self.lock:
            if file_id in self.active_downloads:
                info = self.active_downloads.pop(file_id)
                if file_id in self.scroll_offsets:
                    del self.scroll_offsets[file_id]
                if error:
                    info['status'] = f"Failed: {error}"
                    info['percent'] = 0
                else:
                    info['status'] = "Completed"
                    info['percent'] = 100
                info['rate'] = rate_str
                info['eta'] = "Done"
                self.completed_downloads.append(info)
            self._draw()

    def _draw(self):
        current_time = time.time()
        
        # Update scroll offsets every 0.3 seconds
        if current_time - self.last_scroll_time >= 0.3:
            for file_id, info in self.active_downloads.items():
                filename = info['filename']
                if len(filename) > 20:
                    self.scroll_offsets[file_id] = (self.scroll_offsets.get(file_id, 0) + 1) % (len(filename) + 5)
            self.last_scroll_time = current_time

        if current_time - self.last_draw_time < 0.1 and len(self.active_downloads) > 0:
             return
        self.last_draw_time = current_time

        # Clean way:
        output = []
        for info in self.completed_downloads:
            output.append(self._format_line(info, is_completed=True))
        
        for file_id in sorted(self.active_downloads.keys()):
            output.append(self._format_line(self.active_downloads[file_id], file_id=file_id))
            
        # Move up by the number of lines we previously drew
        if hasattr(self, 'prev_lines') and self.prev_lines > 0:
            sys.stdout.write(f"\033[{self.prev_lines}F")
            
        for line in output:
            # Clear line and print
            sys.stdout.write("\033[K" + line + "\n")
            
        self.prev_lines = len(output)
        sys.stdout.flush()

    def _format_line(self, info, file_id=None, is_completed=False):
        filename = info['filename']
        percent = info['percent']
        rate_str = info['rate']
        eta_str = info['eta']
        status = info['status']
        
        # Scroll or truncate filename
        display_filename = filename
        if len(filename) > 20:
            if is_completed:
                display_filename = filename[:17] + "..."
            else:
                offset = self.scroll_offsets.get(file_id, 0)
                # Padding filename with spaces for smooth loop
                padded_name = filename + "     "
                display_filename = (padded_name[offset:] + padded_name[:offset])[:20]
        
        # Truncate filename if too long for simple fallback
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
        
        percent_str = f"{percent:6.1f}%"
        rate_str_fixed = f"{rate_str:>10}"
        eta_str_fixed = f"{eta_str:<15}"
        
        prefix = f"{display_filename:<20} ["
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
            return f"{prefix}{bar}{reset}{padding}{colored_suffix}"
        else:
            return f"{display_filename[:10]} {percent_str} {rate_str_fixed}"
