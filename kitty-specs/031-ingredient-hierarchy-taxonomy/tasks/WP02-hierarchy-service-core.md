---
work_package_id: WP02
title: Hierarchy Service - Core Functions
lane: done
history:
- timestamp: '2025-12-30T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 2 - Services
review_status: ''
reviewed_by: ''
shell_pid: '3515'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
---

# Work Package Prompt: WP02 – Hierarchy Service - Core Functions

## Objectives & Success Criteria

**Goal**: Implement tree traversal service methods for navigating ingredient hierarchy.

**Success Criteria**:
- New service file created at `src/services/ingredient_hierarchy_service.py`
- All 6 core navigation functions implemented and working
- Functions follow session pattern (optional session parameter)
- Functions return dicts (not ORM objects) per project convention
- Unit tests achieve >70% coverage on all functions
- All tests pass

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md` - Principle III (Layered Architecture)
- Contract: `kitty-specs/031-ingredient-hierarchy-taxonomy/contracts/ingredient_hierarchy_service.md`
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
- Research: `kitty-specs/031-ingredient-hierarchy-taxonomy/research.md` - Decision D2

**Constraints**:
- Follow existing service patterns in `src/services/`
- Use session_scope pattern per CLAUDE.md
- Return dicts from all public functions (not ORM objects)
- Fixed 3-level depth simplifies recursion (no deep recursion concerns)

## Subtasks & Detailed Guidance

### Subtask T007 – Create hierarchy service file
- **Purpose**: Establish new service module with proper imports and structure.
- **Steps**:
  1. Create `src/services/ingredient_hierarchy_service.py`
  2. Add imports:
     ```python
     from typing import List, Dict, Optional
     from src.models.ingredient import Ingredient
     from src.services.database import session_scope
     from src.services.exceptions import IngredientNotFoundError
     ```
  3. Add module docstring explaining purpose
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No (foundation for other subtasks)
- **Notes**: Follow structure of existing services like `ingredient_service.py`

### Subtask T008 – Implement get_root_ingredients()
- **Purpose**: Retrieve all root-level (hierarchy_level=0) ingredients.
- **Steps**:
  1. Implement function with signature: `def get_root_ingredients(session=None) -> List[Dict]`
  2. Query: `session.query(Ingredient).filter(Ingredient.hierarchy_level == 0)`
  3. Sort by display_name
  4. Return list of dicts via `[i.to_dict() for i in results]`
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Simple query, good starting point for testing session pattern

### Subtask T009 – Implement get_children()
- **Purpose**: Get direct children of a given parent ingredient.
- **Steps**:
  1. Implement: `def get_children(parent_id: int, session=None) -> List[Dict]`
  2. Verify parent exists, raise `IngredientNotFoundError` if not
  3. Query: `session.query(Ingredient).filter(Ingredient.parent_ingredient_id == parent_id)`
  4. Sort by display_name
  5. Return list of dicts
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: This is the primary function for lazy-loading tree nodes in UI

### Subtask T010 – Implement get_ancestors()
- **Purpose**: Get path from ingredient to root (for breadcrumb display).
- **Steps**:
  1. Implement: `def get_ancestors(ingredient_id: int, session=None) -> List[Dict]`
  2. Start with ingredient, walk up via parent relationship
  3. Build list from immediate parent to root
  4. Return list of ancestor dicts (ordered: immediate parent first, root last)
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Max 2 iterations (3-level tree), so simple loop is fine

### Subtask T011 – Implement get_all_descendants()
- **Purpose**: Get all descendants (recursive) of an ingredient.
- **Steps**:
  1. Implement: `def get_all_descendants(ancestor_id: int, session=None) -> List[Dict]`
  2. Verify ancestor exists
  3. Use recursive approach or iterative BFS
  4. Collect all children, grandchildren
  5. Return flat list of descendant dicts
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: With 3 levels max, simple recursion is efficient (no stack overflow risk)

### Subtask T012 – Implement get_leaf_ingredients()
- **Purpose**: Get all leaf-level (hierarchy_level=2) ingredients.
- **Steps**:
  1. Implement: `def get_leaf_ingredients(parent_id: Optional[int] = None, session=None) -> List[Dict]`
  2. If parent_id is None: return all leaves
  3. If parent_id provided: return leaves that are descendants of that parent
  4. Sort by display_name
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: When parent_id provided, uses get_all_descendants() then filters to leaves

### Subtask T013 – Implement is_leaf() helper
- **Purpose**: Quick check if ingredient is a leaf (can be used in recipes).
- **Steps**:
  1. Implement: `def is_leaf(ingredient_id: int, session=None) -> bool`
  2. Query ingredient, return `ingredient.hierarchy_level == 2`
  3. Raise `IngredientNotFoundError` if not found
- **Files**: `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: No
- **Notes**: Frequently called during validation, keep it efficient

### Subtask T014 – Write unit tests for core functions [PARALLEL SAFE]
- **Purpose**: Achieve >70% test coverage on hierarchy service.
- **Steps**:
  1. Create `src/tests/services/test_ingredient_hierarchy_service.py`
  2. Create test fixtures with sample hierarchy (e.g., Chocolate → Dark Chocolate → Semi-Sweet Chips)
  3. Write tests for each function:
     - get_root_ingredients: empty tree, populated tree
     - get_children: valid parent, invalid parent, no children
     - get_ancestors: leaf, mid-tier, root
     - get_all_descendants: single level, multi-level
     - get_leaf_ingredients: all leaves, filtered by parent
     - is_leaf: leaf ingredient, non-leaf ingredient, not found
- **Files**: `src/tests/services/test_ingredient_hierarchy_service.py`
- **Parallel?**: Yes (once function signatures are defined)
- **Notes**: Use pytest fixtures for test data setup

## Test Strategy

- **Unit Tests**:
  - Create sample hierarchy in fixtures
  - Test each navigation function independently
  - Test edge cases: empty results, not found errors
  - Verify session parameter works correctly

- **Commands**:
  ```bash
  pytest src/tests/services/test_ingredient_hierarchy_service.py -v
  pytest src/tests/services/test_ingredient_hierarchy_service.py -v --cov=src/services/ingredient_hierarchy_service
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management bugs | Follow CLAUDE.md session pattern; test with and without session parameter |
| ORM objects returned instead of dicts | Explicit to_dict() calls; test return types |
| Missing IngredientNotFoundError in exceptions.py | Add if missing before implementing functions |

## Definition of Done Checklist

- [ ] T007: Service file created with proper structure
- [ ] T008: get_root_ingredients() returns level 0 ingredients
- [ ] T009: get_children() returns direct children
- [ ] T010: get_ancestors() returns path to root
- [ ] T011: get_all_descendants() returns all descendants
- [ ] T012: get_leaf_ingredients() returns filtered/all leaves
- [ ] T013: is_leaf() returns correct boolean
- [ ] T014: Unit tests written with >70% coverage
- [ ] All tests pass
- [ ] Service follows project patterns (session, dicts)

## Review Guidance

- Verify all functions accept optional `session` parameter
- Verify all public functions return dicts (not ORM objects)
- Verify error handling for not-found cases
- Check test coverage meets 70% threshold

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-31T14:24:38Z – claude – shell_pid=29529 – lane=doing – Started implementation
- 2025-12-31T14:26:55Z – claude – shell_pid=29529 – lane=for_review – Ready for review - all 6 core functions implemented with 23 tests
- 2025-12-31T19:37:23Z – claude-reviewer – shell_pid=3515 – lane=done – Code review passed: All 6 core functions + 3 bonus functions implemented, 58/58 tests pass, correct session and dict patterns
