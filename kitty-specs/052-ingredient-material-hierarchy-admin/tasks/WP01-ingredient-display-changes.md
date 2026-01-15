---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Ingredient Display Changes"
phase: "Phase 1 - MVP Display"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T15:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Ingredient Display Changes

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When you understand feedback and begin addressing it.
- **Report progress**: Update Activity Log as you address each item.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Display only L2 (leaf) ingredients in the Ingredients tab with L0 and L1 parent columns for context.

**Success Criteria**:
- Ingredients tab shows ONLY L2 (leaf) ingredients - no L0 or L1 items visible in main listing
- Three hierarchy columns visible: L0 (category), L1 (subcategory), Ingredient (L2 name)
- Existing filter-by-category functionality continues to work
- Performance acceptable with ~100 ingredients

**User Story Reference**: User Story 1 (spec.md) - "View Clear Ingredient Listings"

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; services call models
- IV. Test-Driven Development: Service layer tests required (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Story 1
- `kitty-specs/052-ingredient-material-hierarchy-admin/plan.md` - Technical context
- `kitty-specs/052-ingredient-material-hierarchy-admin/data-model.md` - Service interfaces

**Existing Code**:
- `src/models/ingredient.py` - Has `parent_ingredient_id`, `hierarchy_level`, `get_ancestors()`, `is_leaf`
- `src/ui/ingredients_tab.py` - Current tab implementation to modify

**Parallelization**: This WP can run in parallel with WP02 (Material Display Changes) - different files.

## Subtasks & Detailed Guidance

### Subtask T001 – Create ingredient_hierarchy_service.py with get_leaf_ingredients()

- **Purpose**: Provide service layer method to fetch only L2 ingredients with parent data.
- **Files**: Create `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop while WP02 works on materials

**Implementation**:
```python
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from src.models.ingredient import Ingredient
from src.services.database import session_scope

class IngredientHierarchyService:
    """Service for ingredient hierarchy operations."""

    def get_leaf_ingredients(self, session: Optional[Session] = None) -> List[Ingredient]:
        """
        Get all L2 (leaf) ingredients with parent data eager-loaded.

        Returns:
            List of Ingredient objects where hierarchy_level == 2
        """
        def _impl(sess: Session) -> List[Ingredient]:
            return sess.query(Ingredient).filter(
                Ingredient.hierarchy_level == 2
            ).options(
                joinedload(Ingredient.parent).joinedload(Ingredient.parent)
            ).order_by(Ingredient.display_name).all()

        if session is not None:
            return _impl(session)
        with session_scope() as sess:
            return _impl(sess)

# Module-level instance
ingredient_hierarchy_service = IngredientHierarchyService()
```

**Notes**:
- Use `joinedload` to eager-load parent chain in single query (avoids N+1)
- Follow session parameter pattern per CLAUDE.md Session Management rules
- Default ordering by display_name for consistent UI

### Subtask T002 – Add get_ingredient_with_ancestors() method

- **Purpose**: Return ingredient with L0, L1, L2 names resolved for display.
- **Files**: Add to `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - continues from T001

**Implementation**:
```python
def get_ingredient_with_ancestors(self, ingredient_id: int, session: Optional[Session] = None) -> dict:
    """
    Get ingredient with L0 and L1 ancestor names.

    Returns:
        Dict with keys: l0_name, l1_name, l2_name, ingredient
    """
    def _impl(sess: Session) -> dict:
        ingredient = sess.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).options(
            joinedload(Ingredient.parent).joinedload(Ingredient.parent)
        ).first()

        if not ingredient:
            return None

        l1 = ingredient.parent
        l0 = l1.parent if l1 else None

        return {
            "l0_name": l0.display_name if l0 else "",
            "l1_name": l1.display_name if l1 else "",
            "l2_name": ingredient.display_name,
            "ingredient": ingredient
        }

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Also add bulk method for list display**:
```python
def get_all_leaf_ingredients_with_ancestors(self, session: Optional[Session] = None) -> List[dict]:
    """Get all leaf ingredients with ancestor names for table display."""
    def _impl(sess: Session) -> List[dict]:
        ingredients = self.get_leaf_ingredients(session=sess)
        result = []
        for ing in ingredients:
            l1 = ing.parent
            l0 = l1.parent if l1 else None
            result.append({
                "l0_name": l0.display_name if l0 else "",
                "l1_name": l1.display_name if l1 else "",
                "l2_name": ing.display_name,
                "ingredient": ing
            })
        return result

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Subtask T003 – Create tests for ingredient hierarchy service

- **Purpose**: Ensure service methods work correctly with test data.
- **Files**: Create `src/tests/services/test_ingredient_hierarchy_service.py`
- **Parallel?**: No - depends on T001, T002

**Test Cases**:
1. `test_get_leaf_ingredients_returns_only_l2` - Verify only hierarchy_level=2 returned
2. `test_get_leaf_ingredients_includes_parent_data` - Verify parent chain accessible
3. `test_get_ingredient_with_ancestors_returns_names` - Verify l0_name, l1_name, l2_name populated
4. `test_get_ingredient_with_ancestors_nonexistent` - Verify returns None for bad ID
5. `test_get_all_leaf_ingredients_with_ancestors` - Verify bulk method returns correct structure

**Fixture Setup**:
- Create L0 ingredient (hierarchy_level=0)
- Create L1 ingredient under L0 (hierarchy_level=1)
- Create multiple L2 ingredients under L1 (hierarchy_level=2)

### Subtask T004 – Modify ingredients_tab.py to call hierarchy service

- **Purpose**: Replace direct database queries with service calls.
- **Files**: Modify `src/ui/ingredients_tab.py`
- **Parallel?**: No - depends on T001, T002

**Changes**:
1. Import the new service:
   ```python
   from src.services.ingredient_hierarchy_service import ingredient_hierarchy_service
   ```

2. In `_load_data()` or equivalent method, replace:
   ```python
   # OLD: Direct query for all ingredients
   ingredients = session.query(Ingredient).all()

   # NEW: Service call for leaf ingredients with ancestors
   ingredient_data = ingredient_hierarchy_service.get_all_leaf_ingredients_with_ancestors()
   ```

3. Update the data structure used by table rendering

### Subtask T005 – Add L0 and L1 columns to ingredients table

- **Purpose**: Display parent hierarchy in separate columns.
- **Files**: Modify `src/ui/ingredients_tab.py`
- **Parallel?**: No - depends on T004

**Changes**:
1. In `_create_table()` or column definition:
   - Add "Category" (L0) column before current columns
   - Add "Subcategory" (L1) column after Category
   - Rename or clarify "Ingredient" column as the L2 name

2. Update column configuration:
   ```python
   columns = [
       {"name": "Category", "width": 150},      # L0
       {"name": "Subcategory", "width": 150},   # L1
       {"name": "Ingredient", "width": 200},    # L2
       # ... existing columns
   ]
   ```

3. Update row rendering to use l0_name, l1_name, l2_name from service data

### Subtask T006 – Update filter functionality

- **Purpose**: Ensure existing category filter works with new display.
- **Files**: Modify `src/ui/ingredients_tab.py`
- **Parallel?**: No - depends on T004, T005

**Changes**:
1. Category dropdown should filter by L0 (top-level category)
2. Service may need filter parameter:
   ```python
   def get_all_leaf_ingredients_with_ancestors(self, l0_filter: str = None, session=None):
       # Add filter logic if l0_filter provided
   ```
3. Or filter in UI after service returns all data (simpler for small datasets)

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for all service methods (T003)
- Test fixtures create realistic 3-level hierarchy
- Run: `./run-tests.sh src/tests/services/test_ingredient_hierarchy_service.py -v`

**Edge Case Tests** (from spec.md):
- `test_l1_with_no_l2_children_not_displayed` - Verify L1 with zero L2 children doesn't appear in L2-only listing
- `test_filter_empty_l0_category` - Verify filtering by L0 with no L2 descendants shows empty result gracefully

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| N+1 query performance | Use `joinedload` to eager-load parent chain |
| Breaking existing functionality | Keep filter dropdown working; test thoroughly |
| UI column width issues | Test on actual data; adjust widths as needed |

## Definition of Done Checklist

- [ ] `ingredient_hierarchy_service.py` created with all methods
- [ ] Unit tests pass with >70% coverage on new service
- [ ] `ingredients_tab.py` uses service instead of direct queries
- [ ] Table displays L0, L1, L2 columns correctly
- [ ] Filter by category still works
- [ ] No L0 or L1 items appear in listing (only L2 leaves)

## Review Guidance

**Key checkpoints for reviewer**:
1. Open Ingredients tab - verify only L2 items shown
2. Check columns show correct hierarchy (L0 → L1 → Ingredient)
3. Use category filter - verify filtering works
4. Check service tests pass: `./run-tests.sh -k "ingredient_hierarchy" -v`

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:23:32Z – claude – lane=doing – Started implementation
- 2026-01-15T03:34:40Z – claude – lane=for_review – Implementation complete: L2-only display with L0/L1 columns, 12 new tests pass
- 2026-01-15T05:35:53Z – claude – lane=done – Review approved: All criteria met - L2-only display with L0/L1 columns, 120 tests pass
