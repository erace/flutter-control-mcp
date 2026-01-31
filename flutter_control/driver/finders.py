"""Widget finders for Flutter Driver."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


class Finder(ABC):
    """Base class for widget finders."""

    @abstractmethod
    def serialize(self) -> Dict[str, Any]:
        """Serialize to Flutter Driver JSON format."""
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finder":
        """Create a Finder from a dictionary (MCP tool arguments)."""
        if "key" in data:
            return ByKey(data["key"])
        elif "type" in data:
            return ByType(data["type"])
        elif "text" in data:
            return ByText(data["text"])
        elif "tooltip" in data:
            return ByTooltip(data["tooltip"])
        elif "semanticsLabel" in data:
            return BySemanticsLabel(data["semanticsLabel"])
        else:
            raise ValueError(f"Unknown finder type: {data}")


@dataclass
class ByKey(Finder):
    """Find widget by ValueKey<String>."""

    key: str

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "ByValueKey",
            "keyValueString": self.key,
            "keyValueType": "String",
        }


@dataclass
class ByType(Finder):
    """Find widget by type name."""

    type_name: str

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "ByType",
            "type": self.type_name,
        }


@dataclass
class ByText(Finder):
    """Find widget by visible text."""

    text: str

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "ByText",
            "text": self.text,
        }


@dataclass
class ByTooltip(Finder):
    """Find widget by tooltip."""

    tooltip: str

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "ByTooltipMessage",
            "text": self.tooltip,
        }


@dataclass
class BySemanticsLabel(Finder):
    """Find widget by semantics label."""

    label: str
    is_regex: bool = False

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "BySemanticsLabel",
            "label": self.label,
            "isRegExp": self.is_regex,
        }


@dataclass
class ByAncestor(Finder):
    """Find widget by ancestor relationship."""

    of: Finder
    matching: Finder
    match_root: bool = False
    first_match_only: bool = False

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "Ancestor",
            "of": self.of.serialize(),
            "matching": self.matching.serialize(),
            "matchRoot": self.match_root,
            "firstMatchOnly": self.first_match_only,
        }


@dataclass
class ByDescendant(Finder):
    """Find widget by descendant relationship."""

    of: Finder
    matching: Finder
    match_root: bool = False
    first_match_only: bool = False

    def serialize(self) -> Dict[str, Any]:
        return {
            "finderType": "Descendant",
            "of": self.of.serialize(),
            "matching": self.matching.serialize(),
            "matchRoot": self.match_root,
            "firstMatchOnly": self.first_match_only,
        }
