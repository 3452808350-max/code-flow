"""Unit tests for artifact store backends."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

from backend.app.harness_lab.artifact_store import (
    LocalFilesystemArtifactStore,
    S3CompatibleArtifactStore,
    create_artifact_store,
    _content_type_for,
    _artifact_ref,
)
from backend.app.harness_lab.types import ArtifactRef, ArtifactStoreStatus


class TestContentTypeFor:
    """Test content type detection."""

    def test_explicit_content_type(self):
        assert _content_type_for("test.txt", "application/json", True) == "application/json"

    def test_guess_json(self):
        assert _content_type_for("test.json", None, True) == "application/json"

    def test_guess_html(self):
        assert _content_type_for("test.html", None, True) == "text/html"

    def test_default_text(self):
        # Use a truly unknown extension
        assert _content_type_for("unknown.unknownext", None, True) == "text/plain; charset=utf-8"

    def test_default_binary(self):
        # Use a truly unknown extension
        assert _content_type_for("unknown.unknownext", None, False) == "application/octet-stream"


class TestArtifactRef:
    """Test artifact reference creation."""

    def test_local_backend_sets_relative_path(self):
        ref = _artifact_ref(
            run_id="run_123",
            artifact_type="test",
            storage_backend="local",
            storage_key="run_123/test/file.txt",
            content=b"test content",
            content_type="text/plain",
        )
        assert ref.relative_path == "run_123/test/file.txt"
        assert ref.storage_backend == "local"

    def test_s3_backend_uses_metadata_path(self):
        ref = _artifact_ref(
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="harness-lab/run_123/test/file.txt",
            content=b"test content",
            content_type="text/plain",
            metadata={"relative_path": "test/file.txt"},
        )
        assert ref.relative_path == "test/file.txt"
        assert ref.storage_backend == "s3"

    def test_sha256_computed(self):
        content = b"test content"
        expected_sha256 = "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
        ref = _artifact_ref(
            run_id="run_123",
            artifact_type="test",
            storage_backend="local",
            storage_key="key",
            content=content,
            content_type="text/plain",
        )
        assert ref.sha256 == expected_sha256
        assert ref.size_bytes == len(content)


class TestLocalFilesystemArtifactStore:
    """Test local filesystem artifact store."""

    @pytest.fixture
    def temp_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = LocalFilesystemArtifactStore(tmpdir)
            yield store, tmpdir

    def test_write_and_read_text(self, temp_store):
        store, tmpdir = temp_store
        artifact = store.write_text(
            run_id="run_123",
            artifact_type="context",
            filename="test.txt",
            content="Hello, World!",
        )
        
        assert artifact.artifact_id is not None
        assert artifact.run_id == "run_123"
        assert artifact.artifact_type == "context"
        assert artifact.storage_backend == "local"
        
        # Read it back
        content = store.read_text(artifact)
        assert content == "Hello, World!"

    def test_write_and_read_bytes(self, temp_store):
        store, tmpdir = temp_store
        content = b"\x00\x01\x02\x03"
        artifact = store.write_bytes(
            run_id="run_123",
            artifact_type="binary",
            filename="data.bin",
            content=content,
        )
        
        # Read it back
        read_content = store.read_bytes(artifact)
        assert read_content == content

    def test_exists(self, temp_store):
        store, tmpdir = temp_store
        artifact = store.write_text(
            run_id="run_123",
            artifact_type="test",
            filename="exists.txt",
            content="test",
        )
        
        assert store.exists(artifact) is True
        
        # Non-existent artifact
        fake_artifact = ArtifactRef(
            artifact_id="fake",
            run_id="run_123",
            artifact_type="test",
            storage_backend="local",
            storage_key="run_123/test/nonexistent.txt",
            relative_path="run_123/test/nonexistent.txt",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        assert store.exists(fake_artifact) is False

    def test_resolve_locator(self, temp_store):
        store, tmpdir = temp_store
        artifact = store.write_text(
            run_id="run_123",
            artifact_type="test",
            filename="locator.txt",
            content="test",
        )
        
        locator = store.resolve_locator(artifact)
        assert locator == str(Path(tmpdir) / artifact.storage_key)

    def test_status_ready(self, temp_store):
        store, tmpdir = temp_store
        status = store.status()
        
        assert status.backend == "local"
        assert status.ready is True
        assert status.bucket_or_root == tmpdir
        assert status.last_error is None

    def test_creates_directory_structure(self, temp_store):
        store, tmpdir = temp_store
        artifact = store.write_text(
            run_id="run_nested/deep",
            artifact_type="context/bundle",
            filename="nested.txt",
            content="nested content",
        )
        
        # Directory should exist
        expected_path = Path(tmpdir) / "run_nested/deep/context/bundle"
        assert expected_path.exists()
        
        # Content should be readable
        assert store.read_text(artifact) == "nested content"


class TestS3CompatibleArtifactStore:
    """Test S3-compatible artifact store with mocked client."""

    @pytest.fixture
    def mock_s3_client(self):
        client = Mock()
        return client

    @pytest.fixture
    def s3_store(self, mock_s3_client):
        store = S3CompatibleArtifactStore(
            bucket="test-bucket",
            prefix="test-prefix",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            access_key_id="test-key",
            secret_access_key="test-secret",
            client=mock_s3_client,
        )
        return store, mock_s3_client

    def test_write_text(self, s3_store):
        store, mock_client = s3_store
        
        artifact = store.write_text(
            run_id="run_123",
            artifact_type="context",
            filename="test.txt",
            content="Hello, S3!",
        )
        
        assert artifact.storage_backend == "s3"
        assert artifact.run_id == "run_123"
        assert artifact.artifact_type == "context"
        
        # Verify S3 put_object was called
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test-prefix/run_123/context/test.txt"
        assert call_kwargs["Body"] == b"Hello, S3!"

    def test_write_bytes(self, s3_store):
        store, mock_client = s3_store
        content = b"\x00\x01\x02\x03"
        
        artifact = store.write_bytes(
            run_id="run_123",
            artifact_type="binary",
            filename="data.bin",
            content=content,
        )
        
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Body"] == content

    def test_read_bytes(self, s3_store):
        store, mock_client = s3_store
        
        # Setup mock response
        mock_body = Mock()
        mock_body.read.return_value = b"S3 content"
        mock_client.get_object.return_value = {"Body": mock_body}
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/file.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        content = store.read_bytes(artifact)
        assert content == b"S3 content"
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/run_123/test/file.txt",
        )

    def test_read_text(self, s3_store):
        store, mock_client = s3_store
        
        mock_body = Mock()
        mock_body.read.return_value = b"UTF-8 text"
        mock_client.get_object.return_value = {"Body": mock_body}
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/file.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        content = store.read_text(artifact)
        assert content == "UTF-8 text"

    def test_exists_true(self, s3_store):
        store, mock_client = s3_store
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/file.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        assert store.exists(artifact) is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/run_123/test/file.txt",
        )

    def test_exists_false(self, s3_store):
        store, mock_client = s3_store
        
        # Simulate 404 error
        error_response = {"Error": {"Code": "404"}}
        mock_client.head_object.side_effect = Exception("Not found")
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/missing.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        assert store.exists(artifact) is False

    def test_resolve_locator_with_endpoint(self, s3_store):
        store, mock_client = s3_store
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/file.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        locator = store.resolve_locator(artifact)
        assert locator == "http://localhost:9000/test-bucket/test-prefix/run_123/test/file.txt"

    def test_resolve_locator_without_endpoint(self):
        store = S3CompatibleArtifactStore(
            bucket="test-bucket",
            prefix="test-prefix",
            endpoint_url=None,
            region="us-east-1",
        )
        
        artifact = ArtifactRef(
            artifact_id="test",
            run_id="run_123",
            artifact_type="test",
            storage_backend="s3",
            storage_key="test-prefix/run_123/test/file.txt",
            relative_path="",
            content_type="text/plain",
            size_bytes=0,
            sha256="",
            created_at=datetime.now().isoformat(),
        )
        
        locator = store.resolve_locator(artifact)
        assert locator == "s3://test-bucket/test-prefix/run_123/test/file.txt"

    def test_status_ready(self, s3_store):
        store, mock_client = s3_store
        
        # Mock successful bucket check
        mock_client.list_buckets.return_value = {"Buckets": []}
        mock_client.head_bucket.return_value = {}
        
        status = store.status()
        
        assert status.backend == "s3"
        assert status.ready is True
        assert status.bucket_or_root == "test-bucket"
        assert status.last_error is None

    def test_status_not_ready_no_client(self):
        store = S3CompatibleArtifactStore(
            bucket="test-bucket",
            prefix="test-prefix",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            client=None,
        )
        
        # Simulate boto3 not being installed by making _build_client return None
        store._client = None
        store._last_error = "boto3 is not installed"
        
        status = store.status()
        
        assert status.backend == "s3"
        assert status.ready is False
        assert "boto3" in status.last_error or status.last_error is None

    def test_status_bucket_not_accessible(self, s3_store):
        store, mock_client = s3_store
        
        # Mock bucket access failure
        mock_client.list_buckets.side_effect = Exception("Connection refused")
        
        status = store.status()
        
        assert status.backend == "s3"
        assert status.ready is False
        assert "Connection refused" in status.last_error

    def test_key_generation_with_prefix(self, s3_store):
        store, mock_client = s3_store
        store.write_text(
            run_id="run_123",
            artifact_type="context",
            filename="test.txt",
            content="test",
        )
        
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Key"] == "test-prefix/run_123/context/test.txt"

    def test_key_generation_without_prefix(self):
        store = S3CompatibleArtifactStore(
            bucket="test-bucket",
            prefix="",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
            client=Mock(),
        )
        
        store.write_text(
            run_id="run_123",
            artifact_type="context",
            filename="test.txt",
            content="test",
        )
        
        call_kwargs = store._client.put_object.call_args[1]
        assert call_kwargs["Key"] == "run_123/context/test.txt"


class TestCreateArtifactStore:
    """Test artifact store factory function."""

    def test_create_local_store(self):
        settings = Mock()
        settings.artifact_backend = "local"
        settings.resolved_artifact_root.return_value = "/tmp/artifacts"
        
        store = create_artifact_store(settings)
        
        assert store.backend_name == "local"
        assert isinstance(store, LocalFilesystemArtifactStore)

    def test_create_s3_store(self):
        settings = Mock()
        settings.artifact_backend = "s3"
        settings.artifact_bucket = "test-bucket"
        settings.artifact_prefix = "test-prefix"
        settings.aws_endpoint_url = "http://localhost:9000"
        settings.aws_region = "us-east-1"
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"
        
        store = create_artifact_store(settings)
        
        assert store.backend_name == "s3"
        assert isinstance(store, S3CompatibleArtifactStore)
        assert store.bucket == "test-bucket"

    def test_create_s3_store_with_override(self):
        settings = Mock()
        settings.artifact_backend = "s3"
        settings.artifact_bucket = "test-bucket"
        settings.artifact_prefix = "test-prefix"
        settings.aws_endpoint_url = "http://localhost:9000"
        settings.aws_region = "us-east-1"
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"
        
        mock_client = Mock()
        store = create_artifact_store(settings, client=mock_client)
        
        assert store._client is mock_client
