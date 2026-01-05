"""Base classes for mode architecture.

This module provides foundational UI components for the 5-mode workflow:
- StandardTabLayout: Consistent layout pattern for all tabs
- BaseMode: Abstract base class for mode containers
"""

from .standard_tab_layout import StandardTabLayout
from .base_mode import BaseMode

__all__ = ["StandardTabLayout", "BaseMode"]
