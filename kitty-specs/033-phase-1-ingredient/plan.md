# Implementation Plan: Phase 1 Ingredient Hierarchy Fixes

**Branch**: `033-phase-1-ingredient` | **Date**: 2026-01-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/033-phase-1-ingredient/spec.md`

## Summary

Fix conceptual issues in F032's ingredient hierarchy implementation:
1. Remove level selector dropdown; display level as computed from parent selection
2. Add missing validation convenience functions (`can_change_parent`, `get_product_count`, `get_child_count`)
3. Add hierarchy path column to ingredients tab display
4. Mark legacy `ingredient_form.py` for deprecation

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A (simple UI operations)
**Constraints**: No schema changes; service functions must accept optional session parameter
**Scale/Scope**: Single user, ~100-500 ingredients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Fixes confusing hybrid UI; computed level reduces cognitive load |
| II. Data Integrity & FIFO | PASS | No changes to data model or FIFO logic |
| III. Future-Proof Schema | PASS | No schema changes |
| IV. Test-Driven Development | PASS | New service functions will have unit tests |
| V. Layered Architecture | PASS | UI calls services; services access models |
| VI. Schema Change Strategy | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Simple fix; doesn't block web migration |

**Gate Status**: PASSED

## Project Structure

### Documentation (this feature)

```
kitty-specs/033-phase-1-ingredient/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entity documentation (no changes)
├── research/            # Evidence tracking
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── ingredient.py        # No changes
├── services/
│   └── ingredient_hierarchy_service.py  # Add 3 new functions
├── ui/
│   ├── ingredients_tab.py   # Fix inline form, add hierarchy column
│   └── forms/
│       └── ingredient_form.py  # Add deprecation warning
└── tests/
    └── services/
        └── test_ingredient_hierarchy_service.py  # Add tests for new functions
```

**Structure Decision**: Single project structure; modifications to existing files only.

## Complexity Tracking

*No Constitution violations requiring justification.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |

## Implementation Phases

### Phase 1: Service Layer (P2 Priority)

**Files**: `src/services/ingredient_hierarchy_service.py`

1. Add `get_child_count(ingredient_id, session=None) -> int`
2. Add `get_product_count(ingredient_id, session=None) -> int`
3. Add `can_change_parent(ingredient_id, new_parent_id, session=None) -> dict`
4. Add unit tests for all three functions

**Dependencies**: None (builds on existing functions)

### Phase 2: UI Form Fix (P1 Priority)

**Files**: `src/ui/ingredients_tab.py`

1. Remove `ingredient_level_dropdown` and `ingredient_level_var` (lines ~866-879)
2. Add read-only `level_display` label
3. Update `_on_parent_change()` to compute and display level
4. Update `_on_l0_change()` and `_on_l1_change()` callbacks
5. Filter parent dropdowns to exclude L2 ingredients
6. Add inline warning display for parent changes

**Dependencies**: Phase 1 (needs `can_change_parent()`)

### Phase 3: Display Enhancement (P3 Priority)

**Files**: `src/ui/ingredients_tab.py`

1. Add `hierarchy_path` column to treeview
2. Build `_hierarchy_path_cache` on data load
3. Use `get_ancestors()` to compute paths
4. Display paths in list view

**Dependencies**: None (uses existing `get_ancestors()`)

### Phase 4: Deprecation & Cleanup

**Files**: `src/ui/forms/ingredient_form.py`

1. Add deprecation docstring and comment
2. Optionally add runtime warning when dialog opens
3. Update any code that calls this dialog (if found)

**Dependencies**: None

## Test Strategy

| Test Type | Scope | Location |
|-----------|-------|----------|
| Unit | `get_child_count()` | `test_ingredient_hierarchy_service.py` |
| Unit | `get_product_count()` | `test_ingredient_hierarchy_service.py` |
| Unit | `can_change_parent()` all scenarios | `test_ingredient_hierarchy_service.py` |
| Integration | Parent change with warnings | Manual testing |
| Regression | Existing ingredient CRUD | Run full test suite |

## Success Criteria

- [ ] No explicit level selector in inline form
- [ ] Level displays correctly based on parent selection
- [ ] `can_change_parent()` returns correct allowed/warnings
- [ ] `get_product_count()` returns accurate counts
- [ ] `get_child_count()` returns accurate counts
- [ ] Hierarchy path column displays in ingredients list
- [ ] All new functions have >90% test coverage
- [ ] Existing tests still pass
- [ ] Legacy form marked as deprecated
