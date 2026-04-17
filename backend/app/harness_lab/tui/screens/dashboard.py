"""
Dashboard screen - Main control plane TUI view.

Shows:
- Service status panel (left)
- Worker table (center/right)
- Event stream (bottom)
"""

from textual.screen import Screen
from textual.widgets import Header
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from textual.reactive import reactive

from ..widgets import ServicePanel, WorkerTable, StatusBar, EventStream
from ..theme import ColorTheme


class DashboardScreen(Screen):
    """Main dashboard screen for Control Plane TUI.
    
    Layout:
    ┌───────────────────────────────────────┐
    │ Header                                 │
    ├───────────────────────────────────────┤
    │ ┌───────────┐ ┌─────────────────────┐ │
    │ │ Services  │ │ Workers              │ │
    │ │ Panel     │ │ Table                │ │
    │ └───────────┘ └─────────────────────┘ │
    │ ┌─────────────────────────────────────┐│
    │ │ Event Stream                         ││
    │ └─────────────────────────────────────┘│
    ├───────────────────────────────────────┤
    │ Status Bar                             │
    └───────────────────────────────────────┘
    """
    
    DEFAULT_CSS = """
    DashboardScreen {
        layout: vertical;
    }
    
    DashboardScreen > Header {
        height: 1;
    }
    
    DashboardScreen > Container {
        height: auto;
    }
    
    DashboardScreen > Horizontal {
        height: 1fr;
    }
    
    DashboardScreen > EventStream {
        height: 8;
    }
    """
    
    BINDINGS = [
        ("ctrl+h", "show_help", "Help"),
        ("escape", "quit", "Exit"),
        ("d", "drain_worker", "Drain"),
        ("r", "resume_worker", "Resume"),
        ("i", "inspect_worker", "Inspect"),
        ("l", "toggle_logs", "Logs"),
        ("q", "quit", "Quit"),
    ]
    
    # Reactive state for updating display
    workers_count: reactive[int] = reactive(0)
    tasks_count: reactive[int] = reactive(0)
    
    def __init__(
        self,
        theme: ColorTheme = None,
        api_url: str = "http://localhost:4600",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()
        self.api_url = api_url
    
    def compose(self) -> ComposeResult:
        """Compose dashboard layout."""
        yield Header(id="header")
        
        with Container(id="main"):
            with Horizontal(id="top-panels"):
                yield ServicePanel(self.theme, id="service-panel")
                yield WorkerTable(self.theme, id="worker-table")
            
            yield EventStream(self.theme, id="event-stream")
        
        yield StatusBar(self.theme, id="status-bar")
    
    def on_mount(self) -> None:
        """Initialize dashboard on mount."""
        # Set header title
        header = self.query_one("#header", Header)
        header.title = "Harness Lab Control Plane"
        
        # Initialize with demo data
        self._init_demo_data()
        
        # Start polling for updates (every 2 seconds)
        self.set_interval(2.0, self._poll_status)
    
    def _init_demo_data(self) -> None:
        """Initialize with demo/test data."""
        # Service statuses
        services = self.query_one("#service-panel", ServicePanel)
        services.update_all({
            "PostgreSQL 16": "running",
            "Redis 7": "running",
            "Docker CE": "running",
            "API": "running",
        })
        
        # Workers
        workers = self.query_one("#worker-table", WorkerTable)
        workers.add_worker("w-01", "executing", "executor", "T-42", "30s")
        workers.add_worker("w-02", "idle", "general", "-", "-")
        workers.add_worker("w-03", "draining", "reviewer", "T-41", "5s")
        workers.add_worker("w-04", "offline", "planner", "-", "-")
        
        # Events
        events = self.query_one("#event-stream", EventStream)
        events.add_event("22:00:01", "DISPATCH", "T-42 → w-01 (executor)")
        events.add_event("22:00:00", "HEARTBEAT", "w-02 (idle)")
        events.add_event("21:59:55", "LEASE", "w-03 expired")
        
        # Update counters
        self.workers_count = 4
        self.tasks_count = 21
    
    async def _poll_status(self) -> None:
        """Poll control plane API for status updates.
        
        TODO: Implement actual API polling when control plane is running.
        """
        # For now, just add a demo event
        from datetime import datetime
        events = self.query_one("#event-stream", EventStream)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Simulate events
        import random
        event_types = ["HEARTBEAT", "DISPATCH"]
        workers = ["w-01", "w-02", "w-03"]
        worker = random.choice(workers)
        event_type = random.choice(event_types)
        
        if event_type == "HEARTBEAT":
            events.add_event(timestamp, "HEARTBEAT", f"{worker} (idle)")
        else:
            events.add_event(timestamp, "DISPATCH", f"T-{random.randint(50,100)} → {worker}")
    
    def action_show_help(self) -> None:
        """Show help overlay."""
        self.app.push_screen("help")
    
    def action_drain_worker(self) -> None:
        """Drain selected worker."""
        # TODO: Implement worker selection and drain action
        events = self.query_one("#event-stream", EventStream)
        from datetime import datetime
        events.add_event(datetime.now().strftime("%H:%M:%S"), "LEASE", "Drain action (not implemented)")
    
    def action_resume_worker(self) -> None:
        """Resume selected worker."""
        # TODO: Implement worker selection and resume action
        events = self.query_one("#event-stream", EventStream)
        from datetime import datetime
        events.add_event(datetime.now().strftime("%H:%M:%S"), "LEASE", "Resume action (not implemented)")
    
    def action_inspect_worker(self) -> None:
        """Inspect selected worker."""
        # TODO: Implement worker inspection
        pass
    
    def action_toggle_logs(self) -> None:
        """Toggle log visibility."""
        events = self.query_one("#event-stream", EventStream)
        events.toggle_class("hidden")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit()