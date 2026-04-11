"""Worker module - runtime_client for remote workers.

The worker lifecycle management (register, heartbeat, drain, resume) has been
moved to fleet/worker_registry.py. This module now only exports the client-side
runtime components for remote worker execution.
"""

from .runtime_client import WorkerRuntimeClient, WorkerExecutionLoop

__all__ = ["WorkerRuntimeClient", "WorkerExecutionLoop"]
