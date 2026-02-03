---
work_package_id: WP04
title: UI Migration - Core Tabs
lane: "for_review"
dependencies: [WP03]
base_branch: 089-error-handling-foundation-WP03
base_commit: 845ab60ddd7c9705f76124df0d925332fc6b41b8
created_at: '2026-02-03T00:11:33.209283+00:00'
subtasks:
- T019
- T020
- T021
phase: Phase 2 - UI Migration
assignee: ''
agent: ''
shell_pid: "62222"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – UI Migration - Core Tabs

## ⚠️ IMPORTANT: Review Feedback Status

Check `review_status` field above. If `has_feedback`, address feedback items first.

---

## Review Feedback

*[Empty initially. Reviewers populate if work needs changes.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

**Depends on**: WP03 (needs centralized error handler)

---

## Objectives & Success Criteria

**Objective**: Update exception handling in the highest-impact tabs (materials, inventory, planning) to use the centralized error handler and three-tier pattern.

**Success Criteria**:
- [ ] `materials_tab.py` uses centralized error handler (31 occurrences updated)
- [ ] `inventory_tab.py` uses centralized error handler (20 occurrences updated)
- [ ] `planning_tab.py` uses centralized error handler (21 occurrences updated)
- [ ] No raw Python exceptions shown to users
- [ ] Technical details logged for debugging

---

## Context & Constraints

**Three-Tier Pattern** (from constitution VI.A):
```python
try:
    # Operation
    result = some_service_call()
except SpecificException as e:
    # Tier 1: Specific exception with tailored handling
    handle_error(e, parent=self, operation="Description")
    self.highlight_specific_field()  # Optional custom handling
except ServiceError as e:
    # Tier 2: Generic service error
    handle_error(e, parent=self, operation="Description")
except Exception as e:
    # Tier 3: Unexpected error - always logged
    handle_error(e, parent=self, operation="Description")
```

**Import to Add**:
```python
from src.ui.utils.error_handler import handle_error
from src.services.exceptions import ServiceError
```

**Constraints**:
- Preserve any existing specific exception handling that adds value
- Use `operation=` parameter to describe what was attempted
- Pass `parent=self` for dialog positioning

---

## Subtasks & Detailed Guidance

### Subtask T019 – Update materials_tab.py (31 occurrences)

**Purpose**: Update the materials tab which has the highest count of generic Exception catches.

**Steps**:
1. Open `src/ui/materials_tab.py`
2. Add imports at top:
   ```python
   from src.ui.utils.error_handler import handle_error
   from src.services.exceptions import ServiceError
   ```
3. Find all `except Exception` blocks (31 total)
4. For each block, apply the pattern:

**Before**:
```python
try:
    materials = self.material_service.get_all_materials()
except Exception as e:
    messagebox.showerror("Error", f"Failed to load materials: {str(e)}")
    return []
```

**After**:
```python
try:
    materials = self.material_service.get_all_materials()
except ServiceError as e:
    handle_error(e, parent=self, operation="Load materials")
    return []
except Exception as e:
    handle_error(e, parent=self, operation="Load materials")
    return []
```

5. For silent catches (return empty without showing error), preserve that behavior:

**Before**:
```python
except Exception:
    return []
```

**After** (log but don't show dialog):
```python
except Exception as e:
    handle_error(e, parent=self, operation="Load filter data", show_dialog=False)
    return []
```

**Files**: `src/ui/materials_tab.py`
**Parallel?**: Yes

**Notes**:
- Some catches may be intentionally silent (for non-critical operations) - use `show_dialog=False`
- Review each catch to determine if dialog should show

---

### Subtask T020 – Update inventory_tab.py (20 occurrences)

**Purpose**: Update inventory tab exception handling.

**Steps**:
1. Open `src/ui/inventory_tab.py`
2. Add imports
3. Find all `except Exception` blocks (20 total)
4. Apply three-tier pattern to each

**Common operations in inventory tab**:
- Load inventory items → "Load inventory"
- Search/filter → "Search inventory"
- Update quantity → "Update inventory item"
- Delete item → "Delete inventory item"

**Files**: `src/ui/inventory_tab.py`
**Parallel?**: Yes

---

### Subtask T021 – Update planning_tab.py (21 occurrences)

**Purpose**: Update planning tab exception handling.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Add imports
3. Find all `except Exception` blocks (21 total)
4. Apply three-tier pattern

**Common operations in planning tab**:
- Load plan data → "Load plan"
- Calculate requirements → "Calculate requirements"
- Generate shopping list → "Generate shopping list"
- Update targets → "Update production targets"

**Watch for**: `PlanStateError` - may need specific handling if plan state messages should be shown

**Files**: `src/ui/planning_tab.py`
**Parallel?**: Yes

---

## Test Strategy

**Manual Testing**:
1. Open each tab in the application
2. Trigger error conditions:
   - Delete an item that's in use
   - Search with invalid characters
   - Disconnect database and attempt operation
3. Verify:
   - User sees friendly message (not Python exception)
   - Dialog title is appropriate ("Not Found", "Error", etc.)
   - Technical details appear in logs (check console/log file)

**Grep Verification**:
```bash
# Should return 0 matches for bare "except Exception:" without handler
grep -n "except Exception:" src/ui/materials_tab.py | grep -v "handle_error"
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing error handling | Test each tab manually after changes |
| Silent catches losing errors | Add `show_dialog=False` with logging |
| Missing import | Verify imports at module level |

---

## Definition of Done Checklist

- [ ] All 31 occurrences in `materials_tab.py` updated
- [ ] All 20 occurrences in `inventory_tab.py` updated
- [ ] All 21 occurrences in `planning_tab.py` updated
- [ ] Imports added to all three files
- [ ] Manual testing passes - no raw exceptions shown
- [ ] Grep verification shows no unhandled generic catches

---

## Review Guidance

**Key Checkpoints**:
1. Verify all `except Exception` blocks use `handle_error()`
2. Verify `operation=` parameter describes the action
3. Verify silent catches use `show_dialog=False`
4. Test one error scenario per tab manually

---

## Activity Log

- 2026-02-02T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-03T00:19:21Z – unknown – shell_pid=62222 – lane=for_review – Core tabs updated with centralized error handler pattern
