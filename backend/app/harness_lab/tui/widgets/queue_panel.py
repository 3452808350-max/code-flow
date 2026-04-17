"""
Queue status panel for Harness Lab TUI.

Shows queue depth by shard and overall queue health.
"""

from typing import Dict, List

from textual.widgets import Static
from textual.containers import Vertical, Horizontal
from textual.app import ComposeResult
from rich.text import Text

from ..theme import ColorTheme


class QueueShardRow(Static):
    """Single queue shard status row.
    
    Displays shard name, queue depth, and sample task IDs.
    
    Args:
        shard: Shard name (e.g., "executor/low/unlabeled")
        depth: Queue depth (number of pending tasks)
        sample_tasks: List of sample task IDs
        theme: Color theme instance
    """
    
    def __init__(
        self,
        shard: str = "",
        depth: int = 0,
        sample_tasks: List[str] = None,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.shard_name = shard
        self.queue_depth = depth
        self.sample_tasks = sample_tasks or []
        self.theme = theme or ColorTheme.dark()
    
    @staticmethod
    def _depth_icon(depth: int) -> str:
        """Get status icon based on queue depth.
        
        Args:
            depth: Queue depth
            
        Returns:
            Icon string: 🟢 (normal <5), 🟡 (busy 5-20), 🔴 (congested >20)
        """
        if depth < 5:
            return "🟢"  # Normal
        elif depth <= 20:
            return "🟡"  # Busy
        else:
            return "🔴"  # Congested
    
    def _depth_color(self) -> str:
        """Get color based on queue depth.
        
        Args:
            depth: Queue depth
            
        Returns:
            Color string for Rich Text styling
        """
        if self.queue_depth < 5:
            return self.theme.success
        elif self.queue_depth <= 20:
            return self.theme.warning
        else:
            return self.theme.error
    
    def update_status(
        self,
        shard: str = None,
        depth: int = None,
        sample_tasks: List[str] = None
    ) -> None:
        """Update shard status.
        
        Args:
            shard: New shard name
            depth: New queue depth
            sample_tasks: New sample task IDs
        """
        if shard is not None:
            self.shard_name = shard
        if depth is not None:
            self.queue_depth = depth
        if sample_tasks is not None:
            self.sample_tasks = sample_tasks
        self.refresh()
    
    def render(self) -> Text:
        """Render shard status row.
        
        Returns:
            Rich Text object with formatted shard status
        """
        icon = self._depth_icon(self.queue_depth)
        color = self._depth_color()
        
        # Format: "🟢 executor/low/unlabeled [3] T-42, T-43"
        parts = [f"{icon} {self.shard_name}"]
        
        # Add depth in brackets
        parts.append(f" [{self.queue_depth}]")
        
        # Add sample tasks if available (show up to 3)
        if self.sample_tasks:
            sample_display = self.sample_tasks[:3]
            task_str = ", ".join(f"T-{t}" if not t.startswith("T-") else t 
                                  for t in sample_display)
            if len(self.sample_tasks) > 3:
                task_str += f" +{len(self.sample_tasks) - 3} more"
            parts.append(f" {task_str}")
        
        text = Text("".join(parts), style=color)
        return text


class QueueSummary(Static):
    """Queue summary statistics widget.
    
    Shows overall queue metrics:
    - Total queue depth
    - Active leases
    - Stale leases (for reclaim rate calculation)
    
    Args:
        theme: Color theme instance
    """
    
    DEFAULT_CSS = """
    QueueSummary {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin-top: 1;
    }
    """
    
    def __init__(
        self,
        theme: ColorTheme = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.theme = theme or ColorTheme.dark()
        self.total_depth = 0
        self.active_leases = 0
        self.stale_leases = 0
        self.reclaim_rate = 0.0
    
    def update_summary(self, health: Dict) -> None:
        """Update summary from health data.
        
        Args:
            health: Health dict with keys:
                - ready_queue_depth: Total queue depth
                - active_leases: Number of active leases
                - stale_leases: Number of stale leases
        """
        self.total_depth = health.get("ready_queue_depth", 0)
        self.active_leases = health.get("active_leases", 0)
        self.stale_leases = health.get("stale_leases", 0)
        
        # Calculate reclaim rate
        total_leases = self.active_leases + self.stale_leases
        if total_leases > 0:
            self.reclaim_rate = self.stale_leases / total_leases
        
        self.refresh()
    
    def render(self) -> Text:
        """Render summary statistics.
        
        Returns:
            Rich Text object with formatted summary
        """
        lines = []
        
        # Total depth
        depth_icon = QueueShardRow._depth_icon(self.total_depth)
        depth_color = self.theme.active
        lines.append(Text(f"{depth_icon} Total Depth: {self.total_depth}", style=depth_color))
        
        # Active leases
        lease_color = self.theme.success if self.active_leases > 0 else self.theme.idle
        lines.append(Text(f"   Active Leases: {self.active_leases}", style=lease_color))
        
        # Stale leases and reclaim rate
        stale_color = self.theme.warning if self.stale_leases > 0 else self.theme.idle
        stale_text = f"   Stale Leases: {self.stale_leases}"
        if self.reclaim_rate > 0:
            stale_text += f" (reclaim: {self.reclaim_rate:.1%})"
        lines.append(Text(stale_text, style=stale_color))
        
        # Combine lines
        result = Text()
        for i, line in enumerate(lines):
            if i > 0:
                result.append("\n")
            result.append(line)
        
        return result


class QueuePanel(Vertical):
    """Queue status panel container.
    
    Displays queue depth by shard and overall metrics.
    
    Contains:
    - QueueShardRow widgets for each shard
    - QueueSummary for overall statistics
    
    Args:
        theme: Color theme instance
    """
    
    DEFAULT_CSS = """
    QueuePanel {
        width: 30;
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
        self._shard_rows: Dict[str, QueueShardRow] = {}
        self._summary: QueueSummary = None
    
    def compose(self) -> ComposeResult:
        """Compose queue panel widgets."""
        # Placeholder for shard rows (added dynamically)
        self._summary = QueueSummary(theme=self.theme, id="queue-summary")
        yield self._summary
    
    def on_mount(self) -> None:
        """Set border title on mount."""
        self.border_title = "Queues"
    
    def update_queues(self, shards: List[Dict]) -> None:
        """Update queue status from shard data.
        
        Args:
            shards: List of QueueShardStatus dicts with keys:
                - shard: Shard name
                - depth: Queue depth
                - sample_tasks: List of sample task dicts
        """
        # Get current shard names
        current_shards = set(self._shard_rows.keys())
        new_shards = {s.get("shard", s.get("shard_name", "")) for s in shards}
        
        # Remove stale shard rows
        for shard_name in current_shards - new_shards:
            row = self._shard_rows.pop(shard_name)
            row.remove()
        
        # Update or add shard rows
        for i, shard_data in enumerate(shards):
            shard_name = shard_data.get("shard", shard_data.get("shard_name", f"shard-{i}"))
            depth = shard_data.get("depth", 0)
            
            # Extract task IDs from sample_tasks
            sample_tasks = shard_data.get("sample_tasks", [])
            if isinstance(sample_tasks, list):
                # Handle both string IDs and dict with task_id key
                task_ids = []
                for task in sample_tasks[:3]:
                    if isinstance(task, dict):
                        task_ids.append(task.get("task_id", task.get("id", str(task))))
                    else:
                        task_ids.append(str(task))
                sample_tasks = task_ids
            
            if shard_name in self._shard_rows:
                # Update existing row
                self._shard_rows[shard_name].update_status(
                    shard=shard_name,
                    depth=depth,
                    sample_tasks=sample_tasks
                )
            else:
                # Create new row (insert before summary)
                row = QueueShardRow(
                    shard=shard_name,
                    depth=depth,
                    sample_tasks=sample_tasks,
                    theme=self.theme,
                    id=f"shard-{shard_name.replace('/', '-')}"
                )
                self._shard_rows[shard_name] = row
                # Mount before summary
                self.mount(row, before=self._summary)
    
    def update_summary(self, health: Dict) -> None:
        """Update summary statistics from health data.
        
        Args:
            health: Health dict with ready_queue_depth, active_leases, stale_leases
        """
        if self._summary:
            self._summary.update_summary(health)
    
    def clear_queues(self) -> None:
        """Clear all queue data."""
        for row in list(self._shard_rows.values()):
            row.remove()
        self._shard_rows.clear()