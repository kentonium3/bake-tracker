---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Supplier Model"
phase: "Phase 1 - Schema & Models"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "50566"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-22T14:35:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Supplier Model

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Create the Supplier SQLAlchemy model with all attributes, constraints, and indexes.

**Success Criteria**:
- [ ] Supplier model imports without errors
- [ ] Can create, query, and update suppliers in test database
- [ ] State constraint enforces 2-letter uppercase codes
- [ ] Indexes exist for common query patterns
- [ ] Model tests pass

## Context & Constraints

**Reference Documents**:
- Data model: `kitty-specs/027-product-catalog-management/data-model.md` (Supplier entity)
- Constitution: `.kittify/memory/constitution.md` (Schema principles)
- Session management: `CLAUDE.md` (BaseModel pattern)

**Architectural Constraints**:
- Inherit from BaseModel (provides id, uuid, created_at, updated_at)
- Follow existing model patterns in `src/models/`
- Use SQLAlchemy 2.x type annotations

## Subtasks & Detailed Guidance

### T001 – Create supplier.py with Supplier class

**Purpose**: Establish the Supplier model file following project conventions.

**Steps**:
1. Create `src/models/supplier.py`
2. Import BaseModel from `src/models/base`
3. Import required SQLAlchemy types (String, Boolean, Text, Index, CheckConstraint)
4. Define `class Supplier(BaseModel):`
5. Set `__tablename__ = "suppliers"`

**Files**: `src/models/supplier.py` (NEW)

### T002 – Add all columns

**Purpose**: Define the complete attribute set for suppliers.

**Steps**:
Add columns per data-model.md:
```python
name = Column(String(200), nullable=False)
street_address = Column(String(200), nullable=True)
city = Column(String(100), nullable=False)
state = Column(String(2), nullable=False)
zip_code = Column(String(10), nullable=False)
notes = Column(Text, nullable=True)
is_active = Column(Boolean, nullable=False, default=True)
```

**Notes**:
- BaseModel provides id, uuid, created_at, updated_at
- is_active defaults to True for soft delete pattern
- street_address is optional (nullable=True)

### T003 – Add check constraints for state

**Purpose**: Enforce state code format (2-letter uppercase).

**Steps**:
Add table args with check constraint:
```python
__table_args__ = (
    CheckConstraint(
        "state = UPPER(state) AND LENGTH(state) = 2",
        name="ck_supplier_state_format"
    ),
)
```

**Notes**:
- SQLite supports CHECK constraints
- Test with lowercase input to verify constraint fires

### T004 – Add indexes

**Purpose**: Optimize common query patterns.

**Steps**:
Add to `__table_args__`:
```python
__table_args__ = (
    CheckConstraint(...),
    Index("idx_supplier_name_city", "name", "city"),
    Index("idx_supplier_active", "is_active"),
)
```

**Notes**:
- idx_supplier_name_city: for "Costco in Waltham" lookups
- idx_supplier_active: for filtering active suppliers in dropdowns

### T005 – Update models __init__.py

**Purpose**: Export Supplier for use throughout the application.

**Steps**:
1. Open `src/models/__init__.py`
2. Add import: `from .supplier import Supplier`
3. Add to `__all__` list: `"Supplier"`

**Files**: `src/models/__init__.py` (MODIFY)

### T006 – Write basic model tests

**Purpose**: Verify model creation, constraints, and queries.

**Steps**:
1. Create `src/tests/models/test_supplier_model.py`
2. Write tests:
   - `test_create_supplier_success`: create with valid data
   - `test_supplier_requires_name`: verify nullable=False
   - `test_supplier_state_constraint`: lowercase state should fail or be rejected
   - `test_supplier_default_is_active`: verify default True
   - `test_supplier_has_uuid`: verify UUID generated

**Files**: `src/tests/models/test_supplier_model.py` (NEW)

**Notes**:
- Use existing test fixtures pattern from other model tests
- SQLite may not enforce CHECK at insert time; validate in service layer

## Test Strategy

**Required Tests** (T006):
- Model instantiation with valid data
- Required field validation
- Default values (is_active=True)
- UUID generation

**Commands**:
```bash
pytest src/tests/models/test_supplier_model.py -v
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| State constraint not enforced by SQLite | Add service-layer validation in WP03 |
| Import conflicts | Verify no circular imports |

## Definition of Done Checklist

- [ ] `src/models/supplier.py` created with complete Supplier class
- [ ] All columns defined per data-model.md
- [ ] Check constraint for state format added
- [ ] Indexes added for name_city and active
- [ ] `src/models/__init__.py` exports Supplier
- [ ] Model tests pass
- [ ] No import errors when running application

## Review Guidance

**Key Checkpoints**:
1. Verify inheritance from BaseModel
2. Confirm column types match data-model.md
3. Check constraint syntax is valid
4. Verify indexes are created (check with `.schema suppliers` in SQLite)
5. Run tests to confirm model works

## Activity Log

- 2025-12-22T14:35:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2025-12-22T20:32:44Z – claude – shell_pid=50566 – lane=doing – Started implementation
- 2025-12-22T20:40:49Z – claude – shell_pid=50566 – lane=for_review – Implementation complete: all 19 tests pass
- 2025-12-23T02:38:54Z – claude – shell_pid=50566 – lane=done – Code review APPROVED: All 19 tests pass, model complete with proper constraints and indexes
