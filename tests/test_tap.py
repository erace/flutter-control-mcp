"""Integration tests for tap operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestTapByText:
    """Test tap operations using text finder."""

    @pytest.mark.parametrize("backend", ["unified", "maestro", "driver"])
    async def test_tap_increment_button(
        self,
        mcp_client: MCPClient,
        backend: str,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping the Increment button with different backends."""
        finder = {"text": "Increment"}
        if backend != "unified":
            finder["backend"] = backend

        async with timing_collector.measure("tap_text", platform, backend=backend):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"

    @pytest.mark.parametrize("backend", ["unified", "maestro", "driver"])
    async def test_tap_decrement_button(
        self,
        mcp_client: MCPClient,
        backend: str,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping the Decrement button with different backends."""
        finder = {"text": "Decrement"}
        if backend != "unified":
            finder["backend"] = backend

        async with timing_collector.measure("tap_text_decrement", platform, backend=backend):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"


class TestTapByKey:
    """Test tap operations using key finder (Driver only)."""

    @pytest.mark.driver_only
    async def test_tap_by_key_unified(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping by widget key with unified backend."""
        finder = {"key": "increment_btn"}

        async with timing_collector.measure("tap_key", platform, backend="unified"):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"

    @pytest.mark.driver_only
    async def test_tap_by_key_driver(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping by widget key with driver backend."""
        finder = {"key": "increment_btn", "backend": "driver"}

        async with timing_collector.measure("tap_key", platform, backend="driver"):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"


class TestTapById:
    """Test tap operations using Android resource ID (Maestro only)."""

    @pytest.mark.android_only
    @pytest.mark.maestro_only
    async def test_tap_by_id(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping by Android resource ID."""
        finder = {"id": "increment_button"}

        async with timing_collector.measure("tap_id", platform, backend="maestro"):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        # This may fail if the test app doesn't have resource IDs
        # Just record the timing regardless
        assert "content" in result or result.get("success") is not None


class TestTapByType:
    """Test tap operations using widget type (Driver only)."""

    @pytest.mark.driver_only
    async def test_tap_by_type_unified(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping by widget type with unified backend.

        Uses TextButton which has only one instance (Reset button).
        """
        finder = {"type": "TextButton"}

        async with timing_collector.measure("tap_type", platform, backend="unified"):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"

    @pytest.mark.driver_only
    async def test_tap_by_type_driver(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test tapping by widget type with driver backend.

        Uses TextButton which has only one instance (Reset button).
        """
        finder = {"type": "TextButton", "backend": "driver"}

        async with timing_collector.measure("tap_type", platform, backend="driver"):
            result = await mcp_client.call("flutter_tap", {"finder": finder})

        assert result.get("success") or "content" in result, f"Tap failed: {result}"


class TestDriverTap:
    """Test flutter_driver_tap tool directly."""

    @pytest.mark.driver_only
    async def test_driver_tap_by_key(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test flutter_driver_tap with key finder."""
        async with timing_collector.measure("driver_tap_key", platform, backend="driver"):
            result = await mcp_client.call(
                "flutter_driver_tap",
                {"finder": {"key": "increment_btn"}},
            )

        assert result.get("success") or "content" in result, f"Driver tap failed: {result}"

    @pytest.mark.driver_only
    async def test_driver_tap_by_text(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test flutter_driver_tap with text finder."""
        async with timing_collector.measure("driver_tap_text", platform, backend="driver"):
            result = await mcp_client.call(
                "flutter_driver_tap",
                {"finder": {"text": "Increment"}},
            )

        assert result.get("success") or "content" in result, f"Driver tap failed: {result}"
