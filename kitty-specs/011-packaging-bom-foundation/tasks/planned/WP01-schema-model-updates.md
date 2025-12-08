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
  - "T009"
  - "T010"
  - "T011"
title: "Schema Updates & Model Changes"
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

# Work Package Prompt: WP01 - Schema Updates & Model Changes

## Objectives & Success Criteria

**Goal**: Update Ingredient and Composition models with packaging support; ensure database auto-creates correctly.

**Success Criteria**:
- [ ] Ingredient model has `is_packaging` boolean column (default: False)
- [ ] Composition model has `package_id` FK column
- [ ] Composition model has `packaging_product_id` FK column
- [ ] `component_quantity` changed from Integer to Float
- [ ] XOR constraints updated for parent (assembly_id OR package_id)
- [ ] XOR constraints updated for component (3-way: finished_unit_id, finished_good_id, packaging_product_id)
- [ ] All existing tests pass (no regressions)
- [ ] New schema auto-creates correctly in SQLite

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/011-packaging-bom-foundation/spec.md` (FR-001 through FR-007)
- Data Model: `kitty-specs/011-packaging-bom-foundation/data-model.md`
- Research: `kitty-specs/011-packaging-bom-foundation/research.md` (RQ1, RQ2, RQ3 decisions)

**Architectural Constraints**:
- No Alembic migrations - direct SQLAlchemy model updates with auto-create
- SQLite database with WAL mode
- Backup data before schema changes

**Current State**:
- Composition has `assembly_id` (FK to finished_goods), `finished_unit_id`, `finished_good_id`
- Composition has `component_quantity` as Integer
- Ingredient has no `is_packaging` field

## Subtasks & Detailed Guidance

### Subtask T001 - Add is_packaging to Ingredient model
- **Purpose**: Enable marking ingredients as packaging materials (FR-001)
- **File**: `src/models/ingredient.py`
- **Steps**:
  1. Import `Boolean` from sqlalchemy if not already imported
  2. Add column after existing fields:
     ```python
     is_packaging = Column(Boolean, nullable=False, default=False, index=True)
     ```
  3. Add index in `__table_args__`:
     ```python
     Index("idx_ingredient_is_packaging", "is_packaging"),
     ```
- **Parallel?**: Yes - can proceed independently of Composition changes
- **Notes**: Default False ensures existing food ingredients remain unchanged

### Subtask T002 - Add package_id FK to Composition model
- **Purpose**: Allow compositions to belong to Package (for Package-level packaging) (FR-007)
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add column after `assembly_id`:
     ```python
     package_id = Column(
         Integer, ForeignKey("packages.id", ondelete="CASCADE"),
         nullable=True, index=True
     )
     ```
  2. Change `assembly_id` to `nullable=True` (was False)
- **Parallel?**: No - depends on Package model import
- **Notes**: CASCADE ensures compositions deleted when Package deleted (FR-019)

### Subtask T003 - Add packaging_product_id FK to Composition model
- **Purpose**: Allow compositions to reference packaging products (FR-004)
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add column after `finished_good_id`:
     ```python
     packaging_product_id = Column(
         Integer, ForeignKey("products.id", ondelete="RESTRICT"),
         nullable=True, index=True
     )
     ```
- **Parallel?**: No - sequential with other Composition changes
- **Notes**: RESTRICT prevents deletion of products in use (FR-018)

### Subtask T004 - Change component_quantity to Float
- **Purpose**: Support decimal quantities like "0.5 yards ribbon" (FR-006)
- **File**: `src/models/composition.py`
- **Steps**:
  1. Import `Float` from sqlalchemy
  2. Change line from:
     ```python
     component_quantity = Column(Integer, nullable=False, default=1)
     ```
     To:
     ```python
     component_quantity = Column(Float, nullable=False, default=1.0)
     ```
- **Parallel?**: No - part of Composition model update
- **Notes**: SQLite dynamically typed; existing int values work with Float

### Subtask T005 - Update parent XOR constraint
- **Purpose**: Ensure exactly one parent (assembly_id OR package_id) (FR-005)
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add new CheckConstraint in `__table_args__`:
     ```python
     CheckConstraint(
         "(assembly_id IS NOT NULL AND package_id IS NULL) OR "
         "(assembly_id IS NULL AND package_id IS NOT NULL)",
         name="ck_composition_exactly_one_parent",
     ),
     ```
- **Parallel?**: No - part of constraint updates
- **Notes**: This is a NEW constraint (existing code only has assembly_id)

### Subtask T006 - Update component XOR constraint
- **Purpose**: Ensure exactly one component type (3-way XOR) (FR-005)
- **File**: `src/models/composition.py`
- **Steps**:
  1. Update existing `ck_composition_exactly_one_component` constraint:
     ```python
     CheckConstraint(
         "(finished_unit_id IS NOT NULL AND finished_good_id IS NULL AND packaging_product_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NOT NULL AND packaging_product_id IS NULL) OR "
         "(finished_unit_id IS NULL AND finished_good_id IS NULL AND packaging_product_id IS NOT NULL)",
         name="ck_composition_exactly_one_component",
     ),
     ```
- **Parallel?**: No - part of constraint updates
- **Notes**: Replaces existing 2-way constraint

### Subtask T007 - Add indexes and unique constraints
- **Purpose**: Performance and data integrity for packaging columns
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add indexes:
     ```python
     Index("idx_composition_package", "package_id"),
     Index("idx_composition_packaging_product", "packaging_product_id"),
     ```
  2. Add unique constraints:
     ```python
     UniqueConstraint("assembly_id", "packaging_product_id", name="uq_composition_assembly_packaging"),
     UniqueConstraint("package_id", "packaging_product_id", name="uq_composition_package_packaging"),
     ```
- **Parallel?**: No - part of __table_args__ updates

### Subtask T008 - Add packaging_product relationship
- **Purpose**: Enable ORM navigation from Composition to Product
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add relationship:
     ```python
     packaging_product = relationship(
         "Product", foreign_keys=[packaging_product_id], lazy="joined"
     )
     ```
- **Parallel?**: No - depends on T003

### Subtask T009 - Add package relationship
- **Purpose**: Enable ORM navigation from Composition to Package
- **File**: `src/models/composition.py`
- **Steps**:
  1. Add relationship:
     ```python
     package = relationship(
         "Package", foreign_keys=[package_id],
         back_populates="packaging_compositions", lazy="joined"
     )
     ```
- **Parallel?**: No - depends on T002 and T010

### Subtask T010 - Add packaging_compositions to Package model
- **Purpose**: Enable ORM navigation from Package to its packaging compositions
- **File**: `src/models/package.py`
- **Steps**:
  1. Add relationship after existing `package_finished_goods`:
     ```python
     packaging_compositions = relationship(
         "Composition",
         foreign_keys="Composition.package_id",
         back_populates="package",
         cascade="all, delete-orphan",
         lazy="selectin",
     )
     ```
- **Parallel?**: No - must coordinate with T009

### Subtask T011 - Update models __init__.py
- **Purpose**: Ensure proper import order for new relationships
- **File**: `src/models/__init__.py`
- **Steps**:
  1. Verify Composition is imported after Package and Product
  2. Verify no circular import issues
  3. Run `python -c "from src.models import *"` to test
- **Parallel?**: No - final verification step

## Test Strategy

**Required Tests** (Constitution Principle IV):
1. Verify models import without error
2. Verify database auto-creates with new schema
3. Run existing test suite: `pytest src/tests -v`
4. Verify all existing tests pass (no regressions)

**Test Commands**:
```bash
# Export existing data first
python -c "from src.services.import_export_service import export_all_data; export_all_data('backup_before_wp01.json')"

# Delete database
rm -f data/bake_tracker.db

# Test imports
python -c "from src.models import Ingredient, Composition, Package, Product"

# Run test suite
pytest src/tests -v
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | Medium | High | Careful import order in __init__.py |
| Existing test failures | Low | Medium | Run tests before and after each change |
| Constraint name conflicts | Low | High | Drop/recreate database |
| Data loss | Low | High | Export backup before changes |

## Definition of Done Checklist

- [ ] All 11 subtasks completed
- [ ] `is_packaging` column exists on Ingredient
- [ ] `package_id` and `packaging_product_id` columns exist on Composition
- [ ] `component_quantity` is Float type
- [ ] All constraints and indexes created
- [ ] All relationships work bidirectionally
- [ ] Models import without error
- [ ] All existing tests pass
- [ ] tasks.md updated with status

## Review Guidance

**Key Checkpoints**:
1. Verify XOR constraints work: try to create composition with both assembly_id and package_id (should fail)
2. Verify RESTRICT works: try to delete Product referenced in composition (should fail)
3. Verify Float quantities: create composition with quantity 0.5 (should work)
4. Verify cascade: delete Package, verify compositions deleted

## Activity Log

- 2025-12-08T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
