"""Unified executor - executes commands with auto-fallback."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .backend_selector import BackendSelector, Backend
from ..logging.trace import TraceContext


@dataclass
class ExecutionResult:
    """Result of unified execution."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    backend_used: Optional[Backend] = None
    backends_tried: List[str] = field(default_factory=list)
    fallback_occurred: bool = False


class UnifiedExecutor:
    """Executes commands with auto-backend selection and fallback."""

    def __init__(self, maestro_wrapper, driver_client):
        self.maestro = maestro_wrapper
        self.driver = driver_client
        self._driver_connected = False

    async def ensure_driver_connected(self, trace: TraceContext) -> bool:
        """Ensure driver is connected."""
        if self._driver_connected and self.driver.ws is not None:
            return True
        if self.driver.ws is None:
            connected = await self.driver.connect(trace)
            self._driver_connected = connected
            return connected
        return True

    async def tap(
        self,
        finder: Dict[str, Any],
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None,
    ) -> ExecutionResult:
        """Tap with auto-backend selection and fallback."""
        backends = BackendSelector.get_fallback_order(finder)
        primary, reason = BackendSelector.select(finder)
        trace.log("BACKEND_SEL", f"{primary.value} (reason: {reason})")

        result = ExecutionResult(success=False, backends_tried=[])

        for backend in backends:
            result.backends_tried.append(backend.value)

            if backend == Backend.MAESTRO:
                trace.log("TRY_MAESTRO", f"tap {finder}")
                maestro_result = await self.maestro.tap(finder, trace, timeout, device)
                if maestro_result.success:
                    result.success = True
                    result.backend_used = Backend.MAESTRO
                    result.fallback_occurred = len(result.backends_tried) > 1
                    trace.log("MAESTRO_OK", "tap succeeded")
                    return result
                trace.log("MAESTRO_FAIL", maestro_result.error_message or "unknown error")

            elif backend == Backend.DRIVER:
                if not await self.ensure_driver_connected(trace):
                    trace.log("DRIVER_SKIP", "not connected")
                    continue

                trace.log("TRY_DRIVER", f"tap {finder}")
                from ..driver.finders import Finder
                try:
                    driver_finder = Finder.from_dict(finder)
                    driver_result = await self.driver.tap(driver_finder, trace, timeout)
                    if driver_result.success:
                        result.success = True
                        result.backend_used = Backend.DRIVER
                        result.fallback_occurred = len(result.backends_tried) > 1
                        trace.log("DRIVER_OK", "tap succeeded")
                        return result
                    trace.log("DRIVER_FAIL", driver_result.error or "unknown error")
                except ValueError as e:
                    trace.log("DRIVER_SKIP", f"finder not supported: {e}")
                    continue

        result.error = f"All backends failed: {result.backends_tried}"
        trace.log("ALL_FAIL", result.error)
        return result

    async def get_text(
        self,
        finder: Dict[str, Any],
        trace: TraceContext,
        timeout: int = 30,
    ) -> ExecutionResult:
        """Get text with auto-backend selection and fallback."""
        backends = BackendSelector.get_fallback_order(finder)
        primary, reason = BackendSelector.select(finder)
        trace.log("BACKEND_SEL", f"{primary.value} (reason: {reason})")

        result = ExecutionResult(success=False, backends_tried=[])

        for backend in backends:
            result.backends_tried.append(backend.value)

            if backend == Backend.DRIVER:
                if not await self.ensure_driver_connected(trace):
                    trace.log("DRIVER_SKIP", "not connected")
                    continue

                trace.log("TRY_DRIVER", f"get_text {finder}")
                from ..driver.finders import Finder
                try:
                    driver_finder = Finder.from_dict(finder)
                    driver_result = await self.driver.get_text(driver_finder, trace, timeout)
                    if driver_result.success and driver_result.response:
                        text = driver_result.response.get("response") or driver_result.response.get("text")
                        result.success = True
                        result.data = text
                        result.backend_used = Backend.DRIVER
                        result.fallback_occurred = len(result.backends_tried) > 1
                        trace.log("DRIVER_OK", f"get_text succeeded: {text}")
                        return result
                    trace.log("DRIVER_FAIL", driver_result.error or "unknown error")
                except ValueError as e:
                    trace.log("DRIVER_SKIP", f"finder not supported: {e}")
                    continue

            elif backend == Backend.MAESTRO:
                # Maestro doesn't have a direct get_text, would need to use assertions
                trace.log("MAESTRO_SKIP", "get_text not supported by Maestro")
                continue

        result.error = f"All backends failed: {result.backends_tried}"
        trace.log("ALL_FAIL", result.error)
        return result

    async def assert_visible(
        self,
        finder: Dict[str, Any],
        trace: TraceContext,
        timeout: int = 30,
        device: Optional[str] = None,
    ) -> ExecutionResult:
        """Assert visible with auto-backend selection and fallback."""
        backends = BackendSelector.get_fallback_order(finder)
        primary, reason = BackendSelector.select(finder)
        trace.log("BACKEND_SEL", f"{primary.value} (reason: {reason})")

        result = ExecutionResult(success=False, backends_tried=[])

        for backend in backends:
            result.backends_tried.append(backend.value)

            if backend == Backend.MAESTRO:
                trace.log("TRY_MAESTRO", f"assert_visible {finder}")
                maestro_result = await self.maestro.assert_visible(finder, trace, timeout, device)
                if maestro_result.success:
                    result.success = True
                    result.backend_used = Backend.MAESTRO
                    result.fallback_occurred = len(result.backends_tried) > 1
                    trace.log("MAESTRO_OK", "assert_visible succeeded")
                    return result
                trace.log("MAESTRO_FAIL", maestro_result.error_message or "unknown error")

            elif backend == Backend.DRIVER:
                if not await self.ensure_driver_connected(trace):
                    trace.log("DRIVER_SKIP", "not connected")
                    continue

                trace.log("TRY_DRIVER", f"wait_for {finder}")
                from ..driver.finders import Finder
                try:
                    driver_finder = Finder.from_dict(finder)
                    driver_result = await self.driver.wait_for(driver_finder, trace, timeout)
                    if driver_result.success:
                        result.success = True
                        result.backend_used = Backend.DRIVER
                        result.fallback_occurred = len(result.backends_tried) > 1
                        trace.log("DRIVER_OK", "wait_for succeeded")
                        return result
                    trace.log("DRIVER_FAIL", driver_result.error or "unknown error")
                except ValueError as e:
                    trace.log("DRIVER_SKIP", f"finder not supported: {e}")
                    continue

        result.error = f"All backends failed: {result.backends_tried}"
        trace.log("ALL_FAIL", result.error)
        return result
