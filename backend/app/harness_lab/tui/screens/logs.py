"""
Logs screen - Full-screen log viewer.

Shows worker logs and system events.
"""

from textual.screen import Screen
from textual.widgets import Header
from textual.containers import Container, VerticalScroll
from textual.app import ComposeResult

from ..theme import ColorTheme
from ..widgets import StatusBar


class LogsScreen(Screen):
    """Full-screen log viewer.
    
    Shows system logs with scrolling.
    """
    
    DEFAULT_CSS = """
    LogsScreen {
        layout: vertical;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("f", "follow", "Follow"),
    ]
    
    def __init__(
        self,
        theme: ColorTheme = None,
        follow_mode: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()
        self.follow_mode = follow_mode
    
    def compose(self) -> ComposeResult:
        """Compose logs screen."""
        yield Header()
        
        with Container():
            with VerticalScroll(id="log-container"):
                # Logs will be populated dynamically
                pass
        
        yield StatusBar(self.theme)
    
    def on_mount(self) -> None:
        """Set title on mount."""
        header = self.query_one(Header)
        header.title = "System Logs"
    
    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()
    
    def action_follow(self) -> None:
        """Toggle follow mode."""
        self.follow_mode = not self.follow_mode