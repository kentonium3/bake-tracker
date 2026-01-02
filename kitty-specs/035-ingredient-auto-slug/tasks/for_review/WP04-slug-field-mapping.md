---
work_package_id: "WP04"
subtasks:
  - "T016"
  - "T017"
  - "T018"
title: "Slug Field Mapping Fix"
phase: "Phase 2 - Core Implementation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "18330"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Slug Field Mapping Fix

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Fix the field name mismatch between UI (sends "name") and service (expects "display_name") so that slug auto-generation works correctly when creating ingredients via the UI.

**Success Criteria**:
- `create_ingredient()` normalizes "name" to "display_name" before processing
- Existing slug generation works with both field names
- No breaking changes to existing callers that use "display_name"

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (FR-001 to FR-004)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 4)
- Research: `kitty-specs/035-ingredient-auto-slug/research.md` (Field Mapping Issue section)

**Key Constraints**:
- Must be backward compatible - "display_name" callers must continue to work
- Normalization must happen BEFORE validation
- No changes needed to `create_slug()` utility - it already works correctly

**Research Findings** (from research.md):
- `create_slug()` in `src/utils/slug_utils.py` already generates unique slugs correctly
- `create_ingredient()` at line 188 calls `create_slug(ingredient_data["display_name"], session)`
- UI forms may send "name" instead of "display_name" causing KeyError or missing slug

## Subtasks & Detailed Guidance

### Subtask T016 - Add Field Normalization

**Purpose**: Ensure "name" field is mapped to "display_name" at function entry.

**Steps**:
1. Open `src/services/ingredient_service.py`
2. Find the `create_ingredient()` function
3. Add normalization logic BEFORE validation (before `_validate_ingredient_data` call):

```python
def create_ingredient(ingredient_data: dict, session=None) -> Ingredient:
    """Create a new ingredient with auto-generated slug."""
    # Normalize field names for backward compatibility (F035)
    if "name" in ingredient_data and "display_name" not in ingredient_data:
        ingredient_data["display_name"] = ingredient_data.pop("name")

    # Existing validation and logic follows...
```

**Notes**:
- Use `pop("name")` to remove "name" key after copying to avoid confusion
- Only normalize if "display_name" is not already present (don't override)

**Files**: `src/services/ingredient_service.py`

### Subtask T017 - Verify create_slug Usage

**Purpose**: Confirm existing slug generation works correctly with display_name.

**Steps**:
1. Find the line where `create_slug()` is called (approximately line 188)
2. Verify it uses `ingredient_data["display_name"]`
3. Confirm the session parameter is passed correctly

**Expected code** (should already exist):
```python
# Generate slug from display_name
slug = create_slug(ingredient_data["display_name"], session)
```

**No changes needed** if this already exists correctly.

**Files**: `src/services/ingredient_service.py`

### Subtask T018 - Manual Test Verification

**Purpose**: Verify both field name inputs work correctly.

**Steps**:
1. Test with "display_name" field:
   ```python
   # Should work (existing behavior)
   create_ingredient({"display_name": "Brown Sugar", "parent_ingredient_id": 5})
   ```

2. Test with "name" field:
   ```python
   # Should now work after T016
   create_ingredient({"name": "Brown Sugar", "parent_ingredient_id": 5})
   ```

3. Verify both generate correct slugs (e.g., "brown_sugar")

**Note**: Full automated tests are in WP06 (T032).

## Test Strategy

**Manual Verification**:
1. Create ingredient via dictionary with "name" key - verify slug generated
2. Create ingredient via dictionary with "display_name" key - verify slug generated
3. Verify both result in identical behavior

**Automated**: WP06 includes T032 for field name normalization testing.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | Normalization is additive, doesn't remove "display_name" support |
| "name" and "display_name" both present | Only copy if "display_name" absent - explicit takes precedence |
| Pop removes needed data | Only internal dict, callers keep their original |

## Definition of Done Checklist

- [x] T016: Field normalization added at start of `create_ingredient()`
- [x] T017: Verified `create_slug()` uses `display_name` correctly
- [x] T018: Manual testing confirms both field names work
- [x] No existing tests broken
- [x] Code follows session management pattern

## Review Guidance

- Verify normalization happens BEFORE validation
- Verify "display_name" callers still work (backward compatibility)
- Check that `pop("name")` removes the key cleanly

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:38:05Z - gemini - shell_pid=17160 - lane=doing - Started Wave 2 implementation (parallel with WP03)
- 2026-01-02T19:45:00Z - claude - T016 DONE - Added field normalization at line 171-174 of ingredient_service.py
- 2026-01-02T19:46:00Z - claude - T017 DONE - Verified create_slug at line 194 uses display_name correctly
- 2026-01-02T19:47:00Z - claude - T018 DONE - Added 3 tests to test_ingredient_service.py (TestCreateIngredientFieldNormalization class)
- 2026-01-02T19:48:00Z - claude - All 41 tests pass (38 original + 3 new normalization tests)
- 2026-01-02T19:42:16Z – claude – shell_pid=18330 – lane=for_review – Ready for review - field normalization added with 3 new tests
