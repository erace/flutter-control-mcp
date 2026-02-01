"""Integration tests for Driver-only operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestDriverConnect:
    """Test Flutter Driver connection operations."""

    @pytest.mark.driver_only
    async def test_driver_discover(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test discovering VM service URI."""
        async with timing_collector.measure("driver_discover", platform, backend="driver"):
            result = await mcp_client.call("flutter_driver_discover", {})

        # Should return URI or error
        assert "content" in result or result.get("uri") is not None

    @pytest.mark.driver_only
    async def test_driver_connect(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
        platform_config,
    ):
        """Test connecting to Flutter Driver."""
        # Use VM service URI if provided
        args = {}
        if platform_config.vm_service_uri:
            args["uri"] = platform_config.vm_service_uri

        async with timing_collector.measure("driver_connect", platform, backend="driver"):
            result = await mcp_client.call("flutter_driver_connect", args)

        assert "content" in result or result.get("success") is not None

    @pytest.mark.driver_only
    async def test_driver_disconnect(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
        bootstrap_result,
    ):
        """Test disconnecting from Flutter Driver."""
        async with timing_collector.measure("driver_disconnect", platform, backend="driver"):
            result = await mcp_client.call("flutter_driver_disconnect", {})

        assert "content" in result or result.get("success") is not None

        # Reconnect so subsequent tests still work
        if bootstrap_result.driver_uri:
            await mcp_client.call(
                "flutter_driver_connect", {"uri": bootstrap_result.driver_uri}
            )


class TestGetText:
    """Test getting text from widgets (Driver only)."""

    @pytest.mark.driver_only
    async def test_get_text_by_key(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test getting text from a widget by key."""
        async with timing_collector.measure("get_text_key", platform, backend="driver"):
            result = await mcp_client.call(
                "flutter_get_text",
                {"finder": {"key": "count_label"}},
            )

        # Should return text content or error
        assert "content" in result or result.get("text") is not None

    @pytest.mark.driver_only
    async def test_get_text_by_type(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test getting text from a widget by type."""
        async with timing_collector.measure("get_text_type", platform, backend="driver"):
            result = await mcp_client.call(
                "flutter_get_text",
                {"finder": {"type": "Text"}},
            )

        assert "content" in result or result.get("text") is not None

    @pytest.mark.driver_only
    async def test_get_text_by_text(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test getting text from a widget by text content."""
        async with timing_collector.measure("get_text_text", platform, backend="driver"):
            result = await mcp_client.call(
                "flutter_get_text",
                {"finder": {"text": "Counter"}},
            )

        assert "content" in result or result.get("text") is not None


class TestWidgetTree:
    """Test widget tree inspection (Driver only)."""

    @pytest.mark.driver_only
    @pytest.mark.slow
    async def test_widget_tree(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test getting the widget tree."""
        async with timing_collector.measure("widget_tree", platform, backend="driver"):
            result = await mcp_client.call("flutter_widget_tree", {})

        # Should return tree content or error
        assert "content" in result or result.get("tree") is not None


class TestDriverVersion:
    """Test Flutter Driver version/info."""

    async def test_flutter_version(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test getting Flutter Control version info."""
        async with timing_collector.measure("version", platform, backend="driver"):
            result = await mcp_client.call("flutter_version", {})

        assert "content" in result or result.get("version") is not None
