---
work_package_id: "WP04"
subtasks:
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
title: "Event Service Shopping List Extensions"
phase: "Phase 2 - User Stories"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-08T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Event Service Shopping List Extensions

## Objectives & Success Criteria

**Goal**: Extend event_service to aggregate and display packaging needs on shopping lists.

**Success Criteria**:
- [ ] Shopping list includes packaging section
- [ ] Packaging aggregated from both Package-level and FinishedGood-level compositions
- [ ] Quantities aggregated correctly across multiple sources
- [ ] "To Buy" calculation subtracts on-hand inventory
- [ ] Empty packaging gracefully handled (no empty section)
- [ ] Unit and integration tests pass

## Context & Constraints

**Reference Documents**:
- Contract: `kitty-specs/011-packaging-bom-foundation/contracts/event_service.md`
- Research: `kitty-specs/011-packaging-bom-foundation/research.md` (RQ5)
- Spec: FR-010, FR-011, FR-012, FR-013

**Dependencies**:
- WP01 must be complete (model changes)
- WP03 must be complete (packaging compositions can be created)

**Aggregation Logic** (from research.md):
```
Event -> ERP -> Package:
  - Package.packaging_compositions (direct packaging)
  - Package.package_finished_goods -> FinishedGood.components (where packaging_product_id is set)
```

## Subtasks & Detailed Guidance

### Subtask T030 - Add PackagingNeed dataclass
- **Purpose**: Represent packaging requirement for shopping list
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add dataclass near top of file:
     ```python
     from dataclasses import dataclass

     @dataclass
     class PackagingNeed:
         """Represents packaging requirement for shopping list."""
         product_id: int
         product: Product
         ingredient_name: str
         product_display_name: str
         total_needed: float
         on_hand: float
         to_buy: float
         unit: str
     ```
- **Parallel?**: No - foundational for other methods

### Subtask T031 - Add PackagingSource dataclass
- **Purpose**: Track where packaging need originated (optional detailed breakdown)
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add dataclass:
     ```python
     @dataclass
     class PackagingSource:
         """Tracks where packaging need originated."""
         source_type: str  # "finished_good" or "package"
         source_id: int
         source_name: str
         quantity_per: float
         source_count: int
         total_for_source: float
     ```
- **Parallel?**: No - foundational for detailed breakdown

### Subtask T032 - Implement get_event_packaging_needs()
- **Purpose**: Calculate all packaging needs for an event
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_event_packaging_needs(event_id: int) -> Dict[int, PackagingNeed]:
         """Calculate packaging material needs for an event."""
         with session_scope() as session:
             event = session.query(Event).get(event_id)
             if not event:
                 raise EventNotFoundError(event_id)

             # Aggregate raw quantities
             raw_needs = _aggregate_packaging(session, event)

             # Build PackagingNeed objects with inventory lookup
             needs = {}
             for product_id, total_needed in raw_needs.items():
                 product = session.query(Product).get(product_id)
                 ingredient = product.ingredient
                 on_hand = _get_packaging_on_hand(session, product_id)
                 to_buy = max(0, total_needed - on_hand)

                 needs[product_id] = PackagingNeed(
                     product_id=product_id,
                     product=product,
                     ingredient_name=ingredient.display_name,
                     product_display_name=product.display_name,
                     total_needed=total_needed,
                     on_hand=on_hand,
                     to_buy=to_buy,
                     unit=product.purchase_unit
                 )

             return needs
     ```
- **Parallel?**: No - core aggregation method

### Subtask T033 - Implement _aggregate_packaging() helper
- **Purpose**: Internal method to sum packaging quantities
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add helper:
     ```python
     def _aggregate_packaging(session, event: Event) -> Dict[int, float]:
         """Aggregate packaging quantities for an event."""
         needs: Dict[int, float] = {}

         for erp in event.recipient_packages:
             package = erp.package
             package_qty = erp.quantity or 1

             # Package-level packaging (direct)
             for comp in package.packaging_compositions:
                 if comp.packaging_product_id:
                     pid = comp.packaging_product_id
                     needs[pid] = needs.get(pid, 0) + (comp.component_quantity * package_qty)

             # FinishedGood-level packaging (through package contents)
             for pfg in package.package_finished_goods:
                 fg = pfg.finished_good
                 fg_qty = pfg.quantity * package_qty

                 for comp in fg.components:
                     if comp.packaging_product_id:
                         pid = comp.packaging_product_id
                         needs[pid] = needs.get(pid, 0) + (comp.component_quantity * fg_qty)

         return needs
     ```
- **Parallel?**: No - depends on T032

### Subtask T034 - Implement _get_packaging_on_hand() helper
- **Purpose**: Get current inventory quantity for a packaging product
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add helper:
     ```python
     def _get_packaging_on_hand(session, product_id: int) -> float:
         """Get current inventory quantity for a packaging product."""
         from src.services.inventory_item_service import get_total_quantity_for_product
         # Or query directly:
         total = session.query(func.sum(InventoryItem.quantity)).filter(
             InventoryItem.product_id == product_id
         ).scalar()
         return total or 0.0
     ```
- **Parallel?**: No - utility for T032

### Subtask T035 - Update get_event_shopping_list()
- **Purpose**: Include packaging section in shopping list return
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Find existing get_event_shopping_list function (or create if doesn't exist)
  2. Add `include_packaging: bool = True` parameter
  3. Call get_event_packaging_needs if include_packaging
  4. Add "packaging" key to return dict:
     ```python
     result = {
         "event": {...},
         "ingredients": [...],  # existing
     }

     if include_packaging:
         packaging_needs = get_event_packaging_needs(event_id)
         if packaging_needs:  # Only add if not empty
             result["packaging"] = [
                 {
                     "ingredient_name": need.ingredient_name,
                     "product_name": need.product_display_name,
                     "total_needed": need.total_needed,
                     "on_hand": need.on_hand,
                     "to_buy": need.to_buy,
                     "unit": need.unit
                 }
                 for need in packaging_needs.values()
             ]

     return result
     ```
- **Parallel?**: No - depends on T032

### Subtask T036 - Implement get_event_packaging_breakdown() (Optional)
- **Purpose**: Detailed breakdown of where packaging needs come from
- **File**: `src/services/event_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_event_packaging_breakdown(event_id: int) -> Dict[int, List[PackagingSource]]:
         """Get detailed breakdown of where packaging needs come from."""
         # Similar traversal as _aggregate_packaging but track sources
         # Return dict mapping product_id -> list of PackagingSource
     ```
- **Parallel?**: Yes - optional, independent of core aggregation
- **Notes**: Lower priority; implement if time permits

### Subtask T037 - Add unit tests
- **Purpose**: Test packaging aggregation logic
- **File**: `src/tests/test_services.py` or `src/tests/services/test_event_service.py`
- **Steps**:
  1. Test get_event_packaging_needs returns correct structure
  2. Test aggregation from Package-level packaging only
  3. Test aggregation from FinishedGood-level packaging only
  4. Test aggregation from both levels combined
  5. Test to_buy calculation with inventory
  6. Test empty event returns empty needs
- **Parallel?**: No - depends on implementation

### Subtask T038 - Add integration test
- **Purpose**: End-to-end test of packaging on shopping list
- **File**: `src/tests/integration/test_packaging_flow.py`
- **Steps**:
  1. Create packaging ingredient and product
  2. Add inventory for product
  3. Create FinishedGood with packaging composition
  4. Create Package with packaging composition
  5. Create Event with packages
  6. Call get_event_shopping_list
  7. Verify packaging section contains aggregated, correct quantities
  8. Verify to_buy accounts for on-hand inventory
- **Parallel?**: No - depends on all components

## Test Strategy

**Test Commands**:
```bash
# Run event service tests
pytest src/tests -v -k "event"

# Run integration tests
pytest src/tests/integration -v

# Check coverage
pytest src/tests -v --cov=src/services/event_service
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| N+1 query performance | Medium | Low | Single user, small dataset; optimize later |
| Missing relationship data | Medium | Medium | Eager loading with joinedload/selectin |

## Definition of Done Checklist

- [ ] All 9 subtasks completed
- [ ] PackagingNeed dataclass defined
- [ ] get_event_packaging_needs works
- [ ] _aggregate_packaging traverses both Package and FG levels
- [ ] _get_packaging_on_hand looks up inventory
- [ ] get_event_shopping_list includes packaging section
- [ ] Empty packaging handled gracefully
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Create event with Package having both FG-level and Package-level packaging
2. Verify shopping list shows aggregated totals
3. Add inventory, verify to_buy decreases
4. Event with no packaging - verify no empty "packaging" section

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
