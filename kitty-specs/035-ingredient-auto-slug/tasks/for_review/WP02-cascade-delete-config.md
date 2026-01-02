---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Verify Cascade Delete Configuration"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "16165"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Verify Cascade Delete Configuration

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Verify and configure cascade delete for IngredientAlias and IngredientCrosswalk models so they are automatically deleted when their parent ingredient is deleted.

**Success Criteria**:
- IngredientAlias.ingredient_id FK has `ondelete="CASCADE"`
- IngredientCrosswalk.ingredient_id FK has `ondelete="CASCADE"`
- Research.md updated with verification findings

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (FR-012, FR-013)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 2)
- Research: `kitty-specs/035-ingredient-auto-slug/research.md`

**Key Constraints**:
- These are metadata tables - safe to cascade delete
- Must verify before relying on cascade behavior in deletion service

**Parallel Execution**: This WP can run entirely in parallel with WP01 (different files).

## Subtasks & Detailed Guidance

### Subtask T007 - Verify IngredientAlias FK Configuration

**Purpose**: Ensure IngredientAlias records auto-delete when ingredient is deleted.

**Steps**:
1. Open `src/models/ingredient_alias.py`
2. Find the `ingredient_id` column definition
3. Check if it has `ondelete="CASCADE"`
4. Note the current configuration

**Expected to find** (based on research):
```python
ingredient_id = Column(
    Integer,
    ForeignKey("ingredients.id", ondelete="CASCADE"),
    nullable=False
)
```

**Files**: `src/models/ingredient_alias.py`
**Parallel?**: Yes - can verify both files simultaneously

### Subtask T008 - Verify IngredientCrosswalk FK Configuration

**Purpose**: Ensure IngredientCrosswalk records auto-delete when ingredient is deleted.

**Steps**:
1. Open `src/models/ingredient_crosswalk.py`
2. Find the `ingredient_id` column definition
3. Check if it has `ondelete="CASCADE"`
4. Note the current configuration

**Files**: `src/models/ingredient_crosswalk.py`
**Parallel?**: Yes

### Subtask T009 - Add Cascade Config If Missing

**Purpose**: Configure cascade delete if not already set.

**Steps**:
1. If T007 found cascade is missing for IngredientAlias:
   - Add `ondelete="CASCADE"` to the ForeignKey definition
2. If T008 found cascade is missing for IngredientCrosswalk:
   - Add `ondelete="CASCADE"` to the ForeignKey definition

**Example change**:
```python
# Before (if missing):
ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)

# After:
ingredient_id = Column(
    Integer,
    ForeignKey("ingredients.id", ondelete="CASCADE"),
    nullable=False
)
```

**Files**: `src/models/ingredient_alias.py`, `src/models/ingredient_crosswalk.py`

### Subtask T010 - Document Findings

**Purpose**: Record verification results for traceability.

**Steps**:
1. Open `kitty-specs/035-ingredient-auto-slug/research.md`
2. Add a section "## Cascade Delete Verification" if not present
3. Document:
   - IngredientAlias: [CASCADE present/added]
   - IngredientCrosswalk: [CASCADE present/added]
   - Date verified

**Files**: `kitty-specs/035-ingredient-auto-slug/research.md`

## Test Strategy

**Manual Verification**:
1. Create a test ingredient with an alias (if possible via test data)
2. Delete the ingredient
3. Verify alias was automatically deleted

**Automated**: WP06 includes T028 and T029 for cascade delete tests.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cascade not configured | T009 adds if missing |
| Accidental data loss | These are metadata tables, not user data - safe to cascade |

## Definition of Done Checklist

- [x] T007: IngredientAlias FK verified (cascade present)
- [x] T008: IngredientCrosswalk FK verified (cascade present)
- [x] T009: Cascade added if it was missing (N/A - already present)
- [x] T010: Research.md updated with findings
- [x] Both models have `ondelete="CASCADE"` on ingredient_id FK

## Review Guidance

- Verify both models have CASCADE configured
- Check research.md documents the verification

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:34:08Z – claude – shell_pid=15882 – lane=doing – Started Wave 1 implementation (parallel with WP01)
- 2026-01-02T19:35:00Z - claude - Verified cascade delete configuration:
  - T007: IngredientAlias.ingredient_id has ondelete="CASCADE" (line 32-34)
  - T008: IngredientCrosswalk.ingredient_id has ondelete="CASCADE" (line 34-36)
  - T009: No changes needed - both already configured correctly
  - T010: Updated research.md section "6. Cascade Delete Configuration" with verification table
- 2026-01-02T19:34:54Z – claude – shell_pid=16165 – lane=for_review – Ready for review - cascade delete verified (both already configured)
