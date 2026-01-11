---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Foundation - Material Models"
phase: "Phase 0 - Foundation"
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

# Work Package Prompt: WP01 - Foundation - Material Models

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create all 7 SQLAlchemy models for the Materials Management System. This is the foundation that all other work packages depend on.

**Success Criteria:**
- All 7 models can be imported without errors
- Database tables created successfully via `Base.metadata.create_all()`
- All constraints, indexes, and relationships defined per data-model.md
- Models follow existing patterns (BaseModel inheritance, session management)

## Context & Constraints

**Reference Documents:**
- `kitty-specs/047-materials-management-system/data-model.md` - Complete field definitions
- `kitty-specs/047-materials-management-system/contracts/` - Service interface expectations
- `src/models/base.py` - BaseModel pattern to follow
- `src/models/ingredient.py` - Hierarchy pattern reference
- `src/models/product.py` - Product pattern reference
- `src/models/purchase.py` - Purchase (immutable) pattern reference
- `src/models/production_consumption.py` - Consumption snapshot pattern reference

**Architectural Constraints:**
- All models inherit from `BaseModel`
- Use SQLAlchemy 2.x patterns
- Follow existing naming conventions (snake_case tables, PascalCase classes)
- Use Numeric(10,4) for currency fields
- Include CHECK constraints for validation

**Parallelization Note:** All 7 models (T001-T007) can be built in parallel since they have no internal dependencies. T008 must wait until all models exist.

## Subtasks & Detailed Guidance

### Subtask T001 - Create MaterialCategory Model
- **Purpose**: Top-level grouping for materials (e.g., "Ribbons", "Boxes", "Bags")
- **File**: `src/models/material_category.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialCategory(BaseModel)` class
  3. Set `__tablename__ = "material_categories"`
  4. Add fields per data-model.md: name, slug, description, sort_order
  5. Add relationship to MaterialSubcategory (cascade delete)
  6. Add indexes on name and slug
- **Notes**: slug should be unique and indexed

### Subtask T002 - Create MaterialSubcategory Model
- **Purpose**: Second-level grouping within a category
- **File**: `src/models/material_subcategory.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialSubcategory(BaseModel)` class
  3. Set `__tablename__ = "material_subcategories"`
  4. Add fields: category_id (FK), name, slug, description, sort_order
  5. Add relationship to MaterialCategory (many-to-one)
  6. Add relationship to Material (one-to-many, cascade delete)
  7. Add unique constraint on (category_id, name)
- **Notes**: Foreign key uses `ondelete="CASCADE"`

### Subtask T003 - Create Material Model
- **Purpose**: Abstract material definition (e.g., "Red Satin Ribbon")
- **File**: `src/models/material.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `Material(BaseModel)` class
  3. Set `__tablename__ = "materials"`
  4. Add fields: subcategory_id (FK), name, slug, description, base_unit_type, notes
  5. Add CHECK constraint for base_unit_type IN ('each', 'linear_inches', 'square_inches')
  6. Add relationship to MaterialSubcategory (many-to-one)
  7. Add relationship to MaterialProduct (one-to-many, cascade delete)
  8. Add relationship to MaterialUnit (one-to-many)
- **Notes**: base_unit_type determines how inventory is aggregated

### Subtask T004 - Create MaterialProduct Model
- **Purpose**: Specific purchasable item from a supplier
- **File**: `src/models/material_product.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialProduct(BaseModel)` class
  3. Set `__tablename__ = "material_products"`
  4. Add fields per data-model.md (material_id, supplier_id, name, brand, sku, package_quantity, package_unit, quantity_in_base_units, current_inventory, weighted_avg_cost, is_hidden, notes)
  5. Add CHECK constraints for positive quantities, non-negative inventory/cost
  6. Add relationships to Material, Supplier, MaterialPurchase
  7. Add display_name property
- **Notes**: weighted_avg_cost and current_inventory are updated by purchase service

### Subtask T005 - Create MaterialUnit Model
- **Purpose**: Atomic consumption unit (e.g., "6-inch ribbon")
- **File**: `src/models/material_unit.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialUnit(BaseModel)` class
  3. Set `__tablename__ = "material_units"`
  4. Add fields: material_id (FK), name, slug, quantity_per_unit, description
  5. Add CHECK constraint for quantity_per_unit > 0
  6. Add relationship to Material (many-to-one)
  7. Add computed property stubs for available_inventory and current_cost (actual logic in service)
- **Notes**: quantity_per_unit is in material's base_unit_type

### Subtask T006 - Create MaterialPurchase Model
- **Purpose**: Purchase transaction with immutable cost snapshot
- **File**: `src/models/material_purchase.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialPurchase(BaseModel)` class
  3. Set `__tablename__ = "material_purchases"`
  4. Override `updated_at = None` (immutable record)
  5. Add fields: product_id (FK), supplier_id (FK), purchase_date, packages_purchased, package_price, units_added, unit_cost, notes
  6. Use Numeric(10,4) for price fields
  7. Add CHECK constraints per data-model.md
  8. Add relationships to MaterialProduct, Supplier
- **Notes**: This model is IMMUTABLE - no updated_at

### Subtask T007 - Create MaterialConsumption Model
- **Purpose**: Assembly consumption record with denormalized snapshot
- **File**: `src/models/material_consumption.py`
- **Parallel?**: Yes
- **Steps**:
  1. Create file with standard imports
  2. Define `MaterialConsumption(BaseModel)` class
  3. Set `__tablename__ = "material_consumptions"`
  4. Override `updated_at = None` (immutable snapshot)
  5. Add fields: assembly_run_id (FK), product_id (FK nullable), quantity_consumed, unit_cost, total_cost
  6. Add snapshot fields: product_name, material_name, subcategory_name, category_name, supplier_name
  7. Add relationships to AssemblyRun, MaterialProduct
- **Notes**: Snapshot fields preserve history even if catalog changes

### Subtask T008 - Update models/__init__.py
- **Purpose**: Export all new models for easy importing
- **File**: `src/models/__init__.py`
- **Parallel?**: No (depends on T001-T007)
- **Steps**:
  1. Add imports for all 7 new models
  2. Add to `__all__` list in dependency order:
     - MaterialCategory
     - MaterialSubcategory
     - Material
     - MaterialProduct
     - MaterialUnit
     - MaterialPurchase
     - MaterialConsumption
  3. Verify no circular import issues

## Test Strategy

**Basic validation (no formal tests required for models):**
```python
# Quick smoke test
from src.models import (
    MaterialCategory, MaterialSubcategory, Material,
    MaterialProduct, MaterialUnit, MaterialPurchase, MaterialConsumption
)
from src.services.database import engine
from src.models.base import Base

# Create tables
Base.metadata.create_all(engine)
print("All material models loaded and tables created successfully")
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular imports | Import in dependency order; use TYPE_CHECKING for forward refs |
| Foreign key constraint errors | Ensure referenced tables created first |
| Constraint naming collisions | Use consistent prefixes: `ck_material_*`, `idx_material_*` |
| SQLite compatibility | Avoid features not supported by SQLite (e.g., ARRAY types) |

## Definition of Done Checklist

- [ ] All 7 model files created in `src/models/`
- [ ] All models inherit from BaseModel
- [ ] All fields match data-model.md specifications
- [ ] All CHECK constraints defined
- [ ] All indexes created
- [ ] All relationships defined with correct cascade behavior
- [ ] `src/models/__init__.py` exports all new models
- [ ] Basic import test passes without errors
- [ ] Database tables can be created via `Base.metadata.create_all()`

## Review Guidance

**Reviewer should verify:**
1. Field types match data-model.md exactly
2. Constraint names are unique and follow conventions
3. Relationships have correct `back_populates` settings
4. Immutable models (Purchase, Consumption) have `updated_at = None`
5. No business logic in models (belongs in services)

## Activity Log

- 2026-01-10T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-10T20:31:56Z – claude – lane=doing – Started implementation
- 2026-01-10T20:36:44Z – claude – lane=for_review – All 7 models created and verified
- 2026-01-11T01:06:17Z – claude – lane=done – Review passed: All 7 models created per data-model.md. Gemini test run confirmed all tests passing.
