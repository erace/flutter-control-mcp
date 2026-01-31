"""Flutter Driver JSON-RPC protocol."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio


@dataclass
class DriverRequest:
    """A Flutter Driver command request."""

    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None

    def to_driver_command(self) -> Dict[str, Any]:
        """Convert to Flutter Driver command format."""
        cmd = {"command": self.command, **self.params}
        if self.timeout is not None:
            cmd["timeout"] = self.timeout * 1000000  # microseconds
        return cmd


@dataclass
class DriverResponse:
    """Response from Flutter Driver command."""

    success: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    is_error: bool = False


class DriverProtocol:
    """Handles Flutter Driver protocol over VM Service."""

    DRIVER_EXTENSION = "ext.flutter.driver"

    def __init__(self):
        self._request_id = 0

    def next_id(self) -> str:
        """Generate next request ID."""
        self._request_id += 1
        return str(self._request_id)

    def make_vm_service_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a VM Service JSON-RPC request."""
        request = {
            "jsonrpc": "2.0",
            "id": self.next_id(),
            "method": method,
        }
        if params:
            request["params"] = params
        return request

    def make_driver_request(
        self, isolate_id: str, command: DriverRequest
    ) -> Dict[str, Any]:
        """Create a Flutter Driver extension request."""
        return self.make_vm_service_request(
            self.DRIVER_EXTENSION,
            {
                "isolateId": isolate_id,
                **command.to_driver_command(),
            },
        )

    def parse_response(self, data: Dict[str, Any]) -> DriverResponse:
        """Parse VM Service response."""
        if "error" in data:
            error = data["error"]
            if isinstance(error, dict):
                message = error.get("message", str(error))
                details = error.get("data", {})
                if isinstance(details, dict) and "details" in details:
                    message = f"{message}: {details['details']}"
            else:
                message = str(error)
            return DriverResponse(success=False, error=message, is_error=True)

        result = data.get("result", {})

        # Check for driver-level errors
        if isinstance(result, dict):
            if result.get("isError", False):
                return DriverResponse(
                    success=False,
                    error=result.get("response", "Unknown driver error"),
                    is_error=True,
                )

        return DriverResponse(success=True, response=result)


# Driver command names
class Commands:
    """Flutter Driver command names."""

    # Widget interaction
    TAP = "tap"
    SCROLL = "scroll"
    SCROLL_INTO_VIEW = "scrollIntoView"
    ENTER_TEXT = "enter_text"
    SET_TEXT_ENTRY_EMULATION = "set_text_entry_emulation"

    # Widget inspection
    GET_TEXT = "get_text"
    GET_SEMANTICS_ID = "get_semantics_id"
    GET_OFFSET = "get_offset"

    # Widget tree
    GET_RENDER_TREE = "get_render_tree"
    GET_LAYER_TREE = "get_layer_tree"
    GET_SEMANTICS_TREE = "get_semantics_tree"
    GET_RENDER_OBJECT_DIAGNOSTICS = "get_render_object_diagnostics"

    # Waiting
    WAIT_FOR = "waitFor"
    WAIT_FOR_ABSENT = "waitForAbsent"
    WAIT_FOR_CONDITION = "waitForCondition"

    # Other
    REQUEST_DATA = "request_data"
    SET_FRAME_SYNC = "set_frame_sync"
    SCREENSHOT = "screenshot"
