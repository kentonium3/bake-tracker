# Feature Specification: Cascading Filters & Recipe Integration

**Feature Branch**: `034-cascading-filters-recipe`
**Created**: 2026-01-02
**Status**: Draft
**Input**: Phase 2 of ingredient hierarchy gap analysis (docs/design/_F033_ingredient_hierarchy_gap_analysis.md)

## Background

Phase 1 (F033) fixed the ingredient edit form mental model and ingredients tab display. Phase 2 addresses the remaining integration gaps: cascading filters in Product/Inventory tabs don't update properly when parent selections change, and recipe integration with the ingredient hierarchy is unverified.

**Gap Analysis References**:
- Blocker 3: REQ-ING-023 - Cascading filters broken (L1 doesn't filter based on L0 selection)
- REQ-ING-018/019/020: Recipe integration unverified

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Product Tab Cascading Filters (Priority: P1)

When filtering products by ingredient hierarchy, the user selects an L0 category and expects the L1 dropdown to show only subcategories under that L0. Currently, the L1 dropdown shows all L1 ingredients regardless of L0 selection.

**Why this priority**: Product filtering is a core workflow. Users cannot effectively find products by category if filters don't cascade correctly. This affects daily inventory management.

**Independent Test**: Open Product tab, select an L0 filter, verify L1 dropdown updates to show only children of the selected L0.

**Acceptance Scenarios**:

1. **Given** user is on the Product tab with no filters, **When** they select "Baking" (L0) from the first dropdown, **Then** the L1 dropdown updates to show only subcategories under "Baking" (e.g., "Flour", "Sugar", "Leavening")
2. **Given** user has selected "Baking" (L0) and "Flour" (L1), **When** they change L0 to "Dairy", **Then** the L1 dropdown clears and updates to show only subcategories under "Dairy" (e.g., "Milk", "Butter", "Cheese")
3. **Given** user has selected L0 and L1 filters, **When** they change L1 selection, **Then** the L2 dropdown updates to show only leaf ingredients under the selected L1
4. **Given** user has filters applied, **When** they click a "Clear Filters" button, **Then** all filter dropdowns reset to their default "All" state and the product list shows all products

---

### User Story 2 - Inventory Tab Cascading Filters (Priority: P2)

The Inventory tab has the same cascading filter issue as the Product tab. When filtering inventory by ingredient hierarchy, selecting an L0 should constrain L1 options.

**Why this priority**: Inventory filtering uses the same pattern as Product tab. Fixing one should apply the same solution to the other. Grouped together for consistency.

**Independent Test**: Open Inventory tab, select an L0 filter, verify L1 dropdown updates to show only children of the selected L0.

**Acceptance Scenarios**:

1. **Given** user is on the Inventory tab, **When** they select an L0 category, **Then** the L1 dropdown shows only subcategories under that L0
2. **Given** user has L0 and L1 filters selected, **When** they change L0, **Then** L1 and L2 selections clear and L1 options update accordingly
3. **Given** user has filters applied, **When** they click "Clear Filters", **Then** all hierarchy filter dropdowns reset

---

### User Story 3 - Recipe Ingredient Selection (Priority: P1)

When adding ingredients to a recipe, users should only be able to select L2 (leaf) ingredients. The selection should use cascading dropdowns (L0 -> L1 -> L2) to help users navigate the hierarchy, and the system should prevent selection of L0/L1 ingredients.

**Why this priority**: Recipe creation is a core workflow. If users can select L0/L1 ingredients, recipe cost calculations and shopping lists will be incorrect. This is a data integrity issue.

**Independent Test**: Open recipe create/edit form, attempt to add an ingredient, verify only L2 ingredients can be selected via cascading dropdowns.

**Acceptance Scenarios**:

1. **Given** user is adding an ingredient to a recipe, **When** the ingredient selector appears, **Then** it shows cascading dropdowns for L0, L1, and L2 (not a flat list)
2. **Given** user has selected L0 "Baking" and L1 "Flour", **When** they look at the L2 dropdown, **Then** they see only leaf ingredients under "Flour" (e.g., "All-Purpose Flour", "Bread Flour")
3. **Given** user selects an L2 ingredient, **When** they confirm the selection, **Then** the ingredient is added to the recipe
4. **Given** the ingredient selector UI, **When** user attempts to save without selecting an L2 ingredient, **Then** the system shows a validation error requiring L2 selection

---

### Edge Cases

- What happens when an L0 category has no L1 children? (Show empty L1 dropdown with message "No subcategories")
- What happens when an L1 category has no L2 children? (Show empty L2 dropdown with message "No ingredients")
- How does the system handle rapid filter changes? (Debounce or queue updates to prevent race conditions)
- What if a previously selected L1/L2 becomes invalid after L0 change? (Clear invalid selections automatically)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST update L1 dropdown options when L0 selection changes in Product tab filter
- **FR-002**: System MUST update L2 dropdown options when L1 selection changes in Product tab filter
- **FR-003**: System MUST clear child selections (L1, L2) when parent selection changes
- **FR-004**: System MUST provide "Clear Filters" functionality to reset all hierarchy filters
- **FR-005**: System MUST apply the same cascading behavior to Inventory tab filters
- **FR-006**: System MUST use cascading selectors (L0 -> L1 -> L2) in recipe ingredient selection
- **FR-007**: System MUST validate that only L2 (leaf) ingredients can be added to recipes
- **FR-008**: System MUST display validation error when user attempts to add non-L2 ingredient to recipe
- **FR-009**: System MUST prevent infinite loops in cascading dropdown event handlers (re-entry guards)
- **FR-010**: System MUST filter product/inventory lists based on selected hierarchy level (show all descendants of selected category)

### Key Entities

- **Ingredient**: Three-tier hierarchy (L0 root, L1 subcategory, L2 leaf) via `parent_ingredient_id` self-reference
- **Product**: Links to L2 Ingredient via `ingredient_id` FK
- **Recipe**: Contains RecipeIngredient entries that must reference L2 ingredients only
- **RecipeIngredient**: Junction table linking Recipe to Ingredient with quantity/unit

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All cascading filter interactions complete within 500ms (no perceptible lag)
- **SC-002**: Zero instances of L0/L1 ingredients in recipe ingredient lists after feature deployment
- **SC-003**: L1 dropdown correctly filters to show only children of selected L0 in 100% of test cases
- **SC-004**: Clear Filters resets all dropdowns to default state in single click
- **SC-005**: Recipe ingredient selection uses consistent cascading UI matching Product tab pattern
- **SC-006**: No regressions in existing Product/Inventory tab functionality

## Technical Notes

### Files Likely to Modify

1. **`src/ui/products_tab.py`**: Fix cascading filter logic, add event handler guards
2. **`src/ui/inventory_tab.py`**: Apply same cascading filter fixes
3. **`src/ui/recipes_tab.py`**: Verify/add cascading ingredient selector
4. **`src/ui/forms/recipe_form.py`** or **`src/ui/forms/add_recipe_dialog.py`**: Add cascading selector for ingredient selection
5. **`src/services/ingredient_hierarchy_service.py`**: May need helper for "get children of" queries

### Existing Functions to Leverage

- `get_children(parent_id)` - Returns direct children of an ingredient
- `get_descendants(ingredient_id)` - Returns all descendants (for filtering)
- `validate_hierarchy()` - Validates hierarchy relationships
- Phase 1 added `get_product_count()`, `get_child_count()`, `can_change_parent()`
