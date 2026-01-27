# Implementation Plan: Finished Goods Filtering for Event Planning

**Branch**: `070-finished-goods-filtering` | **Date**: 2026-01-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/070-finished-goods-filtering/spec.md`

## Summary

Enable dynamic filtering of finished goods based on selected recipes. When a baker selects recipes for an event (F069), only FGs whose required recipes are all selected will appear. For bundles (nested FGs), the system recursively decomposes to atomic FinishedUnits to determine all required recipes. Deselecting a recipe automatically removes dependent FG selections with user notification.

**Key Discovery**: FinishedGood is a bundle/assembly container that does NOT directly link to recipes. Recipe linkage is on FinishedUnit (atomic items) via `recipe_id`. Bundles contain components via the Composition junction model, which can reference either FinishedUnit or nested FinishedGood.

## Technical Context

**Language/Version**: Python 3.10+ (per constitution)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest (TDD required per constitution)
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single project with layered architecture
**Performance Goals**: FG list updates within 500ms of recipe selection change
**Constraints**: Circular reference detection required; max 10 nesting levels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Filtering prevents invalid FG selections; auto-removal protects data integrity |
| II. Data Integrity | PASS | Cascade removal ensures no orphaned FG selections |
| III. Future-Proof Schema | PASS | Uses existing models; no schema changes |
| IV. Test-Driven Development | PASS | Service layer methods require unit tests |
| V. Layered Architecture | PASS | Service layer handles logic; UI handles presentation |
| VI. Schema Change Strategy | N/A | No schema changes required |
| VII. Pragmatic Aspiration | PASS | Desktop-focused; service layer is API-ready |

**Re-check after Phase 1**: All gates remain PASS. Design follows existing recursive patterns from `finished_good_service.py` and `batch_calculation.py`.

## Project Structure

### Documentation (this feature)

```
kitty-specs/070-finished-goods-filtering/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── checklists/          # Quality checklists
└── tasks.md             # Phase 2 output (via /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── finished_good.py      # FinishedGood (bundle) model [READ ONLY]
│   ├── finished_unit.py      # FinishedUnit (atomic, has recipe_id) [READ ONLY]
│   ├── composition.py        # Junction: FG -> components [READ ONLY]
│   ├── event_recipe.py       # Junction: Event -> Recipe (F069) [READ ONLY]
│   └── event_finished_good.py # Junction: Event -> FG [READ ONLY]
├── services/
│   ├── event_service.py      # Add: FG availability methods [MODIFY]
│   └── planning/
│       └── batch_calculation.py # Reference pattern [READ ONLY]
├── ui/
│   ├── planning_tab.py       # Integration point [MODIFY]
│   └── components/
│       └── fg_selection_frame.py # NEW: FG selection UI component

tests/
├── test_fg_availability.py   # NEW: Service layer tests
└── test_fg_selection_frame.py # NEW: UI component tests
```

**Structure Decision**: Single project with layered architecture. New service methods added to `event_service.py` (follows F069 pattern). New UI component `fg_selection_frame.py` follows `recipe_selection_frame.py` pattern.

## Parallelization Strategy

**Approach**: Service-first, then parallel UI (user confirmed)

| Phase | Work Packages | Agent | Dependencies |
|-------|--------------|-------|--------------|
| 1 | WP01: Bundle decomposition | Claude (lead) | None |
| 1 | WP02: Availability + cascade removal | Claude (lead) | WP01 |
| 2 | WP03: FG list filtering UI | Gemini | WP01, WP02 |
| 2 | WP04: Real-time updates + notifications | Codex | WP01, WP02 |

**File Boundaries** (prevents merge conflicts):
- **Claude (WP01-02)**: `src/services/event_service.py`, `src/tests/test_fg_availability.py`
- **Gemini (WP03)**: `src/ui/components/fg_selection_frame.py`, `src/tests/test_fg_selection_frame.py`
- **Codex (WP04)**: `src/ui/planning_tab.py` (FG integration section only)

## Work Package Summary

### WP01: Bundle Decomposition Algorithm (Service Layer)

**Agent**: Claude (lead)
**Depends on**: None
**File**: `src/services/event_service.py`

**Deliverables**:
- `get_required_recipes(fg_id, session) -> Set[int]` - Recursively decompose FG to atomic recipe IDs
- Circular reference detection (track visited IDs)
- Depth limiting (max 10 levels)
- Unit tests for: atomic FG, simple bundle, nested bundle, circular reference, deep nesting

**Pattern to follow**: `finished_good_service._get_flattened_components()` (BFS with visited set)

### WP02: FG Availability Checking + Cascade Removal (Service Layer)

**Agent**: Claude (lead)
**Depends on**: WP01
**File**: `src/services/event_service.py`

**Deliverables**:
- `check_fg_availability(fg_id, selected_recipe_ids, session) -> AvailabilityResult` - Check if FG is available
- `get_available_finished_goods(event_id, session) -> List[FinishedGood]` - Get all available FGs for event
- `remove_invalid_fg_selections(event_id, session) -> List[RemovedFG]` - Remove FGs when recipe deselected
- Modify `set_event_recipes()` to call removal after recipe changes
- Unit tests for all methods

### WP03: FG Selection Frame UI Component

**Agent**: Gemini
**Depends on**: WP01, WP02
**File**: `src/ui/components/fg_selection_frame.py` (NEW)

**Deliverables**:
- `FGSelectionFrame(CTkFrame)` - Similar pattern to `RecipeSelectionFrame`
- Display only available FGs (filtered by service)
- Checkbox selection per FG
- Live count display
- Save/Cancel buttons with callback support
- UI tests

**Pattern to follow**: `src/ui/components/recipe_selection_frame.py`

### WP04: Planning Tab Integration + Notifications

**Agent**: Codex
**Depends on**: WP01, WP02
**File**: `src/ui/planning_tab.py`

**Deliverables**:
- Embed `FGSelectionFrame` in Planning Tab (below recipe selection)
- Wire recipe selection changes to trigger FG list refresh
- Show notification when FGs auto-removed
- Handle save/cancel for FG selections
- Integration tests

**Pattern to follow**: Recipe selection integration in `planning_tab.py` (F069)

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Circular references in bundles | Detect with visited set; raise `CircularReferenceError` |
| Deep nesting (performance) | Limit to 10 levels; raise `MaxDepthExceededError` |
| Race conditions on rapid recipe toggles | Service layer is stateless; UI debounces if needed |
| Session detachment issues | All service methods accept `session` parameter (follow F069 pattern) |
| Merge conflicts during parallel work | Strict file boundaries per agent |

## Complexity Tracking

*No constitution violations requiring justification.*

## Next Steps

1. Run `/spec-kitty.tasks` to generate work package task files
2. Claude implements WP01, WP02 sequentially
3. After WP02 complete, Gemini (WP03) and Codex (WP04) work in parallel
4. Review and merge
