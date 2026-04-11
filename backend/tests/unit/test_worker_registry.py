"""Unit tests for fleet WorkerRegistry.

Tests the worker lifecycle management including:
- Worker state derivation
- Drain/resume semantics
- Offline detection
- Worker acquisition/release
"""

import sys
sys.path.insert(0, '/home/kyj/文档/program/programmer (wokerflow)/backend')

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.harness_lab.fleet.worker_registry import WorkerRegistry
from app.harness_lab.types import (
    WorkerSnapshot,
    WorkerRegisterRequest,
    WorkerHeartbeatRequest,
)


class TestWorkerStateDerivation:
    """Test worker state derivation logic."""
    
    def test_idle_worker_with_lease_gets_leased_state(self):
        """Worker with active lease should be 'leased' or 'executing'."""
        from app.harness_lab.types import WorkerLease
        
        # Create a mock database that returns a lease
        mock_db = MagicMock()
        mock_db.get_lease.return_value = WorkerLease(
            lease_id="lease-1",
            worker_id="worker-1",
            run_id="run-1",
            task_node_id="node-1",
            attempt_id="attempt-1",
            status="leased",  # Active lease
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            expires_at=(datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
        )
        
        registry = WorkerRegistry(database=mock_db)
        
        # Create worker with current_lease_id
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="idle",  # Will be overridden
            drain_state="active",
            capabilities=[],
            labels=[],
            current_lease_id="lease-1",  # Has lease
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        derived = registry._derive_state(worker)
        
        # Should be 'leased' because lease status is 'leased'
        assert derived.state == "leased", f"Worker with lease should be 'leased', got {derived.state}"
    
    def test_stale_heartbeat_marked_offline(self):
        """Worker with stale heartbeat should be marked offline."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        # Create worker with stale heartbeat (more than 90 seconds ago)
        stale_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="idle",
            drain_state="active",
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=stale_time,  # Stale
            lease_count=0,
            version="v1",
            created_at=stale_time,
            updated_at=stale_time,
        )
        
        derived = registry._derive_state(worker)
        
        assert derived.state == "offline", f"Worker with stale heartbeat should be 'offline', got {derived.state}"
    
    def test_draining_worker_stays_draining(self):
        """Worker in draining state should stay draining when idle."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        worker = WorkerSnapshot(
            worker_id="worker-1",
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
        
        derived = registry._derive_state(worker)
        
        assert derived.state == "draining", f"Draining worker should be 'draining', got {derived.state}"
    
    def test_unhealthy_worker_with_error(self):
        """Worker with last_error should be marked unhealthy."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="idle",
            drain_state="active",
            capabilities=[],
            labels=[],
            last_error="Connection failed",  # Has error
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        derived = registry._derive_state(worker)
        
        assert derived.state == "unhealthy", f"Worker with error should be 'unhealthy', got {derived.state}"
    
    def test_healthy_idle_worker(self):
        """Healthy idle worker should stay idle."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="idle",
            drain_state="active",
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=datetime.now(timezone.utc).isoformat(),  # Recent
            lease_count=0,
            version="v1",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        
        derived = registry._derive_state(worker)
        
        assert derived.state == "idle", f"Healthy worker should be 'idle', got {derived.state}"


class TestWorkerDrain:
    """Test worker drain/resume semantics."""
    
    def test_drain_worker_sets_drain_state(self):
        """drain_worker should set drain_state to 'draining'."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        # Create worker that will be returned by get_worker
        now = datetime.now(timezone.utc).isoformat()
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="idle",
            drain_state="active",
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=now,
            lease_count=0,
            version="v1",
            created_at=now,
            updated_at=now,
        )
        
        mock_db.fetchone.return_value = {
            "payload_json": worker.model_dump_json()
        }
        
        result = registry.drain_worker("worker-1", reason="maintenance")
        
        assert result.drain_state == "draining", "Worker should be in draining state"
        assert result.state == "draining", "Idle draining worker should have state 'draining'"
    
    def test_resume_worker_sets_active_state(self):
        """resume_worker should set drain_state to 'active'."""
        mock_db = MagicMock()
        registry = WorkerRegistry(database=mock_db)
        
        now = datetime.now(timezone.utc).isoformat()
        worker = WorkerSnapshot(
            worker_id="worker-1",
            label="test",
            state="draining",
            drain_state="draining",  # Currently draining
            capabilities=[],
            labels=[],
            execution_mode="remote_http",
            heartbeat_at=now,
            lease_count=0,
            version="v1",
            created_at=now,
            updated_at=now,
        )
        
        mock_db.fetchone.return_value = {
            "payload_json": worker.model_dump_json()
        }
        
        result = registry.resume_worker("worker-1")
        
        assert result.drain_state == "active", "Worker should be in active state"
        assert result.state == "idle", "Resumed worker should be idle"


class TestWorkerRegistryInterface:
    """Test WorkerRegistry has required interface."""
    
    def test_has_required_methods(self):
        """WorkerRegistry should have all required public methods."""
        required_methods = [
            'register_worker',
            'get_worker',
            'list_workers',
            'heartbeat',
            'drain_worker',
            'resume_worker',
            'acquire_worker',
            'release_worker',
            'ensure_default_worker',
        ]
        
        for method in required_methods:
            assert hasattr(WorkerRegistry, method), f"WorkerRegistry should have {method}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
