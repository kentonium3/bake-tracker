---
work_package_id: WP05
title: Planning Tab Integration
lane: "done"
dependencies:
- WP01
base_branch: 076-assembly-feasibility-single-screen-planning-WP04
base_commit: 2d1fd7d5b1916d6ac510dd1cdb1f1970e9eda2fb
created_at: '2026-01-27T22:13:06.616254+00:00'
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 3 - Integration
assignee: ''
agent: "claude"
shell_pid: "51577"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-27T15:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Planning Tab Integration

## Implementation Command

```bash
spec-kitty implement WP05 --base WP04
```

**Note**: This WP depends on WP01 (service), WP03 (shopping frame), and WP04 (assembly frame). Use `--base WP04` assuming WP04 was the last to complete. If WP03 was last, use `--base WP03`.

## Objectives & Success Criteria

Integrate ShoppingSummaryFrame and AssemblyStatusFrame into planning_tab.py with real-time update propagation.

**Success Criteria**:
- [ ] Shopping summary panel visible in planning tab (row 5)
- [ ] Assembly status panel visible in planning tab (row 6)
- [ ] Selecting an event shows both panels with current data
- [ ] Saving batch decisions updates both panels automatically
- [ ] FG/Recipe changes cascade to shopping and assembly panels

## Context & Constraints

**Reference Documents**:
- `kitty-specs/076-assembly-feasibility-single-screen-planning/plan.md` - D3, D4 design decisions
- `src/ui/planning_tab.py` - Current implementation (~792 lines)

**Current Layout** (from planning_tab.py):
```
Row 0: Action buttons
Row 1: Data table (event list)
Row 2: Recipe selection frame
Row 3: FG selection frame
Row 4: Batch options frame
Row 5: Status bar
```

**Target Layout**:
```
Row 0: Action buttons
Row 1: Data table (event list)
Row 2: Recipe selection frame
Row 3: FG selection frame
Row 4: Batch options frame
Row 5: Shopping summary frame (NEW)
Row 6: Assembly status frame (NEW)
Row 7: Status bar (SHIFTED)
```

**Update Propagation Chain** (from plan.md D4):
```
Recipe change → _refresh_fg_selection() → _load_batch_options() → _update_shopping_summary() → _update_assembly_status()
FG quantity change → _load_batch_options() → _update_shopping_summary() → _update_assembly_status()
Batch decision save → _update_shopping_summary() → _update_assembly_status()
```

## Subtasks & Detailed Guidance

### Subtask T018 – Add ShoppingSummaryFrame to Planning Tab

**Purpose**: Integrate the shopping summary widget into the planning tab layout.

**Steps**:
1. Add import at top of `src/ui/planning_tab.py`:

```python
from src.ui.components.shopping_summary_frame import ShoppingSummaryFrame
```

2. Update grid row configuration in `__init__`:

```python
        # Configure grid (update row weights)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Action buttons
        self.grid_rowconfigure(1, weight=1)  # Data table
        self.grid_rowconfigure(2, weight=0)  # Recipe selection frame
        self.grid_rowconfigure(3, weight=0)  # FG selection frame (F070)
        self.grid_rowconfigure(4, weight=0)  # Batch options frame (F073)
        self.grid_rowconfigure(5, weight=0)  # Shopping summary frame (F076)
        self.grid_rowconfigure(6, weight=0)  # Assembly status frame (F076)
        self.grid_rowconfigure(7, weight=0)  # Status bar
```

3. Add widget creation method (call from `__init__` after `_create_batch_options_frame()`):

```python
    def _create_shopping_summary_frame(self) -> None:
        """Create the shopping summary frame (F076)."""
        self._shopping_summary_frame = ShoppingSummaryFrame(self)
        # Frame starts hidden - shown when event selected
```

4. Update `__init__` to call the new creation method:

```python
        # Build UI
        self._create_action_buttons()
        self._create_data_table()
        self._create_recipe_selection_frame()
        self._create_fg_selection_frame()
        self._create_batch_options_frame()
        self._create_shopping_summary_frame()  # ADD THIS
        # ... assembly status frame added in T019
```

5. Update `_layout_widgets` to shift status bar to row 7:

```python
        # Status bar at bottom (row 7 - shifted for F076)
        self.status_frame.grid(
            row=7, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=(0, PADDING_LARGE)
        )
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Import added
- [ ] Grid rows updated
- [ ] Widget creation method added
- [ ] Status bar moved to row 7

---

### Subtask T019 – Add AssemblyStatusFrame to Planning Tab

**Purpose**: Integrate the assembly status widget into the planning tab layout.

**Steps**:
1. Add import at top of `src/ui/planning_tab.py`:

```python
from src.ui.components.assembly_status_frame import AssemblyStatusFrame
```

2. Add widget creation method:

```python
    def _create_assembly_status_frame(self) -> None:
        """Create the assembly status frame (F076)."""
        self._assembly_status_frame = AssemblyStatusFrame(self)
        # Frame starts hidden - shown when event selected
```

3. Update `__init__` to call the creation method:

```python
        # Build UI
        self._create_action_buttons()
        self._create_data_table()
        self._create_recipe_selection_frame()
        self._create_fg_selection_frame()
        self._create_batch_options_frame()
        self._create_shopping_summary_frame()
        self._create_assembly_status_frame()  # ADD THIS
        self._create_status_bar()
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Import added
- [ ] Widget creation method added
- [ ] Called in correct order in `__init__`

---

### Subtask T020 – Implement Update Callback Methods

**Purpose**: Create methods to update shopping and assembly displays.

**Steps**:
1. Add import for services:

```python
from src.services.inventory_gap_service import analyze_inventory_gaps
from src.services.assembly_feasibility_service import calculate_assembly_feasibility
```

2. Add `_update_shopping_summary` method:

```python
    def _update_shopping_summary(self) -> None:
        """Update the shopping summary panel with current gap analysis."""
        if self._selected_event_id is None:
            self._shopping_summary_frame.clear()
            return

        try:
            gap_result = analyze_inventory_gaps(self._selected_event_id)
            self._shopping_summary_frame.update_summary(gap_result)
        except Exception as e:
            # Log but don't fail - shopping summary is informational
            print(f"Warning: Could not update shopping summary: {e}")
            self._shopping_summary_frame.clear()
```

3. Add `_update_assembly_status` method:

```python
    def _update_assembly_status(self) -> None:
        """Update the assembly status panel with current feasibility."""
        if self._selected_event_id is None:
            self._assembly_status_frame.clear()
            return

        try:
            feasibility = calculate_assembly_feasibility(self._selected_event_id)
            self._assembly_status_frame.update_status(feasibility)
        except Exception as e:
            # Log but don't fail - assembly status is informational
            print(f"Warning: Could not update assembly status: {e}")
            self._assembly_status_frame.clear()
```

4. Add methods to show/hide the frames:

```python
    def _show_shopping_summary(self) -> None:
        """Show and update shopping summary frame."""
        self._update_shopping_summary()
        self._shopping_summary_frame.grid(
            row=5, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _hide_shopping_summary(self) -> None:
        """Hide the shopping summary frame."""
        self._shopping_summary_frame.grid_forget()
        self._shopping_summary_frame.clear()

    def _show_assembly_status(self) -> None:
        """Show and update assembly status frame."""
        self._update_assembly_status()
        self._assembly_status_frame.grid(
            row=6, column=0, sticky="ew",
            padx=PADDING_LARGE, pady=PADDING_MEDIUM
        )

    def _hide_assembly_status(self) -> None:
        """Hide the assembly status frame."""
        self._assembly_status_frame.grid_forget()
        self._assembly_status_frame.clear()
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Service imports added
- [ ] Update methods handle errors gracefully
- [ ] Show/hide methods position at correct rows

---

### Subtask T021 – Wire Callbacks to Save Operations

**Purpose**: Connect update methods to existing save operations for real-time updates.

**Steps**:
1. Update `_on_row_select` to show new panels:

```python
    def _on_row_select(self, event: Optional[Event]) -> None:
        """Handle row selection."""
        # ... existing code up to showing batch options ...

        if self.selected_event:
            self._update_status(f"Selected: {self.selected_event.name}")
            self._selected_event_id = self.selected_event.id
            self._show_recipe_selection(self.selected_event.id)
            self._show_fg_selection(self.selected_event.id)
            self._show_batch_options(self.selected_event.id)
            self._show_shopping_summary()       # ADD THIS
            self._show_assembly_status()        # ADD THIS
        else:
            self._update_status("Ready")
            self._selected_event_id = None
            self._hide_recipe_selection()
            self._hide_fg_selection()
            self._hide_batch_options()
            self._hide_shopping_summary()       # ADD THIS
            self._hide_assembly_status()        # ADD THIS
```

2. Update `refresh` to hide new panels:

```python
    def refresh(self) -> None:
        """Refresh the event list from database."""
        # ... existing code ...

        # Clear selection and hide all panels
        self.selected_event = None
        self._selected_event_id = None
        self._hide_recipe_selection()
        self._hide_fg_selection()
        self._hide_batch_options()
        self._hide_shopping_summary()       # ADD THIS
        self._hide_assembly_status()        # ADD THIS
        self._update_button_states()
```

3. Update `_on_recipe_selection_save` to trigger cascading updates:

At the end of `_on_recipe_selection_save`, after `_refresh_fg_selection()`:

```python
            # F076: Cascade updates to shopping and assembly
            self._update_shopping_summary()
            self._update_assembly_status()
```

4. Update `_on_fg_selection_save` to trigger cascading updates:

At the end of `_on_fg_selection_save`, after showing success message:

```python
            # F076: Reload batch options and update downstream panels
            self._load_batch_options()
            self._update_shopping_summary()
            self._update_assembly_status()
```

5. Update `_save_batch_decisions` to trigger cascading updates:

At the end of `_save_batch_decisions`, after success:

```python
            # F076: Update shopping and assembly status
            self._update_shopping_summary()
            self._update_assembly_status()
```

**Files**: `src/ui/planning_tab.py`

**Validation**:
- [ ] Event selection shows shopping and assembly panels
- [ ] Recipe save triggers shopping/assembly update
- [ ] FG save triggers batch reload + shopping/assembly update
- [ ] Batch save triggers shopping/assembly update
- [ ] Refresh hides all new panels

## Integration Test Checklist

After implementation, manually test:

1. **Launch app**: `python src/main.py`
2. **Navigate to Planning tab**
3. **Create or select an event**
4. **Verify**: Shopping summary and assembly status panels appear
5. **Add recipes**: Verify FG list updates
6. **Add FGs with quantities**: Verify batch options update
7. **Save batch decisions**: Verify shopping summary and assembly status update
8. **Change a batch decision**: Verify updates cascade

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout overflow | Test on 1920x1080; use compact panels |
| Update loop | Updates only cascade forward, not backward |
| Performance | Updates are individual service calls, not nested |

## Definition of Done Checklist

- [ ] ShoppingSummaryFrame integrated at row 5
- [ ] AssemblyStatusFrame integrated at row 6
- [ ] Status bar moved to row 7
- [ ] Event selection shows both new panels
- [ ] Recipe save cascades to shopping/assembly
- [ ] FG save cascades to batch/shopping/assembly
- [ ] Batch save cascades to shopping/assembly
- [ ] Refresh hides all panels
- [ ] No linting errors
- [ ] Manual integration test passes

## Review Guidance

- Verify all callback chains are wired correctly
- Check that panels appear/hide with event selection
- Confirm no circular update loops
- Test with real data if possible

## Activity Log

- 2026-01-27T15:30:00Z – system – lane=planned – Prompt created.
- 2026-01-27T22:16:25Z – claude – shell_pid=48531 – lane=for_review – Planning tab integration complete: shopping summary at row 5, assembly status at row 6, update propagation wired
- 2026-01-27T22:22:38Z – claude – shell_pid=51577 – lane=doing – Started review via workflow command
- 2026-01-27T22:23:49Z – claude – shell_pid=51577 – lane=done – Review passed: planning tab integration complete
