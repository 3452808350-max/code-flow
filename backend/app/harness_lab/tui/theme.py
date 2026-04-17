"""
Color theme for Harness Lab TUI.

Translated from claw-code rusty-claude-cli/src/render.rs ColorTheme.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ColorTheme:
    """Color theme configuration for TUI rendering.
    
    Attributes:
        heading: Color for headings and titles
        emphasis: Color for emphasized text (italic)
        strong: Color for strong text (bold)
        inline_code: Color for inline code
        link: Color for links and URLs
        quote: Color for quotes
        table_border: Color for table borders
        code_block_border: Color for code block borders
        spinner_active: Color for active spinner
        spinner_done: Color for completed spinner
        spinner_failed: Color for failed spinner
        success: Color for success indicators
        warning: Color for warning indicators
        error: Color for error indicators
        idle: Color for idle states
        active: Color for active states
    """
    
    # Text colors (from claw-code)
    heading: str = "cyan"
    emphasis: str = "magenta"
    strong: str = "yellow"
    inline_code: str = "green"
    link: str = "blue"
    quote: str = "grey62"
    table_border: str = "dark_cyan"
    code_block_border: str = "grey62"
    
    # Spinner colors (from claw-code)
    spinner_active: str = "blue"
    spinner_done: str = "green"
    spinner_failed: str = "red"
    
    # Status colors (Harness Lab specific)
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    idle: str = "grey62"
    active: str = "cyan"
    
    @classmethod
    def dark(cls) -> "ColorTheme":
        """Dark theme (default)."""
        return cls()
    
    @classmethod
    def light(cls) -> "ColorTheme":
        """Light theme."""
        return cls(
            heading="dark_cyan",
            emphasis="dark_magenta",
            strong="dark_yellow",
            inline_code="dark_green",
            link="dark_blue",
            quote="grey37",
            table_border="cyan",
            code_block_border="grey37",
            spinner_active="dark_blue",
            spinner_done="dark_green",
            spinner_failed="dark_red",
            success="dark_green",
            warning="dark_yellow",
            error="dark_red",
            idle="grey37",
            active="dark_cyan",
        )
    
    def status_color(self, status: str) -> str:
        """Get color for a given status string.
        
        Args:
            status: Status string (running, idle, draining, offline, error, etc.)
            
        Returns:
            Color string for the status
        """
        status_colors = {
            "running": self.active,
            "executing": self.active,
            "idle": self.idle,
            "draining": self.warning,
            "offline": self.error,
            "error": self.error,
            "success": self.success,
            "failed": self.error,
            "completed": self.spinner_done,
            "pending": self.idle,
        }
        return status_colors.get(status.lower(), self.idle)