# Feature Specification: Phase 1 Ingredient Hierarchy Fixes

**Feature Branch**: `033-phase-1-ingredient`
**Created**: 2026-01-01
**Status**: Draft
**Input**: Gap analysis from `docs/requirements/req_ingredients_GAP_ANALYSIS.md`

## Background

F031 and F032 implemented the ingredient hierarchy infrastructure (three-tier: L0 → L1 → L2). However, a code review and gap analysis revealed critical issues:

1. **Edit Form Mental Model Issue**: The inline edit form in `ingredients_tab.py` has BOTH a level selector dropdown AND parent selection dropdowns. This is conceptually wrong - level should be COMPUTED from parent selection, not chosen directly.

2. **Missing Validation Services**: The gap analysis identified three convenience functions needed for UI warnings: `can_change_parent()`, `get_product_count()`, `get_child_count()`. These do not exist.

3. **Tab Display Gaps**: Need to verify ingredients tab displays hierarchy path correctly (inventory tab was fixed in F032).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Parent Selection UX (Priority: P1)

When editing an ingredient, the user should select its parent ingredient (or "none" for root), and the hierarchy level should be automatically computed and displayed - not selected manually.

**Why this priority**: The current hybrid UI (select level + select parent) confuses the mental model. Users don't understand why they're selecting a level when the level is determined by parent choice.

**Independent Test**: Create/edit an ingredient, verify that selecting a parent automatically shows the correct level, and that there is no separate level selector.

**Acceptance Scenarios**:

1. **Given** user opens the Add Ingredient form, **When** they select no parent, **Then** the form shows "Level: L0 (Root)" as read-only info
2. **Given** user opens the Add Ingredient form, **When** they select an L0 ingredient as parent, **Then** the form shows "Level: L1 (Subcategory)" as read-only info
3. **Given** user opens the Add Ingredient form, **When** they select an L1 ingredient as parent, **Then** the form shows "Level: L2 (Leaf)" as read-only info
4. **Given** user opens the Add Ingredient form, **When** they try to select an L2 ingredient as parent, **Then** the dropdown only shows L0 and L1 ingredients (L2 cannot have children)

---

### User Story 2 - Validation Before Parent Change (Priority: P2)

When changing an ingredient's parent, the system should check if the change is safe and warn the user about potential impacts before allowing the change.

**Why this priority**: Changing an L2 ingredient to L1 (or vice versa) can have cascading effects on products and child ingredients. Users need protection from accidental changes.

**Independent Test**: Attempt to change parent of an ingredient that has children or linked products, verify warning is shown.

**Acceptance Scenarios**:

1. **Given** an L1 ingredient with 3 child L2 ingredients, **When** user tries to change its parent to make it L2, **Then** system shows error "Cannot change: has 3 child ingredients that would exceed max depth"
2. **Given** an L2 ingredient with 5 linked products, **When** user tries to change its parent, **Then** system shows warning "This ingredient has 5 linked products. Changing parent will affect product categorization. Continue?"
3. **Given** an L0 ingredient with descendants, **When** user tries to delete it, **Then** system shows error "Cannot delete: has child ingredients"

---

### User Story 3 - Hierarchy Path Display in Ingredients Tab (Priority: P3)

The ingredients tab list should display the full hierarchy path for each ingredient so users can understand where each ingredient sits in the taxonomy.

**Why this priority**: Visual clarity helps users navigate the hierarchy. This was already done for inventory tab in F032; ingredients tab needs the same treatment.

**Independent Test**: View ingredients list, verify each ingredient shows its hierarchy path (e.g., "Baking > Flour > All-Purpose Flour").

**Acceptance Scenarios**:

1. **Given** an L2 ingredient "All-Purpose Flour" under "Flour" under "Baking", **When** user views the ingredients list, **Then** they see "Baking > Flour > All-Purpose Flour" in the hierarchy column
2. **Given** an L0 ingredient "Baking", **When** user views the ingredients list, **Then** they see just "Baking" in the hierarchy column (no path separators)

---

### Edge Cases

- What happens when the last parent option is deleted? (User should not be stranded with invalid parent references)
- How does system handle circular reference attempts? (Already handled by `validate_hierarchy()`)
- What happens when changing parent would orphan child ingredients? (Block with clear error message)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove the explicit "Ingredient Level" dropdown from the edit form and replace with computed display-only level indicator
- **FR-002**: System MUST filter parent dropdown to only show valid parent options (L0 and L1 ingredients, not L2)
- **FR-003**: System MUST provide `can_change_parent(ingredient_id, new_parent_id)` function returning `{allowed: bool, reason: str, warnings: list}`
- **FR-004**: System MUST provide `get_product_count(ingredient_id)` function returning count of linked products
- **FR-005**: System MUST provide `get_child_count(ingredient_id)` function returning count of direct child ingredients
- **FR-006**: System MUST display warning dialog when parent change affects products or children
- **FR-007**: System MUST block parent changes that would exceed max hierarchy depth (3 levels)
- **FR-008**: System MUST display full hierarchy path in ingredients tab list view

### Key Entities

- **Ingredient**: Core entity with `parent_ingredient_id` (FK to self), `hierarchy_level` (0/1/2), `display_name`
- **Product**: Links to Ingredient via `ingredient_id` FK - must be counted for parent-change warnings

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero instances of explicit level selection in edit form - level is always computed from parent
- **SC-002**: All parent-change operations validate safety before proceeding
- **SC-003**: All validation functions have >90% test coverage
- **SC-004**: Hierarchy path displays correctly for all 3 levels in ingredients tab
- **SC-005**: No regressions in existing ingredient CRUD operations

## Technical Notes

### Files to Modify

1. **`src/ui/ingredients_tab.py`**:
   - Remove `ingredient_level_dropdown` and `ingredient_level_var`
   - Add read-only level display that updates on parent selection
   - Add hierarchy path column to list view

2. **`src/services/ingredient_hierarchy_service.py`**:
   - Add `can_change_parent()` - boolean check with reasons/warnings
   - Add `get_product_count()` - count products linked to ingredient
   - Add `get_child_count()` - count direct children

3. **`src/ui/forms/ingredient_form.py`** (legacy dialog):
   - May need updates to add parent selection if this form is still used

### Existing Functions to Leverage

- `validate_hierarchy()` - Already validates parent changes (raises exceptions)
- `get_children()` - Returns child ingredients
- `get_descendants()` - Returns all descendants
- `get_ancestors()` - Returns ancestor chain (for path display)
