---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Schema & Models"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Schema & Models

## Objectives & Success Criteria

- Add `is_generic` boolean column to Composition model (default False)
- Create new CompositionAssignment junction table model
- Update model exports so new classes are importable
- Document schema migration procedure
- All existing tests continue to pass
- New models can be imported without errors

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 1 details
- `kitty-specs/026-deferred-packaging-decisions/data-model.md` - Full schema specification
- `kitty-specs/026-deferred-packaging-decisions/research.md` - Design decisions D1, D2
- `.kittify/memory/constitution.md` - Principle VI (Schema Change Strategy)

**Constraints**:
- Must maintain backward compatibility (existing compositions unchanged)
- Follow SQLAlchemy 2.x patterns used in codebase
- Include UUID field per BaseModel convention
- Use Constitution VI export/reset/import for schema changes

## Subtasks & Detailed Guidance

### Subtask T001 - Add is_generic column to Composition model

- **Purpose**: Enable compositions to reference generic product types instead of specific products
- **Steps**:
  1. Open `src/models/composition.py`
  2. Add `is_generic = Column(Boolean, nullable=False, default=False)`
  3. Add column to any relevant `__repr__` or serialization methods
  4. Document the column purpose in docstring
- **Files**: `src/models/composition.py`
- **Parallel?**: No
- **Notes**:
  - When `is_generic=True`, `packaging_product_id` references a "template" product whose `product_name` defines the generic requirement
  - Default False ensures existing compositions remain unchanged

### Subtask T002 - Create CompositionAssignment model

- **Purpose**: Track which specific inventory items fulfill a generic packaging requirement
- **Steps**:
  1. Create `src/models/composition_assignment.py`
  2. Define CompositionAssignment class extending BaseModel
  3. Add columns per data-model.md:
     - `composition_id` (FK to compositions.id, ON DELETE CASCADE)
     - `inventory_item_id` (FK to inventory_items.id, ON DELETE RESTRICT)
     - `quantity_assigned` (Float, CHECK > 0)
     - `assigned_at` (DateTime)
  4. Add unique constraint on `(composition_id, inventory_item_id)`
  5. Add indexes for both FK columns
  6. Define relationships to Composition and InventoryItem
- **Files**: `src/models/composition_assignment.py` (new)
- **Parallel?**: No
- **Notes**:
  - Use RESTRICT on inventory_item FK to prevent deleting inventory while assigned
  - Include `uuid` field per BaseModel convention

### Subtask T003 - Update model exports

- **Purpose**: Make new model importable from `src.models`
- **Steps**:
  1. Open `src/models/__init__.py`
  2. Add import for CompositionAssignment
  3. Add to `__all__` list
- **Files**: `src/models/__init__.py`
- **Parallel?**: No
- **Notes**: Follow existing import pattern in the file

### Subtask T004 - Document schema migration

- **Purpose**: Ensure users can migrate existing databases
- **Steps**:
  1. Add migration notes to `kitty-specs/026-deferred-packaging-decisions/quickstart.md`
  2. Document the export/reset/import cycle per Constitution VI
  3. Note that existing data requires no transformation
- **Files**: `kitty-specs/026-deferred-packaging-decisions/quickstart.md`
- **Parallel?**: No
- **Notes**: Migration is purely additive - no data loss risk

## Test Strategy

- Run existing test suite to verify no regressions
- Verify models import correctly:
  ```python
  from src.models import CompositionAssignment
  from src.models.composition import Composition
  assert hasattr(Composition, 'is_generic')
  ```
- Verify table creation by running app against fresh database

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FK constraint blocks testing | Use test fixtures that clean up properly |
| Schema drift with existing DB | Document migration procedure clearly |
| Missing BaseModel fields | Reference existing models for pattern |

## Definition of Done Checklist

- [ ] `is_generic` column added to Composition model
- [ ] CompositionAssignment model created with all fields
- [ ] Model exports updated in `__init__.py`
- [ ] Migration documentation complete
- [ ] Existing tests pass
- [ ] New models importable and createable

## Review Guidance

- Verify FK constraints match data-model.md specification
- Check that default values preserve backward compatibility
- Confirm UUID field included per BaseModel convention
- Validate relationship definitions are correct

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
