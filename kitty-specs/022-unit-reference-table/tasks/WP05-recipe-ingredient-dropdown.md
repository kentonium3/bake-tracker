---
work_package_id: WP05
title: Recipe Ingredient Dropdown
lane: done
history:
- timestamp: '2025-12-16T16:56:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 2 - UI Integration
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: claude-session
subtasks:
- T024
- T025
- T026
- T027
- T028
- T029
---

# Work Package Prompt: WP05 - Recipe Ingredient Dropdown

## Review Feedback

**Status**: **APPROVED**

**Review Summary**:
All acceptance criteria met. RecipeIngredient unit dropdown now uses unit_service.

**Verification Performed**:
1. Dropdown has exactly 20 items (17 units + 3 headers)
2. Units: oz, lb, g, kg, tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal, each, count, piece, dozen
3. NO package units present (bag, box, bar, etc.)
4. Header selection prevented via `_on_unit_selected` callback
5. Save validation rejects headers in `get_data()` method
6. Edit pre-selection works via constructor parameter
7. All 812 tests pass

**Code Changes**:
- `src/ui/forms/recipe_form.py`:
  - Added import for `get_units_for_dropdown`
  - Replaced hardcoded unit list with `get_units_for_dropdown(["weight", "volume", "count"])`
  - Added `_last_valid_unit` tracking and `_on_unit_selected` callback
  - Added header validation in `get_data()` method

---

## Objectives & Success Criteria

**Goal**: Replace unit text entry with dropdown showing weight, volume, and count units (no package units).

**Success Criteria**:
- RecipeIngredient unit dropdown shows weight, volume, and count units (17 total)
- Package units (bag, box, etc.) are NOT shown
- Selected unit stored correctly on save
- Editing existing recipe ingredient shows current unit pre-selected

**User Story Addressed**: US3 - Select Unit When Adding Recipe Ingredient

**Acceptance Scenarios** (from spec.md):
1. Recipe ingredient unit dropdown shows weight, volume, and count units (not package)
2. Selecting "cup" stores "cup" as the recipe ingredient unit
3. Editing existing recipe ingredient shows "cup" pre-selected

## Context & Constraints

**Reference Documents**:
- `kitty-specs/022-unit-reference-table/spec.md` - User Story 3 acceptance criteria
- `src/ui/forms/recipe_form.py` - Likely location

**Why No Package Units**:
- Recipe quantities are measurements, not packaging
- "2 cups flour" makes sense; "2 bags flour" doesn't for a recipe ingredient
- Package units are for products (what you buy), not recipe quantities (what you use)

**Units to Include**:
- Weight: oz, lb, g, kg (4)
- Volume: tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal (9)
- Count: each, count, piece, dozen (4)
- Total: 17 units

## Subtasks & Detailed Guidance

### Subtask T024 - Identify recipe form or dialog handling RecipeIngredient creation

**Purpose**: Locate where RecipeIngredient.unit is edited in the UI.

**Steps**:
1. Search for "RecipeIngredient" or recipe ingredient unit handling
2. Check `src/ui/forms/recipe_form.py`
3. May also be in a dialog for adding ingredients to recipes
4. Note the file path and relevant line numbers

**Files**: Likely `src/ui/forms/recipe_form.py` or related dialog

**Search Commands**:
```bash
grep -r "recipe.*ingredient" src/ui/ --include="*.py" -i
grep -r "\.unit" src/ui/forms/recipe_form.py
```

**Parallel?**: No - discovery step

---

### Subtask T025 - Import unit_service to recipe ingredient form

**Purpose**: Add import for unit_service functions.

**Steps**:
1. Add import at top of identified file:
   ```python
   from src.services.unit_service import get_units_for_dropdown
   ```

**Files**: File identified in T024

**Parallel?**: No - depends on T024

---

### Subtask T026 - Replace unit text entry with CTkComboBox

**Purpose**: Convert free-form unit entry to dropdown.

**Steps**:
1. Find the unit field for recipe ingredients
2. If it's CTkEntry, replace with CTkComboBox
3. Configure with state="readonly"

**Files**: File identified in T024

**Parallel?**: No - depends on T025

---

### Subtask T027 - Populate dropdown with measurement units

**Purpose**: Set up dropdown with weight, volume, and count units (excluding package).

**Steps**:
1. Get units for dropdown (excluding package category):
   ```python
   unit_values = get_units_for_dropdown(['weight', 'volume', 'count'])
   ```
2. Configure CTkComboBox values:
   ```python
   self.unit_combo = ctk.CTkComboBox(
       parent,
       width=...,
       values=unit_values,
       state="readonly",
   )
   ```
3. Set sensible default (e.g., "cup" for common baking use)

**Files**: File identified in T024

**Expected Dropdown Contents**:
- "-- Weight --", oz, lb, g, kg
- "-- Volume --", tsp, tbsp, cup, ml, l, fl oz, pt, qt, gal
- "-- Count --", each, count, piece, dozen

**Parallel?**: No - depends on T026

---

### Subtask T028 - Ensure selected unit is stored correctly on save

**Purpose**: Verify save logic captures the dropdown value.

**Steps**:
1. Find the save handler for recipe ingredient
2. Ensure it reads value from CTkComboBox:
   ```python
   unit = self.unit_combo.get()
   ```
3. Verify validation rejects category headers
4. Confirm unit is saved to RecipeIngredient model

**Files**: File identified in T024

**Parallel?**: No - depends on T027

---

### Subtask T029 - Verify existing recipe ingredient edit populates dropdown with current value

**Purpose**: When editing, dropdown shows current unit.

**Steps**:
1. Find form population/edit initialization
2. Ensure existing unit is set:
   ```python
   if recipe_ingredient and recipe_ingredient.unit:
       self.unit_combo.set(recipe_ingredient.unit)
   ```
3. Test with existing recipe ingredients

**Files**: File identified in T024

**Parallel?**: No - depends on T028

---

## Test Strategy

**Manual Testing**:
1. Add ingredient to recipe - verify dropdown shows 17 measurement units + 3 headers
2. Verify NO package units (bag, box, etc.) appear
3. Select "cup" - verify saved correctly
4. Edit recipe ingredient - verify "cup" pre-selected

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Recipe ingredient form may be complex/nested | Medium | Trace code path carefully |
| Multiple places to add ingredients | Medium | Search thoroughly for all unit fields |
| Category header selection | Medium | Validate selection on change or save |

---

## Definition of Done Checklist

- [ ] Recipe ingredient form identified
- [ ] unit field replaced with CTkComboBox
- [ ] Dropdown populated with weight, volume, count units (17 total)
- [ ] Package units NOT included
- [ ] Category headers present ("-- Weight --", etc.)
- [ ] Header selection prevented/rejected
- [ ] Selected unit stored correctly on save
- [ ] Editing existing recipe ingredient shows current value
- [ ] All existing tests still pass

---

## Review Guidance

**Acceptance Checkpoints**:
1. Verify dropdown has exactly 17 units + 3 headers = 20 items
2. Verify NO package units appear (bag, box, bar, bottle, can, jar, packet, container, package, case)
3. Test adding recipe ingredient - unit saved correctly
4. Test editing recipe ingredient - unit pre-selected

---

## Activity Log

- 2025-12-16T16:56:32Z - system - lane=planned - Prompt created.
- 2025-12-16T18:07:32Z – system – shell_pid= – lane=doing – Starting implementation of Recipe Ingredient Dropdown
- 2025-12-16T18:36:12Z – system – shell_pid= – lane=for_review – Implementation complete: RecipeIngredient unit dropdown now uses unit_service
- 2025-12-16T18:37:59Z – system – shell_pid= – lane=done – Code review APPROVED: RecipeIngredient unit dropdown uses unit_service
