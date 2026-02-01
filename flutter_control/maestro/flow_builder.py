"""Build Maestro YAML flows from tool calls."""

from typing import Dict, Any, Optional, List
from pathlib import Path

from ..config import MAESTRO_FLOW_DIR


class FlowBuilder:
    """Builds Maestro YAML flow files."""

    def __init__(self, trace_id: str, app_id: str = ""):
        self.trace_id = trace_id
        self.app_id = app_id
        self.commands: List[str] = []

    def tap_text(self, text: str, index: int = 0) -> "FlowBuilder":
        """Tap on element by text."""
        if index > 0:
            self.commands.append(f"- tapOn:\n    text: \"{text}\"\n    index: {index}")
        else:
            self.commands.append(f"- tapOn: \"{text}\"")
        return self

    def tap_id(self, element_id: str) -> "FlowBuilder":
        """Tap on element by resource ID."""
        self.commands.append(f"- tapOn:\n    id: \"{element_id}\"")
        return self

    def long_press_text(self, text: str, partial: bool = True) -> "FlowBuilder":
        """Long press on element by text.

        Args:
            text: Text to find
            partial: If True, use partial matching (regex .*text.*)
        """
        if partial and not text.startswith(".*"):
            pattern = f".*{text}.*"
        else:
            pattern = text
        self.commands.append(f"- longPressOn: \"{pattern}\"")
        return self

    def double_tap_text(self, text: str, partial: bool = True) -> "FlowBuilder":
        """Double tap on element by text.

        Args:
            text: Text to find
            partial: If True, use partial matching (regex .*text.*)
        """
        if partial and not text.startswith(".*"):
            pattern = f".*{text}.*"
        else:
            pattern = text
        self.commands.append(f"- doubleTapOn: \"{pattern}\"")
        return self

    def enter_text(self, text: str, element_text: Optional[str] = None, element_id: Optional[str] = None) -> "FlowBuilder":
        """Enter text into a field.

        Args:
            text: Text to enter
            element_text: Optional text to tap first (uses partial matching)
            element_id: Optional resource ID to tap first (preferred for TextFields)
        """
        if element_id:
            # ID finder - preferred for input fields
            self.commands.append(f"- tapOn:\n    id: \"{element_id}\"")
        elif element_text:
            # Text finder - use partial matching for hint text
            self.commands.append(f"- tapOn: \".*{element_text}.*\"")
        self.commands.append(f"- inputText: \"{text}\"")
        return self

    def clear_text(self) -> "FlowBuilder":
        """Clear the current text field."""
        self.commands.append("- eraseText: 100")
        return self

    def swipe(self, direction: str) -> "FlowBuilder":
        """Swipe in a direction (UP, DOWN, LEFT, RIGHT)."""
        direction_upper = direction.upper()
        # Use swipe command with direction - works for all directions
        self.commands.append(f"- swipe:\n    direction: {direction_upper}")
        return self

    def assert_visible(self, text: str, contains: bool = True) -> "FlowBuilder":
        """Assert element with text is visible.

        Args:
            text: Text to find
            contains: If True, use partial matching (regex .*text.*)
        """
        if contains and not text.startswith(".*"):
            # Use regex for partial matching - more reliable
            pattern = f".*{text}.*"
        else:
            pattern = text
        self.commands.append(f"- assertVisible: \"{pattern}\"")
        return self

    def assert_not_visible(self, text: str, contains: bool = True) -> "FlowBuilder":
        """Assert element with text is not visible.

        Args:
            text: Text to find
            contains: If True, use partial matching (regex .*text.*)
        """
        if contains and not text.startswith(".*"):
            pattern = f".*{text}.*"
        else:
            pattern = text
        self.commands.append(f"- assertNotVisible: \"{pattern}\"")
        return self

    def wait_for(self, text: str, timeout_ms: int = 5000) -> "FlowBuilder":
        """Wait for element to appear."""
        self.commands.append(f"- extendedWaitUntil:\n    visible: \"{text}\"\n    timeout: {timeout_ms}")
        return self

    def launch_app(self) -> "FlowBuilder":
        """Launch the app (brings to foreground)."""
        self.commands.append("- launchApp")
        return self

    def screenshot(self, filename: str, output_dir: Optional[str] = None) -> "FlowBuilder":
        """Take a screenshot."""
        if output_dir:
            # Use absolute path - Maestro adds .png automatically
            full_path = f"{output_dir}/{filename}"
            self.commands.append(f"- takeScreenshot: {full_path}")
        else:
            self.commands.append(f"- takeScreenshot: {filename}")
        return self

    def build(self) -> str:
        """Build the YAML flow content."""
        if self.app_id:
            lines = [f"appId: {self.app_id}", "---"]
        else:
            # Empty appId - Maestro will use current foreground app
            lines = ["appId: ''", "---"]
        lines.extend(self.commands)
        return "\n".join(lines)

    def save(self) -> Path:
        """Save flow to file and return path."""
        content = self.build()
        flow_file = MAESTRO_FLOW_DIR / f"{self.trace_id}.yaml"
        flow_file.write_text(content)
        return flow_file
