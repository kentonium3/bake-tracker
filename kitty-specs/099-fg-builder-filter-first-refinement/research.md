# Research: FG Builder Filter-First Refinement

## R1: is_assembled Field vs assembly_type Enum

**Decision**: Use existing `assembly_type` enum (BARE/BUNDLE) instead of adding new `is_assembled` boolean field.

**Rationale**: The func-spec references `is_assembled=True/False` but the FinishedGood model already has `assembly_type` (AssemblyType enum) with:
- `AssemblyType.BARE` = auto-generated 1:1 FinishedUnit wrapper (equivalent to `is_assembled=False`)
- `AssemblyType.BUNDLE` = user-built multi-component assembly (equivalent to `is_assembled=True`)

The service already supports filtering: `get_all_finished_goods(assembly_type=AssemblyType.BUNDLE)`.

**Alternatives considered**:
- Add `is_assembled` boolean column: Redundant with `assembly_type`, creates data consistency risk
- Rename enum values: Breaking change with no benefit

**Mapping for F099 implementation**:
- Spec's "is_assembled=False" → `assembly_type == AssemblyType.BARE`
- Spec's "is_assembled=True" → `assembly_type == AssemblyType.BUNDLE`

## R2: Current Builder Architecture

**Decision**: Modify existing `FinishedGoodBuilderDialog` in-place rather than rewriting.

**Rationale**: The builder is well-structured with clear separation:
- `_create_food_step_content()` — filter bar + item list (lines 297-354)
- `_query_food_items()` — query logic (lines 368-438)
- `_render_food_items()` — display logic (lines 457-512)
- `_on_food_filter_changed()` — change handler (lines 452-455)

Changes are surgical:
1. Modify `_create_food_step_content()` to change filter options and add placeholder
2. Modify `_query_food_items()` to use new filter logic
3. Remove `_on_food_filter_changed()` call from `_set_initial_state()` (line 213)
4. Add confirmation dialog for filter changes when selections exist

**Alternatives considered**:
- New builder dialog class: Unnecessary duplication, current code is well-factored
- Separate filter component: Over-engineering for a single-use dialog

## R3: Service Layer Filter Capabilities

**Decision**: Existing service methods are sufficient. No new service methods needed.

**Rationale**:
- `finished_unit_service.get_all_finished_units(name_search=..., category=...)` — already supports name and category filtering
- `finished_good_service.get_all_finished_goods(name_search=..., assembly_type=...)` — already supports name and assembly_type filtering
- Category filtering for FGs is currently done in-memory via `_get_fg_category()` — this pattern can continue

**Note**: The `get_all_finished_goods()` method does not accept a `category` parameter. Category filtering for FGs happens in the UI layer via `_get_fg_category()` which inspects components. This is acceptable for the current scale and avoids a complex cross-table join.

## R4: Filter UI Widget Choice

**Decision**: Replace existing `CTkSegmentedButton` with updated values.

**Rationale**: Current implementation uses `CTkSegmentedButton(values=["All", "Bare Items Only"])`. Simply change values to `["Finished Units", "Existing Assemblies", "Both"]`. The widget type is appropriate for mutually exclusive filter options.

**Alternatives considered**:
- `CTkComboBox` dropdown: Less visible, hides options behind click
- Radio buttons: More vertical space, doesn't match existing pattern
- `CTkOptionMenu`: Same visibility issue as ComboBox

## R5: Edit Protection Location

**Decision**: Add edit protection check in `finished_goods_tab.py:_edit_finished_good()` before opening builder.

**Rationale**: The edit trigger is at line 443 in `finished_goods_tab.py`. Adding a check there:
1. Catches the action at the earliest point
2. Prevents unnecessary builder dialog instantiation
3. Shows the block message in the tab context (not inside a builder)

```python
# Before opening builder:
if fg.assembly_type == AssemblyType.BARE:
    show_info("Cannot Edit", "This item is auto-created from a recipe. Edit the recipe to change it.")
    return
```

**Alternatives considered**:
- Check inside builder `__init__`: Too late, dialog already created
- Disable Edit button based on selection type: Would need to track assembly_type in selection state

## R6: Filter Change Warning Implementation

**Decision**: Show confirmation dialog before clearing selections when filters change.

**Rationale**: User confirmed "clear selections and warn the user." Implementation:
1. In `_on_food_filter_changed()`, check if `self._food_selections` is non-empty
2. If selections exist, show confirmation: "Changing filters will clear your current selections. Continue?"
3. If user confirms, clear selections and reload
4. If user cancels, revert filter to previous value

**Key detail**: Need to track previous filter values to revert on cancel. Add `_prev_food_type_var` and `_prev_food_category_var` instance variables.

## R7: Blank Start / Placeholder Implementation

**Decision**: Show placeholder text in the scrollable frame when no filters are selected.

**Rationale**: The current `_render_food_items()` already handles empty state. For blank start:
1. Remove `_on_food_filter_changed()` call from `_set_initial_state()` (line 213)
2. Show placeholder text in `_food_item_list_frame` on creation
3. First filter selection triggers `_on_food_filter_changed()` which replaces placeholder

**Placeholder text**: "Select item type above to see available items"
