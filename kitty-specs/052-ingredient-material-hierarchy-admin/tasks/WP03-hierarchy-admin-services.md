---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Hierarchy Admin Services"
phase: "Phase 2 - Services"
lane: "for_review"
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

# Work Package Prompt: WP03 – Hierarchy Admin Services

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When you understand feedback and begin addressing it.
- **Report progress**: Update Activity Log as you address each item.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create shared service layer for hierarchy admin operations including tree building, usage counts, validation, and utility functions.

**Success Criteria**:
- `hierarchy_admin_service.py` created with shared utilities
- `ingredient_hierarchy_service.py` extended with tree and usage methods
- `material_hierarchy_service.py` extended with tree and usage methods
- All service methods have >70% test coverage
- Tree structures correctly represent 3-level hierarchy

**User Story Reference**: User Stories 4, 5, 6, 7 (spec.md) - Admin operations foundation

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: Services encapsulate business logic
- IV. Test-Driven Development: Service layer tests required (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/data-model.md` - Service interfaces
- `kitty-specs/052-ingredient-material-hierarchy-admin/research.md` - Model structure details

**Existing Code**:
- `src/services/ingredient_hierarchy_service.py` (from WP01)
- `src/services/material_hierarchy_service.py` (from WP02)
- `src/models/ingredient.py` - Has `get_descendants()`, `get_ancestors()` methods
- `src/models/material.py`, `material_category.py`, `material_subcategory.py`

**Dependencies**: WP01 and WP02 must be complete (services to extend exist).

## Subtasks & Detailed Guidance

### Subtask T012 – Create hierarchy_admin_service.py with shared utilities

- **Purpose**: Provide reusable validation and utility functions.
- **Files**: Create `src/services/hierarchy_admin_service.py`
- **Parallel?**: Yes - can develop while T016-T019 work on specific services

**Implementation**:
```python
from typing import List, Any
import re

class HierarchyAdminService:
    """Shared utilities for hierarchy admin operations."""

    def validate_unique_sibling_name(
        self, siblings: List[Any], new_name: str, exclude_id: int = None
    ) -> bool:
        """
        Check if name is unique among siblings.

        Args:
            siblings: List of sibling entities with 'name' or 'display_name' attribute
            new_name: Proposed new name
            exclude_id: ID to exclude from check (for rename operations)

        Returns:
            True if name is unique, False if duplicate exists
        """
        new_name_lower = new_name.strip().lower()
        for sibling in siblings:
            if exclude_id and sibling.id == exclude_id:
                continue
            sibling_name = getattr(sibling, 'display_name', None) or getattr(sibling, 'name', '')
            if sibling_name.strip().lower() == new_name_lower:
                return False
        return True

    def generate_slug(self, name: str) -> str:
        """
        Generate URL-friendly slug from name.

        Args:
            name: Display name to slugify

        Returns:
            Lowercase slug with hyphens
        """
        slug = name.strip().lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[\s_]+', '-', slug)   # Replace spaces/underscores with hyphens
        slug = re.sub(r'-+', '-', slug)       # Collapse multiple hyphens
        return slug.strip('-')

    def validate_no_cycle(self, item_descendants: List[Any], proposed_parent: Any) -> bool:
        """
        Ensure reparenting won't create cycle.

        Args:
            item_descendants: List of descendant entities of the item being moved
            proposed_parent: The proposed new parent entity

        Returns:
            True if safe (no cycle), False if cycle would be created
        """
        if proposed_parent is None:
            return True
        return proposed_parent not in item_descendants

# Module-level instance
hierarchy_admin_service = HierarchyAdminService()
```

### Subtask T013 – Add validate_unique_sibling_name() (included in T012)

*Covered by T012 implementation above.*

### Subtask T014 – Add generate_slug() (included in T012)

*Covered by T012 implementation above.*

### Subtask T015 – Add validate_no_cycle() (included in T012)

*Covered by T012 implementation above.*

### Subtask T016 – Add get_hierarchy_tree() to ingredient_hierarchy_service.py

- **Purpose**: Build nested tree structure for admin UI display.
- **Files**: Extend `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T018 (materials)

**Implementation**:
```python
def get_hierarchy_tree(self, session: Optional[Session] = None) -> List[dict]:
    """
    Get full ingredient tree structure for admin UI.

    Returns:
        List of root (L0) nodes, each with nested children structure:
        [{
            "id": int,
            "name": str,
            "level": int,
            "children": [...],
            "ingredient": Ingredient
        }]
    """
    def _impl(sess: Session) -> List[dict]:
        # Get all L0 (root) ingredients
        roots = sess.query(Ingredient).filter(
            Ingredient.hierarchy_level == 0
        ).order_by(Ingredient.display_name).all()

        def build_node(ing: Ingredient) -> dict:
            children = sess.query(Ingredient).filter(
                Ingredient.parent_ingredient_id == ing.id
            ).order_by(Ingredient.display_name).all()

            return {
                "id": ing.id,
                "name": ing.display_name,
                "level": ing.hierarchy_level,
                "children": [build_node(child) for child in children],
                "ingredient": ing
            }

        return [build_node(root) for root in roots]

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Subtask T017 – Add get_usage_counts() to ingredient_hierarchy_service.py

- **Purpose**: Get product and recipe counts for usage display.
- **Files**: Extend `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T019 (materials)

**Implementation**:
```python
def get_usage_counts(self, ingredient_id: int, session: Optional[Session] = None) -> dict:
    """
    Get product and recipe counts for an ingredient.

    Args:
        ingredient_id: ID of ingredient to check

    Returns:
        {"product_count": int, "recipe_count": int}
    """
    def _impl(sess: Session) -> dict:
        from src.models.product import Product
        from src.models.recipe_ingredient import RecipeIngredient

        product_count = sess.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).count()

        recipe_count = sess.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        ).count()

        return {
            "product_count": product_count,
            "recipe_count": recipe_count
        }

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Subtask T018 – Add get_hierarchy_tree() to material_hierarchy_service.py

- **Purpose**: Build nested tree structure for materials admin UI.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T016 (ingredients)

**Implementation**:
```python
def get_hierarchy_tree(self, session: Optional[Session] = None) -> List[dict]:
    """
    Get full material tree structure for admin UI.

    Returns:
        List of category nodes, each with subcategories containing materials:
        [{
            "id": int,
            "name": str,
            "type": "category",
            "children": [{
                "id": int,
                "name": str,
                "type": "subcategory",
                "children": [{
                    "id": int,
                    "name": str,
                    "type": "material",
                    "children": [],
                    "material": Material
                }],
                "subcategory": MaterialSubcategory
            }],
            "category": MaterialCategory
        }]
    """
    def _impl(sess: Session) -> List[dict]:
        from src.models.material_category import MaterialCategory
        from src.models.material_subcategory import MaterialSubcategory
        from src.models.material import Material

        categories = sess.query(MaterialCategory).order_by(
            MaterialCategory.sort_order, MaterialCategory.name
        ).all()

        result = []
        for cat in categories:
            subcategories = sess.query(MaterialSubcategory).filter(
                MaterialSubcategory.category_id == cat.id
            ).order_by(MaterialSubcategory.sort_order, MaterialSubcategory.name).all()

            subcat_nodes = []
            for subcat in subcategories:
                materials = sess.query(Material).filter(
                    Material.subcategory_id == subcat.id
                ).order_by(Material.name).all()

                mat_nodes = [{
                    "id": mat.id,
                    "name": mat.name,
                    "type": "material",
                    "children": [],
                    "material": mat
                } for mat in materials]

                subcat_nodes.append({
                    "id": subcat.id,
                    "name": subcat.name,
                    "type": "subcategory",
                    "children": mat_nodes,
                    "subcategory": subcat
                })

            result.append({
                "id": cat.id,
                "name": cat.name,
                "type": "category",
                "children": subcat_nodes,
                "category": cat
            })

        return result

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Subtask T019 – Add get_usage_counts() to material_hierarchy_service.py

- **Purpose**: Get product count for materials usage display.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T017 (ingredients)

**Implementation**:
```python
def get_usage_counts(self, material_id: int, session: Optional[Session] = None) -> dict:
    """
    Get product count for a material.

    Args:
        material_id: ID of material to check

    Returns:
        {"product_count": int}
    """
    def _impl(sess: Session) -> dict:
        from src.models.material_product import MaterialProduct

        product_count = sess.query(MaterialProduct).filter(
            MaterialProduct.material_id == material_id
        ).count()

        return {"product_count": product_count}

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

### Subtask T020 – Create tests for hierarchy_admin_service.py

- **Purpose**: Ensure shared utilities work correctly.
- **Files**: Create `src/tests/services/test_hierarchy_admin_service.py`
- **Parallel?**: No - depends on T012

**Test Cases**:
1. `test_validate_unique_sibling_name_returns_true_for_unique`
2. `test_validate_unique_sibling_name_returns_false_for_duplicate`
3. `test_validate_unique_sibling_name_excludes_self_on_rename`
4. `test_validate_unique_sibling_name_case_insensitive`
5. `test_generate_slug_basic`
6. `test_generate_slug_special_characters`
7. `test_generate_slug_multiple_spaces`
8. `test_validate_no_cycle_returns_true_for_safe`
9. `test_validate_no_cycle_returns_false_for_descendant`

### Subtask T021 – Extend tests for tree and usage count methods

- **Purpose**: Test tree building and usage count queries.
- **Files**: Extend `src/tests/services/test_ingredient_hierarchy_service.py` and `src/tests/services/test_material_hierarchy_service.py`
- **Parallel?**: No - depends on T016-T019

**Test Cases for Ingredients**:
1. `test_get_hierarchy_tree_returns_nested_structure`
2. `test_get_hierarchy_tree_empty_database`
3. `test_get_usage_counts_with_products`
4. `test_get_usage_counts_with_recipes`
5. `test_get_usage_counts_no_usage`

**Test Cases for Materials**:
1. `test_get_hierarchy_tree_returns_nested_structure`
2. `test_get_hierarchy_tree_empty_database`
3. `test_get_usage_counts_with_products`
4. `test_get_usage_counts_no_usage`

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for all shared utility methods (T020)
- Unit tests for tree and usage count methods (T021)
- Run: `./run-tests.sh -k "hierarchy" -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Recursive tree queries slow | Limit to 3 levels (known max); load all at once |
| Circular import issues | Import models inside functions where needed |
| Usage count performance | Simple COUNT queries, indexed FKs |

## Definition of Done Checklist

- [ ] `hierarchy_admin_service.py` created with all utility methods
- [ ] `ingredient_hierarchy_service.py` has `get_hierarchy_tree()` and `get_usage_counts()`
- [ ] `material_hierarchy_service.py` has `get_hierarchy_tree()` and `get_usage_counts()`
- [ ] Unit tests pass with >70% coverage on all new methods
- [ ] Tree structures correctly represent 3-level hierarchy
- [ ] Usage counts accurately reflect database relationships

## Review Guidance

**Key checkpoints for reviewer**:
1. Run service tests: `./run-tests.sh -k "hierarchy" -v`
2. Verify tree structure is correctly nested
3. Verify usage counts match actual relationships
4. Check slug generation handles edge cases
5. Verify cycle detection works for reparent scenarios

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:43:35Z – claude – lane=doing – Starting implementation
- 2026-01-15T03:49:23Z – claude – lane=for_review – All subtasks complete, 127 tests passing
