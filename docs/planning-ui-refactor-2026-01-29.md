# Planning Tab UI Refactor - Split-Pane Layout

**Date**: 2026-01-29
**Issue**: Planning workflow sections were inaccessible due to lack of scrolling
**Solution**: Implemented split-pane layout with scrollable planning container

---

## Problem Summary

The Planning tab had all required functionality implemented (recipe selection, FG selection, batch options, plan state controls, shopping summary, assembly status, production progress), but the UI was unusable because:

1. All planning sections were stacked vertically using grid layout with `weight=0`
2. The event data table had `weight=1`, taking up all available vertical space
3. Recipe selection alone used 300px height, making lower sections unreachable
4. No scrollable container existed for the planning sections
5. Users could not access sections below recipe selection

## Solution: Split-Pane Layout

Implemented Option A - a two-pane vertical split:

### Top Pane (Fixed)
- Action buttons (Create Event, Edit Event, Delete Event, Refresh)
- Event data table with **fixed 250px height**

### Bottom Pane (Expandable, Scrollable)
- New `CTkScrollableFrame` container that expands to fill available space
- All planning sections pack into this scrollable container
- Sections appear/disappear when events are selected/deselected

---

## Technical Changes

### Grid Configuration (Lines 168-173)

**Before:**
```python
self.grid_rowconfigure(0, weight=0)  # Action buttons
self.grid_rowconfigure(1, weight=1)  # Data table (took all space)
self.grid_rowconfigure(2, weight=0)  # Recipe selection
# ... rows 3-10 for other sections
```

**After:**
```python
self.grid_rowconfigure(0, weight=0)  # Action buttons
self.grid_rowconfigure(1, weight=0)  # Data table (fixed height)
self.grid_rowconfigure(2, weight=1)  # Planning container (expandable!)
self.grid_rowconfigure(3, weight=0)  # Status bar
```

### New Component: Planning Container (Lines 246-252)

```python
def _create_planning_container(self) -> None:
    """Create scrollable container for all planning sections."""
    self._planning_container = ctk.CTkScrollableFrame(
        self,
        fg_color="transparent",
    )
```

### Parent Widget Changes

All planning section frames now use `self._planning_container` as parent instead of `self`:

- `RecipeSelectionFrame` → parent: `self._planning_container`
- `FGSelectionFrame` → parent: `self._planning_container`
- `_batch_options_container` → parent: `self._planning_container`
- `_plan_state_frame` → parent: `self._planning_container`
- `_amendment_controls_frame` → parent: `self._planning_container`
- `ShoppingSummaryFrame` → parent: `self._planning_container`
- `AssemblyStatusFrame` → parent: `self._planning_container`
- `ProductionProgressFrame` → parent: `self._planning_container`

### Layout Method Changes

All `_show_*()` and `_hide_*()` methods changed from **grid** to **pack** layout:

**Before:**
```python
self._recipe_selection_frame.grid(
    row=2, column=0, sticky="ew",
    padx=PADDING_LARGE, pady=PADDING_MEDIUM
)
# ...
self._recipe_selection_frame.grid_forget()
```

**After:**
```python
self._recipe_selection_frame.pack(
    fill="x", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM
)
# ...
self._recipe_selection_frame.pack_forget()
```

### Data Table Height

```python
self.data_table = PlanningEventDataTable(
    self,
    select_callback=self._on_row_select,
    double_click_callback=self._on_row_double_click,
    height=100,  # Compact height - shows 2-3 events, maximizes planning space
)
```

**Rationale**: Once an event is selected, the user focuses on planning details, not browsing events. Keeping the table compact (2-3 visible rows) maximizes space for the scrollable planning sections where the actual work happens.

---

## Files Modified

1. **`src/ui/planning_tab.py`** - Complete refactor (lines 168-1260 affected)
   - Grid configuration
   - Added `_create_planning_container()` method
   - Updated all `_create_*_frame()` methods to use new parent
   - Updated all `_show_*()` and `_hide_*()` methods to use pack/pack_forget
   - Updated `_layout_widgets()` to reflect new structure

---

## Testing Completed

1. ✅ Module imports successfully (`python -c "from src.ui.planning_tab import PlanningTab"`)
2. ✅ No linter errors (`ReadLints` passed)
3. ✅ Syntax validation passed

---

## User Testing Checklist

To verify the fix works as expected:

### 1. Launch Application
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker
source venv/bin/activate
python src/main.py
```

### 2. Navigate to Planning Tab
- Click the "PLAN (Ctrl+3)" button in the top navigation

### 3. Verify Event Table Display
- Event table should be visible at the top
- Table height should be ~250px (5-6 rows visible)
- Action buttons (Create Event, Edit Event, Delete Event, Refresh) should be above table

### 4. Select an Event
- Click on any event in the table
- **Expected Result**: Planning sections should appear below the table

### 5. Verify Scrollable Container
- Planning sections should appear in this order:
  1. **Recipe Selection for [Event Name]**
  2. **Finished Goods for [Event Name]**
  3. **Batch Options** (if recipes selected)
  4. **Plan State: [Draft/Locked/etc]** + transition button
  5. **Shopping Summary** (ingredient gaps)
  6. **Assembly Status** (feasibility check)
  7. **Production Progress** (when in production)

- **Critical Test**: Can you scroll down through all sections?
- **Critical Test**: Are all sections visible by scrolling?

### 6. Verify Section Interactions
- [ ] Recipe selection checkboxes work
- [ ] Recipe Save/Cancel buttons work
- [ ] FG selection checkboxes work
- [ ] FG quantity inputs work
- [ ] FG Save/Cancel buttons work
- [ ] Batch options display and selection works
- [ ] Plan state transitions work (Lock Plan, Start Production, etc.)
- [ ] Shopping summary displays gaps
- [ ] Assembly status displays feasibility

### 7. Verify Layout Responsiveness
- [ ] Resize window - scrollable container should expand/contract
- [ ] Select different events - sections should update correctly
- [ ] Deselect event (click background) - sections should hide

---

## Known Limitations

1. **Event table is now fixed height** (100px) - shows 2-3 events at a time
   - If you have many events, you'll need to use the table's built-in scrolling
   - This trade-off maximizes space for planning sections (the main workflow)

2. **Planning sections use pack layout** - they appear in a fixed vertical order
   - Cannot reorder sections
   - Cannot collapse/expand individual sections (future enhancement)

---

## Rollback Instructions

If issues arise, revert the commit containing this refactor:

```bash
git log --oneline --grep="Planning" -5  # Find the commit
git revert <commit-hash>
```

---

## Future Enhancements

1. **Adjustable splitter** - Allow user to resize table/planning panes
2. **Collapsible sections** - Accordion-style sections to save vertical space
3. **Tabbed interface** - Group related sections (Recipe/FG, Batch Options, Status)
4. **Resizable table** - Add drag handle between table and planning sections
5. **Persistent layout preferences** - Save user's preferred pane sizes

---

## Architecture Notes

### Why Pack Instead of Grid?

The planning container uses `CTkScrollableFrame`, which internally uses a canvas with pack layout. Child widgets must use pack or place (not grid) to work correctly with the scrolling behavior.

### Why 100px Table Height?

Optimized for workflow focus:
- **100px shows 2-3 events** - enough to see current selection + 1-2 alternatives
- **Maximizes planning space** - the scrollable container gets the majority of the screen
- **Event selection is quick** - users can scroll within the table if they have many events
- **Planning is the focus** - once an event is selected, users spend their time in the planning sections

Alternative heights considered:
- 80px: Too cramped (barely 2 rows)
- 100px: **Optimal** (2-3 rows, good balance)
- 150px: Acceptable (3-4 rows, but wastes vertical space)
- 250px: Too tall (5-6 rows, planning sections too small)

### Component Parent Changes

All planning frames now have `_planning_container` as parent instead of the main tab. This is necessary for them to participate in the scrollable container's layout system.

---

## Related Documentation

- Original issue: User screenshot showing only Recipe Selection visible
- F068: Event Management & Planning Data Model
- F069: Recipe Selection for Event Planning
- F070: Finished Goods Filtering for Event Planning
- F071: Finished Goods Quantity Specification
- F073: Batch Calculation User Decisions
- F076: Assembly Feasibility & Single-Screen Planning
- F077: Plan State Management
- F078: Plan Snapshots & Amendments
- F079: Production Progress Display
