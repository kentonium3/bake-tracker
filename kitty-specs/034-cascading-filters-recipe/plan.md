# Implementation Plan: Cascading Filters & Recipe Integration

**Branch**: `034-cascading-filters-recipe` | **Date**: 2026-01-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/034-cascading-filters-recipe/spec.md`

## Summary

Phase 2 of the ingredient hierarchy gap analysis. Fix cascading filter behavior in Product and Inventory tabs (L0 -> L1 -> L2 dropdowns should cascade properly), add "Clear Filters" buttons, and verify recipe integration with L2-only ingredient selection.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x
**Storage**: SQLite (existing database)
**Testing**: pytest
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: Filter interactions under 500ms
**Constraints**: Must not regress existing functionality
**Scale/Scope**: Single user, ~100-500 ingredients

## Constitution Check

*GATE: All checks pass*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Fixes broken UX, adds Clear button for convenience |
| II. Data Integrity | N/A | UI-only changes, no data modifications |
| III. Future-Proof Schema | N/A | No schema changes |
| IV. Test-Driven Development | PASS | Will add tests for cascading behavior |
| V. Layered Architecture | PASS | UI layer only, uses existing services |
| VI. Schema Change Strategy | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Fixes existing feature, no over-engineering |

## Project Structure

### Documentation (this feature)

```
kitty-specs/034-cascading-filters-recipe/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Code analysis and decisions
├── data-model.md        # Entity reference (no changes)
├── research/
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks/               # Work packages (created by /spec-kitty.tasks)
    ├── planned/
    ├── doing/
    └── done/
```

### Source Code (files to modify)

```
src/
├── ui/
│   ├── products_tab.py      # WP1: Fix cascading + Clear button
│   ├── inventory_tab.py     # WP2: Fix cascading + Clear button (parallel)
│   └── forms/
│       └── recipe_form.py   # WP3: Verify L2-only (read-only check)
└── tests/
    └── ui/                  # New integration tests if applicable
```

**Structure Decision**: Existing desktop app structure. No new directories needed.

## Complexity Tracking

*No constitution violations - all changes are straightforward UI fixes*

## Parallelization Strategy

This feature is designed for safe parallel execution between Claude and Gemini.

### Work Package Assignments

| WP | Description | Agent | File(s) | Dependencies |
|----|-------------|-------|---------|--------------|
| WP1 | Products tab cascading fix + Clear button | Claude | `src/ui/products_tab.py` | None |
| WP2 | Inventory tab cascading fix + Clear button | Gemini | `src/ui/inventory_tab.py` | Pattern from WP1 |
| WP3 | Recipe integration verification | Either | `src/ui/forms/recipe_form.py` | None |
| WP4 | Integration tests | Either | `src/tests/` | After WP1+WP2 |

### Parallelization Rules

1. **File Boundaries**: Claude modifies `products_tab.py` ONLY, Gemini modifies `inventory_tab.py` ONLY
2. **Pattern Sharing**: Claude completes WP1 first to establish the fix pattern, then Gemini applies identical pattern to WP2
3. **No Service Changes**: Both tabs use existing `ingredient_hierarchy_service` functions
4. **Test Isolation**: Integration tests written after both fixes are complete

### Execution Order

```
Phase A (Sequential):
  Claude: WP1 - Fix products_tab.py cascading + add Clear button

Phase B (Parallel):
  Gemini: WP2 - Apply same fix to inventory_tab.py (uses WP1 as reference)
  Claude: WP3 - Verify recipe_form.py integration

Phase C (Sequential):
  Either: WP4 - Write integration tests for both tabs
```

## Implementation Details

### WP1: Products Tab Cascading Fix

**Files**: `src/ui/products_tab.py`

**Tasks**:
1. Debug `_on_l0_filter_change()` to identify why L1 doesn't update
2. Add logging/debugging to trace event flow
3. Fix any identified issues (likely timing or state sync)
4. Add re-entry guards if event handlers are recursing
5. Add "Clear Filters" button following `ingredients_tab.py` pattern
6. Test manually with real data

**Clear Button Implementation** (from `ingredients_tab.py:163-170`):
```python
# Add to filter frame
clear_button = ctk.CTkButton(
    filter_frame,
    text="Clear",
    command=self._clear_filters,
    width=60,
)
clear_button.pack(side="left", padx=10, pady=5)

def _clear_filters(self):
    """Clear all hierarchy filters and refresh."""
    self.l0_filter_var.set("All Categories")
    self.l1_filter_var.set("All")
    self.l2_filter_var.set("All")
    self._l1_map = {}
    self._l2_map = {}
    self.l1_filter_dropdown.configure(values=["All"], state="disabled")
    self.l2_filter_dropdown.configure(values=["All"], state="disabled")
    self.brand_var.set("All")
    self.supplier_var.set("All")
    self._load_products()
```

### WP2: Inventory Tab Cascading Fix

**Files**: `src/ui/inventory_tab.py`

**Tasks**: Mirror WP1 changes exactly. The code structure is nearly identical.

### WP3: Recipe Integration Verification

**Files**: `src/ui/forms/recipe_form.py`

**Tasks**:
1. Manual test: Open recipe form, try to add ingredient
2. Verify `IngredientTreeWidget` with `leaf_only=True` works
3. Attempt to select L0/L1 - should be blocked
4. Document any issues found

**Expected Result**: No code changes needed if tree widget works correctly.

### WP4: Integration Tests

**Files**: `src/tests/ui/test_cascading_filters.py` (new)

**Tasks**:
1. Test L0 selection updates L1 options
2. Test L1 selection updates L2 options
3. Test Clear button resets all dropdowns
4. Test filter application to product/inventory lists

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Cascading L0->L1 works | 100% | Manual test + automated |
| Cascading L1->L2 works | 100% | Manual test + automated |
| Clear button resets all | 100% | Manual test |
| Recipe L2-only enforced | 100% | Manual test |
| No regressions | 0 new bugs | Run existing tests |

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Bug is deeper than UI layer | Medium | Add debug logging, check service layer |
| Event handler race conditions | Low | Add re-entry guards |
| Gemini applies pattern incorrectly | Low | WP1 provides clear reference pattern |

## Next Steps

1. Run `/spec-kitty.tasks` to generate work package prompt files
2. Claude executes WP1 first
3. Gemini executes WP2 in parallel with WP3
4. Either agent executes WP4 for tests
5. Run `/spec-kitty.review` when all WPs complete
