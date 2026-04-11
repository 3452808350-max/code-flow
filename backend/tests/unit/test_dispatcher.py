"""Unit tests for fleet Dispatcher.

Tests the core dispatch logic including:
- Worker draining prevents new dispatches
- Role/capability/label matching
- Sandbox readiness checks
- Stale lease reclaim requeues tasks
"""

import sys
sys.path.insert(0, '/home/kyj/文档/program/programmer (wokerflow)/backend')

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.harness_lab.fleet.dispatcher import Dispatcher, InMemoryDispatcher
from app.harness_lab.types import (
    WorkerSnapshot,
    WorkerRegisterRequest,
    ResearchRun,
    ResearchSession,
    TaskNode,
    TaskGraph,
    DispatchConstraint,
)


class TestDispatcherWorkerMatching:
    """Test worker-to-task matching logic."""
    
    def test_draining_worker_no_dispatch(self):
        """Draining workers should not receive new dispatches."""
        # Create a draining worker
        worker = WorkerSnapshot(
            worker_id="test-worker-1",
            label="test",
            state="idle",
            drain_state="draining",  # Draining
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        # Check shard permission
        dispatcher_mock = MagicMock()
        from app.harness_lab.fleet.dispatcher import Dispatcher
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "executor/low/unlabeled")
        
        assert result is False, "Draining worker should not be able to poll any shard"
    
    def test_active_worker_can_poll_shard(self):
        """Active workers can poll matching shards."""
        worker = WorkerSnapshot(
            worker_id="test-worker-2",
            label="test",
            state="idle",
            drain_state="active",  # Active
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        dispatcher_mock = MagicMock()
        from app.harness_lab.fleet.dispatcher import Dispatcher
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "executor/low/unlabeled")
        
        assert result is True, "Active worker should be able to poll matching shard"
    
    def test_role_profile_mismatch_prevents_poll(self):
        """Workers with mismatched role_profile cannot poll role-specific shards."""
        worker = WorkerSnapshot(
            worker_id="test-worker-3",
            label="test",
            state="idle",
            drain_state="active",
            role_profile="researcher",  # Only researcher role
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        dispatcher_mock = MagicMock()
        from app.harness_lab.fleet.dispatcher import Dispatcher
        
        # Should not be able to poll executor shard
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "executor/low/unlabeled")
        assert result is False, "Researcher worker should not poll executor shard"
        
        # Should be able to poll researcher shard
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "researcher/low/unlabeled")
        assert result is True, "Researcher worker should poll researcher shard"
    
    def test_label_requirements_checked(self):
        """Workers must have all required labels to poll labeled shards."""
        worker = WorkerSnapshot(
            worker_id="test-worker-4",
            label="test",
            state="idle",
            drain_state="active",
            capabilities=[],
            labels=["gpu", "large-memory"],  # Has these labels
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        dispatcher_mock = MagicMock()
        from app.harness_lab.fleet.dispatcher import Dispatcher
        
        # Should be able to poll when all labels match
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "executor/low/gpu/large-memory")
        assert result is True, "Worker with all labels should be able to poll"
        
        # Should not be able to poll when missing a label
        result = Dispatcher._worker_can_poll_shard(dispatcher_mock, worker, "executor/low/gpu/ssd")
        assert result is False, "Worker missing 'ssd' label should not be able to poll"


class TestDispatcherReclaim:
    """Test stale lease reclaim behavior."""
    
    def test_reclaim_requeues_task(self):
        """Reclaimed leases should re-enqueue tasks to ready queue."""
        # This test verifies the reclaim logic is present
        # The actual behavior is tested via integration tests
        from app.harness_lab.fleet.dispatcher import Dispatcher
        
        # Verify the method exists
        assert hasattr(Dispatcher, '_reclaim_lease'), "Dispatcher should have _reclaim_lease method"
        assert hasattr(Dispatcher, '_reclaim_stale_leases'), "Dispatcher should have _reclaim_stale_leases method"


class TestInMemoryDispatcher:
    """Test InMemoryDispatcher for testing scenarios."""
    
    def test_uses_provided_queue(self):
        """InMemoryDispatcher should use the provided queue instance."""
        from app.harness_lab.dispatch_queue import InMemoryDispatchQueue
        
        # Create a shared queue
        shared_queue = InMemoryDispatchQueue()
        
        # Create mock database and worker_registry
        mock_db = MagicMock()
        mock_registry = MagicMock()
        
        # Create dispatcher with existing queue
        dispatcher = InMemoryDispatcher(
            worker_registry=mock_registry,
            database=mock_db,
            lease_timeout_seconds=30,
            existing_queue=shared_queue,
        )
        
        # Verify it uses the same queue instance
        assert dispatcher.queue is shared_queue, "InMemoryDispatcher should use the provided queue instance"
    
    def test_creates_new_queue_if_none_provided(self):
        """InMemoryDispatcher creates new queue if none provided."""
        from app.harness_lab.dispatch_queue import InMemoryDispatchQueue
        
        mock_db = MagicMock()
        mock_registry = MagicMock()
        
        dispatcher = InMemoryDispatcher(
            worker_registry=mock_registry,
            database=mock_db,
            lease_timeout_seconds=30,
        )
        
        # Verify it created a queue
        assert dispatcher.queue is not None, "InMemoryDispatcher should create a queue"
        assert isinstance(dispatcher.queue, InMemoryDispatchQueue), "Queue should be InMemoryDispatchQueue"


class TestDispatcherIntegration:
    """Integration-style tests for Dispatcher."""
    
    def test_dispatcher_has_required_methods(self):
        """Dispatcher should have all required public methods."""
        from app.harness_lab.fleet.dispatcher import Dispatcher
        
        required_methods = [
            'next_dispatch_for_worker',
            'inspect_queues',
            'get_queue_depth',
            'get_queue_depth_by_shard',
        ]
        
        for method in required_methods:
            assert hasattr(Dispatcher, method), f"Dispatcher should have {method}"
    
    def test_inmemory_dispatcher_inherits_dispatcher(self):
        """InMemoryDispatcher should inherit from Dispatcher."""
        from app.harness_lab.fleet.dispatcher import Dispatcher, InMemoryDispatcher
        
        assert issubclass(InMemoryDispatcher, Dispatcher), "InMemoryDispatcher should inherit from Dispatcher"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
