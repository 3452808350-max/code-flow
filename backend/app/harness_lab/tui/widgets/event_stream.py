"""
Event stream log panel for real-time events.

Shows: Task dispatches, Worker heartbeats, Lease expirations, etc.
"""

from textual.widgets import Static
from textual.containers import VerticalScroll
from textual.message import Message
from rich.text import Text

from ..theme import ColorTheme


class EventMessage(Static):
    """Single event log line.
    
    Args:
        timestamp: Event timestamp
        event_type: Event type (DISPATCH, HEARTBEAT, LEASE, ERROR, etc.)
        message: Event message
        theme: Color theme
    """
    
    def __init__(
        self,
        timestamp: str,
        event_type: str,
        message: str,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.timestamp = timestamp
        self.event_type = event_type
        self.event_message = message
        self.theme = theme or ColorTheme.dark()
    
    def render(self) -> Text:
        """Render event line."""
        # Color based on event type
        type_colors = {
            "DISPATCH": self.theme.active,
            "HEARTBEAT": self.theme.idle,
            "LEASE": self.theme.warning,
            "ERROR": self.theme.error,
            "COMPLETE": self.theme.success,
            "FAIL": self.theme.error,
        }
        color = type_colors.get(self.event_type, self.theme.idle)
        
        return Text.assemble(
            (f"{self.timestamp} ", "grey62"),
            (f"[{self.event_type}] ", color),
            (self.event_message, ""),
        )


class EventStream(VerticalScroll):
    """Scrollable event log stream.
    
    Contains:
    - List of EventMessage widgets
    - Auto-scroll to latest
    """
    
    DEFAULT_CSS = """
    EventStream {
        width: auto;
        height: 10;
        padding: 1;
        border: solid $primary;
        border-title-align: left;
    }
    """
    
    MAX_EVENTS = 100  # Maximum events to keep
    
    def __init__(
        self,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()
        self._event_count = 0
    
    def on_mount(self) -> None:
        """Set border title on mount."""
        self.border_title = "Event Stream"
    
    def add_event(self, timestamp: str, event_type: str, message: str) -> None:
        """Add an event to the stream."""
        event = EventMessage(timestamp, event_type, message, self.theme)
        
        # Add to top (newest first)
        self.mount(event, at=0)
        self._event_count += 1
        
        # Remove old events if exceeding max
        if self._event_count > self.MAX_EVENTS:
            # Remove oldest (last child)
            children = list(self.children)
            if children:
                children[-1].remove()
                self._event_count -= 1
    
    def clear_events(self) -> None:
        """Clear all events."""
        for child in list(self.children):
            child.remove()
        self._event_count = 0