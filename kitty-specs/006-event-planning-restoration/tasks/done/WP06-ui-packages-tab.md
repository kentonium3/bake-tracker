---
work_package_id: "WP06"
subtasks:
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
title: "UI - Packages Tab"
phase: "Phase 3 - UI Layer"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "9077"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - UI - Packages Tab

## Objectives & Success Criteria

- Restore/update Packages tab for managing gift packages
- Enable adding/removing FinishedGoods to packages
- Display calculated costs from FIFO chain

**Success Criteria**:
- User can create, edit, delete packages
- User can add/remove FinishedGoods with quantities
- Package costs display correctly
- Dependency warnings show when deleting assigned packages

## Context & Constraints

**Architecture**: UI calls PackageService only - no direct database access. Follow constitution principle I (Layered Architecture).

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/spec.md` - User Story 2 acceptance scenarios
- `kitty-specs/006-event-planning-restoration/contracts/package_service.md` - Service interface

**UI Framework**: CustomTkinter

**Dependencies**: Requires WP03 complete (PackageService).

## Subtasks & Detailed Guidance

### Subtask T042 - Review existing `src/ui/packages_tab.py` for reusable patterns

**Purpose**: Determine what can be reused vs needs rewriting.

**Steps**:
1. Check if `src/ui/packages_tab.py` exists
2. If exists, identify:
   - UI component patterns (frames, dialogs, lists)
   - Any Bundle references that need removing
   - Reusable layout code
3. Review other tabs (recipes_tab, pantry_tab) for consistent patterns

**Files**: `src/ui/packages_tab.py`, `src/ui/recipes_tab.py`

### Subtask T043 - Create/update PackagesTab frame with package list view

**Purpose**: Main tab showing all packages.

**Steps**:
1. Create PackagesTab class extending CTkFrame
2. Create left panel with scrollable package list
3. Each list item shows: name, item count, total cost
4. Add "Add Package" button
5. Double-click to edit package

**Files**: `src/ui/packages_tab.py`

**Example structure**:
```python
class PackagesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        self.load_packages()

    def setup_ui(self):
        # Left panel - package list
        # Right panel - package details
        pass

    def load_packages(self):
        packages = PackageService.get_all_packages()
        # Populate list
```

### Subtask T044 - Implement Add Package dialog with name, description, is_template fields

**Purpose**: Dialog for creating new packages.

**Steps**:
1. Create AddPackageDialog class (CTkToplevel)
2. Fields:
   - Name (required)
   - Description (optional)
   - Is Template checkbox
   - Notes (optional)
3. Save button calls PackageService.create_package()
4. Refresh list after successful create

**Files**: `src/ui/packages_tab.py` or `src/ui/dialogs/package_dialog.py`

### Subtask T045 - Implement package content editor (add/remove FinishedGoods with quantities)

**Purpose**: UI for managing package contents.

**Steps**:
1. Create right panel showing package contents
2. Show list of FinishedGoods with quantities and costs
3. Add "Add Item" button that shows FinishedGood picker
4. Allow quantity editing (spinbox or entry)
5. Remove button for each item
6. Service calls:
   - PackageService.add_finished_good_to_package()
   - PackageService.remove_finished_good_from_package()
   - PackageService.update_finished_good_quantity()

**Files**: `src/ui/packages_tab.py`

### Subtask T046 - Display package cost (calculated from FinishedGood costs)

**Purpose**: Show total cost in UI.

**Steps**:
1. Add cost label to package list items
2. Add cost summary in detail panel
3. Call PackageService.calculate_package_cost()
4. Format as currency (e.g., "$12.50")
5. Handle "Cost unavailable" for null costs

**Files**: `src/ui/packages_tab.py`

### Subtask T047 - Implement Edit/Delete package functionality with dependency warnings

**Purpose**: CRUD operations with safety checks.

**Steps**:
1. Edit: Populate dialog with existing values, update on save
2. Delete: Check for event assignments first
   ```python
   if PackageService.check_package_has_event_assignments(package_id):
       show_warning("Cannot delete package assigned to events")
       return
   PackageService.delete_package(package_id)
   ```
3. Refresh list after operations

**Files**: `src/ui/packages_tab.py`
**FR Reference**: FR-013, FR-015

### Subtask T048 - Add search functionality for packages

**Purpose**: Allow filtering package list.

**Steps**:
1. Add search entry above package list
2. Filter on key release (debounced)
3. Call PackageService.search_packages() or filter locally
4. Show "No results" message when empty

**Files**: `src/ui/packages_tab.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Bundle UI patterns in existing code | Rewrite affected sections |
| Performance with many FinishedGoods | Use virtual list if needed |

## Definition of Done Checklist

- [ ] Package list displays correctly
- [ ] Add/Edit/Delete operations work
- [ ] FinishedGood content editing works
- [ ] Costs display correctly
- [ ] Dependency warning on delete
- [ ] Search filters list
- [ ] User Story 2 acceptance scenarios pass
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify layered architecture (UI calls service only)
- Test all CRUD operations
- Check cost display accuracy
- Verify deletion prevention

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:45:21Z – claude – shell_pid=9077 – lane=doing – Started: Updating PackagesTab to use FinishedGood instead of Bundle
- 2025-12-04T02:51:54Z – claude – shell_pid=9077 – lane=for_review – Completed: PackagesTab updated for FinishedGood, removed Bundles tab
- 2025-12-04T03:01:38Z – claude – shell_pid=9077 – lane=done – Approved: PackagesTab implemented (414 lines)
