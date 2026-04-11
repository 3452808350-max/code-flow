"""Fleet module: unified worker fleet coordination.

This module centralizes lease management, worker registry, and dispatch logic.

Architecture:
    - WorkerRegistry: Worker lifecycle management (register, heartbeat, drain, resume)
    - Dispatcher: Task dispatch logic (queue shard selection, worker matching, dispatch creation)
    - LeaseManager: Lease lifecycle management (poll, heartbeat, complete, fail, release)
    - Protocols: Clean interfaces between Runtime and Fleet layers
    - Adapters: RuntimeService implementations of fleet protocols

Reliability Semantics:
    - Draining workers don't receive new dispatches
    - Stale lease reclaim requeues tasks automatically
    - Duplicate/late callbacks record ignored events without state changes
    - Restart recovery via rebuild_dispatch_state()
"""

from .worker_registry import WorkerRegistry
from .dispatcher import Dispatcher, InMemoryDispatcher
from .lease_manager import LeaseManager
from .protocols import (
    RunCoordinationProtocol,
    DispatchConstraintProtocol,
    DispatchContextProtocol,
    TaskExecutionProtocol,
    UtilityProtocol,
)
from .adapters import (
    RuntimeCoordinationAdapter,
    RuntimeConstraintAdapter,
    RuntimeDispatchContextAdapter,
    RuntimeTaskExecutionAdapter,
    RuntimeUtilityAdapter,
    create_protocol_adapters,
)

__all__ = [
    # Core classes
    "WorkerRegistry",
    "Dispatcher",
    "InMemoryDispatcher",
    "LeaseManager",
    # Protocols
    "RunCoordinationProtocol",
    "DispatchConstraintProtocol",
    "DispatchContextProtocol",
    "TaskExecutionProtocol",
    "UtilityProtocol",
    # Adapters
    "RuntimeCoordinationAdapter",
    "RuntimeConstraintAdapter",
    "RuntimeDispatchContextAdapter",
    "RuntimeTaskExecutionAdapter",
    "RuntimeUtilityAdapter",
    "create_protocol_adapters",
]
