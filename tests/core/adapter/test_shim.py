"""Tests for ShimAdapterBase."""

import pytest
from aop.core.adapter.shim import ShimAdapterBase, TaskRunRef
from aop.core.types import NormalizeContext
from aop.core.types.contracts import CapabilitySet


class MockAdapter(ShimAdapterBase):
    """Mock adapter for testing."""
    
    def __init__(self, provider_name: str = "test"):
        self._provider_name = provider_name
        super().__init__(
            provider_id=provider_name,
            binary_name=provider_name,
            capability_set=CapabilitySet(
                tiers=["C0"],
                supports_native_async=False,
                supports_poll_endpoint=False,
                supports_resume_after_restart=False,
                supports_schema_enforcement=False,
                min_supported_version="1.0.0",
                tested_os=["macos", "linux", "windows"],
            )
        )
    
    @property
    def provider_name(self):
        return self._provider_name
    
    def spawn(self, ctx):
        pass
    
    def poll(self, ref):
        pass
    
    def cancel(self, ref):
        pass
    
    def normalize(self, raw, ctx):
        return []


class TestShimAdapterBase:
    def test_adapter_creation(self):
        adapter = MockAdapter()
        assert adapter is not None
        assert adapter.provider_name == "test"
    
    def test_adapter_with_custom_name(self):
        adapter = MockAdapter(provider_name="claude")
        assert adapter.provider_name == "claude"


class TestTaskRunRef:
    def test_ref_creation(self):
        ref = TaskRunRef(
            task_id="test-task-001",
            provider="claude",
            run_id="test-run-001",
            artifact_path="/tmp/artifacts",
            started_at=1234567890.0,
            pid=1234,
            session_id="session-001",
        )
        assert ref.run_id == "test-run-001"
        assert ref.provider == "claude"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
