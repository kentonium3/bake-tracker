# Implementation Plan: Planning FG Selection Refinement

**Branch**: `100-planning-fg-selection-refinement` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/100-planning-fg-selection-refinement/spec.md`

## Summary

Replace the Planning tab's auto-load-all recipe and FG selection with a filter-first pattern (mirroring F099). Recipe selection adds a category filter dropdown; FG selection adds three independent AND-combinable filters (recipe category, item type, yield type). Selections persist across filter changes in-memory and are saved atomically to the database on final Save. Two-level clear buttons and a "Show All Selected" toggle complete the UX.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with in-memory SQLite (`test_db` fixture)
**Target Platform**: macOS desktop (Darwin)
**Project Type**: Single desktop application
**Performance Goals**: Instant blank-start frames; filter results < 200ms
**Constraints**: Must not break existing 3644+ test suite; must preserve existing event_service API contracts
**Scale/Scope**: ~50 recipes, ~100 FGs, ~20 recipe categories typical catalog size

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. User-Centric Design | PASS | Filter-first pattern validated via F099 user testing; mirrors natural workflow |
| II. Data Integrity & FIFO | PASS | No cost/inventory changes; selection persistence is UI-only until atomic save |
| III. Future-Proof Schema | PASS | No schema changes; using existing models (EventFinishedGood, RecipeCategory) |
| IV. Test-Driven Development | PASS | New service query functions require unit tests; UI components need integration tests |
| V. Layered Architecture | PASS | New query logic goes in services; UI calls services for data; no business logic in UI |
| VI. Code Quality | PASS | Session parameter pattern on new service functions; exception-based error handling |
| VII. Schema Change Strategy | N/A | No schema changes required |
| VIII. Pragmatic Aspiration | PASS | Service-layer filtering readily wraps into future API endpoints |

## Project Structure

### Documentation (this feature)

```
kitty-specs/100-planning-fg-selection-refinement/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Phase 2 output (via /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── recipe_category.py        # Existing - queried for filter options
│   ├── recipe.py                 # Existing - Recipe.category field
│   ├── finished_good.py          # Existing - FinishedGood.assembly_type
│   ├── finished_unit.py          # Existing - FinishedUnit.yield_type
│   ├── event_finished_good.py    # Existing - junction table (no changes)
│   └── assembly_type.py          # Existing - BARE/BUNDLE enum
├── services/
│   ├── event_service.py          # MODIFY - add filtered FG query functions
│   ├── recipe_service.py         # Existing - get_recipes_by_category() already exists
│   ├── recipe_category_service.py # Existing - list_categories() already exists
│   ├── finished_good_service.py  # Existing - may add filtered query helper
│   └── finished_unit_service.py  # Existing - list_finished_units_by_recipe() exists
├── ui/
│   ├── planning_tab.py           # MODIFY - orchestration for filter-first flow
│   └── components/
│       ├── recipe_selection_frame.py  # MODIFY - add category filter dropdown
│       └── fg_selection_frame.py      # MODIFY - add three filter dropdowns + persistence
└── tests/
    ├── services/
    │   └── test_event_service.py  # ADD tests for new query functions
    └── ui/
        └── (integration tests if applicable)
```

**Structure Decision**: Existing single-project structure. All changes are modifications to existing files plus new test coverage. No new modules needed.

## Design Decisions

### D1: Where do FG filter queries live?

**Decision**: Add new service functions to `event_service.py` (specifically `get_filtered_finished_goods()`) since FG availability is already event-scoped there.

**Rationale**: `get_available_finished_goods()` already lives in event_service and establishes the pattern. The new filtered version extends this with additional filter parameters.

### D2: Recipe category source for filter dropdowns

**Decision**: Use `recipe_category_service.list_categories()` for the recipe selection category dropdown. For the FG-level recipe category filter, derive categories from recipes that have associated FGs available for the event.

**Rationale**: RecipeCategory model (F096) is the authoritative source. Using it directly ensures consistency with category management.

### D3: Selection persistence mechanism

**Decision**: In-memory `Set[int]` on the UI frame components. Selections are tracked as FG IDs (and recipe IDs) in Python sets that survive filter changes. Only written to DB on explicit Save.

**Rationale**: Matches spec requirement FR-014 (UI state persistence). No new models or intermediate DB writes needed. The existing `set_event_fg_quantities()` handles atomic save.

### D4: FG filter dimensions

**Decision**: Three independent dropdowns:
1. **Recipe Category**: Filters FGs whose recipe belongs to selected category (uses `Recipe.category` field matched against `RecipeCategory.name`)
2. **Item Type**: "Finished Units" (BARE FGs) vs "Assemblies" (BUNDLE FGs) vs "All" (uses `FinishedGood.assembly_type`)
3. **Yield Type**: "EA" vs "SERVING" vs "All" (uses `FinishedUnit.yield_type`, only applicable to BARE FGs)

**Rationale**: These three dimensions cover the natural categorization of the catalog and match the spec's filter requirements.

### D5: Quantity entry location

**Decision**: Keep quantities integrated in the FG selection frame (current F071 pattern). Do NOT create a separate "quantity step" — spec references steps but the current UI uses a single frame with checkboxes + quantity entries side by side.

**Rationale**: The current FGSelectionFrame already has quantity inputs per-row (F071). Adding a separate step would be unnecessary complexity. The spec's "quantity step" language maps to the existing pattern where quantities are entered alongside FG selection.

### D6: How "Show All Selected" works

**Decision**: A toggle button on the FG selection frame that, when active, replaces the filtered list with only selected FGs (from the in-memory selection set). Filter dropdowns remain visible but are visually dimmed. Changing any filter exits the mode.

**Rationale**: Matches spec FR-011/FR-012. Simple UI state toggle.

## Implementation Approach

### Phase 1: Recipe Selection Enhancement (US1)

1. Modify `RecipeSelectionFrame` to add a category filter dropdown at the top
2. Start with blank scroll frame + placeholder text
3. On category change, call `recipe_service.get_recipes_by_category()` or `get_all_recipes()` for "All"
4. Maintain `_selected_recipe_ids: Set[int]` that persists across filter changes
5. When rendering checkboxes after filter change, restore checked state from the set

### Phase 2: FG Filtered Selection (US2, US3)

1. Modify `FGSelectionFrame` to add three filter dropdowns above the scroll area
2. Add new service function: `get_filtered_available_fgs(event_id, recipe_category, assembly_type, yield_type, session)` in `event_service.py`
3. Start blank; load on first filter selection
4. AND-combine filters; query service layer
5. Maintain `_selected_fg_ids: Set[int]` and `_fg_quantities: Dict[int, int]` that persist across filter changes
6. When rendering, restore checkbox + quantity state from persistence dicts

### Phase 3: Clear Buttons (US4)

1. Add "Clear All" and "Clear Finished Goods" buttons to the planning container
2. Both show confirmation dialogs before executing
3. "Clear All" resets recipe selection + FG selection + quantities
4. "Clear Finished Goods" resets only FG selection + quantities

### Phase 4: Show All Selected Toggle (US5)

1. Add "Show All Selected" / "Show Filtered View" toggle button to FG frame
2. When active, render only FGs in `_selected_fg_ids` regardless of filters
3. Display count indicator: "Showing N selected items"
4. Exit mode on any filter dropdown change

### Phase 5: Quantity Persistence & Atomic Save (US6)

1. Quantities already live in `_fg_quantities: Dict[int, int]`
2. On Save, call `set_event_fg_quantities()` with all selected FG/qty pairs
3. Validation: positive integers only (existing F071 pattern)
4. Save button disabled when validation errors exist

## Complexity Tracking

No constitution violations. All changes follow existing patterns.
