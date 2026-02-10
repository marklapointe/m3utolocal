import curses
import time
from utils import format_size

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
            
            # Scroll filename if too long for TUI
            display_name = name
            if len(name) > w - 10:
                # Use time for scrolling effect in TUI
                scroll_w = w - 10
                offset = int(time.time() * 2) % (len(name) + 5)
                padded_name = name + "     "
                display_name = (padded_name[offset:] + padded_name[:offset])[:scroll_w]

            item_prefix = f" {idx+1}. {display_name}"
            
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
                
    try:
        return curses.wrapper(main_tui)
    except KeyboardInterrupt:
        return None
