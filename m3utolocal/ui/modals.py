"""Modal screens: confirm, help, language, cleanup preview, error."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static

from m3utolocal.i18n import _
from m3utolocal.i18n.languages import LanguageInfo


class ConfirmModal(ModalScreen[bool]):
    """Confirm an action; returns True if confirmed."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "confirm", "Confirm", show=True),
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "cancel", "No", show=False),
    ]

    def __init__(self, message: str, title: str | None = None) -> None:
        super().__init__()
        self.message = message
        self.title_text = title or _("Confirm")

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(self.title_text, classes="modal-title", id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(classes="action-bar"):
                yield Button(_("Confirm"), variant="primary", id="btn-ok")
                yield Button(_("Cancel"), variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class HelpModal(ModalScreen[None]):
    """Keyboard shortcuts and navigation guide."""

    BINDINGS = [Binding("escape", "close", "Close"), Binding("q", "close", "Close")]

    def compose(self) -> ComposeResult:
        help_text = (
            f"=== {_('HomeScreen Keys')} ===\n"
            f"[1] / [/] : {_('Search playlist')}\n"
            f"[2] / [c] : {_('Cleanup library')}\n"
            f"[3] / [s] : {_('Settings')}\n"
            f"[4] / [L] : {_('Language')}\n"
            f"[5] / [d] : {_('Downloads Queue')}\n"
            f"[6] / [q] : {_('Quit')}\n\n"
            f"=== {_('SearchScreen Keys')} ===\n"
            f"[Space] : {_('Toggle item')}\n"
            f"[t] : {_('Toggle & Down')}\n"
            f"[Dbl Click / Enter] : {_('Toggle / Add selection')}\n"
            f"[a] : {_('Select All')}\n"
            f"[n] : {_('Select None')}\n"
            f"[i] : {_('Invert selection')}\n"
            f"[d] : {_('Download selected')}\n"
            f"[j/k or Arrows] : {_('Navigate items')}\n\n"
            f"=== {_('General Keys')} ===\n"
            f"[?] : {_('Help')}\n"
            f"[Esc / q] : {_('Back or Quit')}\n"
        )
        with Vertical(classes="modal-box"):
            yield Static(_("Help & Keyboard Shortcuts"), classes="modal-title", id="help-title")
            yield Label(help_text, id="help-content", markup=False)
            with Horizontal(classes="action-bar"):
                yield Button(_("Close"), variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


class LanguageModal(ModalScreen[str | None]):
    """Pick a language; returns language code or None."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "choose", "Choose"),
    ]

    def __init__(self, languages: list[LanguageInfo], current: str = "en") -> None:
        super().__init__()
        self.languages = languages
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(_("Language"), classes="modal-title", id="lang-title")
            items = []
            for lang in self.languages:
                mark = " ★" if lang.code == self.current else ""
                label = f"{lang.native_name} ({lang.code}){mark}"
                items.append(ListItem(Label(label), id=f"lang-{lang.code}"))
            yield ListView(*items, id="lang-list")
            with Horizontal(classes="action-bar"):
                yield Button(_("Apply"), variant="primary", id="btn-apply")
                yield Button(_("Cancel"), id="btn-cancel")

    def _selected_code(self) -> str | None:
        lv = self.query_one("#lang-list", ListView)
        if lv.index is None:
            return None
        item = lv.highlighted_child
        if item is None or not item.id:
            return None
        return item.id.removeprefix("lang-")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply":
            self.action_choose()
        else:
            self.dismiss(None)

    def action_choose(self) -> None:
        self.dismiss(self._selected_code())

    def action_cancel(self) -> None:
        self.dismiss(None)


class CleanupPreviewModal(ModalScreen[bool]):
    """Show cleanup items; confirm to apply."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Apply"),
    ]

    def __init__(self, lines: list[str], total_bytes: int) -> None:
        super().__init__()
        self.lines = lines
        self.total_bytes = total_bytes

    def compose(self) -> ComposeResult:
        from utils import format_size

        with Vertical(classes="modal-box"):
            yield Static(_("Cleanup preview"), classes="modal-title", id="cleanup-title")
            yield Label(
                _("Plan: {n} items ({size})").format(
                    n=len(self.lines), size=format_size(self.total_bytes)
                )
            )
            body = "\n".join(self.lines[:50]) or _("Nothing to clean.")
            if len(self.lines) > 50:
                body += f"\n… +{len(self.lines) - 50}"
            yield Static(body, id="cleanup-list")
            with Horizontal(classes="action-bar"):
                yield Button(_("Apply cleanup"), variant="error", id="btn-ok")
                yield Button(_("Cancel"), id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-ok")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ErrorModal(ModalScreen[None]):
    """Display an error message modal."""

    BINDINGS = [Binding("escape", "close", "Close"), Binding("enter", "close", "Close")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-box"):
            yield Static(_("Error"), classes="modal-title", id="error-title")
            yield Label(self.message, id="error-message")
            with Horizontal(classes="action-bar"):
                yield Button(_("Close"), variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
