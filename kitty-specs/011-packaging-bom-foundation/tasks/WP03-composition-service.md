---
work_package_id: WP03
title: Composition Service Packaging Extensions
lane: done
history:
- timestamp: '2025-12-08T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-opus-4-5
assignee: claude
phase: Phase 1 - Foundation
review_status: approved without changes
reviewed_by: claude-opus-4-5
shell_pid: review
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
---

# Work Package Prompt: WP03 - Composition Service Packaging Extensions

## Objectives & Success Criteria

**Goal**: Extend composition_service to support packaging compositions for both FinishedGood and Package.

**Success Criteria**:
- [ ] Can add packaging product to FinishedGood assembly
- [ ] Can add packaging product to Package
- [ ] Can retrieve packaging for assembly and package
- [ ] Can update packaging quantity (including decimals)
- [ ] Can remove packaging
- [ ] Validates that product is actually a packaging product
- [ ] RESTRICT prevents deletion of products in use
- [ ] Unit tests pass with >70% coverage

## Context & Constraints

**Reference Documents**:
- Contract: `kitty-specs/011-packaging-bom-foundation/contracts/composition_service.md`
- Data Model: `kitty-specs/011-packaging-bom-foundation/data-model.md`
- Spec: FR-004, FR-005, FR-006, FR-007, FR-018

**Dependencies**:
- WP01 must be complete (Composition model changes)
- WP02 must be complete (is_packaging_ingredient helper)

## Subtasks & Detailed Guidance

### Subtask T020 - Update create_composition()
- **Purpose**: Accept package_id and packaging_product_id parameters
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Update function signature:
     ```python
     def create_composition(
         assembly_id: Optional[int] = None,
         package_id: Optional[int] = None,  # NEW
         finished_unit_id: Optional[int] = None,
         finished_good_id: Optional[int] = None,
         packaging_product_id: Optional[int] = None,  # NEW
         quantity: float = 1.0,  # CHANGED from int
         notes: Optional[str] = None,
         sort_order: int = 0
     ) -> Composition:
     ```
  2. Add validation for parent XOR
  3. Add validation for component XOR
  4. Pass new parameters to Composition constructor
- **Parallel?**: No - core function update

### Subtask T021 - Implement add_packaging_to_assembly()
- **Purpose**: Convenience method to add packaging to FinishedGood
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def add_packaging_to_assembly(
         assembly_id: int,
         packaging_product_id: int,
         quantity: float = 1.0,
         notes: Optional[str] = None,
         sort_order: int = 0
     ) -> Composition:
         """Add packaging product to a FinishedGood assembly."""
         # Validate assembly exists
         # Validate product exists and is packaging
         # Create composition with assembly_id and packaging_product_id
         return create_composition(
             assembly_id=assembly_id,
             packaging_product_id=packaging_product_id,
             quantity=quantity,
             notes=notes,
             sort_order=sort_order
         )
     ```
- **Parallel?**: No - depends on T020 and T027

### Subtask T022 - Implement add_packaging_to_package()
- **Purpose**: Convenience method to add packaging to Package
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def add_packaging_to_package(
         package_id: int,
         packaging_product_id: int,
         quantity: float = 1.0,
         notes: Optional[str] = None,
         sort_order: int = 0
     ) -> Composition:
         """Add packaging product to a Package."""
         # Validate package exists
         # Validate product exists and is packaging
         # Create composition with package_id and packaging_product_id
         return create_composition(
             package_id=package_id,
             packaging_product_id=packaging_product_id,
             quantity=quantity,
             notes=notes,
             sort_order=sort_order
         )
     ```
- **Parallel?**: No - depends on T020 and T027

### Subtask T023 - Implement get_assembly_packaging()
- **Purpose**: Retrieve all packaging compositions for a FinishedGood
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_assembly_packaging(assembly_id: int) -> List[Composition]:
         """Get all packaging compositions for a FinishedGood assembly."""
         with session_scope() as session:
             return session.query(Composition).filter(
                 Composition.assembly_id == assembly_id,
                 Composition.packaging_product_id.isnot(None)
             ).order_by(Composition.sort_order).all()
     ```
- **Parallel?**: Yes - independent query method

### Subtask T024 - Implement get_package_packaging()
- **Purpose**: Retrieve all packaging compositions for a Package
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_package_packaging(package_id: int) -> List[Composition]:
         """Get all packaging compositions for a Package."""
         with session_scope() as session:
             return session.query(Composition).filter(
                 Composition.package_id == package_id,
                 Composition.packaging_product_id.isnot(None)
             ).order_by(Composition.sort_order).all()
     ```
- **Parallel?**: Yes - independent query method

### Subtask T025 - Implement update_packaging_quantity()
- **Purpose**: Update quantity for a packaging composition
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def update_packaging_quantity(composition_id: int, quantity: float) -> Composition:
         """Update quantity for a packaging composition."""
         if quantity <= 0:
             raise ValidationError("Quantity must be greater than 0")

         with session_scope() as session:
             composition = session.query(Composition).get(composition_id)
             if not composition:
                 raise ValidationError(f"Composition with ID {composition_id} not found")
             if composition.packaging_product_id is None:
                 raise ValidationError("This composition is not a packaging composition")

             composition.component_quantity = quantity
             session.commit()
             return composition
     ```
- **Parallel?**: No - depends on T020 pattern

### Subtask T026 - Implement remove_packaging()
- **Purpose**: Remove a packaging composition
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add function:
     ```python
     def remove_packaging(composition_id: int) -> bool:
         """Remove a packaging composition."""
         with session_scope() as session:
             composition = session.query(Composition).get(composition_id)
             if not composition:
                 return False
             if composition.packaging_product_id is None:
                 raise ValidationError("This composition is not a packaging composition")

             session.delete(composition)
             session.commit()
             return True
     ```
- **Parallel?**: No - standard CRUD pattern

### Subtask T027 - Add packaging product validation
- **Purpose**: Ensure only packaging products can be added to packaging compositions
- **File**: `src/services/composition_service.py`
- **Steps**:
  1. Add validation helper:
     ```python
     def _validate_packaging_product(session, product_id: int) -> Product:
         """Validate that product exists and is a packaging product."""
         product = session.query(Product).get(product_id)
         if not product:
             raise ValidationError(f"Product with ID {product_id} not found")

         ingredient = session.query(Ingredient).get(product.ingredient_id)
         if not ingredient.is_packaging:
             raise ValidationError(f"Product '{product.display_name}' is not a packaging product")

         return product
     ```
  2. Use in add_packaging_to_assembly and add_packaging_to_package
- **Parallel?**: No - utility needed by T021, T022

### Subtask T028 - Handle product deletion restriction
- **Purpose**: User-friendly error when trying to delete product in use
- **File**: `src/services/product_service.py` (or composition_service.py)
- **Steps**:
  1. In delete_product() or similar:
     ```python
     try:
         session.delete(product)
         session.commit()
     except IntegrityError as e:
         session.rollback()
         # Check if it's a packaging composition reference
         count = session.query(Composition).filter(
             Composition.packaging_product_id == product_id
         ).count()
         if count > 0:
             raise ValidationError(f"Cannot delete product - it is used in {count} packaging composition(s)")
         raise
     ```
- **Parallel?**: No - depends on understanding of deletion flow

### Subtask T029 - Add unit tests
- **Purpose**: Test all new methods per Constitution Principle IV
- **File**: `src/tests/services/test_composition_service.py` or `src/tests/test_services.py`
- **Steps**:
  1. Test add_packaging_to_assembly creates correct composition
  2. Test add_packaging_to_package creates correct composition
  3. Test get_assembly_packaging returns only packaging
  4. Test get_package_packaging returns only packaging
  5. Test update_packaging_quantity with valid float
  6. Test update_packaging_quantity rejects <= 0
  7. Test remove_packaging deletes correctly
  8. Test validation rejects non-packaging product
  9. Test duplicate packaging raises error (unique constraint)
- **Example**:
  ```python
  def test_add_packaging_to_assembly():
      # Setup: create packaging ingredient, product, finished good
      composition = composition_service.add_packaging_to_assembly(
          assembly_id=fg.id,
          packaging_product_id=product.id,
          quantity=2.5
      )
      assert composition.assembly_id == fg.id
      assert composition.packaging_product_id == product.id
      assert composition.component_quantity == 2.5
  ```
- **Parallel?**: No - depends on all other subtasks

## Test Strategy

**Test Commands**:
```bash
# Run composition service tests
pytest src/tests -v -k "composition"

# Check coverage
pytest src/tests -v --cov=src/services/composition_service
```

**Required Coverage**: >70% for new methods

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| XOR constraint violations at runtime | Medium | Medium | Service-level validation before insert |
| Foreign key issues during testing | Low | Medium | Proper test fixture setup/teardown |

## Definition of Done Checklist

- [ ] All 10 subtasks completed
- [ ] create_composition accepts new parameters
- [ ] add_packaging_to_assembly works
- [ ] add_packaging_to_package works
- [ ] get_assembly_packaging works
- [ ] get_package_packaging works
- [ ] update_packaging_quantity works with floats
- [ ] remove_packaging works
- [ ] Packaging product validation enforced
- [ ] Product deletion restriction works
- [ ] All tests pass
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Add packaging to FG - verify composition created correctly
2. Add packaging to Package - verify composition created correctly
3. Try to add non-packaging product - should fail with clear error
4. Delete product in use - should fail with count of compositions

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-08T16:54:45Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-08T17:02:40Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-09T11:20:00Z – claude-opus-4-5 – shell_pid=review – lane=done – Code review: Approved. All 23 tests pass. Implementation complete with packaging product validation, duplicate prevention, decimal quantity support, and product deletion restriction.
- 2025-12-09T11:19:55Z – claude-opus-4-5 – shell_pid=review – lane=done – Code review: Approved - All tests pass
