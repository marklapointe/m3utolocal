"""Fallback curses TUI selection interface."""

import curses
import time
from m3utolocal.utils import format_size


def tui_select(matches):
    """Interactive curses multi-select for playlist matches."""

    def draw_menu(stdscr, cursor_idx, selected_indices, scroll_offset):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 4 or w < 20:
            return

        # Calculate total size of selected items
        total_selected_size = sum(matches[idx].get("size", 0) for idx in selected_indices)
        size_str = format_size(total_selected_size)

        # Header
        header = f" m3utolocal | Found {len(matches)} matches · {len(selected_indices)} selected ({size_str}) "
        header_str = header[:w].ljust(w)
        stdscr.addstr(0, 0, header_str, curses.A_REVERSE | curses.A_BOLD)

        # List items
        list_h = h - 2  # Room for header and footer status
        for i in range(list_h):
            idx = i + scroll_offset
            if idx >= len(matches):
                break

            is_selected = idx in selected_indices
            is_cursor = idx == cursor_idx

            name = matches[idx].get("tvg-id") or matches[idx].get("tvg-name") or "unnamed"
            item_size = format_size(matches[idx].get("size", 0))

            # Scroll filename if too long for TUI window width
            max_name_w = max(10, w - 22)
            display_name = name
            if len(name) > max_name_w:
                padded_name = name + "    "
                offset = int(time.time() * 2) % len(padded_name)
                display_name = (padded_name[offset:] + padded_name[:offset])[:max_name_w]

            check_mark = "✔" if is_selected else " "
            line_str = f" [{check_mark}] {idx + 1:3d}. {display_name:<{max_name_w}} ({item_size:>8})"
            truncated_line = line_str[: w - 1]

            if is_cursor:
                stdscr.attron(curses.A_REVERSE)
                if is_selected and curses.has_colors():
                    stdscr.addstr(i + 1, 0, truncated_line.ljust(w - 1), curses.A_REVERSE | curses.color_pair(1))
                else:
                    stdscr.addstr(i + 1, 0, truncated_line.ljust(w - 1), curses.A_REVERSE)
                stdscr.attroff(curses.A_REVERSE)
            else:
                if is_selected and curses.has_colors():
                    stdscr.addstr(i + 1, 0, truncated_line[:4])
                    stdscr.addstr(truncated_line[4:5], curses.color_pair(1) | curses.A_BOLD)
                    stdscr.addstr(truncated_line[5:])
                else:
                    stdscr.addstr(i + 1, 0, truncated_line)

        # Footer
        footer = " Space: Toggle | t: Toggle & Down | Enter: Confirm | a: All | n: None | i: Invert | q: Quit "
        stdscr.addstr(h - 1, 0, footer[:w].ljust(w), curses.A_REVERSE)
        stdscr.refresh()

    def main_tui(stdscr):
        try:
            curses.curs_set(0)  # Hide cursor
        except Exception:
            pass

        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_GREEN, -1)
        except Exception:
            pass

        cursor_idx = 0
        selected_indices = set(range(len(matches)))
        scroll_offset = 0

        while True:
            h, w = stdscr.getmaxyx()
            list_h = max(1, h - 2)

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

            if key in [ord("q"), ord("Q")]:
                return None
            elif key in [curses.KEY_UP, ord("k")]:
                cursor_idx = max(0, cursor_idx - 1)
            elif key in [curses.KEY_DOWN, ord("j")]:
                cursor_idx = min(len(matches) - 1, cursor_idx + 1)
            elif key == ord(" "):
                if cursor_idx in selected_indices:
                    selected_indices.remove(cursor_idx)
                else:
                    selected_indices.add(cursor_idx)
            elif key == ord("t"):
                if cursor_idx in selected_indices:
                    selected_indices.remove(cursor_idx)
                else:
                    selected_indices.add(cursor_idx)
                cursor_idx = min(len(matches) - 1, cursor_idx + 1)
            elif key == ord("a"):
                selected_indices = set(range(len(matches)))
            elif key == ord("n"):
                selected_indices = set()
            elif key == ord("i"):
                selected_indices = set(range(len(matches))) - selected_indices
            elif key in [curses.KEY_ENTER, 10, 13]:  # Enter
                if not selected_indices:
                    stdscr.addstr(
                        h - 1,
                        0,
                        " Error: Select at least one item or press 'q' to quit.".ljust(w),
                        curses.A_BOLD | curses.color_pair(1),
                    )
                    stdscr.refresh()
                    time.sleep(0.8)
                    continue
                return sorted(list(selected_indices))
            elif key == curses.KEY_RESIZE:
                stdscr.erase()

    try:
        return curses.wrapper(main_tui)
    except KeyboardInterrupt:
        return None
