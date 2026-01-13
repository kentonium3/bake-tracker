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
title: "Schema Validation Service"
phase: "Phase 0 - Foundational"
lane: "done"
assignee: ""
agent: "codex"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Schema Validation Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create a reusable JSON schema validation service that validates import file structure before database operations begin.

**Success Criteria**:
- `schema_validation_service.py` exists with all entity validators
- Validators return structured `ValidationResult` with errors and warnings
- Malformed JSON files produce clear error messages with record numbers
- Unit tests cover happy path and error cases for each validator
- Service integrates cleanly with existing import workflow

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US4 - Pre-Import Schema Validation)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`
- Data Model: `kitty-specs/051-import-export-ui-rationalization/data-model.md` (ValidationResult dataclass)
- Constitution: `.kittify/memory/constitution.md`

**Architecture Constraints**:
- Service layer only (no UI imports)
- Return dataclasses, not exceptions (let caller decide how to present)
- Follow existing service patterns in `src/services/`

**Existing Patterns**:
- `src/services/import_export_service.py` - ImportResult pattern
- `src/services/catalog_import_service.py` - VALID_ENTITIES, entity validation

## Subtasks & Detailed Guidance

### Subtask T001 - Create schema_validation_service.py with dataclasses
- **Purpose**: Establish the validation result structure used by all validators
- **Steps**:
  1. Create `src/services/schema_validation_service.py`
  2. Define `ValidationError` dataclass with fields: `field`, `message`, `record_number`, `expected`, `actual`
  3. Define `ValidationWarning` dataclass with fields: `field`, `message`, `record_number`
  4. Define `ValidationResult` dataclass with fields: `valid`, `errors`, `warnings` and helper properties
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: Yes
- **Notes**: See `data-model.md` for exact field definitions

### Subtask T002 - Implement validate_supplier_schema()
- **Purpose**: Validate supplier entity records
- **Steps**:
  1. Check `suppliers` array exists and is a list
  2. For each record, validate:
     - `name` (required, non-empty string)
     - `slug` (optional, if present must be valid slug format)
     - `contact_info` (optional string)
     - `notes` (optional string)
  3. Return ValidationResult with all errors/warnings
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: Yes
- **Notes**: Slug format: lowercase alphanumeric with hyphens

### Subtask T003 - Implement validate_ingredient_schema()
- **Purpose**: Validate ingredient entity records
- **Steps**:
  1. Check `ingredients` array exists and is a list
  2. For each record, validate:
     - `display_name` (required, non-empty string)
     - `category` (optional string)
     - `package_unit` (optional, if present must be in MEASUREMENT_UNITS)
     - `package_unit_quantity` (optional, if present must be positive number)
     - `notes` (optional string)
  3. Warn on unexpected fields
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: Yes
- **Notes**: Reference `src/utils/constants.py` for valid units

### Subtask T004 - Implement validate_product_schema()
- **Purpose**: Validate product entity records with FK references
- **Steps**:
  1. Check `products` array exists and is a list
  2. For each record, validate:
     - `display_name` (required, non-empty string)
     - `ingredient_slug` (required, non-empty string - FK reference)
     - `supplier_slug` (optional string - FK reference)
     - `brand` (optional string)
     - `package_unit` (optional, valid unit)
     - `unit_cost` (optional, if present must be non-negative decimal)
  3. Note: FK existence validation happens at import time, not schema validation
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: Yes
- **Notes**: Schema validation checks structure, not FK existence

### Subtask T005 - Implement validate_recipe_schema()
- **Purpose**: Validate recipe entity records with nested ingredients
- **Steps**:
  1. Check `recipes` array exists and is a list
  2. For each record, validate:
     - `name` (required, non-empty string)
     - `category` (optional string)
     - `yield_quantity` (optional positive number)
     - `yield_unit` (optional string)
     - `ingredients` (optional array, if present validate each item has `ingredient_name`, `quantity`, `unit`)
     - `components` (optional array for nested recipes)
  3. Validate nested ingredient structure
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: Yes
- **Notes**: Recipes can reference other recipes via components[]

### Subtask T006 - Implement validate_import_file() dispatcher
- **Purpose**: Route validation to appropriate entity validators based on file content
- **Steps**:
  1. Accept parsed JSON data (dict)
  2. Detect which entity arrays are present
  3. Call appropriate validators for each detected entity
  4. Merge all ValidationResults into single result
  5. Handle multi-entity files (validate all present entities)
- **Files**: `src/services/schema_validation_service.py`
- **Parallel?**: No (depends on T001-T005)
- **Notes**: This is the main entry point for import validation

### Subtask T007 - Create test_schema_validation_service.py
- **Purpose**: Unit test coverage for validation service
- **Steps**:
  1. Create `src/tests/test_schema_validation_service.py`
  2. Test valid files return `ValidationResult(valid=True)`
  3. Test missing required fields return appropriate errors
  4. Test wrong types return errors with expected vs actual
  5. Test unexpected fields generate warnings (not errors)
  6. Test multi-entity files validate all entities
  7. Test empty arrays are valid (0 records)
- **Files**: `src/tests/test_schema_validation_service.py`
- **Parallel?**: Yes (once validators exist)
- **Notes**: Use pytest fixtures for test data; aim for >80% coverage

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Inconsistent validation rules | Review existing import logic in `catalog_import_service.py` for field requirements |
| Missing edge cases | Include tests for empty data, null values, wrong types |
| Performance with large files | Validate lazily; stop on first N errors if configurable |

## Definition of Done Checklist

- [ ] `src/services/schema_validation_service.py` created with all validators
- [ ] ValidationResult, ValidationError, ValidationWarning dataclasses defined
- [ ] All entity validators implemented (supplier, ingredient, product, recipe)
- [ ] `validate_import_file()` dispatcher routes to correct validators
- [ ] `src/tests/test_schema_validation_service.py` exists with comprehensive tests
- [ ] All tests pass: `./run-tests.sh src/tests/test_schema_validation_service.py -v`
- [ ] Code follows existing service patterns (no UI imports)

## Review Guidance

**Key checkpoints**:
1. Verify ValidationResult structure matches `data-model.md`
2. Verify error messages are actionable (include record number, field, expected/actual)
3. Verify unexpected fields generate warnings, not errors
4. Verify unit tests cover all validators
5. Run `./run-tests.sh src/tests/test_schema_validation_service.py -v` to confirm

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:14:44Z – codex – lane=doing – Started implementation
- 2026-01-13T18:24:26Z – codex – lane=for_review – Ready for review
- 2026-01-13T20:56:52Z – codex – lane=done – Code review APPROVED by claude - All tests pass (51 schema validation tests), validators for suppliers/ingredients/products/recipes/materials implemented, FR-012 compliance
