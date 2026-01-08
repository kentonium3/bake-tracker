---
work_package_id: WP01
title: Unit Model & Seeding
lane: done
history:
- timestamp: '2025-12-16T16:56:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 1 - Foundation
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: '23336'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
---

# Work Package Prompt: WP01 - Unit Model & Seeding

## Review Feedback

**Status**: **APPROVED**

**Review Summary**:
All acceptance criteria met. Implementation follows established patterns and matches data-model.md specification.

**Verification Performed**:
1. Unit model structure verified (all required columns present)
2. Unit exported from `src/models/__init__.py`
3. `seed_units()` function exists with complete UNIT_METADATA (27 entries)
4. `init_database()` calls `seed_units()` at line 227
5. All 21 new tests pass (11 model tests, 10 seeding tests)
6. Full test suite passes (784 passed, 12 skipped)

**Tests Executed**:
- `pytest src/tests/test_unit_model.py src/tests/test_unit_seeding.py -v` - 21/21 passed

---

## Objectives & Success Criteria

**Goal**: Create the Unit model and seed all 27 units on database initialization.

**Success Criteria**:
- Unit model exists in `src/models/unit.py` following BaseModel pattern
- Unit model exported from `src/models/__init__.py`
- `seed_units()` function populates 27 units from constants.py
- Seeding is idempotent (no duplicates on restart)
- All existing tests continue to pass
- Fresh database startup creates units table with exactly 27 units

**User Story Addressed**: US4 - Reference Table Seeded on First Launch

## Context & Constraints

**Reference Documents**:
- `.kittify/memory/constitution.md` - Project principles
- `kitty-specs/022-unit-reference-table/plan.md` - Technical approach
- `kitty-specs/022-unit-reference-table/data-model.md` - Unit entity definition
- `kitty-specs/022-unit-reference-table/spec.md` - User Story 4 acceptance criteria

**Architectural Constraints**:
- Follow BaseModel pattern from `src/models/base.py`
- Use existing constants from `src/utils/constants.py`
- Seeding happens in `src/services/database.py` init_database()
- No migration scripts needed (per Constitution VI)

**Key Data**:
- 27 units total: 4 weight, 9 volume, 4 count, 10 package
- Categories: "weight", "volume", "count", "package"
- Each unit has: code, display_name, symbol, category, un_cefact_code (nullable), sort_order

## Subtasks & Detailed Guidance

### Subtask T001 - Create Unit model in `src/models/unit.py`

**Purpose**: Define the Unit reference table schema.

**Steps**:
1. Create new file `src/models/unit.py`
2. Import BaseModel from `.base`
3. Define Unit class inheriting from BaseModel
4. Add columns:
   - `code`: String(20), unique, not null, indexed - the unit code stored in other tables (e.g., "oz", "cup")
   - `display_name`: String(50), not null - human-readable name (e.g., "ounce", "cup")
   - `symbol`: String(20), not null - what shows in UI (typically same as code)
   - `category`: String(20), not null, indexed - one of: "weight", "volume", "count", "package"
   - `un_cefact_code`: String(10), nullable - for future international standard compliance
   - `sort_order`: Integer, not null, default 0 - display order within category
5. Add `__tablename__ = "units"`
6. Add appropriate indexes (`idx_unit_code`, `idx_unit_category`)

**Files**: `src/models/unit.py` (create)

**Example Structure**:
```python
from sqlalchemy import Column, String, Integer, Index
from .base import BaseModel

class Unit(BaseModel):
    __tablename__ = "units"

    code = Column(String(20), unique=True, nullable=False, index=True)
    display_name = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False, index=True)
    un_cefact_code = Column(String(10), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_unit_code", "code"),
        Index("idx_unit_category", "category"),
    )

    def __repr__(self) -> str:
        return f"Unit(code='{self.code}', category='{self.category}')"
```

**Parallel?**: No - foundational, others depend on it

---

### Subtask T002 - Update `src/models/__init__.py` to export Unit

**Purpose**: Make Unit model importable from the models package.

**Steps**:
1. Open `src/models/__init__.py`
2. Add import: `from .unit import Unit`
3. Add `Unit` to `__all__` list if one exists

**Files**: `src/models/__init__.py` (modify)

**Parallel?**: Yes - can run after T001

---

### Subtask T003 - Create `seed_units()` function in `src/services/database.py`

**Purpose**: Create idempotent function that populates the units table from constants.py.

**Steps**:
1. Open `src/services/database.py`
2. Import Unit model and constants:
   ```python
   from ..models.unit import Unit
   from ..utils.constants import WEIGHT_UNITS, VOLUME_UNITS, COUNT_UNITS, PACKAGE_UNITS
   ```
3. Create `seed_units()` function that:
   - Opens a session using session_scope()
   - Checks if units table is empty: `session.query(Unit).count() == 0`
   - If empty, creates Unit objects for all 27 units
   - Assigns sort_order incrementally within each category

**Files**: `src/services/database.py` (modify)

**Seed Data Reference** (from data-model.md):

Weight units (sort_order 0-3):
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| oz | ounce | oz | ONZ |
| lb | pound | lb | LBR |
| g | gram | g | GRM |
| kg | kilogram | kg | KGM |

Volume units (sort_order 0-8):
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| tsp | teaspoon | tsp | - |
| tbsp | tablespoon | tbsp | - |
| cup | cup | cup | - |
| ml | milliliter | ml | MLT |
| l | liter | l | LTR |
| fl oz | fluid ounce | fl oz | OZA |
| pt | pint | pt | PTI |
| qt | quart | qt | QTI |
| gal | gallon | gal | GLL |

Count units (sort_order 0-3):
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| each | each | ea | EA |
| count | count | ct | - |
| piece | piece | pc | PCE |
| dozen | dozen | dz | DZN |

Package units (sort_order 0-9):
| code | display_name | symbol | un_cefact_code |
|------|--------------|--------|----------------|
| bag | bag | bag | BG |
| box | box | box | BX |
| bar | bar | bar | - |
| bottle | bottle | bottle | BO |
| can | can | can | CA |
| jar | jar | jar | JR |
| packet | packet | packet | PA |
| container | container | container | - |
| package | package | pkg | PK |
| case | case | case | CS |

**Parallel?**: No - depends on T001

---

### Subtask T004 - Call `seed_units()` from `init_database()` function

**Purpose**: Ensure units are seeded whenever database is initialized.

**Steps**:
1. In `src/services/database.py`, find `init_database()` function (around line 90)
2. After `Base.metadata.create_all(engine)`, call `seed_units()`
3. Add logging: `logger.info("Seeding unit reference table")`

**Files**: `src/services/database.py` (modify)

**Parallel?**: No - depends on T003

---

### Subtask T005 - Write tests for Unit model in `src/tests/test_unit_model.py`

**Purpose**: Verify Unit model works correctly.

**Steps**:
1. Create `src/tests/test_unit_model.py`
2. Test cases:
   - Unit can be created with required fields
   - Unit.code must be unique
   - Unit.category is stored correctly
   - Unit inherits BaseModel fields (id, uuid, created_at, updated_at)
   - __repr__ returns expected string

**Files**: `src/tests/test_unit_model.py` (create)

**Parallel?**: Yes - can run after T001

---

### Subtask T006 - Write tests for seeding in `src/tests/test_unit_seeding.py`

**Purpose**: Verify seeding works correctly and is idempotent.

**Steps**:
1. Create `src/tests/test_unit_seeding.py`
2. Test cases:
   - Fresh database has 27 units after init
   - Units distributed correctly: 4 weight, 9 volume, 4 count, 10 package
   - Running seed_units() twice doesn't create duplicates
   - All expected unit codes are present
   - Each unit has correct category

**Files**: `src/tests/test_unit_seeding.py` (create)

**Parallel?**: Yes - can run after T003/T004

---

## Test Strategy

**Required Tests**:
- `src/tests/test_unit_model.py` - Unit model validation
- `src/tests/test_unit_seeding.py` - Seeding functionality

**Run Command**:
```bash
pytest src/tests/test_unit_model.py src/tests/test_unit_seeding.py -v
```

**Verification**:
- All tests pass
- `pytest src/tests -v` (full suite) still passes

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Duplicate seeding on restart | Low | Idempotent check: `count() == 0` |
| Missing units | Low | Test asserts exactly 27 units |
| Import circular dependency | Low | Import Unit locally in seed_units() if needed |

---

## Definition of Done Checklist

- [ ] `src/models/unit.py` created with Unit class
- [ ] Unit exported from `src/models/__init__.py`
- [ ] `seed_units()` function created in database.py
- [ ] `init_database()` calls `seed_units()`
- [ ] `src/tests/test_unit_model.py` written and passing
- [ ] `src/tests/test_unit_seeding.py` written and passing
- [ ] All existing tests still pass
- [ ] Fresh database startup creates 27 units

---

## Review Guidance

**Acceptance Checkpoints**:
1. Verify Unit model matches data-model.md specification
2. Run `pytest src/tests/test_unit*.py -v` - all pass
3. Delete database, restart app, verify 27 units seeded
4. Restart app again, verify still 27 units (no duplicates)

---

## Activity Log

- 2025-12-16T16:56:32Z - system - lane=planned - Prompt created.
- 2025-12-16T17:11:11Z – claude – shell_pid=23336 – lane=doing – Started implementation of Unit Model & Seeding
- 2025-12-16T17:28:36Z – claude – shell_pid=23336 – lane=for_review – Implementation complete: Unit model, seeding, and tests all passing
- 2025-12-16T17:31:52Z – claude – shell_pid=23336 – lane=done – Code review APPROVED: All 21 tests pass, Unit model matches data-model.md spec, seeding is idempotent
