---
work_package_id: "WP04"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Import/Export Updates"
phase: "Phase 3 - Import/Export"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "3015"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Import/Export Updates

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- **Primary Objective**: Handle 4 density fields in JSON import/export; ignore legacy field
- **Success Criteria**:
  - Export includes all 4 density fields per ingredient (FR-010)
  - Import reads all 4 density fields (FR-011)
  - Legacy `density_g_per_ml` field is ignored on import (FR-012)
  - Round-trip export→import preserves density data (SC-003)
  - sample_data.json updated with new format
  - Import/export tests pass

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/010-user-friendly-ingredient/spec.md` - FR-010, FR-011, FR-012
- `kitty-specs/010-user-friendly-ingredient/data-model.md` - Import/export format

**Dependencies**:
- **Requires WP01 complete**: Ingredient model must have 4 density fields

**Key Constraints**:
- No backward compatibility - legacy `density_g_per_ml` is ignored
- Export format follows v3.0 JSON schema (from Feature 009)
- Density fields are optional (null if not set)

**Existing Code Reference**:
- `src/services/import_export_service.py` - Export/import functions
- `test_data/sample_data.json` - Sample data file

## Subtasks & Detailed Guidance

### Subtask T018 - Update Ingredient Export [PARALLEL]

- **Purpose**: Include 4 density fields in ingredient export
- **Steps**:
  1. Open `src/services/import_export_service.py`
  2. Locate the ingredient export function (likely `export_ingredients_to_json()` or within `export_all_to_json()`)
  3. Find where ingredient dict is built
  4. Add the 4 density fields:
     ```python
     ingredient_dict = {
         "slug": ingredient.slug,
         "name": ingredient.name,
         "category": ingredient.category,
         "recipe_unit": ingredient.recipe_unit,
         "description": ingredient.description,
         "notes": ingredient.notes,
         # New density fields
         "density_volume_value": ingredient.density_volume_value,
         "density_volume_unit": ingredient.density_volume_unit,
         "density_weight_value": ingredient.density_weight_value,
         "density_weight_unit": ingredient.density_weight_unit,
     }
     ```
  5. Remove any reference to `density_g_per_ml` in export
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes - can proceed alongside T019
- **Notes**: Fields will be null in JSON if not set on ingredient

### Subtask T019 - Update Ingredient Import [PARALLEL]

- **Purpose**: Read 4 density fields from JSON; ignore legacy field
- **Steps**:
  1. In `src/services/import_export_service.py`
  2. Locate the ingredient import function (likely `import_ingredients_from_json()`)
  3. Update to read 4 density fields:
     ```python
     ingredient = Ingredient(
         slug=data.get("slug"),
         name=data.get("name"),
         category=data.get("category"),
         recipe_unit=data.get("recipe_unit"),
         description=data.get("description"),
         notes=data.get("notes"),
         # New density fields (ignore legacy density_g_per_ml)
         density_volume_value=data.get("density_volume_value"),
         density_volume_unit=data.get("density_volume_unit"),
         density_weight_value=data.get("density_weight_value"),
         density_weight_unit=data.get("density_weight_unit"),
     )
     ```
  4. Remove any reference to importing `density_g_per_ml`
  5. Do NOT add automatic conversion of legacy field
- **Files**: `src/services/import_export_service.py`
- **Parallel?**: Yes - can proceed alongside T018
- **Notes**: Legacy field in JSON is simply ignored

### Subtask T020 - Update sample_data.json [PARALLEL]

- **Purpose**: Update sample data to use new density format
- **Steps**:
  1. Open `test_data/sample_data.json`
  2. Find all ingredient entries
  3. Remove any `density_g_per_ml` fields
  4. Add realistic density values for common baking ingredients:
     ```json
     {
       "slug": "all-purpose-flour",
       "name": "All-Purpose Flour",
       "category": "Flour",
       "recipe_unit": "cup",
       "density_volume_value": 1.0,
       "density_volume_unit": "cup",
       "density_weight_value": 4.25,
       "density_weight_unit": "oz",
       ...
     }
     ```
  5. Common density values to include:
     - All-Purpose Flour: 1 cup = 4.25 oz (120g)
     - Granulated Sugar: 1 cup = 7 oz (200g)
     - Brown Sugar (packed): 1 cup = 7.75 oz (220g)
     - Butter: 1 cup = 8 oz (227g)
     - Cocoa Powder: 1 cup = 3 oz (85g)
  6. Some ingredients may not have density (leave fields null)
- **Files**: `test_data/sample_data.json`
- **Parallel?**: Yes - can proceed alongside T018/T019
- **Notes**: Values should be realistic for holiday baking scenario

### Subtask T021 - Add Import/Export Tests

- **Purpose**: Verify density fields work correctly in import/export
- **Steps**:
  1. Open `src/tests/services/test_import_export_service.py`
  2. Add test for export including density:
     ```python
     def test_export_ingredient_includes_density_fields():
         """Export includes all 4 density fields."""
         # Setup ingredient with density
         ingredient = create_test_ingredient_with_density()

         # Export
         result = export_ingredients_to_json()

         # Verify density fields present
         exported = result[0]  # First ingredient
         assert "density_volume_value" in exported
         assert "density_volume_unit" in exported
         assert "density_weight_value" in exported
         assert "density_weight_unit" in exported
     ```
  3. Add test for import reading density:
     ```python
     def test_import_ingredient_reads_density_fields():
         """Import reads all 4 density fields."""
         data = {
             "slug": "test-flour",
             "name": "Test Flour",
             "category": "Flour",
             "density_volume_value": 1.0,
             "density_volume_unit": "cup",
             "density_weight_value": 4.25,
             "density_weight_unit": "oz",
         }

         # Import
         ingredient = import_ingredient_from_dict(data)

         # Verify
         assert ingredient.density_volume_value == 1.0
         assert ingredient.density_volume_unit == "cup"
         assert ingredient.density_weight_value == 4.25
         assert ingredient.density_weight_unit == "oz"
     ```
  4. Add test for ignoring legacy field:
     ```python
     def test_import_ignores_legacy_density_field():
         """Import ignores legacy density_g_per_ml field."""
         data = {
             "slug": "test-flour",
             "name": "Test Flour",
             "category": "Flour",
             "density_g_per_ml": 0.5,  # Legacy field - should be ignored
         }

         # Import
         ingredient = import_ingredient_from_dict(data)

         # Verify density fields are None (not populated from legacy)
         assert ingredient.density_volume_value is None
         assert ingredient.get_density_g_per_ml() is None
     ```
  5. Add round-trip test:
     ```python
     def test_density_round_trip():
         """Export and reimport preserves density."""
         # Create ingredient with density
         original = Ingredient(
             slug="test",
             name="Test",
             category="Flour",
             density_volume_value=1.0,
             density_volume_unit="cup",
             density_weight_value=4.25,
             density_weight_unit="oz",
         )

         # Export
         exported = export_ingredient_to_dict(original)

         # Import
         reimported = import_ingredient_from_dict(exported)

         # Verify density matches
         assert reimported.density_volume_value == original.density_volume_value
         assert reimported.density_volume_unit == original.density_volume_unit
         assert reimported.density_weight_value == original.density_weight_value
         assert reimported.density_weight_unit == original.density_weight_unit
     ```
- **Files**: `src/tests/services/test_import_export_service.py`
- **Notes**: May need to adjust based on actual import/export function signatures

## Test Strategy

- **Test Command**: `pytest src/tests/services/test_import_export_service.py -v -k density`
- **Full Suite**: `pytest src/tests/services/test_import_export_service.py -v`
- **Key Scenarios**:
  - Export with density
  - Export without density (fields null)
  - Import with density
  - Import without density
  - Import with legacy field (ignored)
  - Round-trip preservation

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking sample_data.json format | Update carefully, validate JSON syntax |
| Missing fields in export | Test all 4 fields explicitly |
| Legacy data confusion | Clear documentation that old field ignored |

## Definition of Done Checklist

- [x] T018: Export includes 4 density fields
- [x] T019: Import reads 4 density fields
- [x] T020: sample_data.json updated with new format
- [x] T021: Import/export tests pass (7 tests)
- [x] No references to `density_g_per_ml` in import/export code (import ignores legacy)
- [x] sample_data.json is valid JSON

## Review Guidance

- Verify JSON structure matches v3.0 spec
- Check sample_data.json has realistic density values
- Confirm legacy field truly ignored (not converted)
- Test round-trip with actual file write/read

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-05T03:29:31Z – claude – shell_pid=3015 – lane=doing – Moved to doing
- 2025-12-05T03:45:00Z – claude – shell_pid=3015 – lane=for_review – All subtasks T018-T021 complete; 7 tests pass
