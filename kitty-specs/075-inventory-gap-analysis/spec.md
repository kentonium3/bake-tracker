# Feature Specification: Inventory Gap Analysis

**Feature Branch**: `075-inventory-gap-analysis`
**Created**: 2026-01-27
**Status**: Draft
**Input**: see docs/func-spec/F075_inventory_gap_analysis.md
**Depends On**: F074 (Ingredient Aggregation)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Shopping List from Ingredient Totals (Priority: P1)

When a user has batch decisions for an event (with ingredient totals calculated via F074), the system compares those totals against current inventory to identify what needs to be purchased.

**Why this priority**: This is the core value proposition - turning ingredient needs into actionable shopping information.

**Independent Test**: Can be tested with aggregated ingredients from F074 and mock inventory levels.

**Acceptance Scenarios**:

1. **Given** 6 cups flour needed and 2 cups flour in inventory, **When** gap analysis runs, **Then** the result shows 4 cups flour to purchase.
2. **Given** 3 cups sugar needed and 5 cups sugar in inventory, **When** gap analysis runs, **Then** sugar appears in the "sufficient" list (not in shopping list).
3. **Given** ingredient totals for an event, **When** gap analysis completes, **Then** every ingredient appears in exactly one category: either "to purchase" or "sufficient".

---

### User Story 2 - Handle Missing Inventory Gracefully (Priority: P1)

When an ingredient has no inventory records (never purchased or fully depleted), the system treats current stock as zero and flags the full amount for purchase.

**Why this priority**: Common scenario for new ingredients or seasonal items - must not error.

**Independent Test**: Can be tested with an ingredient that has no InventoryItem records.

**Acceptance Scenarios**:

1. **Given** 2 cups vanilla extract needed and no inventory records exist, **When** gap analysis runs, **Then** 2 cups vanilla extract appears in shopping list.
2. **Given** an ingredient with inventory records all showing zero quantity, **When** gap analysis runs, **Then** full amount appears in shopping list.

---

### User Story 3 - Display Shopping List with Clear Separation (Priority: P1)

When gap analysis completes, the user sees a clear display separating items requiring purchase from items already sufficient in stock.

**Why this priority**: User must be able to quickly scan what to buy vs what's already available.

**Independent Test**: Can be tested with a mix of sufficient and insufficient ingredients.

**Acceptance Scenarios**:

1. **Given** gap analysis results with 3 items to purchase and 2 sufficient items, **When** displayed, **Then** purchase items appear in one section and sufficient items in another.
2. **Given** shopping list items, **When** displayed, **Then** each item shows: ingredient name, quantity to purchase, and unit.
3. **Given** sufficient items, **When** displayed, **Then** each shows: ingredient name, quantity needed, quantity on hand, and unit.

---

### Edge Cases

- What happens when no ingredients are needed (empty F074 result)? Return empty shopping list and empty sufficient list.
- What happens when all ingredients are sufficient? Shopping list is empty; all items in sufficient list.
- What happens when all ingredients need purchasing? Sufficient list is empty; all items in shopping list.
- How are different units for same ingredient handled? Each (ingredient_id, unit) pair is evaluated separately, matching F074's aggregation key.
- What happens if inventory has different units than needed? Units must match exactly; mismatched units are treated as zero inventory for that specific unit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST query current inventory quantity for each ingredient in the aggregated totals
- **FR-002**: System MUST treat missing inventory (no records) as zero quantity on hand
- **FR-003**: System MUST calculate gap as: `gap = max(0, needed - on_hand)`
- **FR-004**: System MUST flag any ingredient with gap > 0 as requiring purchase
- **FR-005**: System MUST identify ingredients with gap = 0 as sufficient
- **FR-006**: System MUST maintain unit consistency - only compare quantities with matching units
- **FR-007**: System MUST return structured results separating purchase items from sufficient items
- **FR-008**: System MUST display shopping list in a user-readable format
- **FR-009**: System MUST display sufficient items separately with on-hand quantities shown

### Key Entities

- **IngredientTotal** (from F074): Aggregated ingredient needs with ingredient_id, ingredient_name, unit, total_quantity
- **InventoryItem**: Current stock records linked to Products which link to Ingredients
- **GapResult**: Output structure containing purchase list and sufficient list

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gap calculation is mathematically correct for 100% of test cases
- **SC-002**: Zero inventory is correctly handled (treated as 0, not error)
- **SC-003**: Every ingredient from F074 appears in exactly one output category
- **SC-004**: Display clearly separates purchase items from sufficient items
- **SC-005**: Analysis completes for events with up to 100 ingredients in under 2 seconds

## Assumptions

- F074 ingredient aggregation has already been run before gap analysis
- Inventory is tracked by ingredient via Product.ingredient_id relationship
- Unit matching is exact string comparison (no unit conversion)
- Inventory quantities are expressed in the same units as recipe ingredients (via Product.package_unit)
- The `get_total_quantity(ingredient_slug)` function in inventory_item_service returns Dict[str, Decimal] by unit

## Out of Scope

- Shopping list export to external formats (future feature)
- Store assignment for items (future feature)
- Price estimation for shopping list (future feature)
- Automatic unit conversion between compatible units
