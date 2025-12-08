---
work_package_id: "WP07"
subtasks:
  - "T056"
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
title: "Validation & Edge Cases"
phase: "Phase 3 - Polish"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "42685"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-08T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Validation & Edge Cases

## Objectives & Success Criteria

**Goal**: Handle edge cases and ensure referential integrity works correctly.

**Success Criteria**:
- [ ] Deletion blocked with clear message when product in use
- [ ] Shopping list with no packaging shows only ingredients
- [ ] Packaging ingredient with no products is allowed
- [ ] Fractional quantities (0.5, 1.5) work correctly
- [ ] Same packaging in FG and Package aggregates correctly
- [ ] Cascade deletes work for Package and FinishedGood
- [ ] RESTRICT prevents deletion of referenced products

## Context & Constraints

**Reference Documents**:
- Spec: Edge Cases section
- Spec: FR-018 (prevent deletion), FR-019 (cascade delete)

**Dependencies**:
- WP01-WP06 must be complete

**Edge Cases from Spec**:
1. Packaging product deleted that is referenced -> block with error
2. Shopping list with no packaging requirements -> no empty section
3. Packaging ingredient with no products -> allowed
4. Fractional quantities like "0.5 yards ribbon" -> supported
5. Same packaging in FG and Package for same event -> aggregates correctly

## Subtasks & Detailed Guidance

### Subtask T056 - Implement user-friendly delete error message
- **Purpose**: Clear error when trying to delete packaging product in use (FR-018)
- **File**: `src/services/product_service.py`
- **Steps**:
  1. Find delete_product function
  2. Before deletion, check for compositions:
     ```python
     def delete_product(product_id: int) -> bool:
         with session_scope() as session:
             # Check for packaging compositions
             comp_count = session.query(Composition).filter(
                 Composition.packaging_product_id == product_id
             ).count()

             if comp_count > 0:
                 product = session.query(Product).get(product_id)
                 raise ValidationError(
                     f"Cannot delete '{product.display_name}' - it is used in {comp_count} packaging composition(s). "
                     f"Remove the packaging from FinishedGoods/Packages first."
                 )

             # Proceed with deletion
             ...
     ```
  3. Or catch IntegrityError from RESTRICT FK and provide message
- **Parallel?**: No - standalone fix

### Subtask T057 - Test: empty packaging handling
- **Purpose**: Verify shopping list doesn't show empty packaging section
- **File**: `src/tests/test_services.py` or edge case tests
- **Steps**:
  1. Create event with packages that have NO packaging requirements
  2. Call get_event_shopping_list
  3. Verify "packaging" key either:
     - Not present in result dict, OR
     - Present but empty list is acceptable
  4. Test:
     ```python
     def test_shopping_list_no_packaging_no_empty_section():
         # Create event with no packaging
         event = create_test_event_without_packaging()

         result = get_event_shopping_list(event.id)

         # Either no key or empty list
         assert "packaging" not in result or len(result.get("packaging", [])) == 0
     ```
- **Parallel?**: Yes - independent test

### Subtask T058 - Test: packaging ingredient with no products
- **Purpose**: Verify user can create packaging ingredient without products
- **File**: `src/tests/test_services.py`
- **Steps**:
  1. Create packaging ingredient with is_packaging=True
  2. Don't create any products for it
  3. Verify no errors
  4. Verify get_packaging_ingredients includes it
  5. Test:
     ```python
     def test_packaging_ingredient_without_products_allowed():
         ingredient = ingredient_service.create_ingredient(
             display_name="Empty Bags Category",
             category="Bags",
             is_packaging=True
         )

         # Should not raise
         assert ingredient.is_packaging == True

         # Should appear in packaging list
         packaging = ingredient_service.get_packaging_ingredients()
         assert any(i.id == ingredient.id for i in packaging)
     ```
- **Parallel?**: Yes - independent test

### Subtask T059 - Test: fractional quantities
- **Purpose**: Verify decimal quantities work (FR-006)
- **File**: `src/tests/test_services.py`
- **Steps**:
  1. Create packaging composition with quantity 0.5
  2. Verify stored correctly
  3. Retrieve and verify 0.5 returned
  4. Update to 1.5, verify
  5. Test:
     ```python
     def test_fractional_packaging_quantities():
         composition = composition_service.add_packaging_to_assembly(
             assembly_id=fg.id,
             packaging_product_id=product.id,
             quantity=0.5
         )
         assert composition.component_quantity == 0.5

         # Update
         composition_service.update_packaging_quantity(composition.id, 1.5)
         updated = get_composition(composition.id)
         assert updated.component_quantity == 1.5
     ```
- **Parallel?**: Yes - independent test

### Subtask T060 - Test: aggregation across FG and Package
- **Purpose**: Verify same packaging in both FG and Package aggregates correctly
- **File**: `src/tests/integration/test_packaging_flow.py`
- **Steps**:
  1. Create packaging product (e.g., ribbon)
  2. Add to FinishedGood with quantity 2
  3. Add same product to Package with quantity 1
  4. Create event with 3 packages containing that FG
  5. Calculate shopping list
  6. Verify total = (2 * 3) + (1 * 3) = 9
  7. Test:
     ```python
     def test_same_packaging_in_fg_and_package_aggregates():
         # Setup: ribbon product
         ribbon = create_packaging_product("Ribbon")

         # FG needs 2 ribbons
         add_packaging_to_assembly(fg.id, ribbon.id, quantity=2)

         # Package needs 1 ribbon (outer)
         add_packaging_to_package(package.id, ribbon.id, quantity=1)

         # Package contains the FG
         add_finished_good_to_package(package.id, fg.id, quantity=1)

         # Event has 3 of this package
         assign_package_to_event(event.id, package.id, quantity=3)

         # Calculate
         needs = get_event_packaging_needs(event.id)

         # FG: 2 * 1 * 3 = 6, Package: 1 * 3 = 3, Total: 9
         assert needs[ribbon.id].total_needed == 9
     ```
- **Parallel?**: Yes - independent integration test

### Subtask T061 - Test: Package cascade delete
- **Purpose**: Verify compositions deleted when Package deleted (FR-019)
- **File**: `src/tests/test_services.py`
- **Steps**:
  1. Create Package with packaging composition
  2. Note composition ID
  3. Delete Package
  4. Verify composition no longer exists
  5. Test:
     ```python
     def test_package_delete_cascades_compositions():
         package = create_package("Test Package")
         composition = add_packaging_to_package(package.id, product.id, quantity=1)
         comp_id = composition.id

         # Delete package
         delete_package(package.id)

         # Verify composition deleted
         with pytest.raises(Exception):  # Or returns None
             get_composition(comp_id)
     ```
- **Parallel?**: Yes - independent test

### Subtask T062 - Test: FinishedGood cascade delete
- **Purpose**: Verify compositions deleted when FinishedGood deleted
- **File**: `src/tests/test_services.py`
- **Steps**:
  1. Create FinishedGood with packaging composition
  2. Note composition ID
  3. Delete FinishedGood
  4. Verify composition no longer exists
  5. Similar pattern to T061
- **Parallel?**: Yes - independent test

### Subtask T063 - Verify SQLite RESTRICT behavior
- **Purpose**: Ensure FK RESTRICT works with SQLite PRAGMA foreign_keys=ON
- **File**: `src/tests/test_services.py`
- **Steps**:
  1. Verify database.py has PRAGMA foreign_keys=ON
  2. Create packaging product in composition
  3. Try to delete product directly (bypassing service validation)
  4. Verify IntegrityError raised
  5. Test:
     ```python
     def test_sqlite_restrict_fk_prevents_deletion():
         # Create composition referencing product
         composition = add_packaging_to_assembly(fg.id, product.id, quantity=1)

         # Try direct deletion bypassing service
         with session_scope() as session:
             prod = session.query(Product).get(product.id)
             session.delete(prod)

             with pytest.raises(IntegrityError):
                 session.commit()
     ```
- **Parallel?**: No - verifies database behavior

## Test Strategy

**Test Commands**:
```bash
# Run all edge case tests
pytest src/tests -v -k "edge" -k "packaging"

# Run integration tests
pytest src/tests/integration -v

# Verify cascade behavior
pytest src/tests -v -k "cascade"
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQLite RESTRICT different from PostgreSQL | Low | Medium | Explicit test T063 |
| Edge case missed | Medium | Low | Spec has good coverage; add tests as discovered |

## Definition of Done Checklist

- [ ] All 8 subtasks completed
- [ ] T056: Delete error message clear and helpful
- [ ] T057: Empty packaging handled gracefully
- [ ] T058: Packaging ingredient without products works
- [ ] T059: Fractional quantities work
- [ ] T060: Aggregation across FG and Package correct
- [ ] T061: Package cascade delete works
- [ ] T062: FG cascade delete works
- [ ] T063: SQLite RESTRICT verified
- [ ] All tests pass
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Try to delete product in use - verify clear error
2. Create event with no packaging - verify no crash or empty section
3. Create FG and Package using same packaging - verify aggregation
4. Delete Package - verify compositions gone

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-08T17:47:26Z – claude – shell_pid=41142 – lane=doing – Started implementation
- 2025-12-08T17:55:16Z – claude – shell_pid=42685 – lane=for_review – All subtasks T056-T063 completed, 485 tests pass
