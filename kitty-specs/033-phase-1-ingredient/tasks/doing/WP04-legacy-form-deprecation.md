---
work_package_id: "WP04"
subtasks:
  - "T014"
  - "T015"
title: "Legacy Form Deprecation"
phase: "Phase 4 - Cleanup"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Legacy Form Deprecation

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Goal**: Mark `ingredient_form.py` legacy dialog as deprecated to prevent future use.

**Success Criteria**:
- Deprecation docstring added to module and class
- Runtime deprecation warning when dialog is instantiated
- No breaking changes to existing functionality
- Call sites documented for future removal

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/033-phase-1-ingredient/plan.md`
- Research: `kitty-specs/033-phase-1-ingredient/research.md` (Decision 3: Deprecate Legacy Form)

**Dependencies**:
- None (independent cleanup task)
- Can run in parallel with WP02/WP03

**Background**:
- `ingredient_form.py` uses category dropdown (pre-hierarchy design)
- Inline form in `ingredients_tab.py` is the primary interface
- Legacy form should be deprecated, not removed, to avoid breaking any existing code

## Subtasks & Detailed Guidance

### Subtask T014 - Add Deprecation Docstring and Comment

**Purpose**: Document that this form is deprecated and what to use instead.

**Steps**:
1. Open `src/ui/forms/ingredient_form.py`
2. Add module-level deprecation docstring at top of file
3. Add deprecation note to class docstring
4. Add inline comment explaining deprecation

**Files**: `src/ui/forms/ingredient_form.py`

**Parallel?**: Yes - can be done alongside T015

**Implementation**:
```python
"""
Ingredient form dialog for adding and editing ingredients.

.. deprecated::
    This dialog is deprecated as of Feature 033. Use the inline form in
    `ingredients_tab.py` instead, which supports the ingredient hierarchy.
    This file is retained for backward compatibility but will be removed
    in a future version.

Provides a comprehensive form for creating and updating ingredient records
with validation and error handling.
"""

import warnings
import customtkinter as ctk
# ... rest of imports ...


class IngredientFormDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing an ingredient.

    .. deprecated::
        Use the inline form in `ingredients_tab.py` instead.
        This dialog does not support the ingredient hierarchy (L0/L1/L2)
        and will be removed in a future version.

    Provides a comprehensive form with validation for all ingredient fields.
    """
```

### Subtask T015 - Add Runtime Deprecation Warning

**Purpose**: Warn developers at runtime when the deprecated dialog is used.

**Steps**:
1. Import `warnings` module at top of file
2. Add `warnings.warn()` call in `__init__` method
3. Use `stacklevel=2` for accurate call site reporting

**Files**: `src/ui/forms/ingredient_form.py`

**Parallel?**: Yes - can be done alongside T014

**Implementation**:
```python
import warnings

class IngredientFormDialog(ctk.CTkToplevel):
    """..."""

    def __init__(
        self,
        parent,
        ingredient: Optional[Ingredient] = None,
        title: str = "Add Ingredient",
    ):
        """
        Initialize the ingredient form dialog.

        Args:
            parent: Parent window
            ingredient: Existing ingredient to edit (None for new)
            title: Dialog title
        """
        # Emit deprecation warning
        warnings.warn(
            "IngredientFormDialog is deprecated. Use the inline form in "
            "ingredients_tab.py instead, which supports ingredient hierarchy.",
            DeprecationWarning,
            stacklevel=2
        )

        super().__init__(parent)
        # ... rest of __init__ ...
```

**Notes**:
- `stacklevel=2` ensures the warning points to the caller, not this line
- Warning will appear once per call site (Python caches by location)
- In production, warnings may be filtered - this is mainly for development

### Optional: Document Call Sites

**Purpose**: Find and document where this dialog is currently used.

**Steps**:
1. Search codebase for `IngredientFormDialog`
2. Document each usage in a comment block at top of file

**Command**:
```bash
grep -rn "IngredientFormDialog" src/
```

**Documentation Format**:
```python
"""
...

Known Call Sites (as of 2026-01-02):
- src/ui/ingredients_tab.py (if any)
- [other files if found]

These should be migrated to the inline form before this file is removed.
"""
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Only add warnings, don't modify behavior |
| Warning noise in tests | Can filter DeprecationWarning in pytest config if needed |
| Missing call sites | Search codebase before marking as deprecated |

## Definition of Done Checklist

- [ ] Module-level deprecation docstring added
- [ ] Class-level deprecation docstring added
- [ ] `warnings.warn()` call added in `__init__`
- [ ] Warning uses `stacklevel=2` for accurate reporting
- [ ] Call sites searched and documented (if any found)
- [ ] Existing functionality still works (dialog opens, saves, cancels)
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify docstrings are clear about what to use instead
2. Test that warning is emitted when dialog is opened
3. Verify warning points to correct call site (not the init method)
4. Confirm dialog still functions correctly after changes
5. Check for any usages in the codebase

**Manual Test Scenario**:
1. Open Python with `-W default::DeprecationWarning`
2. Import and instantiate IngredientFormDialog
3. Verify warning message appears with correct file/line info
4. Verify dialog still opens and functions normally

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-02T05:44:52Z – system – shell_pid= – lane=doing – Moved to doing
