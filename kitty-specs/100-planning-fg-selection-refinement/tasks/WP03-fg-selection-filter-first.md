---
work_package_id: WP03
title: FG Selection Filter-First with Persistence
lane: "done"
dependencies:
- WP01
base_branch: 100-planning-fg-selection-refinement-WP01
base_commit: 6c92909fd76434cb9e671aba7680c5efcfb2be4a
created_at: '2026-02-09T21:59:05.619014+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - FG Filtered Selection
assignee: ''
agent: "gemini"
shell_pid: "26148"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-09T21:25:52Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 -- FG Selection Filter-First with Persistence

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

Depends on WP01 (uses `get_filtered_available_fgs()` and `get_available_recipe_categories_for_event()`).

---

## Objectives & Success Criteria

Replace the auto-load-all FG selection with a three-filter blank-start pattern. Selections and quantities persist across filter changes. This implements User Stories 2 and 3 from the spec.

**Success Criteria:**
- FG selection frame starts blank with placeholder "Select filters to see available finished goods"
- Three independent filter dropdowns visible: Recipe Category, Item Type, Yield Type
- FGs load only after at least one filter is applied
- Filters combine with AND logic
- Checked FGs remain selected when filters change (even if hidden from view)
- Quantities entered for FGs persist when filters change
- Returning to original filter shows checkboxes and quantities restored

## Context & Constraints

- **Spec**: US2 (6 acceptance scenarios), US3 (4 acceptance scenarios)
- **Plan**: Phase 2, Design Decisions D1, D3, D4, D5
- **Current code**: `src/ui/components/fg_selection_frame.py` (357 lines, checkbox + qty grid)
- **Current orchestration**: `src/ui/planning_tab.py` lines 652-691 (`_show_fg_selection`)
- **WP01 service functions**: `get_filtered_available_fgs()`, `get_available_recipe_categories_for_event()`

**Key Constraints:**
- FG frame has existing quantity entry fields per row (F071) — preserve this pattern
- Existing `populate_finished_goods()` and `set_selected_with_quantities()` methods exist — refactor to work with filters
- session management: service calls need a session, use `session_scope()` from UI layer
- Event must be in DRAFT state for modifications (checked by service layer on save)

## Subtasks & Detailed Guidance

### Subtask T008 -- Add three filter dropdowns and blank-start to FGSelectionFrame

- **Purpose**: Add recipe category, item type, and yield type filter dropdowns above the scroll area. Start with blank content.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: [P] Can start alongside T009

**Steps**:

1. **Add imports** at top:
```python
from src.services import event_service, recipe_category_service
from src.services.database import session_scope
from src.models.assembly_type import AssemblyType
```

2. **Add filter state** to `__init__`:
```python
# Filter state
self._event_id: Optional[int] = None
self._current_recipe_category: Optional[str] = None
self._current_assembly_type: Optional[str] = None
self._current_yield_type: Optional[str] = None
```

3. **Add filter frame** in `_create_widgets()`, between header and scroll frame:
```python
# Filter frame with three dropdowns
self._filter_frame = ctk.CTkFrame(self, fg_color="transparent")
self._filter_frame.pack(fill="x", padx=10, pady=(0, 5))

# Row 1: Recipe Category
cat_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
cat_row.pack(fill="x", pady=2)
ctk.CTkLabel(cat_row, text="Recipe Category:", width=120, anchor="w").pack(side="left")
self._recipe_cat_var = ctk.StringVar(value="")
self._recipe_cat_dropdown = ctk.CTkComboBox(
    cat_row, variable=self._recipe_cat_var,
    values=[], command=self._on_filter_change,
    width=200, state="readonly",
)
self._recipe_cat_dropdown.pack(side="left", padx=5)

# Row 2: Item Type
type_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
type_row.pack(fill="x", pady=2)
ctk.CTkLabel(type_row, text="Item Type:", width=120, anchor="w").pack(side="left")
self._item_type_var = ctk.StringVar(value="")
self._item_type_dropdown = ctk.CTkComboBox(
    type_row, variable=self._item_type_var,
    values=["All Types", "Finished Units", "Assemblies"],
    command=self._on_filter_change,
    width=200, state="readonly",
)
self._item_type_dropdown.pack(side="left", padx=5)

# Row 3: Yield Type
yield_row = ctk.CTkFrame(self._filter_frame, fg_color="transparent")
yield_row.pack(fill="x", pady=2)
ctk.CTkLabel(yield_row, text="Yield Type:", width=120, anchor="w").pack(side="left")
self._yield_type_var = ctk.StringVar(value="")
self._yield_type_dropdown = ctk.CTkComboBox(
    yield_row, variable=self._yield_type_var,
    values=["All Yields", "EA", "SERVING"],
    command=self._on_filter_change,
    width=200, state="readonly",
)
self._yield_type_dropdown.pack(side="left", padx=5)
```

4. **Add placeholder** in scroll frame:
```python
self._placeholder_label = ctk.CTkLabel(
    self._scroll_frame,
    text="Select filters to see available finished goods",
    font=ctk.CTkFont(size=12, slant="italic"),
    text_color=("gray50", "gray60"),
)
self._placeholder_label.pack(pady=40)
```

5. **Add method** to set the event and populate category dropdown:
```python
def set_event(self, event_id: int) -> None:
    """Set the event context and populate filter options."""
    self._event_id = event_id
    with session_scope() as session:
        categories = event_service.get_available_recipe_categories_for_event(
            event_id, session
        )
    cat_values = ["All Categories"] + categories
    self._recipe_cat_dropdown.configure(values=cat_values)
```

### Subtask T009 -- Implement AND-combine filter logic

- **Purpose**: When any filter changes, query the service layer with all current filter values.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: [P] Can start alongside T008

**Steps**:

1. **Implement `_on_filter_change(choice: str)`**:
```python
def _on_filter_change(self, choice: str) -> None:
    """Handle any filter dropdown change."""
    if self._event_id is None:
        return

    # Read current filter values
    recipe_cat = self._recipe_cat_var.get()
    item_type = self._item_type_var.get()
    yield_type = self._yield_type_var.get()

    # Check if at least one filter is set (FR-007)
    if not recipe_cat and not item_type and not yield_type:
        return  # Keep showing placeholder

    # Convert display values to service parameters
    cat_param = None if recipe_cat in ("", "All Categories") else recipe_cat
    type_param = None
    if item_type == "Finished Units":
        type_param = "bare"
    elif item_type == "Assemblies":
        type_param = "bundle"
    yield_param = None if yield_type in ("", "All Yields") else yield_type

    # Save current selections before re-render
    self._save_current_selections()

    # Query service
    with session_scope() as session:
        fgs = event_service.get_filtered_available_fgs(
            self._event_id, session,
            recipe_category=cat_param,
            assembly_type=type_param,
            yield_type=yield_param,
        )

    self._render_finished_goods(fgs)
```

2. **Implement `_render_finished_goods(fgs: List[FinishedGood])`**: Extract the rendering logic from `populate_finished_goods()` into this method. After rendering, restore checkboxes and quantities from persistence dicts.

### Subtask T010 -- Add selection and quantity persistence state

- **Purpose**: Maintain `_selected_fg_ids` and `_fg_quantities` dicts that survive filter changes.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T008 structure)

**Steps**:

1. **Add persistence state** to `__init__`:
```python
# Selection persistence (survives filter changes)
self._selected_fg_ids: set = set()
self._fg_quantities: dict = {}  # fg_id -> int quantity
```

2. **Add `_save_current_selections()` method**:
```python
def _save_current_selections(self) -> None:
    """Save current UI state to persistence dicts."""
    for fg_id, var in self._checkbox_vars.items():
        if var.get():
            self._selected_fg_ids.add(fg_id)
            # Save quantity if valid
            qty_var = self._quantity_vars.get(fg_id)
            if qty_var:
                qty_text = qty_var.get().strip()
                try:
                    qty = int(qty_text)
                    if qty > 0:
                        self._fg_quantities[fg_id] = qty
                except (ValueError, TypeError):
                    pass  # Keep existing quantity in dict
        else:
            self._selected_fg_ids.discard(fg_id)
            # Don't remove from _fg_quantities — user might re-check later
```

3. **Modify checkbox command** to update persistence on each click:
```python
# In checkbox creation, update command:
checkbox = ctk.CTkCheckBox(
    self._scroll_frame,
    text=fg.display_name,
    variable=var,
    command=lambda fid=fg.id: self._on_checkbox_toggle(fid),
)

def _on_checkbox_toggle(self, fg_id: int) -> None:
    """Handle checkbox toggle and update persistence."""
    var = self._checkbox_vars.get(fg_id)
    if var:
        if var.get():
            self._selected_fg_ids.add(fg_id)
        else:
            self._selected_fg_ids.discard(fg_id)
    self._update_count()
```

4. **Modify quantity trace** to update persistence on each change:
```python
def _on_quantity_change(self, fg_id: int) -> None:
    """Handle quantity entry change and update persistence."""
    qty_var = self._quantity_vars.get(fg_id)
    if qty_var:
        qty_text = qty_var.get().strip()
        try:
            qty = int(qty_text)
            if qty > 0:
                self._fg_quantities[fg_id] = qty
        except (ValueError, TypeError):
            pass
    self._validate_quantity(fg_id)
```

### Subtask T011 -- Restore checkbox and quantity state on re-render

- **Purpose**: When `_render_finished_goods()` is called after a filter change, restore checked state and quantities from persistence dicts.
- **Files**: `src/ui/components/fg_selection_frame.py`
- **Parallel?**: No (depends on T010)

**Steps**:

1. In `_render_finished_goods()`, after creating each row:
```python
# Restore selection state from persistence
var = ctk.BooleanVar(value=fg.id in self._selected_fg_ids)
self._checkbox_vars[fg.id] = var

# Restore quantity from persistence
qty_var = ctk.StringVar(value="")
if fg.id in self._fg_quantities:
    qty_var.set(str(self._fg_quantities[fg.id]))
self._quantity_vars[fg.id] = qty_var
```

2. **Modify `get_selected()`** to return from persistence state:
```python
def get_selected(self) -> List[Tuple[int, int]]:
    """Get ALL selected FGs with quantities (including hidden ones)."""
    self._save_current_selections()
    return [
        (fg_id, self._fg_quantities.get(fg_id, 0))
        for fg_id in self._selected_fg_ids
        if self._fg_quantities.get(fg_id, 0) > 0
    ]
```

3. **Modify `get_selected_ids()`** to return from persistence:
```python
def get_selected_ids(self) -> List[int]:
    """Get ALL selected FG IDs (including hidden ones)."""
    self._save_current_selections()
    return list(self._selected_fg_ids)
```

4. **Modify `_update_count()`** to show total including hidden:
```python
def _update_count(self) -> None:
    visible_selected = sum(1 for var in self._checkbox_vars.values() if var.get())
    total_visible = len(self._checkbox_vars)
    total_selected = len(self._selected_fg_ids)
    if total_selected > visible_selected:
        self._count_label.configure(
            text=f"{visible_selected} of {total_visible} shown ({total_selected} total selected)"
        )
    else:
        self._count_label.configure(
            text=f"{visible_selected} of {total_visible} selected"
        )
```

5. **Add `clear_selections()` method** (needed by WP04):
```python
def clear_selections(self) -> None:
    """Clear all FG selections and quantities."""
    self._selected_fg_ids.clear()
    self._fg_quantities.clear()
    for var in self._checkbox_vars.values():
        var.set(False)
    for qty_var in self._quantity_vars.values():
        qty_var.set("")
    self._update_count()
```

6. **Add `set_selected_with_quantities()` update** to populate persistence:
```python
def set_selected_with_quantities(self, fg_quantities: List[Tuple[int, int]]) -> None:
    """Set selected FGs with quantities (updates persistence)."""
    self._selected_fg_ids.clear()
    self._fg_quantities.clear()
    for fg_id, qty in fg_quantities:
        self._selected_fg_ids.add(fg_id)
        self._fg_quantities[fg_id] = qty
    # Update visible checkboxes
    for fg_id, checkbox_var in self._checkbox_vars.items():
        if fg_id in self._selected_fg_ids:
            checkbox_var.set(True)
            if fg_id in self._quantity_vars:
                self._quantity_vars[fg_id].set(str(self._fg_quantities.get(fg_id, "")))
        else:
            checkbox_var.set(False)
            if fg_id in self._quantity_vars:
                self._quantity_vars[fg_id].set("")
    self._update_count()
```

### Subtask T012 -- Update planning_tab.py orchestration for filtered FG selection

- **Purpose**: Modify the planning tab to work with the new filter-first FG selection.
- **Files**: `src/ui/planning_tab.py`
- **Parallel?**: No (depends on T008-T011)

**Steps**:

1. **Modify `_show_fg_selection()`** (around line 652):
   - Instead of calling `get_available_finished_goods()` and `populate_finished_goods()`:
   - Call `_fg_selection_frame.set_event(event_id)` to set context and load filter options
   - Call `_fg_selection_frame.set_selected_with_quantities(qty_tuples)` to restore existing selections
   - Do NOT auto-populate FGs — let the frame start blank

2. **Before**:
```python
def _show_fg_selection(self, event_id):
    with session_scope() as session:
        available_fgs = get_available_finished_goods(event_id, session)
        qty_tuples = get_event_fg_quantities(session, event_id)
    self._fg_selection_frame.populate_finished_goods(available_fgs, event_name)
    self._fg_selection_frame.set_selected_with_quantities([(fg.id, qty) for fg, qty in qty_tuples])
```

3. **After**:
```python
def _show_fg_selection(self, event_id):
    self._fg_selection_frame.set_event(event_id)
    with session_scope() as session:
        qty_tuples = get_event_fg_quantities(session, event_id)
    self._fg_selection_frame.set_selected_with_quantities(
        [(fg.id, qty) for fg, qty in qty_tuples]
    )
    # Frame starts blank; user selects filters to see FGs
```

## Risks & Mitigations

- **Risk**: FG objects from service call become detached after session_scope exits
  - **Mitigation**: Only use FG.id, FG.display_name, FG.assembly_type in rendering — these are simple attributes that survive detachment
- **Risk**: Large number of FGs causes slow rendering
  - **Mitigation**: Catalog is ~100 FGs; no optimization needed
- **Risk**: Quantity StringVar trace fires during restore, causing spurious persistence updates
  - **Mitigation**: Use a `_restoring` flag to suppress trace callbacks during `_render_finished_goods()`

## Definition of Done Checklist

- [ ] FG frame starts blank with placeholder text and three filter dropdowns
- [ ] Recipe category dropdown populated from event's available categories
- [ ] Item type dropdown has: All Types, Finished Units, Assemblies
- [ ] Yield type dropdown has: All Yields, EA, SERVING
- [ ] Selecting any filter loads matching FGs (AND logic)
- [ ] Changing filters preserves checkbox selections
- [ ] Changing filters preserves quantity entries
- [ ] Count label shows visible and total selections
- [ ] `clear_selections()` method available for WP04
- [ ] planning_tab orchestration updated for blank-start
- [ ] All existing tests still pass (no regressions)

## Review Guidance

- **US2 Acceptance Scenarios**: Walk through all 6 scenarios from spec
- **US3 Acceptance Scenarios**: Walk through all 4 scenarios from spec
- Verify three-filter AND logic with various combinations
- Verify persistence: check FGs, change filters, change back, verify checked + quantities
- Verify blank start: no FGs shown until filter selected
- Check session management: no nested session_scope() calls
- Verify `_save_current_selections()` called before every re-render

## Activity Log

- 2026-02-09T21:25:52Z -- system -- lane=planned -- Prompt created.
- 2026-02-09T21:59:06Z – gemini – shell_pid=26148 – lane=doing – Assigned agent via workflow command
- 2026-02-09T22:40:33Z – gemini – shell_pid=26148 – lane=for_review – Ready for review: Filter-first FG selection with 3 dropdowns (recipe category, item type, yield type), blank start, AND-combine filters, selection+quantity persistence across filter changes. All 3663 tests pass.
