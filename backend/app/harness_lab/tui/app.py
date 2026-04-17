"""
Harness Lab TUI Application.

Main entry point for the Terminal User Interface.
"""

from textual.app import App
from textual.widgets import Header
from textual.binding import Binding

from .screens import DashboardScreen, WorkersScreen, LogsScreen
from .theme import ColorTheme


class HarnessLabTUI(App):
    """Harness Lab Terminal User Interface.
    
    Provides visual management for:
    - Control Plane: Service status, Worker management, Task queue
    - Worker: Local status, Task execution, Logs
    
    Usage:
        hlab tui control [--port 4600]
        hlab tui worker [--control-plane-url URL]
    
    Screens:
        - DashboardScreen: Main view with all panels
        - WorkersScreen: Worker details
        - LogsScreen: Full-screen log viewer
    """
    
    CSS_PATH = None  # Using inline CSS for now
    
    BINDINGS = [
        Binding("ctrl+h", "show_help", "Help", show=True),
        Binding("ctrl+l", "push_screen('logs')", "Logs", show=False),
        Binding("escape", "quit", "Exit", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]
    
    SCREENS = {
        "dashboard": DashboardScreen,
        "workers": WorkersScreen,
        "logs": LogsScreen,
    }
    
    def __init__(
        self,
        mode: str = "control",
        theme: ColorTheme = None,
        api_url: str = "http://localhost:4600",
        **kwargs
    ):
        """
        Initialize TUI application.
        
        Args:
            mode: TUI mode ('control' or 'worker')
            theme: Color theme (default: dark)
            api_url: Control plane API URL
        """
        super().__init__(**kwargs)
        self.mode = mode
        self.theme = theme or ColorTheme.dark()
        self.api_url = api_url
    
    def on_mount(self) -> None:
        """Mount initial screen."""
        # Push dashboard as initial screen
        self.push_screen(DashboardScreen(self.theme, self.api_url))
    
    def action_show_help(self) -> None:
        """Show help overlay."""
        # TODO: Implement help overlay
        self.bell()
    
    def get_css_variables(self) -> dict:
        """Get CSS variables from theme."""
        return {
            "primary": self.theme.heading,
            "secondary": self.theme.emphasis,
            "accent": self.theme.strong,
            "success": self.theme.success,
            "warning": self.theme.warning,
            "error": self.theme.error,
            "background": "black",
            "surface": "#1e1e1e",
        }