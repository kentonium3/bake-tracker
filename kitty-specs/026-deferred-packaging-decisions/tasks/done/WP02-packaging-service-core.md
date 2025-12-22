---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Packaging Service Core"
phase: "Phase 2 - Service Layer"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "94728"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Packaging Service Core

## Objectives & Success Criteria

- Create `packaging_service.py` with all core methods
- Implement inventory aggregation by `product_name`
- Implement estimated cost calculation (weighted average)
- Implement material assignment with validation
- Implement pending requirements query
- Achieve >80% unit test coverage
- All methods follow session management pattern (accept `session=None`)

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 2 details
- `kitty-specs/026-deferred-packaging-decisions/data-model.md` - Query patterns
- `kitty-specs/026-deferred-packaging-decisions/research.md` - Service design
- `kitty-specs/026-deferred-packaging-decisions/quickstart.md` - API summary
- `CLAUDE.md` - Session Management section (CRITICAL)

**Constraints**:
- Must follow session management pattern per CLAUDE.md
- Use SQLAlchemy 2.x query style
- Cost calculation must use same logic as existing FIFO system
- All methods must accept optional `session=None` parameter

## Subtasks & Detailed Guidance

### Subtask T005 - Create packaging_service.py structure

- **Purpose**: Establish service module with proper imports and structure
- **Steps**:
  1. Create `src/services/packaging_service.py`
  2. Add imports for models (Product, Composition, CompositionAssignment, InventoryItem, Ingredient)
  3. Add session_scope import
  4. Create module docstring explaining purpose
- **Files**: `src/services/packaging_service.py` (new)
- **Parallel?**: No
- **Notes**: Follow pattern of existing service files

### Subtask T006 - Implement get_generic_products()

- **Purpose**: List available generic product types for UI dropdown
- **Steps**:
  1. Query distinct `product_name` from products where `ingredient.is_packaging=True`
  2. Filter to only include names with inventory > 0
  3. Return sorted list of strings
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def get_generic_products(session=None) -> list[str]:
      """Get distinct product_name values for packaging products with inventory."""
  ```

### Subtask T007 - Implement get_generic_inventory_summary()

- **Purpose**: Show total and breakdown by brand for a generic product type
- **Steps**:
  1. Query products with matching `product_name` and `ingredient.is_packaging=True`
  2. Join to inventory_items to get quantities
  3. Group by brand and product_id
  4. Return dict with total and breakdown
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def get_generic_inventory_summary(product_name: str, session=None) -> dict:
      """
      Returns: {
          'total': int,
          'breakdown': [{'brand': str, 'product_id': int, 'available': int}]
      }
      """
  ```

### Subtask T008 - Implement get_estimated_cost()

- **Purpose**: Calculate average price for cost estimation during planning
- **Steps**:
  1. Get all products with matching `product_name`
  2. Get current cost per unit for each (use existing `get_current_cost_per_unit()`)
  3. Calculate weighted average based on inventory quantities
  4. Multiply by requested quantity
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def get_estimated_cost(product_name: str, quantity: float, session=None) -> float:
      """Average price across all products with this product_name."""
  ```

### Subtask T009 - Implement create_generic_requirement()

- **Purpose**: Set up a composition as generic packaging requirement
- **Steps**:
  1. Find or create composition with `is_generic=True`
  2. Set `packaging_product_id` to a template product with the given `product_name`
  3. Return composition ID
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**: May delegate to composition_service for actual creation

### Subtask T010 - Implement assign_materials()

- **Purpose**: Create assignment records linking inventory items to generic requirements
- **Steps**:
  1. Validate composition has `is_generic=True`
  2. Validate sum of quantities matches `component_quantity`
  3. Validate each quantity doesn't exceed inventory availability
  4. Validate all products have matching `product_name`
  5. Create CompositionAssignment records
  6. Return success boolean
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def assign_materials(composition_id: int, assignments: list[dict], session=None) -> bool:
      """
      Create assignment records.
      assignments: [{'inventory_item_id': int, 'quantity': float}]
      Raises ValueError if validation fails.
      """
  ```

### Subtask T011 - Implement get_pending_requirements()

- **Purpose**: Find compositions needing material assignment
- **Steps**:
  1. Query compositions where `is_generic=True`
  2. Left join to composition_assignments
  3. Filter to those with no assignments OR partial assignments
  4. Optionally filter by event_id
  5. Return list of Composition objects with relevant details
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def get_pending_requirements(event_id: int = None, session=None) -> list[Composition]:
      """Find compositions where is_generic=True and not fully assigned."""
  ```

### Subtask T012 - Implement is_fully_assigned()

- **Purpose**: Check if a generic composition has complete assignments
- **Steps**:
  1. Get composition by ID
  2. Sum `quantity_assigned` from all CompositionAssignment records
  3. Compare to `component_quantity`
  4. Return boolean
- **Files**: `src/services/packaging_service.py`
- **Parallel?**: No
- **Notes**:
  ```python
  def is_fully_assigned(composition_id: int, session=None) -> bool:
      """True when assignment quantities sum to component_quantity."""
  ```

### Subtask T013 - Create unit tests

- **Purpose**: Validate all service methods with test coverage >80%
- **Steps**:
  1. Create `src/tests/services/test_packaging_service.py`
  2. Write fixture for test data (packaging ingredients, products, inventory)
  3. Test each method:
     - `test_get_generic_products()` - returns distinct names
     - `test_get_generic_inventory_summary()` - correct totals and breakdown
     - `test_get_estimated_cost()` - weighted average calculation
     - `test_assign_materials_validates_quantity()` - sum must equal required
     - `test_assign_materials_validates_availability()` - cannot exceed inventory
     - `test_is_fully_assigned()` - true when complete, false otherwise
     - `test_get_pending_requirements()` - finds unassigned
- **Files**: `src/tests/services/test_packaging_service.py` (new)
- **Parallel?**: Yes - can be written alongside implementation
- **Notes**: Use pytest fixtures pattern from existing tests

## Test Strategy

```bash
# Run packaging service tests
pytest src/tests/services/test_packaging_service.py -v

# Check coverage
pytest src/tests/services/test_packaging_service.py -v --cov=src/services/packaging_service
```

Required tests:
- `test_get_generic_products_returns_distinct_names`
- `test_get_generic_products_excludes_zero_inventory`
- `test_get_generic_inventory_summary_totals`
- `test_get_generic_inventory_summary_breakdown`
- `test_get_estimated_cost_weighted_average`
- `test_assign_materials_success`
- `test_assign_materials_quantity_mismatch_error`
- `test_assign_materials_exceeds_inventory_error`
- `test_assign_materials_wrong_product_name_error`
- `test_is_fully_assigned_complete`
- `test_is_fully_assigned_partial`
- `test_get_pending_requirements_finds_unassigned`
- `test_get_pending_requirements_filters_by_event`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cost calculation accuracy | Use same costing logic as existing FIFO system |
| Session management errors | Follow pattern in CLAUDE.md; accept session=None |
| Query performance | Add indexes in WP01; test with realistic data volumes |

## Definition of Done Checklist

- [ ] `packaging_service.py` created with all methods
- [ ] All methods accept `session=None` parameter
- [ ] Unit tests created with >80% coverage
- [ ] All tests pass
- [ ] No lint errors (black, flake8)
- [ ] Type hints added to all methods

## Review Guidance

- Verify session management pattern followed correctly
- Check cost calculation matches existing FIFO logic
- Confirm validation error messages are user-friendly
- Validate query efficiency (no N+1 queries)

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T21:43:05Z – claude – shell_pid=94728 – lane=doing – Started implementation of packaging service core
- 2025-12-21T21:56:30Z – claude – shell_pid=94728 – lane=for_review – Implementation complete, 45 tests passing
- 2025-12-22T02:26:43Z – claude – shell_pid=94728 – lane=done – Approved: All tests pass
