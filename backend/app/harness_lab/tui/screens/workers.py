"""
Workers screen - Detailed worker management view.

Shows worker details and allows drain/resume operations.
"""

from textual.screen import Screen
from textual.widgets import Header, Static
from textual.containers import Container, VerticalScroll
from textual.app import ComposeResult

from ..theme import ColorTheme
from ..widgets import StatusBar


class WorkersScreen(Screen):
    """Worker details screen.
    
    Shows detailed information about a selected worker.
    """
    
    DEFAULT_CSS = """
    WorkersScreen {
        layout: vertical;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "Back"),
        ("d", "drain", "Drain"),
        ("r", "resume", "Resume"),
    ]
    
    def __init__(
        self,
        worker_id: str = None,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.worker_id = worker_id
        self.theme = theme or ColorTheme.dark()
    
    def compose(self) -> ComposeResult:
        """Compose workers screen."""
        yield Header()
        
        with Container():
            yield Static(f"Worker: {self.worker_id or 'Not selected'}", id="worker-title")
            
            with VerticalScroll():
                yield Static("Worker details will be shown here...", id="worker-details")
        
        yield StatusBar(self.theme)
    
    def on_mount(self) -> None:
        """Set title on mount."""
        header = self.query_one(Header)
        header.title = f"Worker: {self.worker_id}"
    
    def action_back(self) -> None:
        """Go back to dashboard."""
        self.app.pop_screen()
    
    def action_drain(self) -> None:
        """Drain this worker."""
        # TODO: Implement drain via API
        pass
    
    def action_resume(self) -> None:
        """Resume this worker."""
        # TODO: Implement resume via API
        pass