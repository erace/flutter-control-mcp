"""Unified API - auto-select backend with fallback."""

from .backend_selector import BackendSelector, Backend
from .executor import UnifiedExecutor

__all__ = ["BackendSelector", "Backend", "UnifiedExecutor"]
