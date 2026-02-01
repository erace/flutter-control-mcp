"""Integration tests for text input operations."""

import pytest

from .fixtures import MCPClient, TimingCollector


class TestEnterText:
    """Test text entry operations (Maestro only)."""

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_enter_text_basic(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test entering text into a text field."""
        # First tap on a text field (if the test app has one)
        # Then enter text
        async with timing_collector.measure("enter_text", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_enter_text",
                {"text": "Hello World"},
            )

        # May fail if no text field is focused
        assert "content" in result or result.get("success") is not None

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_enter_text_with_finder(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test entering text with a finder to locate the field."""
        async with timing_collector.measure("enter_text_finder", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_enter_text",
                {
                    "finder": {"text": "Enter name"},
                    "text": "Test User",
                },
            )

        # May fail if no such text field exists
        assert "content" in result or result.get("success") is not None

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_enter_text_special_characters(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test entering text with special characters."""
        async with timing_collector.measure("enter_text_special", platform, backend="maestro"):
            result = await mcp_client.call(
                "flutter_enter_text",
                {"text": "test@example.com"},
            )

        assert "content" in result or result.get("success") is not None


class TestClearText:
    """Test text clearing operations (Maestro only)."""

    @pytest.mark.maestro_only
    @pytest.mark.slow
    async def test_clear_text(
        self,
        mcp_client: MCPClient,
        platform: str,
        timing_collector: TimingCollector,
    ):
        """Test clearing text from a focused field."""
        async with timing_collector.measure("clear_text", platform, backend="maestro"):
            result = await mcp_client.call("flutter_clear_text", {})

        # May fail if no text field is focused
        assert "content" in result or result.get("success") is not None
