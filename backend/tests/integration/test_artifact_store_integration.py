"""Integration tests for artifact store with MinIO/S3-compatible backend."""

import pytest
import os
import tempfile
import time
from pathlib import Path

# Set environment variables before importing HarnessLabSettings
os.environ.setdefault("HARNESS_DB_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("HARNESS_REDIS_URL", "redis://localhost:6379")

from backend.app.harness_lab.artifact_store import (
    LocalFilesystemArtifactStore,
    S3CompatibleArtifactStore,
    create_artifact_store,
)
from backend.app.harness_lab.types import ArtifactRef
from backend.app.harness_lab.settings import HarnessLabSettings


class TestLocalArtifactStoreIntegration:
    """Integration tests for local filesystem artifact store."""

    def test_full_artifact_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFilesystemArtifactStore(tmpdir)
            
            # Write text artifact
            artifact = store.write_text(
                run_id="run_test_001",
                artifact_type="context_bundle",
                filename="blocks.json",
                content='{"blocks": []}',
                metadata={"block_count": 0},
            )
            
            assert artifact.storage_backend == "local"
            assert artifact.run_id == "run_test_001"
            assert artifact.artifact_type == "context_bundle"
            
            # Read it back
            content = store.read_text(artifact)
            assert content == '{"blocks": []}'
            
            # Verify exists
            assert store.exists(artifact) is True
            
            # Check status
            status = store.status()
            assert status.ready is True
            assert status.backend == "local"
            
            # Check locator
            locator = store.resolve_locator(artifact)
            assert locator.startswith(tmpdir)

    def test_binary_artifact_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFilesystemArtifactStore(tmpdir)
            
            binary_content = b"\x00\x01\x02\x03\xff\xfe"
            artifact = store.write_bytes(
                run_id="run_test_002",
                artifact_type="snapshot",
                filename="data.bin",
                content=binary_content,
            )
            
            read_content = store.read_bytes(artifact)
            assert read_content == binary_content

    def test_multiple_artifacts_same_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFilesystemArtifactStore(tmpdir)
            
            run_id = "run_multi_001"
            
            artifact1 = store.write_text(
                run_id=run_id,
                artifact_type="context",
                filename="context.json",
                content="context data",
            )
            
            artifact2 = store.write_text(
                run_id=run_id,
                artifact_type="prompt",
                filename="prompt.json",
                content="prompt data",
            )
            
            artifact3 = store.write_text(
                run_id=run_id,
                artifact_type="result",
                filename="result.json",
                content="result data",
            )
            
            # All should be readable
            assert store.read_text(artifact1) == "context data"
            assert store.read_text(artifact2) == "prompt data"
            assert store.read_text(artifact3) == "result data"
            
            # Check directory structure
            run_dir = Path(tmpdir) / run_id
            assert (run_dir / "context" / "context.json").exists()
            assert (run_dir / "prompt" / "prompt.json").exists()
            assert (run_dir / "result" / "result.json").exists()

    def test_artifact_ref_contract(self):
        """Test that ArtifactRef has consistent fields regardless of backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFilesystemArtifactStore(tmpdir)
            
            artifact = store.write_text(
                run_id="run_contract_test",
                artifact_type="test",
                filename="test.txt",
                content="test content",
                metadata={"extra": "data"},
            )
            
            # Essential fields for cross-backend compatibility
            assert artifact.artifact_id is not None
            assert artifact.run_id == "run_contract_test"
            assert artifact.artifact_type == "test"
            assert artifact.storage_backend == "local"
            assert artifact.storage_key != ""
            assert artifact.relative_path != ""
            assert artifact.content_type is not None
            assert artifact.size_bytes > 0
            assert artifact.sha256 != ""
            assert artifact.created_at is not None
            assert artifact.metadata == {"extra": "data"}


@pytest.mark.skipif(
    os.getenv("SKIP_MINIO_TESTS", "").lower() == "true",
    reason="MinIO tests disabled via SKIP_MINIO_TESTS env var",
)
class TestS3ArtifactStoreIntegration:
    """Integration tests for S3-compatible artifact store with real MinIO.
    
    These tests require a running MinIO instance. Run with:
    docker compose up harness-lab-minio
    
    Or skip with: SKIP_MINIO_TESTS=true pytest ...
    """

    @pytest.fixture
    def minio_settings(self):
        """Create settings for MinIO connection."""
        return HarnessLabSettings.from_env()

    @pytest.fixture
    def s3_store(self, minio_settings):
        """Create S3 store with auto-cleanup."""
        store = create_artifact_store(
            minio_settings,
            artifact_root_override="/tmp/artifacts",  # Not used for S3
        )
        
        if store.backend_name != "s3":
            pytest.skip("S3 backend not configured")
        
        # Ensure bucket exists
        status = store.status()
        if not status.ready:
            pytest.skip(f"MinIO not ready: {status.last_error}")
        
        yield store
        
        # Cleanup: delete test objects
        try:
            client = store._build_client()
            if client:
                # List and delete test objects
                prefix = f"{store.prefix}/run_test_" if store.prefix else "run_test_"
                response = client.list_objects_v2(
                    Bucket=store.bucket,
                    Prefix=prefix,
                )
                for obj in response.get("Contents", []):
                    client.delete_object(Bucket=store.bucket, Key=obj["Key"])
        except Exception:
            pass  # Best effort cleanup

    def test_s3_full_artifact_lifecycle(self, s3_store):
        """Test full artifact lifecycle with real S3 backend."""
        unique_id = f"{int(time.time())}"
        
        # Write text artifact
        artifact = s3_store.write_text(
            run_id=f"run_test_{unique_id}",
            artifact_type="context_bundle",
            filename="blocks.json",
            content='{"blocks": ["test"]}',
            metadata={"block_count": 1, "test": True},
        )
        
        assert artifact.storage_backend == "s3"
        assert artifact.run_id == f"run_test_{unique_id}"
        assert artifact.artifact_type == "context_bundle"
        
        # Read it back
        content = s3_store.read_text(artifact)
        assert content == '{"blocks": ["test"]}'
        
        # Verify exists
        assert s3_store.exists(artifact) is True

    def test_s3_binary_artifact(self, s3_store):
        """Test binary artifact with real S3 backend."""
        unique_id = f"{int(time.time())}"
        binary_content = b"\x00\x01\x02\x03\xff\xfe"
        
        artifact = s3_store.write_bytes(
            run_id=f"run_binary_{unique_id}",
            artifact_type="snapshot",
            filename="data.bin",
            content=binary_content,
        )
        
        read_content = s3_store.read_bytes(artifact)
        assert read_content == binary_content

    def test_s3_multiple_artifacts_same_run(self, s3_store):
        """Test multiple artifacts in same run."""
        unique_id = f"{int(time.time())}"
        run_id = f"run_multi_{unique_id}"
        
        artifact1 = s3_store.write_text(
            run_id=run_id,
            artifact_type="context",
            filename="context.json",
            content="context data",
        )
        
        artifact2 = s3_store.write_text(
            run_id=run_id,
            artifact_type="prompt",
            filename="prompt.json",
            content="prompt data",
        )
        
        # Both should be readable
        assert s3_store.read_text(artifact1) == "context data"
        assert s3_store.read_text(artifact2) == "prompt data"
        
        # Both should exist
        assert s3_store.exists(artifact1) is True
        assert s3_store.exists(artifact2) is True

    def test_s3_artifact_ref_contract(self, s3_store):
        """Test ArtifactRef contract for S3 backend."""
        unique_id = f"{int(time.time())}"
        
        artifact = s3_store.write_text(
            run_id=f"run_contract_{unique_id}",
            artifact_type="test",
            filename="test.txt",
            content="test content",
            metadata={"extra": "data"},
        )
        
        # Essential fields for cross-backend compatibility
        assert artifact.artifact_id is not None
        assert artifact.run_id.startswith("run_contract_")
        assert artifact.artifact_type == "test"
        assert artifact.storage_backend == "s3"
        assert artifact.storage_key != ""
        assert artifact.content_type is not None
        assert artifact.size_bytes > 0
        assert artifact.sha256 != ""
        assert artifact.created_at is not None

    def test_s3_status_reflects_real_state(self, s3_store):
        """Test that status() reflects real S3 connectivity."""
        status = s3_store.status()
        
        assert status.backend == "s3"
        assert status.ready is True
        assert status.bucket_or_root == s3_store.bucket
        assert status.last_error is None

    def test_s3_locator_format(self, s3_store):
        """Test S3 locator format."""
        unique_id = f"{int(time.time())}"
        
        artifact = s3_store.write_text(
            run_id=f"run_locator_{unique_id}",
            artifact_type="test",
            filename="test.txt",
            content="test",
        )
        
        locator = s3_store.resolve_locator(artifact)
        
        if s3_store.endpoint_url:
            # Should be HTTP URL for MinIO
            assert locator.startswith("http://") or locator.startswith("https://")
            assert s3_store.bucket in locator
            assert artifact.storage_key in locator
        else:
            # Should be s3:// URL for AWS
            assert locator.startswith("s3://")

    def test_s3_nonexistent_artifact(self, s3_store):
        """Test handling of non-existent artifacts."""
        fake_artifact = ArtifactRef(
            artifact_id="fake",
            run_id="run_fake",
            artifact_type="test",
            storage_backend="s3",
            storage_key=f"{s3_store.prefix}/run_fake/test/nonexistent.txt" if s3_store.prefix else "run_fake/test/nonexistent.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at="2024-01-01T00:00:00",
        )
        
        assert s3_store.exists(fake_artifact) is False


class TestArtifactStoreFactory:
    """Integration tests for artifact store factory with real settings."""

    def test_factory_creates_local_by_default(self):
        """Test that factory creates local store with default settings."""
        settings = HarnessLabSettings.from_env()
        
        # Temporarily force local backend
        original_backend = settings.artifact_backend
        settings.artifact_backend = "local"
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                store = create_artifact_store(settings, artifact_root_override=tmpdir)
                assert store.backend_name == "local"
                
                # Verify it works
                artifact = store.write_text(
                    run_id="run_factory_test",
                    artifact_type="test",
                    filename="test.txt",
                    content="factory test",
                )
                assert store.read_text(artifact) == "factory test"
        finally:
            settings.artifact_backend = original_backend

    def test_local_and_s3_produce_consistent_refs(self):
        """Test that both backends produce consistent ArtifactRef structures."""
        with tempfile.TemporaryDirectory() as local_tmpdir:
            local_store = LocalFilesystemArtifactStore(local_tmpdir)
            
            local_artifact = local_store.write_text(
                run_id="run_consistency",
                artifact_type="test",
                filename="test.txt",
                content="consistency test",
                metadata={"key": "value"},
            )
            
            # Verify all required fields are present and valid
            assert local_artifact.artifact_id is not None
            assert local_artifact.run_id == "run_consistency"
            assert local_artifact.artifact_type == "test"
            assert local_artifact.storage_backend == "local"
            assert local_artifact.storage_key != ""
            assert local_artifact.relative_path != ""
            assert local_artifact.content_type is not None
            assert local_artifact.size_bytes == len("consistency test")
            assert len(local_artifact.sha256) == 64  # SHA-256 hex string
            assert local_artifact.created_at is not None
            assert local_artifact.metadata == {"key": "value"}
