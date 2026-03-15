# Implementation Plan: Fix Plan Mode FG and Batch Scoping

**Branch**: `103-fix-plan-mode-fg-batch-scoping` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/103-fix-plan-mode-fg-batch-scoping/spec.md`

## Summary

Two bugs in Plan mode where Finished Goods selection and Batch Options are incorrectly scoped. The FG selection uses `get_available_finished_goods()` which requires ALL component recipes to be selected (designed for assembly availability, wrong for recipe-level planning). Batch options use `decompose_event_to_fu_requirements()` which includes stale EventFinishedGood records from deselected recipes.

**Approach**: Replace the FG query with a simpler join through FinishedUnit.recipe_id to EventRecipe. Filter batch decomposition to current recipe selections. Add eager cleanup of stale EventFinishedGood records when recipes are deselected (cleanup already partially exists via `remove_invalid_fg_selections()` but relies on the same assembly-oriented availability check).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest
**Target Platform**: macOS desktop (Darwin)
**Project Type**: Single desktop application
**Performance Goals**: FG list loads in < 1 second
**Constraints**: No schema changes. Must not break existing planning tests.
**Scale/Scope**: Bug fix touching 3 service functions, 1 UI component

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Fixes broken planning workflow reported by primary user |
| II. Data Integrity | PASS | Eager cleanup prevents stale data from polluting calculations |
| III. Future-Proof Schema | PASS | No schema changes |
| IV. Test-Driven Development | PASS | Service changes will have unit tests |
| V. Layered Architecture | PASS | Service layer changes only; UI change is a single service call swap |
| VI-C. Session Parameter | PASS | New/modified functions will accept optional session parameter |
| VI-D. API Consistency | PASS | New function returns list (consistent with existing patterns) |
| VII. Schema Change Strategy | N/A | No schema changes |
| VIII. Pragmatic Aspiration | PASS | Simple fix, no over-engineering |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/103-fix-plan-mode-fg-batch-scoping/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/
├── services/
│   ├── event_service.py           # New function: get_fus_for_selected_recipes()
│   │                              # Modify: remove_invalid_fg_selections()
│   └── planning_service.py        # Modify: decompose_event_to_fu_requirements()
├── ui/
│   └── components/
│       └── fg_selection_frame.py   # Swap service call for FG loading
└── tests/
    ├── services/
    │   └── test_event_service.py   # Tests for new FG query + cleanup
    └── services/
        └── test_planning_service.py # Tests for filtered batch decomposition
```

## Phase 0: Research

### R1: Current FG Loading Data Flow

**Finding**: `fg_selection_frame.py` line 307 calls `event_service.get_filtered_available_fgs()` which calls `get_available_finished_goods()` (line 436-480). This function:
1. Gets selected recipe IDs via `get_event_recipe_ids()`
2. Queries ALL FinishedGoods from DB
3. For each FG, recursively decomposes via `check_fg_availability()` to find required recipes
4. Returns only FGs where ALL required recipes are in the selected set

**Problem**: This is designed for assembly/bundle availability (where all ingredients must be present). For simple recipe planning, a FG should appear if its recipe is selected — period.

### R2: Existing Cleanup Mechanism

**Finding**: `set_event_recipes()` (line 3367-3427) already calls `remove_invalid_fg_selections()` which uses `check_fg_availability()` — the same "all recipes required" logic. This cleanup works correctly for its intended purpose but is tied to the assembly model.

**Decision**: The cleanup logic is correct but the availability check it delegates to (`check_fg_availability`) is overly complex for our needs. For eager cleanup, we need a simpler check: does the finished unit's recipe still appear in EventRecipe? We can query this directly without recursive decomposition.

### R3: Batch Decomposition Scope

**Finding**: `decompose_event_to_fu_requirements()` (planning_service.py line 55-117) queries ALL EventFinishedGood records for the event with no recipe filtering. If stale records exist (recipe deselected but EventFinishedGood not cleaned up), they appear in batch options.

**Decision**: Add a filter join: EventFinishedGood → FinishedGood → components → FinishedUnit → Recipe, checking Recipe.id is in EventRecipe for this event. This is a defense-in-depth measure — the eager cleanup should prevent stale records, but the query filter ensures correctness even if cleanup is missed.

### R4: FinishedGood vs FinishedUnit Relationship

**Finding**: The data model has an indirection layer:
- EventFinishedGood references FinishedGood (a "bare" or "bundle" product)
- FinishedGood has components (FinishedGoodComponent)
- Each component references either a FinishedUnit (which has recipe_id) or another FinishedGood
- For "bare" FGs, there's exactly one component pointing to one FinishedUnit

**Decision for FG display**: Instead of querying FinishedGoods and decomposing, query FinishedUnits directly joined through Recipe → EventRecipe. Then wrap them as the UI expects. This is simpler and directly answers "show FUs for selected recipes."

## Phase 1: Design

### D1: New Service Function — `get_finished_units_for_event_recipes()`

**Location**: `src/services/event_service.py`

```python
def get_finished_units_for_event_recipes(
    event_id: int,
    session: Session,
    recipe_category: Optional[str] = None,
    yield_type: Optional[str] = None,
) -> List[FinishedUnit]:
    """
    Get all finished units whose recipe is selected for the event.

    Transaction boundary: Inherits session from caller (required parameter).
    Read-only query within the caller's transaction scope.

    Args:
        event_id: Event to get FUs for
        session: Database session
        recipe_category: Optional filter by recipe category
        yield_type: Optional filter by yield_type ("EA" or "SERVING")

    Returns:
        List of FinishedUnit objects for selected recipes
    """
```

**Query logic**:
```
SELECT fu.*
FROM finished_units fu
JOIN recipes r ON fu.recipe_id = r.id
JOIN event_recipes er ON er.recipe_id = r.id
WHERE er.event_id = :event_id
  AND (r.category = :recipe_category OR :recipe_category IS NULL)
  AND (fu.yield_type = :yield_type OR :yield_type IS NULL)
ORDER BY r.category, r.name, fu.display_name
```

### D2: Modified Cleanup — `remove_invalid_fg_selections()`

**Location**: `src/services/event_service.py` (line 595)

Add a simpler cleanup path alongside the existing bundle-aware logic:
1. Get current selected recipe IDs from EventRecipe
2. For each EventFinishedGood, check if its FinishedGood's component FinishedUnit's recipe_id is in the selected set
3. Delete EventFinishedGood records where the recipe is no longer selected

The existing recursive `check_fg_availability()` remains available for future assembly planning.

### D3: Modified Batch Decomposition

**Location**: `src/services/planning_service.py` (line 55)

In `_decompose_event_to_fu_requirements_impl()`, after querying EventFinishedGood records (line 96-98), add a filter:
1. Get selected recipe IDs from EventRecipe
2. For each EventFinishedGood, decompose to FURequirements as before
3. Filter results: only include FURequirements where `fu.recipe.id` is in selected recipe IDs

This is defense-in-depth — the eager cleanup (D2) should prevent stale records, but this filter catches any that slip through.

### D4: UI Change — `fg_selection_frame.py`

**Location**: `src/ui/components/fg_selection_frame.py` (line 307)

Replace call to `get_filtered_available_fgs()` with `get_finished_units_for_event_recipes()`. The UI will need minor adaptation since it currently expects FinishedGood objects but will now receive FinishedUnit objects. The display logic (checkbox list with names and quantities) is similar.

### Key Decision: FinishedGood vs FinishedUnit in UI

The FG selection frame currently works with FinishedGood objects. The new query returns FinishedUnit objects. Options:
1. **Adapt UI to work with FinishedUnits directly** — cleaner, but may break EventFinishedGood saving
2. **Query FinishedUnits then map back to their FinishedGoods** — preserves existing save logic

**Decision**: Option 2 — query FUs for filtering, but return the corresponding FinishedGood (bare) objects. This preserves the existing EventFinishedGood save flow. The new service function will return FinishedGood objects by joining through FinishedUnit.

### Constitution Re-Check (Post-Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| V. Layered Architecture | PASS | Service layer changes; UI only swaps service call |
| VI-C. Session Parameter | PASS | New function accepts session parameter |
| VI-D. API Consistency | PASS | Returns List[FinishedGood] matching existing pattern |

No new violations introduced.
