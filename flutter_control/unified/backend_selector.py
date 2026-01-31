"""Backend selector - determines which backend to use based on finder."""

from enum import Enum
from typing import Dict, Any, List, Tuple


class Backend(Enum):
    """Available backends."""
    MAESTRO = "maestro"
    DRIVER = "driver"


class BackendSelector:
    """Selects backend based on finder type."""

    # Finders that work best with Maestro (accessibility layer)
    MAESTRO_FINDERS = {"text", "id", "contentDescription"}

    # Finders that require Flutter Driver (widget tree)
    DRIVER_FINDERS = {"key", "type", "tooltip", "semanticsLabel"}

    # Finders that work with both
    BOTH_FINDERS = {"text", "semanticsLabel"}

    @classmethod
    def select(cls, finder: Dict[str, Any]) -> Tuple[Backend, str]:
        """
        Select primary backend based on finder.

        Returns:
            Tuple of (primary_backend, reason)
        """
        finder_keys = set(finder.keys()) - {"first", "index", "backend", "timeout"}

        # Check if backend is explicitly specified
        if "backend" in finder:
            explicit = finder["backend"].lower()
            if explicit == "maestro":
                return Backend.MAESTRO, "explicit backend=maestro"
            elif explicit == "driver":
                return Backend.DRIVER, "explicit backend=driver"

        # Check for driver-only finders first (they're more specific)
        driver_only = cls.DRIVER_FINDERS - cls.BOTH_FINDERS
        if finder_keys & driver_only:
            key = (finder_keys & driver_only).pop()
            return Backend.DRIVER, f"{key} finder requires driver"

        # Check for maestro-preferred finders
        maestro_preferred = cls.MAESTRO_FINDERS - cls.BOTH_FINDERS
        if finder_keys & maestro_preferred:
            key = (finder_keys & maestro_preferred).pop()
            return Backend.MAESTRO, f"{key} finder prefers maestro"

        # For finders that work with both, prefer Maestro (more stable)
        if finder_keys & cls.BOTH_FINDERS:
            key = (finder_keys & cls.BOTH_FINDERS).pop()
            return Backend.MAESTRO, f"{key} finder (maestro preferred)"

        # Default to Maestro
        return Backend.MAESTRO, "default"

    @classmethod
    def get_fallback_order(cls, finder: Dict[str, Any]) -> List[Backend]:
        """
        Get the order of backends to try (with fallback).

        Returns:
            List of backends to try in order
        """
        primary, _ = cls.select(finder)

        # For driver-only finders, don't fall back to Maestro (it won't work)
        driver_only = cls.DRIVER_FINDERS - cls.BOTH_FINDERS
        finder_keys = set(finder.keys()) - {"first", "index", "backend", "timeout"}
        if finder_keys & driver_only:
            return [Backend.DRIVER]

        # For maestro-only finders, don't fall back to Driver
        maestro_only = cls.MAESTRO_FINDERS - cls.BOTH_FINDERS
        if finder_keys & maestro_only:
            return [Backend.MAESTRO]

        # For finders that work with both, try primary first then fallback
        if primary == Backend.MAESTRO:
            return [Backend.MAESTRO, Backend.DRIVER]
        else:
            return [Backend.DRIVER, Backend.MAESTRO]

    @classmethod
    def can_use_backend(cls, finder: Dict[str, Any], backend: Backend) -> bool:
        """Check if a finder can be used with a specific backend."""
        finder_keys = set(finder.keys()) - {"first", "index", "backend", "timeout"}

        if backend == Backend.MAESTRO:
            # Maestro can't use driver-only finders
            driver_only = cls.DRIVER_FINDERS - cls.BOTH_FINDERS
            return not bool(finder_keys & driver_only)
        else:
            # Driver can use all finders
            return True
