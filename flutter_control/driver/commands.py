"""Higher-level Flutter Driver commands."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import FlutterDriverClient
from .finders import Finder
from .protocol import DriverResponse
from ..logging.trace import TraceContext


@dataclass
class CommandResult:
    """Result of a driver command."""

    success: bool
    error: Optional[str] = None
    data: Optional[Any] = None


class DriverCommands:
    """High-level Flutter Driver command interface."""

    def __init__(self, client: FlutterDriverClient):
        self.client = client

    async def tap_by_key(
        self, key: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Tap widget by key."""
        from .finders import ByKey

        finder = ByKey(key)
        resp = await self.client.tap(finder, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def tap_by_type(
        self, type_name: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Tap first widget of given type."""
        from .finders import ByType

        finder = ByType(type_name)
        resp = await self.client.tap(finder, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def tap_by_text(
        self, text: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Tap widget by text."""
        from .finders import ByText

        finder = ByText(text)
        resp = await self.client.tap(finder, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def get_text_by_key(
        self, key: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Get text from widget by key."""
        from .finders import ByKey

        finder = ByKey(key)
        resp = await self.client.get_text(finder, trace, timeout)
        if resp.success and resp.response:
            return CommandResult(success=True, data=resp.response.get("text"))
        return CommandResult(success=False, error=resp.error)

    async def get_text_by_type(
        self, type_name: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Get text from first widget of given type."""
        from .finders import ByType

        finder = ByType(type_name)
        resp = await self.client.get_text(finder, trace, timeout)
        if resp.success and resp.response:
            return CommandResult(success=True, data=resp.response.get("text"))
        return CommandResult(success=False, error=resp.error)

    async def enter_text(
        self, text: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Enter text into focused field."""
        resp = await self.client.enter_text(text, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def wait_for_key(
        self, key: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Wait for widget by key to appear."""
        from .finders import ByKey

        finder = ByKey(key)
        resp = await self.client.wait_for(finder, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def wait_for_text(
        self, text: str, trace: Optional[TraceContext] = None, timeout: int = 30
    ) -> CommandResult:
        """Wait for widget with text to appear."""
        from .finders import ByText

        finder = ByText(text)
        resp = await self.client.wait_for(finder, trace, timeout)
        return CommandResult(success=resp.success, error=resp.error)

    async def get_widget_tree(
        self, trace: Optional[TraceContext] = None
    ) -> CommandResult:
        """Get the widget/render tree."""
        resp = await self.client.get_render_tree(trace)
        if resp.success and resp.response:
            return CommandResult(success=True, data=resp.response.get("tree"))
        return CommandResult(success=False, error=resp.error)

    async def get_semantics_tree(
        self, trace: Optional[TraceContext] = None
    ) -> CommandResult:
        """Get the semantics tree (accessibility)."""
        resp = await self.client.get_semantics_tree(trace)
        if resp.success and resp.response:
            return CommandResult(success=True, data=resp.response.get("tree"))
        return CommandResult(success=False, error=resp.error)
