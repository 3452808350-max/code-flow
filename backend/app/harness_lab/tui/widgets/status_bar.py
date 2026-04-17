"""
Status bar for TUI bottom display.

Shows: Model, Workers, Tasks, Time, Help hints.
"""

from textual.widgets import Footer
from textual.binding import Binding

from ..theme import ColorTheme


class StatusBar(Footer):
    """Bottom status bar with key hints.
    
    Bindings:
    - Ctrl+H: Show help
    - ESC: Close/Exit
    - d: Drain selected worker
    - r: Resume selected worker
    - i: Inspect selected worker
    """
    
    BINDINGS = [
        Binding("ctrl+h", "show_help", "Help", show=True),
        Binding("escape", "quit", "Exit", show=True),
        Binding("d", "drain_worker", "Drain", show=True),
        Binding("r", "resume_worker", "Resume", show=True),
        Binding("i", "inspect_worker", "Inspect", show=True),
        Binding("l", "toggle_logs", "Logs", show=True),
    ]
    
    def __init__(
        self,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()