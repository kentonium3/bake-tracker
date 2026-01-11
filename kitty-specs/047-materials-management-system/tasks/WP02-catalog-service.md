---
work_package_id: "WP02"
subtasks:
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Catalog Service - User Story 1"
phase: "Phase 1 - Core Services"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Catalog Service - User Story 1

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Implement CRUD operations for the material hierarchy (Category > Subcategory > Material > Product).

**User Story**: As a baker, I need to organize my packaging materials in a logical hierarchy so I can find and manage them easily.

**Success Criteria:**
- Can create complete hierarchy via service calls
- Slug auto-generated from name when not provided
- Delete operations validate no children exist (cascade protection)
- All acceptance scenarios from spec.md User Story 1 pass
- Service layer tests achieve >70% coverage

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/spec.md` - User Story 1 acceptance scenarios
- `kitty-specs/047-materials-management-system/contracts/material_catalog_service.md` - Service interface
- `src/services/ingredient_crud_service.py` - Pattern to follow
- `CLAUDE.md` - Session management rules (CRITICAL)

**Session Management (from CLAUDE.md):**
```python
def create_category(name: str, session: Session | None = None) -> MaterialCategory:
    if session is not None:
        return _create_category_impl(name, session)
    with session_scope() as session:
        return _create_category_impl(name, session)
```

**Dependencies:**
- WP01 must be complete (models must exist)

## Subtasks & Detailed Guidance

### Subtask T009 - Category CRUD Operations
- **Purpose**: Create, read, update, delete for MaterialCategory
- **File**: `src/services/material_catalog_service.py`
- **Parallel?**: No (sequential build)
- **Steps**:
  1. Create file with imports from models, database, utils
  2. Implement `create_category(name, slug=None, description=None, sort_order=0, session=None)`
  3. Implement `get_category(category_id=None, slug=None, session=None)`
  4. Implement `list_categories(session=None)` - ordered by sort_order
  5. Implement `update_category(category_id, name=None, description=None, sort_order=None, session=None)`
  6. Implement `delete_category(category_id, session=None)` - validate no subcategories
- **Notes**: All functions accept optional session parameter

### Subtask T010 - Subcategory CRUD Operations
- **Purpose**: Create, read, update, delete for MaterialSubcategory
- **File**: `src/services/material_catalog_service.py` (same file)
- **Parallel?**: No
- **Steps**:
  1. Implement `create_subcategory(category_id, name, slug=None, description=None, sort_order=0, session=None)`
  2. Implement `get_subcategory(subcategory_id=None, slug=None, session=None)`
  3. Implement `list_subcategories(category_id=None, session=None)`
  4. Implement `update_subcategory(subcategory_id, name=None, description=None, sort_order=None, session=None)`
  5. Implement `delete_subcategory(subcategory_id, session=None)` - validate no materials

### Subtask T011 - Material CRUD Operations
- **Purpose**: Create, read, update, delete for Material
- **File**: `src/services/material_catalog_service.py` (same file)
- **Parallel?**: No
- **Steps**:
  1. Implement `create_material(subcategory_id, name, base_unit_type, slug=None, description=None, notes=None, session=None)`
  2. Validate base_unit_type is one of: 'each', 'linear_inches', 'square_inches'
  3. Implement `get_material(material_id=None, slug=None, session=None)`
  4. Implement `list_materials(subcategory_id=None, category_id=None, session=None)`
  5. Implement `update_material(material_id, name=None, description=None, notes=None, session=None)` - cannot change base_unit_type
  6. Implement `delete_material(material_id, session=None)` - validate no products with inventory

### Subtask T012 - Product CRUD Operations
- **Purpose**: Create, read, update, delete for MaterialProduct
- **File**: `src/services/material_catalog_service.py` (same file)
- **Parallel?**: No
- **Steps**:
  1. Implement `create_product(material_id, name, package_quantity, package_unit, brand=None, supplier_id=None, sku=None, notes=None, session=None)`
  2. Calculate `quantity_in_base_units` from package_quantity and package_unit using unit conversion
  3. Implement `get_product(product_id, session=None)`
  4. Implement `list_products(material_id=None, include_hidden=False, session=None)`
  5. Implement `update_product(product_id, name=None, brand=None, supplier_id=None, sku=None, is_hidden=None, notes=None, session=None)`
  6. Implement `delete_product(product_id, session=None)` - validate current_inventory == 0

### Subtask T013 - Slug Auto-generation
- **Purpose**: Generate URL-friendly slugs from names automatically
- **File**: `src/services/material_catalog_service.py`
- **Parallel?**: No
- **Steps**:
  1. Import or create `slugify()` function (check `src/utils/string_utils.py`)
  2. In all create functions: `slug = slug or slugify(name)`
  3. Handle uniqueness - append number if slug exists
  4. Ensure slugs are lowercase, alphanumeric with underscores

### Subtask T014 - Cascade Delete Validation
- **Purpose**: Prevent deletion of entities with children or inventory
- **File**: `src/services/material_catalog_service.py`
- **Parallel?**: No
- **Steps**:
  1. In `delete_category`: Check `category.subcategories` is empty
  2. In `delete_subcategory`: Check `subcategory.materials` is empty
  3. In `delete_material`: Check no products have `current_inventory > 0`
  4. In `delete_material`: Check not used in any Composition
  5. In `delete_product`: Check `product.current_inventory == 0`
  6. Raise `ValidationError` with clear message on violation

### Subtask T015 - Service Tests
- **Purpose**: Achieve >70% coverage for catalog service
- **File**: `src/tests/test_material_catalog_service.py`
- **Parallel?**: Yes (can write tests while implementing)
- **Steps**:
  1. Create test file with pytest fixtures
  2. Test create operations for all entity types
  3. Test get/list operations
  4. Test update operations
  5. Test delete validation (should fail with children)
  6. Test slug auto-generation
  7. Test error cases (invalid base_unit_type, duplicate names)

### Subtask T016 - Export Service
- **Purpose**: Make service available for import
- **File**: `src/services/__init__.py`
- **Parallel?**: No
- **Steps**:
  1. Add import for material_catalog_service
  2. Add to `__all__` if using explicit exports

## Test Strategy

```python
# Example test structure
import pytest
from src.services.material_catalog_service import (
    create_category, get_category, list_categories,
    create_subcategory, create_material, create_product
)

@pytest.fixture
def sample_category(db_session):
    return create_category("Ribbons", session=db_session)

def test_create_category(db_session):
    cat = create_category("Boxes", session=db_session)
    assert cat.name == "Boxes"
    assert cat.slug == "boxes"

def test_create_hierarchy(db_session, sample_category):
    subcat = create_subcategory(sample_category.id, "Satin", session=db_session)
    mat = create_material(subcat.id, "Red Satin", "linear_inches", session=db_session)
    prod = create_product(mat.id, "Michaels 100ft Roll", 100, "feet", session=db_session)

    assert prod.quantity_in_base_units == 1200  # 100 feet = 1200 inches

def test_delete_with_children_fails(db_session, sample_category):
    create_subcategory(sample_category.id, "Satin", session=db_session)
    with pytest.raises(ValidationError):
        delete_category(sample_category.id, session=db_session)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session management bugs | Follow CLAUDE.md patterns exactly |
| Slug collisions | Implement collision detection with numeric suffix |
| Unit conversion errors | Validate package_unit is recognized before conversion |
| Orphaned data on delete | Use database CASCADE for safe cases; validation for risky cases |

## Definition of Done Checklist

- [ ] All CRUD functions implemented for 4 entity types
- [ ] All functions accept optional `session` parameter
- [ ] Slug auto-generation working with collision handling
- [ ] Delete validation prevents orphaned data
- [ ] Unit conversion correctly calculates quantity_in_base_units
- [ ] Tests achieve >70% coverage
- [ ] Service exported in `__init__.py`
- [ ] Acceptance scenarios from User Story 1 can be demonstrated

## Review Guidance

**Reviewer should verify:**
1. Session parameter pattern matches CLAUDE.md exactly
2. Delete operations validate children before proceeding
3. Slug generation handles edge cases (special chars, collisions)
4. Unit conversion uses existing unit_converter.py patterns
5. Error messages are user-friendly

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T20:36:50Z – claude – lane=doing – Started catalog service implementation
- 2026-01-10T20:44:55Z – claude – lane=for_review – All 46 tests passing. Full CRUD for Category, Subcategory, Material, Product with slug auto-gen and delete validation
- 2026-01-11T01:06:22Z – claude – lane=done – Review passed: Full CRUD for 4 entity types, slug auto-generation, delete validation. 46 tests passing.
