"""Integration tests for screenshot operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestScreenshotMaestro:
    """Test Maestro-based screenshots."""

    @pytest.mark.slow
    async def test_screenshot_maestro(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test taking a screenshot with Maestro."""
        async with timing_collector.measure("screenshot_maestro", platform, backend="maestro"):
            result = await mcp_client.call("flutter_screenshot", {}, timeout=120.0)

        # Should return success or image data
        assert result.get("success") or "content" in result, f"Screenshot failed: {result}"


class TestScreenshotADB:
    """Test ADB-based screenshots (Android only)."""

    @pytest.mark.android_only
    async def test_screenshot_adb(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test taking a screenshot with ADB (fast method)."""
        async with timing_collector.measure("screenshot_adb", platform, backend="maestro"):
            result = await mcp_client.call("flutter_screenshot_adb", {})

        assert result.get("success") or "content" in result, f"ADB screenshot failed: {result}"

    @pytest.mark.android_only
    async def test_screenshot_adb_multiple(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test taking multiple ADB screenshots to verify consistency."""
        for i in range(3):
            async with timing_collector.measure(f"screenshot_adb_{i}", platform, backend="maestro"):
                result = await mcp_client.call("flutter_screenshot_adb", {})

            assert result.get("success") or "content" in result


class TestScreenshotComparison:
    """Compare screenshot methods."""

    @pytest.mark.android_only
    @pytest.mark.slow
    async def test_screenshot_comparison(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test both screenshot methods and compare timing."""
        # ADB screenshot (fast)
        async with timing_collector.measure("screenshot_adb", platform, backend="maestro"):
            adb_result = await mcp_client.call("flutter_screenshot_adb", {})

        # Maestro screenshot (slow)
        async with timing_collector.measure("screenshot_maestro", platform, backend="maestro"):
            maestro_result = await mcp_client.call("flutter_screenshot", {}, timeout=120.0)

        # Both should succeed
        assert adb_result.get("success") or "content" in adb_result
        assert maestro_result.get("success") or "content" in maestro_result

        # Get timings for comparison
        adb_timing = timing_collector.get_average("screenshot_adb", platform)
        maestro_timing = timing_collector.get_average("screenshot_maestro", platform)

        if adb_timing and maestro_timing:
            speedup = maestro_timing / adb_timing
            print(f"\nScreenshot speedup: ADB is {speedup:.1f}x faster than Maestro")
            print(f"  ADB: {adb_timing:.0f}ms")
            print(f"  Maestro: {maestro_timing:.0f}ms")
