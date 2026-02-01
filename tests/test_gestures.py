"""Integration tests for gesture operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestSwipe:
    """Test swipe operations (Maestro only)."""

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_swipe_up(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test swiping up."""
        async with timing_collector.measure("swipe_up", platform, backend="maestro"):
            result = await mcp_client.call("flutter_swipe", {"direction": "up"})

        assert result.get("success") or "content" in result, f"Swipe up failed: {result}"

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_swipe_down(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test swiping down."""
        async with timing_collector.measure("swipe_down", platform, backend="maestro"):
            result = await mcp_client.call("flutter_swipe", {"direction": "down"})

        assert result.get("success") or "content" in result, f"Swipe down failed: {result}"

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_swipe_left(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test swiping left."""
        async with timing_collector.measure("swipe_left", platform, backend="maestro"):
            result = await mcp_client.call("flutter_swipe", {"direction": "left"})

        assert result.get("success") or "content" in result, f"Swipe left failed: {result}"

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_swipe_right(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test swiping right."""
        async with timing_collector.measure("swipe_right", platform, backend="maestro"):
            result = await mcp_client.call("flutter_swipe", {"direction": "right"})

        assert result.get("success") or "content" in result, f"Swipe right failed: {result}"


class TestDoubleTap:
    """Test double tap operations (Maestro only)."""

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_double_tap_text(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test double tapping on text."""
        async with timing_collector.measure("double_tap", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_double_tap",
                {"finder": {"text": "Counter"}},
            )

        assert result.get("success") or "content" in result, f"Double tap failed: {result}"

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_double_tap_button(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test double tapping a button."""
        async with timing_collector.measure("double_tap_btn", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_double_tap",
                {"finder": {"text": "Increment"}},
            )

        assert result.get("success") or "content" in result, f"Double tap failed: {result}"


class TestLongPress:
    """Test long press operations (Maestro only)."""

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_long_press_text(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test long pressing on text."""
        async with timing_collector.measure("long_press", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_long_press",
                {"finder": {"text": "Counter"}},
            )

        assert result.get("success") or "content" in result, f"Long press failed: {result}"

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_long_press_button(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test long pressing a button."""
        async with timing_collector.measure("long_press_btn", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_long_press",
                {"finder": {"text": "Increment"}},
            )

        assert result.get("success") or "content" in result, f"Long press failed: {result}"
