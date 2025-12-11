---
work_package_id: "WP08"
subtasks:
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
title: "UI - Targets Tab"
phase: "Phase 6 - UI Targets Tab"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "94501"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - UI - Targets Tab

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Add Targets tab to Event Detail window with production/assembly progress display.

**Success Criteria**:
- Targets tab appears in Event Detail window (after Assignments)
- Production Targets section shows all targets with progress
- Assembly Targets section shows all targets with progress
- Progress displayed as CTkProgressBar + text (e.g., "2/4 (50%)")
- Add/Edit/Delete functionality works for targets
- Progress updates after recording production

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - FR-025, FR-026, User Stories 3-6
- `kitty-specs/016-event-centric-production/quickstart.md` - Progress bar pattern

**Existing Code**:
- `src/ui/event_detail_window.py`

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Christmas 2025                                                   │
├──────────┬──────────┬──────────────┬───────────┬────────────────┤
│Assignments│ Targets │ Recipe Needs │Shopping   │ Summary        │
├──────────┴──────────┴──────────────┴───────────┴────────────────┤
│                                                                  │
│ Production Targets                          [+ Add Target]       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Chocolate Chip    │ ████░░░░ │ 2/4 (50%)                    │ │
│ │ Sugar Cookies     │ ████████ │ 2/2 (100%) ✓                 │ │
│ │ Snickerdoodles    │ ░░░░░░░░ │ 0/1 (0%)                     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Assembly Targets                            [+ Add Target]       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Cookie Gift Box   │ █████░░░ │ 3/5 (60%)                    │ │
│ │ Simple Cookie Bag │ ████████ │ 10/10 (100%) ✓               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Dependencies**: WP03 (target CRUD), WP04 (progress calculation)

---

## Subtasks & Detailed Guidance

### Subtask T041 - Add "Targets" tab to EventDetailWindow

**Purpose**: Create the tab structure for targets display.

**Steps**:
1. Open `src/ui/event_detail_window.py`
2. Find where tabs are created (likely in `__init__` or `_create_tabs`)
3. Add Targets tab after Assignments:
   ```python
   # Create tabs (example - adapt to existing pattern)
   self.tabview = ctk.CTkTabview(self)

   self.assignments_tab = self.tabview.add("Assignments")
   self.targets_tab = self.tabview.add("Targets")  # NEW
   self.recipe_needs_tab = self.tabview.add("Recipe Needs")
   self.shopping_tab = self.tabview.add("Shopping List")
   self.summary_tab = self.tabview.add("Summary")
   ```
4. Create frame for targets content:
   ```python
   self.targets_frame = ctk.CTkScrollableFrame(self.targets_tab)
   self.targets_frame.pack(fill="both", expand=True, padx=10, pady=10)
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No (foundational)
**Notes**: Check existing tab implementation pattern and follow it.

---

### Subtask T042 - Create Production Targets section

**Purpose**: Display production targets with header and add button.

**Steps**:
1. Create method `_create_production_targets_section()`:
   ```python
   def _create_production_targets_section(self):
       # Header with Add button
       header_frame = ctk.CTkFrame(self.targets_frame)
       header_frame.pack(fill="x", pady=(0, 5))

       header_label = ctk.CTkLabel(
           header_frame,
           text="Production Targets",
           font=("", 14, "bold")
       )
       header_label.pack(side="left", padx=5)

       add_btn = ctk.CTkButton(
           header_frame,
           text="+ Add Target",
           width=100,
           command=self._on_add_production_target
       )
       add_btn.pack(side="right", padx=5)

       # Targets list container
       self.production_targets_container = ctk.CTkFrame(self.targets_frame)
       self.production_targets_container.pack(fill="x", pady=5)
   ```
2. Call from tab setup

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No
**Notes**: Container will hold progress rows.

---

### Subtask T043 - Create Assembly Targets section

**Purpose**: Display assembly targets with header and add button.

**Steps**:
1. Create method `_create_assembly_targets_section()` following same pattern
2. Create container for assembly target rows

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: Yes (can proceed with T042)
**Notes**: Same structure as production targets.

---

### Subtask T044 - Implement progress display

**Purpose**: Show CTkProgressBar + text for each target.

**Steps**:
1. Create method to build progress row:
   ```python
   def _create_progress_row(
       self,
       parent,
       name: str,
       produced: int,
       target: int,
       on_edit=None,
       on_delete=None
   ):
       row = ctk.CTkFrame(parent)
       row.pack(fill="x", pady=2)

       # Name
       name_label = ctk.CTkLabel(row, text=name, width=150, anchor="w")
       name_label.pack(side="left", padx=5)

       # Progress bar
       progress_pct = produced / target if target > 0 else 0
       progress_bar = ctk.CTkProgressBar(row, width=100)
       progress_bar.set(min(progress_pct, 1.0))  # Cap at 1.0 for display
       progress_bar.pack(side="left", padx=5)

       # Text (can show > 100%)
       pct_display = int(progress_pct * 100)
       text = f"{produced}/{target} ({pct_display}%)"
       text_label = ctk.CTkLabel(row, text=text, width=100)
       text_label.pack(side="left", padx=5)

       # Complete indicator
       if produced >= target:
           check = ctk.CTkLabel(row, text="✓", text_color="green")
           check.pack(side="left", padx=2)

       # Edit/Delete buttons
       if on_edit:
           edit_btn = ctk.CTkButton(row, text="Edit", width=50, command=on_edit)
           edit_btn.pack(side="right", padx=2)
       if on_delete:
           del_btn = ctk.CTkButton(row, text="Del", width=50, command=on_delete)
           del_btn.pack(side="right", padx=2)

       return row
   ```
2. Create refresh method:
   ```python
   def _refresh_targets(self):
       # Clear existing rows
       for widget in self.production_targets_container.winfo_children():
           widget.destroy()

       # Get progress data
       prod_progress = event_service.get_production_progress(self.event_id)

       for p in prod_progress:
           self._create_progress_row(
               self.production_targets_container,
               p['recipe_name'],
               p['produced_batches'],
               p['target_batches'],
               on_edit=lambda r=p['recipe']: self._on_edit_production_target(r),
               on_delete=lambda r=p['recipe']: self._on_delete_production_target(r)
           )

       # Same for assembly targets...
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No
**Notes**: Progress bar capped at 1.0 but text shows actual percentage.

---

### Subtask T045 - Add "Add Production Target" dialog

**Purpose**: Dialog for creating new production targets.

**Steps**:
1. Create dialog class or method:
   ```python
   def _on_add_production_target(self):
       dialog = ctk.CTkInputDialog(
           text="Select Recipe and Target Batches",
           title="Add Production Target"
       )
       # Or create custom dialog with:
       # - Recipe dropdown (exclude already-targeted recipes)
       # - Target batches entry
       # - Notes textbox
       # - Cancel/Save buttons
   ```
2. On save, call:
   ```python
   event_service.set_production_target(
       event_id=self.event_id,
       recipe_id=selected_recipe_id,
       target_batches=target_batches,
       notes=notes
   )
   self._refresh_targets()
   ```

**Files**: `src/ui/event_detail_window.py` (or new dialog file)
**Parallel?**: No
**Notes**: May need custom dialog for recipe dropdown.

---

### Subtask T046 - Add "Add Assembly Target" dialog

**Purpose**: Dialog for creating new assembly targets.

**Steps**:
1. Follow same pattern as T045 but for finished goods
2. Use finished_good dropdown instead of recipe

**Files**: `src/ui/event_detail_window.py` (or new dialog file)
**Parallel?**: Yes (can proceed with T045)
**Notes**: Same structure as production target dialog.

---

### Subtask T047 - Implement edit/delete functionality for targets

**Purpose**: Allow modifying or removing existing targets.

**Steps**:
1. Edit handler:
   ```python
   def _on_edit_production_target(self, recipe):
       # Show dialog with current values
       # On save: event_service.set_production_target(...)
       # Refresh
   ```
2. Delete handler:
   ```python
   def _on_delete_production_target(self, recipe):
       # Confirm dialog
       if confirm:
           event_service.delete_production_target(self.event_id, recipe.id)
           self._refresh_targets()
   ```
3. Same for assembly targets

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No
**Notes**: Consider confirmation dialog for delete.

---

### Subtask T048 - Implement refresh to update progress after production

**Purpose**: Keep progress display current.

**Steps**:
1. Add `_refresh_targets()` to tab selection callback:
   ```python
   self.tabview.configure(command=self._on_tab_changed)

   def _on_tab_changed(self):
       if self.tabview.get() == "Targets":
           self._refresh_targets()
   ```
2. Optionally add refresh button to targets tab

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: No
**Notes**: Refresh on tab selection ensures data is current.

---

### Subtask T049 - Manual UI testing checklist

**Purpose**: Verify targets tab functionality.

**Testing Checklist**:
1. [ ] Open Event Detail window
2. [ ] Targets tab visible (after Assignments)
3. [ ] Production Targets section shows correctly
4. [ ] Assembly Targets section shows correctly
5. [ ] Add production target - dialog works
6. [ ] New target appears in list
7. [ ] Progress bar shows correctly for various percentages
8. [ ] 0% - empty bar, 50% - half bar, 100% - full bar + checkmark
9. [ ] >100% - full bar + checkmark + percentage > 100
10. [ ] Edit target - values update
11. [ ] Delete target - removed from list
12. [ ] Record production for targeted recipe
13. [ ] Refresh targets tab - progress updated
14. [ ] Repeat for assembly targets
15. [ ] Test with no targets - sections show empty

**Files**: N/A
**Parallel?**: No
**Notes**: Test all progress scenarios.

---

## Test Strategy

**Manual UI Testing**:
- Follow checklist in T049
- Test with 0, 1, many targets
- Test all progress percentages

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with many targets | Use scrollable frame |
| Progress not updating | Refresh on tab selection |
| Layout issues | Test different window sizes |

---

## Definition of Done Checklist

- [ ] Targets tab in Event Detail window
- [ ] Production Targets section with progress
- [ ] Assembly Targets section with progress
- [ ] CTkProgressBar + text display works
- [ ] Over-production (>100%) displays correctly
- [ ] Add Production Target dialog works
- [ ] Add Assembly Target dialog works
- [ ] Edit functionality works
- [ ] Delete functionality works
- [ ] Refresh updates progress
- [ ] Manual testing checklist complete
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Tab appears in correct position
2. Progress calculations match service layer
3. Progress bar caps at 1.0 but text shows actual
4. Complete checkmark appears at >= 100%
5. Add/Edit/Delete all refresh the list
6. Scrolling works with many targets

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T17:29:25Z – claude – shell_pid=93900 – lane=doing – Started implementation of UI Targets Tab
- 2025-12-11T17:32:17Z – claude – shell_pid=94501 – lane=for_review – Ready for review - all subtasks implemented
- 2025-12-11T17:51:27Z – claude – shell_pid=94501 – lane=done – Code review approved - Targets tab with progress bars implemented, syntax verified
