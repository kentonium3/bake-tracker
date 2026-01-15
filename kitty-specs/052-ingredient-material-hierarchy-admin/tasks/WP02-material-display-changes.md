---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Material Display Changes"
phase: "Phase 1 - MVP Display"
lane: "doing"
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

# Work Package Prompt: WP02 – Material Display Changes

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

**Goal**: Display only materials (not categories/subcategories) in the Materials tab with Category and Subcategory columns for context.

**Success Criteria**:
- Materials tab shows ONLY materials - no category or subcategory items visible
- Two parent columns visible: Category, Subcategory, plus Material name
- Existing filter functionality continues to work
- Pattern matches WP01 for UI consistency

**User Story Reference**: User Story 2 (spec.md) - "View Clear Material Listings"

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; services call models
- IV. Test-Driven Development: Service layer tests required (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Story 2
- `kitty-specs/052-ingredient-material-hierarchy-admin/data-model.md` - Material hierarchy structure

**Existing Code**:
- `src/models/material.py` - Material model with `subcategory` relationship
- `src/models/material_subcategory.py` - Has `category` relationship
- `src/models/material_category.py` - Top-level category
- `src/ui/materials_tab.py` - Current tab implementation to modify

**Parallelization**: This WP can run in parallel with WP01 (Ingredient Display Changes) - different files.

## Subtasks & Detailed Guidance

### Subtask T007 – Create material_hierarchy_service.py with get_materials_with_parents()

- **Purpose**: Provide service layer method to fetch materials with category/subcategory data.
- **Files**: Create `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop while WP01 works on ingredients

**Implementation**:
```python
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from src.models.material import Material
from src.services.database import session_scope

class MaterialHierarchyService:
    """Service for material hierarchy operations."""

    def get_materials_with_parents(self, session: Optional[Session] = None) -> List[dict]:
        """
        Get all materials with category and subcategory names.

        Returns:
            List of dicts with keys: category_name, subcategory_name, material
        """
        def _impl(sess: Session) -> List[dict]:
            materials = sess.query(Material).options(
                joinedload(Material.subcategory).joinedload("category")
            ).order_by(Material.name).all()

            result = []
            for mat in materials:
                subcat = mat.subcategory
                cat = subcat.category if subcat else None
                result.append({
                    "category_name": cat.name if cat else "",
                    "subcategory_name": subcat.name if subcat else "",
                    "material_name": mat.name,
                    "material": mat
                })
            return result

        if session is not None:
            return _impl(session)
        with session_scope() as sess:
            return _impl(sess)

# Module-level instance
material_hierarchy_service = MaterialHierarchyService()
```

**Notes**:
- Uses explicit `joinedload` chain: Material → Subcategory → Category
- Follow session parameter pattern per CLAUDE.md
- Match WP01 pattern for consistency

### Subtask T008 – Create tests for material hierarchy service

- **Purpose**: Ensure service methods work correctly with test data.
- **Files**: Create `src/tests/services/test_material_hierarchy_service.py`
- **Parallel?**: No - depends on T007

**Test Cases**:
1. `test_get_materials_with_parents_returns_all_materials` - Verify all materials returned
2. `test_get_materials_with_parents_includes_hierarchy` - Verify category_name, subcategory_name populated
3. `test_get_materials_with_parents_empty_db` - Verify empty list when no materials
4. `test_get_materials_with_parents_ordering` - Verify ordered by material name

**Fixture Setup**:
- Create MaterialCategory (e.g., "Ribbons")
- Create MaterialSubcategory under category (e.g., "Satin")
- Create multiple Materials under subcategory (e.g., "Red Satin 1-inch")

### Subtask T009 – Modify materials_tab.py to call hierarchy service

- **Purpose**: Replace direct database queries with service calls.
- **Files**: Modify `src/ui/materials_tab.py`
- **Parallel?**: No - depends on T007

**Changes**:
1. Import the new service:
   ```python
   from src.services.material_hierarchy_service import material_hierarchy_service
   ```

2. In `_load_data()` or equivalent method, replace direct queries:
   ```python
   # OLD: Direct query
   materials = session.query(Material).all()

   # NEW: Service call with parent data
   material_data = material_hierarchy_service.get_materials_with_parents()
   ```

3. Update data structure used by table rendering

### Subtask T010 – Add Category and Subcategory columns to materials table

- **Purpose**: Display parent hierarchy in separate columns.
- **Files**: Modify `src/ui/materials_tab.py`
- **Parallel?**: No - depends on T009

**Changes**:
1. In `_create_table()` or column definition:
   - Add "Category" column (first)
   - Add "Subcategory" column (second)
   - "Material" column (third)

2. Update column configuration:
   ```python
   columns = [
       {"name": "Category", "width": 150},
       {"name": "Subcategory", "width": 150},
       {"name": "Material", "width": 200},
       # ... existing columns (products, inventory, etc.)
   ]
   ```

3. Update row rendering to use category_name, subcategory_name, material_name

### Subtask T011 – Update material filter functionality

- **Purpose**: Ensure existing category filter works with new display.
- **Files**: Modify `src/ui/materials_tab.py`
- **Parallel?**: No - depends on T009, T010

**Changes**:
1. If category dropdown exists, ensure it filters by category_name
2. Add filter parameter to service if needed:
   ```python
   def get_materials_with_parents(self, category_filter: str = None, session=None):
       # Add filter logic
   ```
3. Or filter in UI after service returns (simpler for small datasets)

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for all service methods (T008)
- Test fixtures create 3-level hierarchy (Category → Subcategory → Material)
- Run: `./run-tests.sh src/tests/services/test_material_hierarchy_service.py -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Different model structure than ingredients | Use explicit joins (not self-referential) |
| UI inconsistency with WP01 | Match column naming and layout |
| Missing test data | Create fixtures with realistic hierarchy |

## Definition of Done Checklist

- [ ] `material_hierarchy_service.py` created with all methods
- [ ] Unit tests pass with >70% coverage on new service
- [ ] `materials_tab.py` uses service instead of direct queries
- [ ] Table displays Category, Subcategory, Material columns correctly
- [ ] Filter by category still works
- [ ] No category or subcategory items appear in listing (only materials)

## Review Guidance

**Key checkpoints for reviewer**:
1. Open Materials tab - verify only materials shown (not categories/subcategories)
2. Check columns show correct hierarchy (Category → Subcategory → Material)
3. Use category filter - verify filtering works
4. Check service tests pass: `./run-tests.sh -k "material_hierarchy" -v`
5. Compare with WP01 for UI consistency

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:38:59Z – claude – lane=doing – Starting implementation
