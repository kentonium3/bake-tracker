---
id: WP01
title: Mode Navigation Reorder
lane: "done"
agent: null
review_status: null
created_at: 2026-01-15
---

# WP01: Mode Navigation Reorder

**Feature**: 055-workflow-aligned-navigation-cleanup
**Phase**: 1 | **Risk**: Low
**FR Coverage**: FR-001, FR-002, FR-003

---

## Objective

Reorder the mode navigation to match user workflow (Observe first, Deliver last) and add a placeholder Deliver mode.

---

## Context

### Current State
- `MODE_ORDER = ["CATALOG", "PLAN", "PURCHASE", "MAKE", "OBSERVE"]`
- 5 modes with Ctrl+1-5 shortcuts
- Observe is last but should be first (users check status first)

### Target State
- `MODE_ORDER = ["OBSERVE", "CATALOG", "PLAN", "PURCHASE", "MAKE", "DELIVER"]`
- 6 modes with Ctrl+1-6 shortcuts
- Deliver mode shows placeholder message

---

## Subtasks

- [ ] T001: Update MODE_ORDER in mode_manager.py
- [ ] T002: Add DELIVER to mode_tab_state initialization
- [ ] T003: Create deliver_mode.py with placeholder
- [ ] T004: Update main_window.py mode_configs and grid

---

## Implementation Details

### T001: Update MODE_ORDER (mode_manager.py:35)

```python
# Change from:
MODE_ORDER = ["CATALOG", "PLAN", "PURCHASE", "MAKE", "OBSERVE"]

# To:
MODE_ORDER = ["OBSERVE", "CATALOG", "PLAN", "PURCHASE", "MAKE", "DELIVER"]
```

### T002: Add DELIVER to mode_tab_state (mode_manager.py:41-47)

Add `"DELIVER": None` to the mode_tab_state dictionary initialization.

### T003: Create deliver_mode.py

Create `src/ui/modes/deliver_mode.py`:

```python
"""Deliver mode - placeholder for future delivery workflows."""
import customtkinter as ctk
from src.ui.modes.base_mode import BaseMode


class DeliverMode(BaseMode):
    """Placeholder mode for delivery workflows."""

    def __init__(self, parent, mode_manager):
        super().__init__(parent, mode_manager)
        self.mode_name = "DELIVER"

    def setup_tabs(self):
        """Create placeholder content instead of tabs."""
        # Placeholder message
        placeholder = ctk.CTkLabel(
            self.content_frame,
            text="Delivery workflows coming soon",
            font=ctk.CTkFont(size=18),
        )
        placeholder.pack(expand=True)

    def setup_dashboard(self):
        """No dashboard for placeholder mode."""
        pass

    def activate(self):
        """Activate the deliver mode."""
        super().activate()

    def refresh_all_tabs(self):
        """Nothing to refresh in placeholder mode."""
        pass
```

### T004: Update main_window.py

**mode_configs (lines 136-142)**: Update to new order with 6 modes:

```python
mode_configs = [
    ("Observe", "OBSERVE", "<Control-Key-1>"),
    ("Catalog", "CATALOG", "<Control-Key-2>"),
    ("Plan", "PLAN", "<Control-Key-3>"),
    ("Purchase", "PURCHASE", "<Control-Key-4>"),
    ("Make", "MAKE", "<Control-Key-5>"),
    ("Deliver", "DELIVER", "<Control-Key-6>"),
]
```

**mode_bar grid (lines 132-133)**: Change columns from 5 to 6.

**Import and instantiate**: Add DeliverMode import and registration with mode_manager.

---

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `src/ui/mode_manager.py` | MODIFY | 35, 41-47 |
| `src/ui/main_window.py` | MODIFY | 132-133, 136-142, imports |
| `src/ui/modes/deliver_mode.py` | NEW | - |

---

## Acceptance Criteria

- [ ] Modes appear in order: Observe, Catalog, Plan, Purchase, Make, Deliver
- [ ] Ctrl+1 activates Observe mode
- [ ] Ctrl+2 activates Catalog mode
- [ ] Ctrl+3 activates Plan mode
- [ ] Ctrl+4 activates Purchase mode
- [ ] Ctrl+5 activates Make mode
- [ ] Ctrl+6 activates Deliver mode
- [ ] Deliver mode shows "Delivery workflows coming soon" message
- [ ] Mode switching preserves tab state

---

## Testing

```bash
# Run app and verify:
# 1. Click each mode button - verify order matches
# 2. Press Ctrl+1 through Ctrl+6 - verify correct modes activate
# 3. Click Deliver - verify placeholder message displays
# 4. Switch modes - verify tab state preserved
```

## Activity Log

- 2026-01-16T02:12:07Z – null – lane=doing – Started implementation via workflow command
- 2026-01-16T02:37:23Z – null – lane=for_review – Completed mode navigation reorder: MODE_ORDER updated, DELIVER mode added, keyboard shortcuts updated to Ctrl+1-6
- 2026-01-16T04:29:02Z – null – lane=doing – Started review via workflow command
- 2026-01-16T04:30:22Z – null – lane=done – Review passed: all 9 acceptance criteria verified against implementation
