---
work_package_id: "WP03"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
title: "Hierarchy Service - Validation & Management"
phase: "Phase 2 - Services"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "29529"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Hierarchy Service - Validation & Management

## Objectives & Success Criteria

**Goal**: Implement validation and hierarchy management operations.

**Success Criteria**:
- Validation functions prevent invalid operations (circular references, depth exceeded)
- move_ingredient() correctly updates hierarchy with all validations
- search_ingredients() returns matches with ancestry information
- Custom hierarchy exceptions added to exceptions.py
- Unit tests achieve >70% coverage
- All tests pass

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md` - Principle III (Layered Architecture)
- Contract: `kitty-specs/031-ingredient-hierarchy-taxonomy/contracts/ingredient_hierarchy_service.md`
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
- Data Model: `kitty-specs/031-ingredient-hierarchy-taxonomy/data-model.md` - Validation Rules

**Constraints**:
- Cycle detection must be bulletproof (data integrity critical)
- Depth validation must prevent exceeding 3 levels
- Error messages should be user-friendly and suggest alternatives
- Follow session pattern per CLAUDE.md

## Subtasks & Detailed Guidance

### Subtask T015 – Implement validate_hierarchy_level()
- **Purpose**: Check if ingredient is at an allowed hierarchy level.
- **Steps**:
  1. Implement: `def validate_hierarchy_level(ingredient_id: int, allowed_levels: List[int], session=None) -> bool`
  2. Get ingredient, check hierarchy_level against allowed_levels
  3. Return True if valid
  4. Raise ValidationError with helpful message if invalid
  5. Message should include current level and allowed levels
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Primary use case: allowed_levels=[2] for recipe/product validation

### Subtask T016 – Implement would_create_cycle()
- **Purpose**: Detect if setting new_parent_id would create circular reference.
- **Steps**:
  1. Implement: `def would_create_cycle(ingredient_id: int, new_parent_id: int, session=None) -> bool`
  2. Walk from new_parent_id up to root via parent relationship
  3. If ingredient_id is encountered in the chain, return True (cycle detected)
  4. If root reached without finding ingredient_id, return False (safe)
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Critical safety function - must be called before any parent change

### Subtask T017 – Implement move_ingredient()
- **Purpose**: Move ingredient to a new parent with full validation.
- **Steps**:
  1. Implement: `def move_ingredient(ingredient_id: int, new_parent_id: Optional[int], session=None) -> Dict`
  2. Validation steps:
     a. Verify ingredient exists
     b. If new_parent_id provided, verify parent exists
     c. Check would_create_cycle() - raise CircularReferenceError if True
     d. Calculate new hierarchy_level (parent.level + 1, or 0 if no parent)
     e. Verify new level doesn't exceed 2 (max depth)
     f. If ingredient has children, verify they won't exceed depth after move
  3. Update ingredient.parent_ingredient_id and hierarchy_level
  4. Recursively update children's hierarchy_levels if needed
  5. Return updated ingredient dict
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Most complex function - ensure atomic transaction via session

### Subtask T018 – Implement search_ingredients()
- **Purpose**: Search ingredients with ancestry info for UI display.
- **Steps**:
  1. Implement: `def search_ingredients(query: str, session=None) -> List[Dict]`
  2. Query: case-insensitive partial match on display_name
  3. For each match, call get_ancestors() to populate ancestry
  4. Add `ancestors` field to each result dict
  5. Sort results by display_name
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Ancestry info enables "Chocolate → Dark Chocolate → Chips" display in search results

### Subtask T019 – Add hierarchy exceptions to exceptions.py
- **Purpose**: Define custom exceptions for hierarchy operations.
- **Steps**:
  1. Open `src/services/exceptions.py`
  2. Add if not present:
     ```python
     class HierarchyValidationError(ValidationError):
         """Raised for hierarchy-specific validation failures."""
         pass

     class CircularReferenceError(HierarchyValidationError):
         """Raised when operation would create circular reference."""
         pass

     class MaxDepthExceededError(HierarchyValidationError):
         """Raised when operation would exceed maximum hierarchy depth."""
         pass
     ```
  3. Ensure IngredientNotFoundError exists (may already exist)
- **Files**: `src/services/exceptions.py`
- **Parallel?**: No (should be done early as other functions depend on it)
- **Notes**: Place after existing exception classes

### Subtask T020 – Write unit tests for validation functions [PARALLEL SAFE]
- **Purpose**: Comprehensive testing of validation and management functions.
- **Steps**:
  1. Add to `src/tests/services/test_ingredient_hierarchy_service.py`
  2. Test validate_hierarchy_level:
     - Valid level returns True
     - Invalid level raises ValidationError with helpful message
  3. Test would_create_cycle:
     - Direct cycle (A becomes child of A)
     - Indirect cycle (A becomes child of its descendant)
     - Safe move returns False
  4. Test move_ingredient:
     - Valid move updates parent and level
     - Cycle detection prevents invalid move
     - Depth exceeded prevents invalid move
     - Moving to root (new_parent_id=None) works
  5. Test search_ingredients:
     - Match found with ancestors populated
     - Partial match works
     - No match returns empty list
- **Files**: `src/tests/services/test_ingredient_hierarchy_service.py`
- **Parallel?**: Yes (once function signatures defined)
- **Notes**: Use separate fixtures for validation edge cases

## Test Strategy

- **Unit Tests**:
  - Create complex hierarchy for cycle detection tests
  - Test all validation error paths
  - Verify error messages are user-friendly
  - Test edge cases: moving root, moving to same parent

- **Commands**:
  ```bash
  pytest src/tests/services/test_ingredient_hierarchy_service.py -v
  pytest src/tests/services/test_ingredient_hierarchy_service.py -v --cov=src/services/ingredient_hierarchy_service
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cycle detection misses edge case | Comprehensive test cases; walk full chain every time |
| Children orphaned during move | Recursive update of children's levels in same transaction |
| Exception imports missing | Verify imports at top of hierarchy service file |

## Definition of Done Checklist

- [ ] T015: validate_hierarchy_level() validates correctly
- [ ] T016: would_create_cycle() detects all cycle types
- [ ] T017: move_ingredient() works with full validation
- [ ] T018: search_ingredients() returns matches with ancestors
- [ ] T019: Hierarchy exceptions added to exceptions.py
- [ ] T020: Unit tests cover all validation scenarios
- [ ] All tests pass
- [ ] Error messages are user-friendly

## Review Guidance

- Verify cycle detection is called before any parent update
- Verify move_ingredient handles children's levels correctly
- Check that exceptions inherit correctly
- Verify search returns ancestry info in correct order

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T14:27:14Z – claude – shell_pid=29529 – lane=doing – Started implementation
- 2025-12-31T14:30:11Z – claude – shell_pid=29529 – lane=for_review – Ready for review - validation functions with 19 tests
