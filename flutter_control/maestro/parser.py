"""Parse Maestro CLI output."""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MaestroResult:
    """Result from a Maestro command."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    error_message: Optional[str] = None
    output_dir: Optional[str] = None  # Test output directory
    screenshot_base64: Optional[str] = None  # Base64-encoded screenshot

    def to_dict(self):
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "output_dir": self.output_dir,
            "screenshot_base64": self.screenshot_base64,
        }


def parse_maestro_output(exit_code: int, stdout: str, stderr: str) -> MaestroResult:
    """Parse Maestro CLI output into structured result."""
    success = exit_code == 0
    error_message = None
    output_dir = None

    combined = stdout + stderr

    # Extract test output directory (appears in both success and failure)
    # Maestro outputs paths like: /Users/.../.maestro/tests/2026-01-31_134000
    dir_match = re.search(r"(/[^\s]+/\.maestro/tests/\d{4}-\d{2}-\d{2}_\d+)", combined)
    if dir_match:
        output_dir = dir_match.group(1)

    if not success:
        if "Unable to find" in combined or "Element not found" in combined:
            match = re.search(r"Unable to find[^:]*: (.+)", combined)
            if match:
                error_message = f"Element not found: {match.group(1)}"
            else:
                error_message = "Element not found"
        elif "Timeout" in combined or "timed out" in combined:
            error_message = "Timeout waiting for element"
        elif "No app" in combined or "not running" in combined:
            error_message = "App not running on device"
        else:
            # Look for more specific error messages
            lines = [l.strip() for l in combined.split("\n") if l.strip()]
            # Filter out the output dir from error message
            filtered = [l for l in lines if not l.startswith("/") or "maestro/tests" not in l]
            if filtered:
                error_message = filtered[-1][:200]
            else:
                error_message = f"Maestro failed with exit code {exit_code}"

    return MaestroResult(
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error_message=error_message,
        output_dir=output_dir,
    )
