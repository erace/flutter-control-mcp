"""Timing collection for integration tests."""

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TimingResult:
    """Result of a timed operation."""

    operation: str
    platform: str
    backend: str  # "unified", "maestro", or "driver"
    duration_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error}"
        return f"{self.operation}[{self.platform}/{self.backend}]: {self.duration_ms:.0f}ms ({status})"


class TimingCollector:
    """Collects timing results from test operations."""

    def __init__(self):
        self.results: list[TimingResult] = []

    @asynccontextmanager
    async def measure(
        self,
        operation: str,
        platform: str,
        backend: str = "unified",
    ):
        """Context manager to measure operation timing.

        Args:
            operation: Name of the operation (e.g., "tap_text")
            platform: Platform name (e.g., "android", "ios")
            backend: Backend name ("unified", "maestro", or "driver")

        Yields:
            TimingResult that will be populated after the operation

        Example:
            async with timing.measure("tap_text", "android", "maestro") as result:
                await mcp_client.call("flutter_tap", {...})
            print(f"Duration: {result.duration_ms}ms")
        """
        result = TimingResult(
            operation=operation,
            platform=platform,
            backend=backend,
            duration_ms=0,
            success=True,
        )

        start = time.perf_counter()
        try:
            yield result
        except Exception as e:
            result.success = False
            result.error = str(e)
            raise
        finally:
            end = time.perf_counter()
            result.duration_ms = (end - start) * 1000
            result.timestamp = datetime.now()
            self.results.append(result)

    def record(
        self,
        operation: str,
        platform: str,
        duration_ms: float,
        backend: str = "unified",
        success: bool = True,
        error: Optional[str] = None,
    ) -> TimingResult:
        """Manually record a timing result.

        Args:
            operation: Name of the operation
            platform: Platform name
            duration_ms: Duration in milliseconds
            backend: Backend name
            success: Whether the operation succeeded
            error: Error message if failed

        Returns:
            The recorded TimingResult
        """
        result = TimingResult(
            operation=operation,
            platform=platform,
            backend=backend,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )
        self.results.append(result)
        return result

    def get_results(
        self,
        operation: Optional[str] = None,
        platform: Optional[str] = None,
        backend: Optional[str] = None,
        success_only: bool = False,
    ) -> list[TimingResult]:
        """Get filtered timing results.

        Args:
            operation: Filter by operation name
            platform: Filter by platform
            backend: Filter by backend
            success_only: Only return successful results

        Returns:
            List of matching TimingResult objects
        """
        results = self.results

        if operation:
            results = [r for r in results if r.operation == operation]
        if platform:
            results = [r for r in results if r.platform == platform]
        if backend:
            results = [r for r in results if r.backend == backend]
        if success_only:
            results = [r for r in results if r.success]

        return results

    def get_average(
        self,
        operation: str,
        platform: str,
        backend: str = "unified",
    ) -> Optional[float]:
        """Get average duration for an operation.

        Args:
            operation: Operation name
            platform: Platform name
            backend: Backend name

        Returns:
            Average duration in ms, or None if no results
        """
        results = self.get_results(
            operation=operation,
            platform=platform,
            backend=backend,
            success_only=True,
        )

        if not results:
            return None

        return sum(r.duration_ms for r in results) / len(results)

    def clear(self):
        """Clear all collected results."""
        self.results.clear()

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self):
        return iter(self.results)
