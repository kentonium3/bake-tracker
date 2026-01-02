---
work_package_id: "WP05"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "UI Delete Handler Integration"
phase: "Phase 3 - UI Integration"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "15513"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - UI Delete Handler Integration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update the UI delete handler to use the new `delete_ingredient_safe()` service function and display detailed error messages with counts when deletion is blocked.

**Success Criteria**:
- UI calls `delete_ingredient_safe()` instead of old deletion method
- `IngredientInUse` exception is caught and displayed as user-friendly message
- Error messages include counts of products, recipes, and children that block deletion
- User understands what action to take when deletion is blocked

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (FR-007, FR-008, FR-009)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 5)
- Constitution: `.kittify/memory/constitution.md` (UI layer rules)

**Key Constraints**:
- UI must NOT contain business logic - only display service results
- Error messages must be user-friendly (non-technical language)
- Follow existing UI patterns in the application

**Dependencies**:
- WP03 must be complete (`delete_ingredient_safe()` must exist)
- `IngredientInUse` exception must have details dict

## Subtasks & Detailed Guidance

### Subtask T019 - Locate _delete() Method

**Purpose**: Find and understand the current deletion handler.

**Steps**:
1. Open `src/ui/ingredients_tab.py`
2. Find the `IngredientFormDialog` class
3. Locate the `_delete()` method (approximately around line 1370)
4. Understand current deletion flow

**Expected structure** (current):
```python
def _delete(self):
    """Delete the current ingredient."""
    # Confirmation dialog
    # Call to ingredient_service.delete_ingredient(slug)
    # Success/error handling
```

**Files**: `src/ui/ingredients_tab.py`

### Subtask T020 - Import delete_ingredient_safe

**Purpose**: Add the import for the new safe deletion function.

**Steps**:
1. Find imports section at top of `src/ui/ingredients_tab.py`
2. Locate the existing ingredient_service import
3. Add `delete_ingredient_safe` to the imports:

```python
from ..services.ingredient_service import (
    # ... existing imports ...
    delete_ingredient_safe,
)
```

4. Also import the exception class:

```python
from ..services.exceptions import IngredientInUse, IngredientNotFound
```

**Note**: Check if exceptions module exists or if exceptions are in ingredient_service.

**Files**: `src/ui/ingredients_tab.py`

### Subtask T021 - Update _delete() to Use Safe Deletion

**Purpose**: Replace old deletion call with new safe version.

**Steps**:
1. In the `_delete()` method, find the call to `delete_ingredient()` or similar
2. Replace with call to `delete_ingredient_safe()`:

```python
def _delete(self):
    """Delete the current ingredient with protection checks."""
    if not self.ingredient:
        return

    # Confirmation dialog (keep existing)
    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Are you sure you want to delete '{self.ingredient.display_name}'?"
    )
    if not confirm:
        return

    try:
        delete_ingredient_safe(self.ingredient.id)
        # Success handling...
```

**Files**: `src/ui/ingredients_tab.py`

### Subtask T022 - Handle IngredientInUse Exception

**Purpose**: Catch the blocking exception and extract details.

**Steps**:
1. Add exception handling for `IngredientInUse`:

```python
try:
    delete_ingredient_safe(self.ingredient.id)
    messagebox.showinfo("Success", "Ingredient deleted successfully.")
    self._on_delete_success()
except IngredientInUse as e:
    # Extract details from exception
    details = e.details if hasattr(e, 'details') else {}
    self._show_deletion_blocked_message(details)
except IngredientNotFound:
    messagebox.showerror("Error", "Ingredient not found.")
except Exception as e:
    messagebox.showerror("Error", f"Failed to delete ingredient: {str(e)}")
```

**Files**: `src/ui/ingredients_tab.py`

### Subtask T023 - Display User-Friendly Error with Counts

**Purpose**: Show clear message explaining why deletion is blocked and what user must do.

**Steps**:
1. Create helper method to format the message:

```python
def _show_deletion_blocked_message(self, details: dict):
    """Display user-friendly message when deletion is blocked."""
    parts = []

    if details.get("products", 0) > 0:
        count = details["products"]
        parts.append(f"{count} product{'s' if count > 1 else ''}")

    if details.get("recipes", 0) > 0:
        count = details["recipes"]
        parts.append(f"{count} recipe{'s' if count > 1 else ''}")

    if details.get("children", 0) > 0:
        count = details["children"]
        parts.append(f"{count} child ingredient{'s' if count > 1 else ''}")

    if parts:
        items = ", ".join(parts[:-1])
        if len(parts) > 1:
            items += f" and {parts[-1]}"
        else:
            items = parts[0]

        message = (
            f"Cannot delete this ingredient.\n\n"
            f"It is referenced by {items}.\n\n"
            f"Please reassign or remove these references first."
        )
    else:
        message = "Cannot delete this ingredient. It has active references."

    messagebox.showerror("Cannot Delete", message)
```

2. Call this from the exception handler (T022)

**Example messages**:
- "Cannot delete this ingredient.\n\nIt is referenced by 3 products and 2 recipes.\n\nPlease reassign or remove these references first."
- "Cannot delete this ingredient.\n\nIt is referenced by 5 child ingredients.\n\nPlease reassign or remove these references first."

**Files**: `src/ui/ingredients_tab.py`

## Test Strategy

**Manual UI Testing**:
1. Attempt to delete an ingredient with product references - verify blocked with count
2. Attempt to delete an ingredient with recipe references - verify blocked with count
3. Attempt to delete an ingredient with children - verify blocked with count
4. Attempt to delete an ingredient with no references - verify success

**Note**: Automated UI tests are complex; focus on service layer tests in WP06.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Exception class structure differs | Check actual exception implementation from WP03 |
| UI error handling inconsistent | Follow existing patterns in other dialogs |
| Message too technical | Use plain language, no code terms |

## Definition of Done Checklist

- [ ] T019: `_delete()` method located and understood
- [ ] T020: Imports added for `delete_ingredient_safe` and exceptions
- [ ] T021: `_delete()` updated to call safe deletion
- [ ] T022: `IngredientInUse` exception handled correctly
- [ ] T023: User-friendly message displays counts and action needed
- [ ] Error messages follow FR-007, FR-008, FR-009 requirements
- [ ] Existing success path still works

## Review Guidance

- Verify UI shows counts correctly (plural handling)
- Verify message clearly tells user what to do
- Check that success case still works as before
- Ensure no business logic leaked into UI layer

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:43:15Z – claude – shell_pid=15513 – lane=doing – Started Wave 3 implementation
