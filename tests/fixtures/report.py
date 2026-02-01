"""Report generator for integration test results."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .timing import TimingCollector, TimingResult


class ReportGenerator:
    """Generates markdown reports from timing results."""

    def __init__(self, collector: TimingCollector):
        self.collector = collector

    def generate(self, output_path: Optional[Path] = None) -> str:
        """Generate a markdown report.

        Args:
            output_path: Optional path to write the report to

        Returns:
            The report as a string
        """
        report = self._build_report()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)

        return report

    def _build_report(self) -> str:
        """Build the report content."""
        lines = [
            "# Flutter Control MCP - Integration Test Report",
            "",
            f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",
            "",
        ]

        # Organize results by category
        three_backend_ops = self._get_three_backend_operations()
        maestro_only_ops = self._get_single_backend_operations("maestro")
        driver_only_ops = self._get_single_backend_operations("driver")
        screenshot_results = self._get_screenshot_results()

        # 3-Backend Comparison section
        if three_backend_ops:
            lines.extend(self._format_three_backend_section(three_backend_ops))

        # Maestro-Only section
        if maestro_only_ops:
            lines.extend(self._format_single_backend_section(
                "Maestro-Only Operations",
                maestro_only_ops,
            ))

        # Driver-Only section
        if driver_only_ops:
            lines.extend(self._format_single_backend_section(
                "Driver-Only Operations",
                driver_only_ops,
            ))

        # Screenshot Comparison section
        if screenshot_results:
            lines.extend(self._format_screenshot_section(screenshot_results))

        # Summary section
        lines.extend(self._format_summary())

        return "\n".join(lines)

    def _get_three_backend_operations(self) -> dict[str, dict[str, dict[str, float]]]:
        """Get operations that have results for all 3 backends.

        Returns:
            Nested dict: operation -> platform -> backend -> duration_ms
        """
        # Group by operation and platform
        grouped: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )

        for result in self.collector.get_results(success_only=True):
            grouped[result.operation][result.platform][result.backend].append(
                result.duration_ms
            )

        # Calculate averages and filter for operations with multiple backends
        three_backend: dict[str, dict[str, dict[str, float]]] = {}

        for op, platforms in grouped.items():
            op_has_multiple_backends = False
            for platform, backends in platforms.items():
                if len(backends) > 1:
                    op_has_multiple_backends = True
                    break

            if op_has_multiple_backends:
                three_backend[op] = {}
                for platform, backends in platforms.items():
                    three_backend[op][platform] = {}
                    for backend, durations in backends.items():
                        three_backend[op][platform][backend] = sum(durations) / len(durations)

        return three_backend

    def _get_single_backend_operations(
        self,
        backend: str,
    ) -> dict[str, dict[str, float]]:
        """Get operations that only have results for a single backend.

        Args:
            backend: The backend to filter for

        Returns:
            Nested dict: operation -> platform -> duration_ms
        """
        # Group by operation and platform
        grouped: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        ops_with_multiple_backends: set[str] = set()

        for result in self.collector.get_results(success_only=True):
            grouped[result.operation][result.platform].append(
                (result.backend, result.duration_ms)
            )

        # Find operations that only have the specified backend
        single_backend: dict[str, dict[str, float]] = {}

        for op, platforms in grouped.items():
            # Check if this operation only has results from the target backend
            backends_seen = set()
            for platform, results in platforms.items():
                for b, _ in results:
                    backends_seen.add(b)

            # Skip if we see other backends (including "unified" which auto-selects)
            if len(backends_seen) == 1 and backend in backends_seen:
                single_backend[op] = {}
                for platform, results in platforms.items():
                    durations = [d for b, d in results if b == backend]
                    if durations:
                        single_backend[op][platform] = sum(durations) / len(durations)

        return single_backend

    def _get_screenshot_results(self) -> dict[str, dict[str, float]]:
        """Get screenshot operation results.

        Returns:
            Nested dict: method -> platform -> duration_ms
        """
        screenshot_ops = ["screenshot", "screenshot_maestro", "screenshot_adb"]
        results: dict[str, dict[str, float]] = {}

        for op in screenshot_ops:
            op_results = self.collector.get_results(operation=op, success_only=True)
            if op_results:
                results[op] = {}
                by_platform: dict[str, list[float]] = defaultdict(list)
                for r in op_results:
                    by_platform[r.platform].append(r.duration_ms)
                for platform, durations in by_platform.items():
                    results[op][platform] = sum(durations) / len(durations)

        return results

    def _format_three_backend_section(
        self,
        ops: dict[str, dict[str, dict[str, float]]],
    ) -> list[str]:
        """Format the 3-backend comparison section."""
        lines = [
            "## 3-Backend Comparison",
            "",
            "| Operation | Platform | Unified (ms) | Maestro (ms) | Driver (ms) | Notes |",
            "|-----------|----------|--------------|--------------|-------------|-------|",
        ]

        for op in sorted(ops.keys()):
            platforms = ops[op]
            for platform in sorted(platforms.keys()):
                backends = platforms[platform]
                unified = backends.get("unified")
                maestro = backends.get("maestro")
                driver = backends.get("driver")

                unified_str = f"{unified:.0f}" if unified else "N/A"
                maestro_str = f"{maestro:.0f}" if maestro else "N/A"
                driver_str = f"{driver:.0f}" if driver else "N/A"

                # Generate notes about which backend unified selected
                notes = self._generate_backend_notes(unified, maestro, driver)

                lines.append(
                    f"| {op} | {platform} | {unified_str} | {maestro_str} | {driver_str} | {notes} |"
                )

        lines.append("")
        return lines

    def _generate_backend_notes(
        self,
        unified: Optional[float],
        maestro: Optional[float],
        driver: Optional[float],
    ) -> str:
        """Generate notes about backend selection."""
        if unified is None:
            return ""

        # Check if unified timing is close to maestro or driver
        if maestro and abs(unified - maestro) < 50:
            return "Unified → Maestro"
        if driver and abs(unified - driver) < 50:
            return "Unified → Driver"

        return ""

    def _format_single_backend_section(
        self,
        title: str,
        ops: dict[str, dict[str, float]],
    ) -> list[str]:
        """Format a single-backend operations section."""
        lines = [
            f"## {title}",
            "",
            "| Operation | Android (ms) | iOS (ms) |",
            "|-----------|--------------|----------|",
        ]

        for op in sorted(ops.keys()):
            platforms = ops[op]
            android = platforms.get("android")
            ios = platforms.get("ios")

            android_str = f"{android:.0f}" if android else "N/A"
            ios_str = f"{ios:.0f}" if ios else "N/A"

            lines.append(f"| {op} | {android_str} | {ios_str} |")

        lines.append("")
        return lines

    def _format_screenshot_section(
        self,
        results: dict[str, dict[str, float]],
    ) -> list[str]:
        """Format the screenshot comparison section."""
        lines = [
            "## Screenshot Comparison",
            "",
            "| Method | Android (ms) | iOS (ms) |",
            "|--------|--------------|----------|",
        ]

        # Map operation names to display names
        display_names = {
            "screenshot": "Maestro",
            "screenshot_maestro": "Maestro",
            "screenshot_adb": "ADB",
        }

        for op in sorted(results.keys()):
            platforms = results[op]
            display_name = display_names.get(op, op)
            android = platforms.get("android")
            ios = platforms.get("ios")

            android_str = f"{android:.0f}" if android else "N/A"
            ios_str = f"{ios:.0f}" if ios else "N/A"

            lines.append(f"| {display_name} | {android_str} | {ios_str} |")

        # Calculate speedup if we have both Maestro and ADB for Android
        maestro_android = results.get("screenshot", {}).get("android") or results.get(
            "screenshot_maestro", {}
        ).get("android")
        adb_android = results.get("screenshot_adb", {}).get("android")

        if maestro_android and adb_android:
            speedup = maestro_android / adb_android
            lines.append(f"| **Speedup** | **{speedup:.0f}x** | - |")

        lines.append("")
        return lines

    def _format_summary(self) -> list[str]:
        """Format the summary section."""
        total = len(self.collector.results)
        successful = len(self.collector.get_results(success_only=True))
        failed = total - successful

        lines = [
            "## Summary",
            "",
            f"- **Total operations:** {total}",
            f"- **Successful:** {successful}",
            f"- **Failed:** {failed}",
            "",
        ]

        if failed > 0:
            lines.append("### Failures")
            lines.append("")
            for result in self.collector.results:
                if not result.success:
                    lines.append(
                        f"- {result.operation}[{result.platform}/{result.backend}]: {result.error}"
                    )
            lines.append("")

        return lines
