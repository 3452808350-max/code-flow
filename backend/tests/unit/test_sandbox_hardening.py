"""Unit tests for hardened sandbox functionality."""

from __future__ import annotations

import pytest
from pathlib import Path

from app.harness_lab.boundary.sandbox import SandboxManager
from app.harness_lab.settings import HarnessLabSettings
from app.harness_lab.types import (
    ActionPlan,
    HardenedSandboxConfig,
    PolicyVerdictSnapshot,
    SideEffectClass,
)


class FakeDatabase:
    """Fake database for testing."""
    def __init__(self, repo_root: Path):
        self.repo_root = str(repo_root)
        self.artifact_root = str(repo_root / "artifacts")


@pytest.fixture
def sandbox_manager(tmp_path):
    """Create a sandbox manager for testing."""
    settings = HarnessLabSettings(
        HARNESS_DB_URL="postgresql://test:test@localhost/test",
        HARNESS_REDIS_URL="redis://localhost:6379/0",
    )
    db = FakeDatabase(tmp_path)
    return SandboxManager(settings, db)


class TestHardenedDockerCommand:
    """Tests for hardened Docker command generation."""

    def test_hardened_config_includes_no_new_privileges(self, sandbox_manager):
        """Verify hardened config includes no-new-privileges."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        config = sandbox_manager._build_hardened_config(action)
        
        assert config.no_new_privileges is True
        assert "no-new-privileges:true" in config.security_options

    def test_hardened_config_cap_drop_all(self, sandbox_manager):
        """Verify hardened config drops all capabilities."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        config = sandbox_manager._build_hardened_config(action)
        
        assert config.cap_drop_all is True

    def test_hardened_config_rootless_user(self, sandbox_manager):
        """Verify hardened config uses rootless user."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        config = sandbox_manager._build_hardened_config(action)
        
        assert config.rootless_user == "1000:1000"

    def test_capability_whitelist_for_write_file(self, sandbox_manager):
        """Verify write_file gets appropriate capability whitelist."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.write_file",
            payload={"action": "write_file", "path": "test.txt", "content": "hello"},
        )
        caps = sandbox_manager._get_capability_whitelist(action)
        
        assert "CAP_CHOWN" in caps
        assert "CAP_DAC_OVERRIDE" in caps

    def test_capability_whitelist_for_shell(self, sandbox_manager):
        """Verify shell gets minimal capability whitelist."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "ls"},
        )
        caps = sandbox_manager._get_capability_whitelist(action)
        
        assert "CAP_DAC_OVERRIDE" in caps

    def test_capability_whitelist_for_git(self, sandbox_manager):
        """Verify git gets empty capability whitelist."""
        action = ActionPlan(
            tool_name="git",
            subject="tool.git.status",
            payload={"action": "status"},
        )
        caps = sandbox_manager._get_capability_whitelist(action)
        
        assert caps == []

    def test_docker_command_includes_security_options(self, sandbox_manager, tmp_path):
        """Verify Docker command includes security options."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        cmd, cleanup_dir, mounts = sandbox_manager._build_hardened_docker_command(
            action, spec, "test-container"
        )
        
        # Check security options
        assert "--security-opt" in cmd
        assert "no-new-privileges:true" in cmd
        
        # Check capabilities
        assert "--cap-drop=ALL" in cmd
        
        # Check user
        assert "--user" in cmd
        assert "1000:1000" in cmd
        
        # Check read-only
        assert "--read-only" in cmd

    def test_docker_command_network_none_for_shell(self, sandbox_manager, tmp_path):
        """Verify shell uses network=none."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        cmd, _, _ = sandbox_manager._build_hardened_docker_command(
            action, spec, "test-container"
        )
        
        network_idx = cmd.index("--network")
        assert cmd[network_idx + 1] == "none"

    def test_docker_command_network_restricted_for_http_fetch(self, sandbox_manager, tmp_path):
        """Verify http_fetch uses network=restricted (bridge)."""
        action = ActionPlan(
            tool_name="http_fetch",
            subject="tool.http_fetch",
            payload={"url": "https://example.com"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        assert spec.network_policy == "restricted"
        
        cmd, _, _ = sandbox_manager._build_hardened_docker_command(
            action, spec, "test-container"
        )
        
        network_idx = cmd.index("--network")
        # Currently restricted maps to bridge
        assert cmd[network_idx + 1] == "bridge"


class TestSideEffectClassification:
    """Tests for side effect classification."""

    def test_write_file_classified_as_sandboxed_mutation(self, sandbox_manager):
        """Verify write_file is classified as sandboxed_mutation."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.write_file",
            payload={"action": "write_file", "path": "test.txt", "content": "hello"},
        )
        classification = sandbox_manager.classify_side_effect(action)
        
        assert classification == "sandboxed_mutation"

    def test_shell_classified_as_sandboxed_read(self, sandbox_manager):
        """Verify shell is classified as sandboxed_read."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "ls"},
        )
        classification = sandbox_manager.classify_side_effect(action)
        
        assert classification == "sandboxed_read"

    def test_git_classified_as_sandboxed_read(self, sandbox_manager):
        """Verify git is classified as sandboxed_read."""
        action = ActionPlan(
            tool_name="git",
            subject="tool.git.status",
            payload={"action": "status"},
        )
        classification = sandbox_manager.classify_side_effect(action)
        
        assert classification == "sandboxed_read"

    def test_http_fetch_classified_as_sandboxed_read(self, sandbox_manager):
        """Verify http_fetch is classified as sandboxed_read."""
        action = ActionPlan(
            tool_name="http_fetch",
            subject="tool.http_fetch",
            payload={"url": "https://example.com"},
        )
        classification = sandbox_manager.classify_side_effect(action)
        
        assert classification == "sandboxed_read"

    def test_denied_by_policy_classification(self, sandbox_manager):
        """Verify denied actions are classified correctly."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "rm -rf /"},
        )
        verdict = PolicyVerdictSnapshot(
            decision="deny",
            subject="tool.shell.execute",
            rule_id="rule_001",
        )
        classification = sandbox_manager.classify_side_effect(action, verdict)
        
        assert classification == "denied_before_sandbox"

    def test_approval_required_classification(self, sandbox_manager):
        """Verify approval-required actions are classified correctly."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.write_file",
            payload={"action": "write_file", "path": "test.txt", "content": "hello"},
        )
        verdict = PolicyVerdictSnapshot(
            decision="approval_required",
            subject="tool.filesystem.write_file",
            rule_id="rule_002",
        )
        classification = sandbox_manager.classify_side_effect(action, verdict)
        
        assert classification == "approval_blocked"


class TestSandboxSpec:
    """Tests for sandbox spec generation."""

    def test_spec_includes_hardened_config(self, sandbox_manager):
        """Verify sandbox spec includes hardened config."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        assert spec.hardened_config is not None
        assert spec.hardened_config.no_new_privileges is True

    def test_spec_network_policy_for_shell(self, sandbox_manager):
        """Verify shell spec uses network=none."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "echo hello"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        assert spec.network_policy == "none"

    def test_spec_network_policy_for_http_fetch(self, sandbox_manager):
        """Verify http_fetch spec uses network=restricted."""
        action = ActionPlan(
            tool_name="http_fetch",
            subject="tool.http_fetch",
            payload={"url": "https://example.com"},
        )
        spec = sandbox_manager.sandbox_spec_for(action)
        
        assert spec.network_policy == "restricted"

    def test_spec_includes_approval_token(self, sandbox_manager):
        """Verify spec includes approval token when provided."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.write_file",
            payload={"action": "write_file", "path": "test.txt", "content": "hello"},
        )
        spec = sandbox_manager.sandbox_spec_for(
            action, approval_token="approval:test:approve"
        )
        
        assert spec.approval_token == "approval:test:approve"


class TestSandboxStatus:
    """Tests for sandbox status reporting."""

    def test_status_includes_hardened_fields(self, sandbox_manager):
        """Verify status includes hardened readiness fields."""
        status = sandbox_manager.status()
        
        # Check hardened fields exist
        assert hasattr(status, "hardened_ready")
        assert hasattr(status, "rootless_ready")
        assert hasattr(status, "no_new_privileges_ready")
        assert hasattr(status, "capability_drop_ready")
        assert hasattr(status, "policy_enforcement_ready")
        
        # Check probe checks exist
        assert hasattr(status, "probe_checks")

    def test_status_probe_checks_structure(self, sandbox_manager):
        """Verify probe checks have correct structure."""
        status = sandbox_manager.status()
        
        for check in status.probe_checks:
            assert hasattr(check, "check")
            assert hasattr(check, "passed")
            assert hasattr(check, "error")


class TestRequiresSandbox:
    """Tests for sandbox requirement detection."""

    def test_shell_requires_sandbox(self, sandbox_manager):
        """Verify shell requires sandbox."""
        action = ActionPlan(
            tool_name="shell",
            subject="tool.shell.execute",
            payload={"command": "ls"},
        )
        assert sandbox_manager.requires_sandbox(action) is True

    def test_git_requires_sandbox(self, sandbox_manager):
        """Verify git requires sandbox."""
        action = ActionPlan(
            tool_name="git",
            subject="tool.git.status",
            payload={"action": "status"},
        )
        assert sandbox_manager.requires_sandbox(action) is True

    def test_http_fetch_requires_sandbox(self, sandbox_manager):
        """Verify http_fetch requires sandbox."""
        action = ActionPlan(
            tool_name="http_fetch",
            subject="tool.http_fetch",
            payload={"url": "https://example.com"},
        )
        assert sandbox_manager.requires_sandbox(action) is True

    def test_write_file_requires_sandbox(self, sandbox_manager):
        """Verify write_file requires sandbox."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.write_file",
            payload={"action": "write_file", "path": "test.txt", "content": "hello"},
        )
        assert sandbox_manager.requires_sandbox(action) is True

    def test_read_file_does_not_require_sandbox(self, sandbox_manager):
        """Verify read_file does not require sandbox."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.read_file",
            payload={"action": "read_file", "path": "test.txt"},
        )
        assert sandbox_manager.requires_sandbox(action) is False

    def test_list_dir_does_not_require_sandbox(self, sandbox_manager):
        """Verify list_dir does not require sandbox."""
        action = ActionPlan(
            tool_name="filesystem",
            subject="tool.filesystem.list_dir",
            payload={"action": "list_dir", "path": "."},
        )
        assert sandbox_manager.requires_sandbox(action) is False
