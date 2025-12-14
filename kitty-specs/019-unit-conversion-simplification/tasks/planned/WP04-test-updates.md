---
work_package_id: "WP04"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Test Updates & Validation"
phase: "Phase 3 - Testing"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Test Updates & Validation

## Objectives & Success Criteria

- Update/remove tests for deleted UnitConversion model
- Remove recipe_unit expectations from ingredient tests
- Add/verify unit tests for `convert_any_units()` accuracy
- Update import/export tests for v3.3 format
- Add test for v3.2 import rejection

**Success Test**: `pytest src/tests -v` passes with >70% coverage on affected services.

## Context & Constraints

- **Spec**: `kitty-specs/019-unit-conversion-simplification/spec.md` (FR-006, FR-007)
- **Plan**: `kitty-specs/019-unit-conversion-simplification/plan.md`
- **Depends on**: WP01, WP02, WP03

**Testing Philosophy** (from user):
- Tests verify math is correct (not regression comparison)
- Unit tests should validate conversion calculations produce accurate results
- No need to compare against "old" values

**Key Test Files**:
- `src/tests/test_models.py`
- `src/tests/test_unit_converter.py`
- `src/tests/services/test_import_export_service.py`
- `src/tests/services/test_ingredient_service.py`
- `src/tests/conftest.py` (fixtures)

## Subtasks & Detailed Guidance

### Subtask T019 – Update test_models.py for UnitConversion removal

- **Purpose**: Remove tests for the deleted UnitConversion model.
- **Steps**:
  1. Open `src/tests/test_models.py`
  2. Find and remove any test classes/functions for UnitConversion
  3. Remove any fixtures that create UnitConversion instances
  4. Update ingredient model tests to not expect `conversions` relationship
- **Files**: `src/tests/test_models.py` (EDIT)
- **Parallel?**: No - do first to understand test patterns
- **Notes**: Search for `UnitConversion`, `unit_conversion`, `conversions`.

### Subtask T020 – Update ingredient-related tests

- **Purpose**: Remove recipe_unit expectations from ingredient tests.
- **Steps**:
  1. Grep all test files for `recipe_unit`: `grep -r "recipe_unit" src/tests/`
  2. For each occurrence:
     - If it's a fixture creating ingredients, remove the recipe_unit parameter
     - If it's an assertion checking recipe_unit, remove the assertion
     - If it's testing recipe_unit functionality, remove the test
  3. Update `src/tests/conftest.py` fixtures if they create ingredients with recipe_unit
- **Files**: Multiple test files (EDIT)
- **Parallel?**: Yes - can be done with T021, T022
- **Notes**: Focus on `conftest.py`, `test_ingredient_service.py`, integration tests.

### Subtask T021 – Add/verify convert_any_units() accuracy tests

- **Purpose**: Ensure unit conversion math is correct.
- **Steps**:
  1. Open `src/tests/test_unit_converter.py`
  2. Verify or add tests for:
     - Same-type weight conversions: `convert_any_units(1, "lb", "oz")` == 16
     - Same-type volume conversions: `convert_any_units(1, "cup", "tbsp")` == 16
     - Cross-type with density: `convert_any_units(1, "cup", "oz", ingredient_with_density)`
  3. Add test for known density: All-Purpose Flour (1 cup = 4.25 oz)
     ```python
     def test_convert_flour_cup_to_oz():
         # Create mock ingredient with density: 1 cup = 4.25 oz
         # Density in g/ml = (4.25 * 28.3495) / 236.588 ≈ 0.509
         success, result, error = convert_any_units(1, "cup", "oz", density_g_per_ml=0.509)
         assert success
         assert abs(result - 4.25) < 0.1  # Allow small floating point variance
     ```
  4. Verify edge cases: missing density returns appropriate error
- **Files**: `src/tests/test_unit_converter.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: These tests validate math correctness, not regression.

### Subtask T022 – Update import/export tests for v3.3

- **Purpose**: Update tests to expect v3.3 format.
- **Steps**:
  1. Open `src/tests/services/test_import_export_service.py`
  2. Update any test fixtures that create v3.2 format data to use v3.3
  3. Remove `unit_conversions` from test data
  4. Remove `recipe_unit` from ingredient test data
  5. Update version assertions from "3.2" to "3.3"
  6. Remove any tests that specifically test unit_conversions import/export
- **Files**: `src/tests/services/test_import_export_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Search for `"3.2"`, `unit_conversion`, `recipe_unit`.

### Subtask T023 – Add v3.2 import rejection test

- **Purpose**: Verify old format is rejected with clear error.
- **Steps**:
  1. Add a test that attempts to import v3.2 format data
  2. Verify it raises `ImportVersionError`
  3. Verify the error message is user-friendly
  ```python
  def test_import_v32_rejected():
      v32_data = {"version": "3.2", "ingredients": []}
      # Write to temp file and attempt import
      with pytest.raises(ImportVersionError) as exc_info:
          import_all_from_json_v3(temp_file_path)
      assert "3.3" in str(exc_info.value)  # Error mentions required version
  ```
- **Files**: `src/tests/services/test_import_export_service.py` (EDIT)
- **Parallel?**: No - should be done after T022
- **Notes**: This is a new test, not an update.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test fixtures break | Update conftest.py first |
| Coverage drops | Focus on conversion accuracy tests |
| Flaky floating point tests | Use appropriate tolerance (< 0.1) |

## Definition of Done Checklist

- [ ] No tests reference UnitConversion model
- [ ] No tests expect recipe_unit field
- [ ] Tests exist verifying `convert_any_units()` math accuracy
- [ ] Import/export tests use v3.3 format
- [ ] Test exists for v3.2 rejection
- [ ] `pytest src/tests -v` passes
- [ ] Coverage >70% on affected services

## Review Guidance

- Verify new conversion tests use realistic values (e.g., flour density)
- Check that v3.2 rejection test has clear error message assertion
- Ensure no orphaned fixtures or imports remain
- Run full test suite to verify no regressions

## Activity Log

- 2025-12-14T12:00:00Z – system – lane=planned – Prompt created.
