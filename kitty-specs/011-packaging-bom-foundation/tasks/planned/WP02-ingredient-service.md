---
work_package_id: "WP02"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
title: "Ingredient Service Packaging Extensions"
phase: "Phase 1 - Foundation"
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

# Work Package Prompt: WP02 - Ingredient Service Packaging Extensions

## Objectives & Success Criteria

**Goal**: Extend ingredient_service to support packaging flag and filtering.

**Success Criteria**:
- [ ] Can create ingredient with `is_packaging=True`
- [ ] Can filter to get only packaging ingredients
- [ ] Can filter to get only food (non-packaging) ingredients
- [ ] Can check if specific ingredient is packaging
- [ ] Packaging categories constant available
- [ ] Unit tests pass with >70% coverage for new methods

## Context & Constraints

**Reference Documents**:
- Contract: `kitty-specs/011-packaging-bom-foundation/contracts/ingredient_service.md`
- Spec: FR-001, FR-002, FR-003

**Dependencies**:
- WP01 must be complete (Ingredient model has `is_packaging` column)

**Packaging Categories** (from spec FR-002):
- Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, Other Packaging

## Subtasks & Detailed Guidance

### Subtask T012 - Add PACKAGING_CATEGORIES constant
- **Purpose**: Define valid packaging categories for validation and UI
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add constant near top of file (after imports):
     ```python
     PACKAGING_CATEGORIES = [
         "Bags",
         "Boxes",
         "Ribbon",
         "Labels",
         "Tissue Paper",
         "Wrapping",
         "Other Packaging"
     ]
     ```
- **Parallel?**: No - foundational for other methods

### Subtask T013 - Update create_ingredient()
- **Purpose**: Accept `is_packaging` parameter when creating ingredients
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add `is_packaging: bool = False` parameter to function signature
  2. Pass `is_packaging` to Ingredient constructor
  3. Log warning if `is_packaging=True` and category not in PACKAGING_CATEGORIES:
     ```python
     if is_packaging and category not in PACKAGING_CATEGORIES:
         logger.warning(f"Packaging ingredient '{display_name}' has non-standard category '{category}'")
     ```
- **Parallel?**: No - core function update
- **Notes**: Default False maintains backward compatibility

### Subtask T014 - Update update_ingredient()
- **Purpose**: Allow updating `is_packaging` flag with protection
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add `is_packaging: Optional[bool] = None` parameter
  2. Before changing from True to False, check for products in packaging compositions:
     ```python
     if is_packaging is False and ingredient.is_packaging:
         # Check if any products are used in packaging compositions
         from src.models.composition import Composition
         count = session.query(Composition).join(Product).filter(
             Product.ingredient_id == ingredient_id,
             Composition.packaging_product_id.isnot(None)
         ).count()
         if count > 0:
             raise ValidationError(f"Cannot unmark packaging: ingredient has products used in {count} composition(s)")
     ```
  3. Update the field if validation passes
- **Parallel?**: No - depends on T013 pattern

### Subtask T015 - Implement get_packaging_ingredients()
- **Purpose**: Retrieve all ingredients marked as packaging
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_packaging_ingredients() -> List[Ingredient]:
         """Get all ingredients marked as packaging, sorted by category then display_name."""
         with session_scope() as session:
             return session.query(Ingredient).filter(
                 Ingredient.is_packaging == True
             ).order_by(Ingredient.category, Ingredient.display_name).all()
     ```
- **Parallel?**: Yes - independent query method

### Subtask T016 - Implement get_food_ingredients()
- **Purpose**: Retrieve all ingredients that are NOT packaging
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add function:
     ```python
     def get_food_ingredients() -> List[Ingredient]:
         """Get all ingredients that are NOT packaging, sorted by category then display_name."""
         with session_scope() as session:
             return session.query(Ingredient).filter(
                 Ingredient.is_packaging == False
             ).order_by(Ingredient.category, Ingredient.display_name).all()
     ```
- **Parallel?**: Yes - independent query method

### Subtask T017 - Implement is_packaging_ingredient()
- **Purpose**: Quick check if specific ingredient is packaging
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add function:
     ```python
     def is_packaging_ingredient(ingredient_id: int) -> bool:
         """Check if an ingredient is marked as packaging."""
         with session_scope() as session:
             ingredient = session.query(Ingredient).get(ingredient_id)
             return ingredient.is_packaging if ingredient else False
     ```
- **Parallel?**: Yes - independent helper

### Subtask T018 - Implement validate_packaging_category()
- **Purpose**: Check if category is in PACKAGING_CATEGORIES
- **File**: `src/services/ingredient_service.py`
- **Steps**:
  1. Add function:
     ```python
     def validate_packaging_category(category: str) -> bool:
         """Check if category is a valid packaging category."""
         return category in PACKAGING_CATEGORIES
     ```
- **Parallel?**: Yes - independent helper

### Subtask T019 - Add unit tests
- **Purpose**: Test all new methods per Constitution Principle IV (TDD)
- **File**: `src/tests/test_services.py` or new `src/tests/services/test_ingredient_service.py`
- **Steps**:
  1. Test create_ingredient with is_packaging=True
  2. Test create_ingredient with is_packaging=False (default)
  3. Test get_packaging_ingredients returns only packaging
  4. Test get_food_ingredients returns only non-packaging
  5. Test is_packaging_ingredient returns correct boolean
  6. Test validate_packaging_category for valid and invalid categories
  7. Test update_ingredient is_packaging change protection
- **Example**:
  ```python
  def test_create_packaging_ingredient():
      ingredient = ingredient_service.create_ingredient(
          display_name="Test Bags",
          category="Bags",
          is_packaging=True
      )
      assert ingredient.is_packaging == True

  def test_get_packaging_ingredients_filters_correctly():
      # Create one packaging, one food
      packaging = ingredient_service.create_ingredient("Bags", "Bags", is_packaging=True)
      food = ingredient_service.create_ingredient("Flour", "Flour", is_packaging=False)

      results = ingredient_service.get_packaging_ingredients()
      assert len(results) == 1
      assert results[0].display_name == "Bags"
  ```
- **Parallel?**: No - depends on all other subtasks

## Test Strategy

**Test Commands**:
```bash
# Run ingredient service tests
pytest src/tests -v -k "ingredient"

# Check coverage
pytest src/tests -v --cov=src/services/ingredient_service
```

**Required Coverage**: >70% for new methods

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing create_ingredient calls | Low | High | Default is_packaging=False |
| Query performance | Low | Low | Index on is_packaging added in WP01 |

## Definition of Done Checklist

- [ ] All 8 subtasks completed
- [ ] PACKAGING_CATEGORIES constant defined
- [ ] create_ingredient accepts is_packaging parameter
- [ ] update_ingredient handles is_packaging with protection
- [ ] get_packaging_ingredients works
- [ ] get_food_ingredients works
- [ ] is_packaging_ingredient helper works
- [ ] validate_packaging_category helper works
- [ ] All tests pass
- [ ] Coverage >70% for new methods
- [ ] tasks.md updated

## Review Guidance

**Key Checkpoints**:
1. Create packaging ingredient - verify is_packaging=True persisted
2. Call get_packaging_ingredients - verify only packaging returned
3. Try to unmark is_packaging on ingredient with products in compositions - should fail

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
