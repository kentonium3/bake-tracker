---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Export Version Bump and Test Updates"
phase: "Phase 3 - Polish"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T18:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Export Version Bump and Test Updates

## Objectives & Success Criteria

**Goal**: Bump export version from 4.0 to 4.1; identify and fix all failing tests; verify the complete import/export cycle works correctly.

**Success Criteria**:
- Export version is "4.1"
- All pytest tests pass (or intentionally skipped with documented reason)
- Sample data files load successfully
- Full export -> reset -> import cycle preserves data integrity

**Independent Test**:
```bash
pytest src/tests -v  # All tests pass
python -c "from src.services.import_export_service import export_all_to_json"  # Imports work
```

## Context & Constraints

**Related Documents**:
- Feature Spec: `kitty-specs/045-cost-architecture-refactor/spec.md` (FR-015, FR-016, FR-017)
- Implementation Plan: `kitty-specs/045-cost-architecture-refactor/plan.md`
- Research: `kitty-specs/045-cost-architecture-refactor/research.md`

**Architecture Constraints**:
- Export version must be exactly "4.1" (not 4.1.0 or v4.1)
- v4.0 imports will fail due to schema mismatch - this is expected behavior
- Sample data files are already compliant (no cost fields) per research

**Dependencies**:
- **MUST wait for WP03 to complete** before starting this WP
- All model and service changes must be in place first

## Subtasks & Detailed Guidance

### Subtask T017 - Bump Export Version to 4.1

**Purpose**: Update the export format version to indicate cost fields are no longer included.

**Steps**:
1. Open `src/services/import_export_service.py`
2. Locate line 1138 (in `export_all_to_json()` function)
3. Change `"version": "4.0"` to `"version": "4.1"`

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes, can be done immediately

**Code Change**:
```python
# Before (line 1138)
"version": "4.0",  # Feature 040: v4.0 schema upgrade

# After
"version": "4.1",  # Feature 045: Cost field removal from definitions
```

### Subtask T018 - Run pytest to Identify Failures

**Purpose**: Discover all tests that fail due to the cost field removal.

**Steps**:
1. Run the full test suite:
   ```bash
   pytest src/tests -v 2>&1 | tee pytest_output.txt
   ```
2. Identify all failing tests
3. Categorize failures:
   - Tests that assert on `unit_cost` field
   - Tests that assert on `total_cost` field
   - Tests that call removed methods
   - Tests that expect cost fields in dict outputs

**Expected Failures** (from research.md):
- `src/tests/test_models.py` - Model field tests
- `src/tests/services/test_import_export_service.py` - Export/import tests
- Any test file referencing FinishedUnit.unit_cost or FinishedGood.total_cost

**Search Command**:
```bash
grep -rn "unit_cost\|total_cost" src/tests/ --include="*.py"
```

**Files**: `src/tests/` (all test files)
**Parallel?**: No, must run after previous WPs complete

### Subtask T019 - Update Failing Tests

**Purpose**: Fix all tests that fail due to cost field removal.

**Steps**:
For each failing test, apply the appropriate fix:

1. **Tests asserting on model attributes**:
   - Remove assertions on `unit_cost` or `total_cost`
   - Example: `assert fu.unit_cost == Decimal("1.00")` -> DELETE

2. **Tests setting cost fields in fixtures**:
   - Remove cost field assignments
   - Example: `FinishedUnit(unit_cost=Decimal("1.00"), ...)` -> Remove parameter

3. **Tests calling removed methods**:
   - Remove the test entirely, or
   - Update to test remaining functionality
   - Example: `test_calculate_recipe_cost_per_item()` -> DELETE

4. **Tests expecting cost in dict output**:
   - Remove assertions on cost keys
   - Example: `assert "unit_cost" in result` -> DELETE

5. **Tests for export/import**:
   - Update version assertions from "4.0" to "4.1"
   - Verify no cost fields in export assertions

**Files**: Various test files in `src/tests/`
**Parallel?**: No, sequential after T018

### Subtask T020 - Verify Sample Data Files Load

**Purpose**: Confirm sample data files are compatible with new schema.

**Steps**:
1. Per research.md, sample data files are already compliant (no cost fields)
2. Verify by attempting to load them:
   ```python
   from src.services.import_export_service import import_all_from_json_v4
   result = import_all_from_json_v4("test_data/sample_data_min.json", mode="merge")
   assert result.success
   ```
3. Check both files:
   - `test_data/sample_data_min.json`
   - `test_data/sample_data_all.json`

**Note**: If version field in sample data is "4.0", update it to "4.1".

**Files**: `test_data/sample_data_min.json`, `test_data/sample_data_all.json`
**Parallel?**: No, depends on T019

### Subtask T021 - Verify Full Import/Export Cycle

**Purpose**: End-to-end validation that data survives export, reset, and re-import.

**Steps**:
1. **Export existing data** (if any):
   ```python
   from src.services.import_export_service import export_all_to_json
   result = export_all_to_json("/tmp/backup.json")
   ```

2. **Verify export format**:
   - Check version is "4.1"
   - Check no `unit_cost` in finished_units entries
   - Check no `total_cost` in finished_goods entries

3. **Reset database** (per user workflow):
   - Delete or rename the SQLite database file
   - Application will recreate on next start

4. **Import data**:
   ```python
   from src.services.import_export_service import import_all_from_json_v4
   result = import_all_from_json_v4("/tmp/backup.json", mode="replace")
   ```

5. **Verify data integrity**:
   - Count records before and after
   - Spot-check a few records for correct field values
   - Verify relationships intact

**Files**: N/A (integration test)
**Parallel?**: No, final verification step

## Test Strategy

**Required Tests** (per FR-015, FR-016, FR-017):

1. **FR-015 - Export excludes cost fields**:
   ```python
   def test_export_excludes_unit_cost():
       data = export_finished_units_to_json()
       for fu in data:
           assert "unit_cost" not in fu

   def test_export_excludes_total_cost():
       # Similar for finished_goods
   ```

2. **FR-016 - Import rejects deprecated fields** (per user decision, standard schema validation):
   - v4.0 files with cost fields will fail on import due to schema mismatch
   - No special field-by-field validation needed

3. **FR-017 - Sample data version compliant**:
   ```python
   def test_sample_data_version():
       with open("test_data/sample_data_min.json") as f:
           data = json.load(f)
       assert data["version"] == "4.1"
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Many tests fail in unexpected ways | High | Categorize failures systematically; fix in priority order |
| Sample data needs version update | Low | Quick fix if needed |
| Import/export cycle loses data | High | Test with minimal data first; verify counts |
| Hidden test dependencies | Medium | Run full suite multiple times after fixes |

## Definition of Done Checklist

- [ ] T017: Export version changed to "4.1"
- [ ] T018: All failing tests identified and documented
- [ ] T019: All tests pass (or intentionally skipped)
- [ ] T020: Sample data files load successfully
- [ ] T021: Full import/export cycle verified
- [ ] No grep matches for removed cost fields in test assertions
- [ ] `tasks.md` updated with status change

## Review Guidance

**Key Verification Points**:
1. Run `pytest src/tests -v` - All tests should pass
2. Export a file and verify:
   - Version is "4.1"
   - No `unit_cost` in any finished_units entry
   - No `total_cost` in any finished_goods entry
3. Import sample data - Should succeed without error
4. Grep for cost assertions in tests - Should be removed or updated

**Success Criteria Mapping**:
| Spec Criteria | Verification |
|---------------|--------------|
| SC-002: Tests pass | pytest passes |
| SC-003: No unit_cost in export | Manual export verification |
| SC-004: No total_cost in export | Manual export verification |
| SC-006: Sample data loads | import_all_from_json_v4 succeeds |

## Activity Log

- 2026-01-09T18:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-09T23:40:10Z – claude – lane=doing – Started implementation
- 2026-01-10T00:58:50Z – claude – lane=for_review – All tests pass, export/import verified
- 2026-01-10T01:27:47Z – claude – lane=done – Code review approved: Export version 4.1, sample data v4.1, all 1774 tests pass
