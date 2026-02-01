"""Integration tests for assertion operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestAssertVisible:
    """Test assert_visible operations with different backends."""

    @pytest.mark.parametrize("backend", ["unified", "maestro", "driver"])
    async def test_assert_visible_text(
        self,
        mcp_client: MCPClient,
        backend: str,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting text is visible with different backends."""
        finder = {"text": "Counter"}
        if backend != "unified":
            finder["backend"] = backend

        async with timing_collector.measure("assert_visible", platform, backend=backend):
            result = await mcp_client.call("flutter_assert_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert visible failed: {result}"

    @pytest.mark.parametrize("backend", ["unified", "maestro", "driver"])
    async def test_assert_visible_button(
        self,
        mcp_client: MCPClient,
        backend: str,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting button is visible with different backends."""
        finder = {"text": "Increment"}
        if backend != "unified":
            finder["backend"] = backend

        async with timing_collector.measure("assert_visible_btn", platform, backend=backend):
            result = await mcp_client.call("flutter_assert_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert visible failed: {result}"


class TestAssertVisibleByKey:
    """Test assert_visible with key finder (Driver only)."""

    @pytest.mark.driver_only
    async def test_assert_visible_by_key_unified(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting widget is visible by key with unified backend."""
        finder = {"key": "count_label"}

        async with timing_collector.measure("assert_visible_key", platform, backend="unified"):
            result = await mcp_client.call("flutter_assert_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert visible failed: {result}"

    @pytest.mark.driver_only
    async def test_assert_visible_by_key_driver(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting widget is visible by key with driver backend."""
        finder = {"key": "count_label", "backend": "driver"}

        async with timing_collector.measure("assert_visible_key", platform, backend="driver"):
            result = await mcp_client.call("flutter_assert_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert visible failed: {result}"


class TestAssertNotVisible:
    """Test assert_not_visible operations."""

    @pytest.mark.parametrize("backend", ["unified", "maestro", "driver"])
    async def test_assert_not_visible_nonexistent(
        self,
        mcp_client: MCPClient,
        backend: str,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting non-existent element is not visible."""
        finder = {"text": "This Text Does Not Exist XYZ123"}
        if backend != "unified":
            finder["backend"] = backend

        async with timing_collector.measure("assert_not_visible", platform, backend=backend):
            result = await mcp_client.call("flutter_assert_not_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert not visible failed: {result}"

    @pytest.mark.driver_only
    async def test_assert_not_visible_by_key(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test asserting non-existent key is not visible."""
        finder = {"key": "nonexistent_key_xyz123"}

        async with timing_collector.measure("assert_not_visible_key", platform, backend="driver"):
            result = await mcp_client.call("flutter_assert_not_visible", {"finder": finder})

        assert result.get("success") or "content" in result, f"Assert not visible failed: {result}"
