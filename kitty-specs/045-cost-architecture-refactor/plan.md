# Implementation Plan: Cost Architecture Refactor

**Branch**: `045-cost-architecture-refactor` | **Date**: 2026-01-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/045-cost-architecture-refactor/spec.md`

## Summary

Remove stored cost fields (`unit_cost`, `total_cost`) from definition models (FinishedUnit, FinishedGood) to eliminate cost staleness issues. This is a "removal only" refactor - no new functionality. Database reset + re-import workflow instead of migration script. Export version bumps from 4.0 to 4.1.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode (reset + re-import for schema changes)
**Testing**: pytest
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: N/A (removal refactor)
**Constraints**: Must not break existing data through import/export cycle
**Scale/Scope**: Single-user application

## Constitution Check

*No constitution file exists yet. Proceeding with project CLAUDE.md guidelines.*

**Architecture Compliance**:
- Layered architecture maintained (UI -> Services -> Models -> Database)
- Changes follow dependency flow (models first, then services, then UI)

**Testing Discipline**:
- Service layer changes require test updates
- Coverage target >70% for service layer

## Project Structure

### Documentation (this feature)

```
kitty-specs/045-cost-architecture-refactor/
├── spec.md              # Feature specification (exists)
├── plan.md              # This file
├── research.md          # Codebase investigation findings
├── tasks.md             # Task breakdown (created by /spec-kitty.tasks)
└── tasks/               # Work package prompts
```

### Source Code (files to modify)

```
src/
├── models/
│   ├── finished_unit.py      # Remove unit_cost column + related methods
│   └── finished_good.py      # Remove total_cost column + related methods
├── services/
│   ├── finished_unit_service.py  # Remove cost calculation references
│   ├── finished_good_service.py  # Remove cost assignment/retrieval
│   └── import_export_service.py  # Bump version 4.0 -> 4.1
├── ui/
│   └── forms/
│       ├── finished_unit_detail.py  # Remove cost display
│       └── finished_good_detail.py  # Remove cost display
└── tests/
    └── [various test files]  # Update tests referencing cost fields
```

**Structure Decision**: Existing single-project structure. No new directories needed.

## Complexity Tracking

*No violations. This is a straightforward removal refactor.*

---

## Investigation Findings

### Current State Analysis

**Export/Import Already Clean**:
- `export_finished_units_to_json()` (line 755-800) does NOT include `unit_cost`
- `export_all_to_json()` (line 1094+) does NOT include cost fields for finished units/goods
- `import_finished_units_from_json()` (line 1666-1745) does NOT set `unit_cost`
- Sample data files (`test_data/sample_data_min.json`, `test_data/sample_data_all.json`) do NOT contain cost fields

**Model Fields to Remove**:

1. **FinishedUnit** (`src/models/finished_unit.py:98`):
   ```python
   unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
   ```
   Also remove:
   - `calculate_recipe_cost_per_item()` method (lines 171-196)
   - `update_unit_cost_from_recipe()` method (lines 198-205)
   - `to_dict()` cost-related fields (lines 253-254, 257)
   - CheckConstraint `ck_finished_unit_unit_cost_non_negative` (line 133)

2. **FinishedGood** (`src/models/finished_good.py:76`):
   ```python
   total_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
   ```
   Also remove:
   - `calculate_component_cost()` method (lines 114-142)
   - `update_total_cost_from_components()` method (lines 144-151)
   - `get_component_breakdown()` cost references (lines 173-174, 183-184, 193-195)
   - `to_dict()` cost-related fields (lines 312, 315)
   - CheckConstraint `ck_finished_good_total_cost_non_negative` (line 106)

**Service References to Update**:

1. **finished_unit_service.py**:
   - Line 587: `fifo_cost = FinishedUnitService._calculate_fifo_unit_cost(unit)`
   - Line 743: `purchase_cost = FinishedUnitService._get_inventory_item_unit_cost(...)`
   - Line 811: `unit_cost = Decimal(str(purchase.unit_cost))`
   - Line 1037: `return FinishedUnitService.calculate_unit_cost(finished_unit_id)`

2. **finished_good_service.py**:
   - Line 277: `finished_good.total_cost = total_cost_with_packaging`
   - Line 1131: `return component.unit_cost if component else Decimal("0.0000")`
   - Line 1134: `return component.total_cost if component else Decimal("0.0000")`
   - Lines 1200, 1218, 1275-1276, 1294-1295: Cost references in breakdown methods
   - Lines 1339, 1389, 1396, 1405, 1408, 1410: Assembly cost calculations
   - Lines 1479, 1502: More cost references

**UI References to Remove**:

1. **finished_unit_detail.py**:
   - Line 167: `cost = self.finished_unit.unit_cost or 0`
   - Line 324: `cost = self.finished_unit.unit_cost or 0`

2. **finished_good_detail.py**:
   - Line 143: `cost = self.finished_good.total_cost or 0`
   - Line 426: `cost = self.finished_good.total_cost or 0`

**Export Version Change**:
- `src/services/import_export_service.py:1138`: Change `"version": "4.0"` to `"version": "4.1"`

---

## Parallelization Strategy

### Safe to Parallelize (Independent Files)

**Work Package 1** (Claude): FinishedUnit model + UI
- `src/models/finished_unit.py`
- `src/ui/forms/finished_unit_detail.py`

**Work Package 2** (Gemini): FinishedGood model + UI
- `src/models/finished_good.py`
- `src/ui/forms/finished_good_detail.py`

### Sequential (Dependencies)

**Work Package 3**: Service layer updates (after WP1 + WP2)
- `src/services/finished_unit_service.py`
- `src/services/finished_good_service.py`

**Work Package 4**: Export version + Tests (after WP3)
- `src/services/import_export_service.py` (version bump only)
- Test file updates

---

## Implementation Approach

### Database Workflow

Per user confirmation: No migration script. Workflow is:
1. Update code (remove columns from models)
2. Delete existing database file
3. Re-import data using app's import service

### Import Validation

Per user confirmation: Standard schema compliance - import either succeeds with new schema or fails. No special field-by-field rejection messages needed.

### Version Strategy

- Export version changes from "4.0" to "4.1"
- v4.0 imports will fail due to schema mismatch (expected behavior)
- Clear break approach - no backward compatibility shims

---

## Risk Assessment

**Low Risk**:
- Export already excludes cost fields (minimal change)
- Sample data already compliant (no updates needed)
- Single-user app with reset workflow

**Medium Risk**:
- Service layer has extensive cost references that need careful removal
- Tests may have cost-related assertions that need updating

**Mitigation**:
- Run full test suite after each work package
- Verify import/export cycle works end-to-end

---

## Success Criteria Mapping

| Spec Criteria | Implementation |
|---------------|----------------|
| SC-001: Migration completes | N/A (reset workflow) |
| SC-002: Tests pass | Update tests, run pytest |
| SC-003: No unit_cost in export | Already true, verify |
| SC-004: No total_cost in export | Already true, verify |
| SC-005: Import rejects deprecated | Schema validation handles |
| SC-006: Sample data loads | Already compliant |
| SC-007: UI no cost columns | Remove from detail views |

---

## Next Steps

1. Run `/spec-kitty.tasks` to generate work packages
2. Assign WP1 to Claude, WP2 to Gemini (parallel)
3. Complete WP3 and WP4 sequentially
4. Run full test suite
5. Verify import/export cycle
