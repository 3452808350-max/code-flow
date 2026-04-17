"""
Service status panel for Control Plane TUI.

Shows status of PostgreSQL, Redis, Docker, and API services.
"""

from textual.widgets import Static
from textual.containers import Vertical
from textual.app import ComposeResult
from rich.text import Text
from rich.panel import Panel

from ..theme import ColorTheme


class ServiceStatus(Static):
    """Single service status indicator.
    
    Args:
        name: Service name (e.g., "PostgreSQL 16")
        status: Service status (running, stopped, error)
        theme: Color theme instance
    """
    
    def __init__(
        self, 
        name: str, 
        status: str = "unknown",
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.service_name = name
        self.service_status = status
        self.theme = theme or ColorTheme.dark()
    
    def update_status(self, status: str) -> None:
        """Update service status."""
        self.service_status = status
        self.refresh()
    
    def render(self) -> Text:
        """Render service status line."""
        # Status icon based on status
        icons = {
            "running": "🟢",
            "stopped": "⚫",
            "error": "🔴",
            "warning": "🟡",
            "unknown": "⚪",
        }
        icon = icons.get(self.service_status.lower(), "⚪")
        
        # Color based on status
        color = self.theme.status_color(self.service_status)
        
        return Text(f"{icon} {self.service_name}", style=color)


class ServicePanel(Vertical):
    """Panel showing all system service statuses.
    
    Contains:
    - PostgreSQL status
    - Redis status  
    - Docker status
    - API status
    """
    
    DEFAULT_CSS = """
    ServicePanel {
        width: 25;
        height: auto;
        padding: 1;
        border: solid $primary;
        border-title-align: left;
    }
    """
    
    def __init__(
        self,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()
        self.services = {
            "PostgreSQL 16": ServiceStatus("PostgreSQL 16", "unknown", self.theme, id="postgres-status"),
            "Redis 7": ServiceStatus("Redis 7", "unknown", self.theme, id="redis-status"),
            "Docker CE": ServiceStatus("Docker CE", "unknown", self.theme, id="docker-status"),
            "API": ServiceStatus("API :4600", "unknown", self.theme, id="api-status"),
        }
    
    def compose(self) -> ComposeResult:
        """Compose service status widgets."""
        for service in self.services.values():
            yield service
    
    def on_mount(self) -> None:
        """Set border title on mount."""
        self.border_title = "Services"
    
    def update_service(self, name: str, status: str) -> None:
        """Update a specific service status."""
        if name in self.services:
            self.services[name].update_status(status)
    
    def update_all(self, statuses: dict[str, str]) -> None:
        """Update all service statuses."""
        for name, status in statuses.items():
            self.update_service(name, status)