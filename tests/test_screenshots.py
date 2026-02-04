"""Integration tests for screenshot operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestScreenshot:
    """Test smart screenshot (auto-selects ADB/simctl, falls back to Maestro)."""

    async def test_screenshot_smart(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test smart screenshot - uses fastest method per platform."""
        async with timing_collector.measure("screenshot_smart", platform, backend="native"):
            result = await mcp_client.call("flutter_screenshot", {})

        assert result.get("success"), f"Screenshot failed: {result}"
        # Screenshots now save to file and return path
        assert "path" in result, f"No path in result: {result}"
        # Should report which method was used
        assert result.get("method") in ["adb", "simctl", "maestro"], f"Unknown method: {result}"

    async def test_screenshot_smart_multiple(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test multiple smart screenshots to verify consistency."""
        for i in range(3):
            async with timing_collector.measure(f"screenshot_smart_{i}", platform, backend="native"):
                result = await mcp_client.call("flutter_screenshot", {})

            assert result.get("success"), f"Screenshot {i} failed: {result}"


class TestScreenshotMaestro:
    """Test explicit Maestro screenshots."""

    @pytest.mark.slow
    async def test_screenshot_maestro(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test taking a screenshot with explicit Maestro."""
        async with timing_collector.measure("screenshot_maestro", platform, backend="maestro"):
            result = await mcp_client.call("flutter_screenshot_maestro", {}, timeout=120.0)

        # Should return success or image data
        assert result.get("success") or "content" in result, f"Screenshot failed: {result}"


class TestScreenshotComparison:
    """Compare screenshot methods."""

    @pytest.mark.slow
    async def test_screenshot_comparison(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test both screenshot methods and compare timing."""
        # Smart screenshot (fast - ADB or simctl)
        async with timing_collector.measure("screenshot_smart", platform, backend="native"):
            smart_result = await mcp_client.call("flutter_screenshot", {})

        # Maestro screenshot (slower)
        async with timing_collector.measure("screenshot_maestro", platform, backend="maestro"):
            maestro_result = await mcp_client.call("flutter_screenshot_maestro", {}, timeout=120.0)

        # Smart should succeed
        assert smart_result.get("success"), f"Smart screenshot failed: {smart_result}"

        # Maestro may fail on iOS with "Restricted methods" - that's ok
        if not maestro_result.get("success"):
            pytest.skip(f"Maestro screenshot not available: {maestro_result.get('error')}")

        # Get timings for comparison
        smart_timing = timing_collector.get_average("screenshot_smart", platform)
        maestro_timing = timing_collector.get_average("screenshot_maestro", platform)

        if smart_timing and maestro_timing:
            speedup = maestro_timing / smart_timing
            print(f"\nScreenshot speedup: native is {speedup:.1f}x faster than Maestro")
            print(f"  Native ({smart_result.get('method')}): {smart_timing:.0f}ms")
            print(f"  Maestro: {maestro_timing:.0f}ms")
