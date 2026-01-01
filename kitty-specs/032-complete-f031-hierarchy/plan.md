# Implementation Plan: Complete F031 Hierarchy UI

**Branch**: `032-complete-f031-hierarchy` | **Date**: 2025-12-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/032-complete-f031-hierarchy/spec.md`

## Summary

Complete the UI implementation for F031 Ingredient Hierarchy. The backend (schema, services, import/export) is fully operational. This plan covers updating 5 UI components to use the three-tier hierarchy (L0 Root → L1 Subcategory → L2 Leaf) instead of the deprecated `category` field.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x
**Storage**: SQLite with WAL mode
**Testing**: pytest (service layer); manual UI testing
**Target Platform**: Desktop (macOS, Windows)
**Project Type**: Single desktop application
**Performance Goals**: Responsive UI (<200ms for hierarchy lookups)
**Constraints**: Single-user desktop app, no backend changes
**Scale/Scope**: ~400 ingredients across 3 hierarchy levels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Hierarchy display matches natural ingredient organization |
| II. Data Integrity & FIFO | PASS | No changes to FIFO or cost calculations |
| III. Future-Proof Schema | PASS | Using existing hierarchy fields, no schema changes |
| IV. Test-Driven Development | PASS | Service layer already tested; manual UI tests defined |
| V. Layered Architecture | PASS | UI changes only; services unchanged |
| VI. Schema Change Strategy | N/A | No schema changes |
| VII. Pragmatic Aspiration | PASS | Completing existing feature, no web-blocking changes |

**Constitution Check Result**: All gates pass. Proceed with implementation.

## Project Structure

### Documentation (this feature)

```
kitty-specs/032-complete-f031-hierarchy/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity documentation (no changes)
├── quickstart.md        # Implementation guide
├── research/
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (files to modify)

```
src/ui/
├── ingredients_tab.py      # P1: Grid columns, level filter, edit form
├── products_tab.py         # P2: Hierarchy filter, ingredient path display
├── inventory_tab.py        # P2: Hierarchy columns and filter
└── forms/
    ├── add_product_dialog.py    # COMPLETE (reference implementation)
    └── inventory_form.py        # P2: Read-only hierarchy display
```

## Implementation Phases

### Phase 1: Ingredients Tab (P1 - High Priority)

**Scope**: User Stories 1, 2, 3

**Work Packages**:

1. **WP1-1: Grid Column Update**
   - Replace "Category" column with "Root (L0)", "Subcategory (L1)", "Name" columns
   - Build hierarchy cache using `get_ancestors()` for efficient display
   - Update `_update_ingredient_display()` method
   - Maintain sorting by each column

2. **WP1-2: Level Filter**
   - Replace category dropdown with level filter
   - Options: All Levels, Root (L0), Subcategory (L1), Leaf (L2)
   - Use `get_ingredients_by_level()` or filter locally
   - Update `_apply_filters()` method

3. **WP1-3: Ingredient Edit Form**
   - Replace category dropdown with cascading L0/L1 dropdowns
   - Add ingredient type selector (Root/Subcategory/Leaf)
   - Use `get_root_ingredients()` for L0 dropdown
   - Use `get_children()` for L1 cascade
   - Use `get_ancestors()` to pre-populate when editing
   - Apply withdraw/deiconify pattern for modal stability

### Phase 2: Products Tab (P2 - Medium Priority)

**Scope**: User Story 4

**Work Packages**:

4. **WP2-1: Product Grid Update**
   - Add ingredient hierarchy path column (or modify existing)
   - Display as "L0 → L1 → L2" format
   - Use `get_ancestors()` or similar for path display

5. **WP2-2: Product Hierarchy Filter**
   - Add cascading hierarchy filters (L0 → L1 → L2)
   - Filter products by ingredient hierarchy membership
   - Remove deprecated category filter

### Phase 3: Inventory Tab (P2 - Medium Priority)

**Scope**: User Story 5

**Work Packages**:

6. **WP3-1: Inventory Grid Update**
   - Replace category column with hierarchy columns or path
   - Similar pattern to Products Tab

7. **WP3-2: Inventory Hierarchy Filter**
   - Add hierarchy-based filtering
   - Remove deprecated category filter

8. **WP3-3: Inventory Edit Form**
   - Display read-only hierarchy labels
   - Show L0, L1, L2 as informational fields

### Phase 4: Validation & Testing

**Scope**: User Story 6, all acceptance scenarios

**Work Packages**:

9. **WP4-1: Leaf-Only Validation**
   - Update product ingredient selector to use `get_leaf_ingredients()`
   - Add validation error for non-leaf selection attempts
   - Apply to recipe ingredient selection if applicable

10. **WP4-2: Manual Testing**
    - Execute all 10 test cases from bug specification
    - Verify no deprecated "category" UI elements remain
    - User testing with primary user (Marianne)

## Key Patterns

### Cascading Dropdown Pattern

```python
def _on_category_change(self, choice: str):
    """Handle L0 category selection - populate L1 dropdown."""
    if choice not in self.categories_map:
        self.subcategory_dropdown.configure(values=["(Select category first)"], state="disabled")
        return

    category = self.categories_map[choice]
    self.subcategories = ingredient_hierarchy_service.get_children(category["id"])
    self.subcategories_map = {sub["display_name"]: sub for sub in self.subcategories}

    if self.subcategories:
        self.subcategory_dropdown.configure(values=sorted(self.subcategories_map.keys()), state="normal")
    else:
        self.subcategory_dropdown.configure(values=["(No subcategories)"], state="disabled")
```

### Modal Dialog Pattern

```python
# In __init__:
self.withdraw()  # Hide while building
self.transient(parent)

# ... build UI ...

# After UI complete:
self.deiconify()
self.update()
try:
    self.wait_visibility()
    self.grab_set()
except Exception:
    if not self.winfo_exists():
        return
self.lift()
self.focus_force()
```

### Hierarchy Cache Pattern

```python
def _build_hierarchy_cache(self) -> Dict[int, Tuple[str, str]]:
    """Build cache mapping ingredient ID to (L0_name, L1_name)."""
    cache = {}
    for ingredient in self.ingredients:
        ing_id = ingredient.get("id")
        if not ing_id:
            continue
        ancestors = ingredient_hierarchy_service.get_ancestors(ing_id)
        # ancestors[0] = immediate parent, ancestors[1] = grandparent
        l0_name = ancestors[1]["display_name"] if len(ancestors) >= 2 else "—"
        l1_name = ancestors[0]["display_name"] if len(ancestors) >= 1 else "—"
        cache[ing_id] = (l0_name, l1_name)
    return cache
```

## Complexity Tracking

*No constitution violations. All changes follow existing patterns.*

## Dependencies

- `ingredient_hierarchy_service.py` functions (all available)
- Existing UI component patterns
- No external dependencies

## Estimated Effort

| Phase | Work Packages | Estimated Hours |
|-------|---------------|-----------------|
| Phase 1 | WP1-1, WP1-2, WP1-3 | 8-10 |
| Phase 2 | WP2-1, WP2-2 | 4-5 |
| Phase 3 | WP3-1, WP3-2, WP3-3 | 4-5 |
| Phase 4 | WP4-1, WP4-2 | 4-5 |
| **Total** | 10 work packages | **20-25 hours** |

## Next Steps

1. Run `/spec-kitty.tasks` to generate detailed task prompts
2. Begin with Phase 1 (Ingredients Tab) as highest priority
3. Manual testing after each phase
4. User acceptance testing with Marianne after Phase 4
