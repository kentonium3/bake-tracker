---
work_package_id: WP05
title: Secondary Service Updates
lane: "planned"
dependencies: [WP01]
base_branch: 094-core-api-standardization-WP01
base_commit: 4f0333494559e2a44d97431f1ae745eda905680c
created_at: '2026-02-03T16:39:31.107148+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase 2 - Core Services
assignee: ''
agent: "codex"
shell_pid: "51956"
review_status: "has_feedback"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 - Secondary Service Updates

## Objectives & Success Criteria

- Update remaining services with Optional returns to raise exceptions
- Services: composition, supplier, recipient, unit, material_catalog
- Lower risk - these are less UI-facing or internal services

## Context & Constraints

- **Depends on WP01**: Exception types must be available
- These services have fewer call sites - lower risk
- `supplier_service.py` already has `get_supplier_or_raise()` pattern
- `material_catalog_service.py` is internal - mostly used by other services

## Subtasks & Detailed Guidance

### Subtask T026 - Update composition_service.py get functions

**Purpose**: Convert composition lookups to use exceptions.

**Functions to update**:
- `get_composition_by_id()` (line 242 class, line 1849 wrapper)
- `get_composition()` (line 1854 wrapper - calls get_composition_by_id)

**Steps**:
1. Import `CompositionNotFoundById` from exceptions
2. Update class method to raise exception
3. Update return types

**Files**: `src/services/composition_service.py`

### Subtask T027 - Update supplier_service.py get functions

**Purpose**: Convert supplier lookups to use exceptions.

**Functions to update**:
- `get_supplier()` (line 296) -> raise `SupplierNotFoundError`
- `get_supplier_by_uuid()` (line 328) -> may need new exception or use existing

**Note**: `get_supplier_or_raise()` already exists (line 703) - use it as the model pattern.

**Steps**:
1. Update `get_supplier()` to behave like `get_supplier_or_raise()`
2. Update `get_supplier_by_uuid()` similarly
3. Consider if `get_supplier_or_raise()` can be deprecated

**Files**: `src/services/supplier_service.py`

### Subtask T028 - Update recipient_service.py get_recipient_by_name()

**Purpose**: Convert recipient lookup to use exceptions.

**Function to update**:
- `get_recipient_by_name()` (line 184) -> needs new exception or use generic

**Steps**:
1. Create `RecipientNotFoundByName` exception if not exists (or use generic `NotFoundError`)
2. Update function to raise exception
3. Update return type

**Files**: `src/services/recipient_service.py`, possibly `src/services/exceptions.py`

### Subtask T029 - Update unit_service.py get_unit_by_code()

**Purpose**: Convert unit lookup to use exceptions.

**Function to update**:
- `get_unit_by_code()` (line 117) -> raise `UnitNotFoundByCode`

**Steps**:
1. Import `UnitNotFoundByCode` from exceptions
2. Update function to raise exception
3. Update return type

**Files**: `src/services/unit_service.py`

### Subtask T030 - Update material_catalog_service.py get functions

**Purpose**: Convert material catalog lookups to use exceptions.

**Functions to update**:
- `get_category()` (line 269) -> raise `MaterialCategoryNotFound`
- `get_subcategory()` (line 477) -> raise `MaterialSubcategoryNotFound`
- `get_material()` (line 720) -> raise `MaterialNotFound`
- `get_product()` (line 1087) -> raise `MaterialProductNotFound`

**Steps**:
1. Import exception types from exceptions
2. Update each function to raise appropriate exception
3. Update return types

**Files**: `src/services/material_catalog_service.py`

### Subtask T031 - Update calling code for all secondary services

**Purpose**: All code that calls these functions must handle exceptions.

**Steps**:
1. Find all call sites for each function
2. Update to use try/except

**Key files to check**:
- Composition usages in assembly services
- Supplier usages in purchase services
- Material catalog usages in material services

**Files**: Multiple files

### Subtask T032 - Update tests for secondary services

**Purpose**: Tests should expect exceptions for not-found cases.

**Files**:
- `src/tests/services/test_composition_service.py`
- `src/tests/services/test_supplier_service.py`
- `src/tests/services/test_recipient_service.py`
- `src/tests/services/test_unit_service.py`
- `src/tests/services/test_material_catalog_service.py`

## Test Strategy

Run affected tests:
```bash
./run-tests.sh src/tests/services/test_composition_service.py -v
./run-tests.sh src/tests/services/test_supplier_service.py -v
./run-tests.sh src/tests/services/test_unit_service.py -v
```

## Risks & Mitigations

- **Lower risk services**: These are less UI-facing
- **Internal services**: material_catalog is mostly internal
- **Existing patterns**: supplier_service has _or_raise pattern to follow

## Definition of Done Checklist

- [ ] composition_service get functions raise exceptions
- [ ] supplier_service get functions raise exceptions
- [ ] recipient_service `get_recipient_by_name()` raises exception
- [ ] unit_service `get_unit_by_code()` raises exception
- [ ] material_catalog_service get functions raise exceptions
- [ ] All calling code updated
- [ ] Tests updated
- [ ] All tests pass

## Review Guidance

- Verify exception types match lookup field (ById vs ByCode vs ByName)
- Check supplier service consistency with existing _or_raise pattern
- Ensure material catalog internal callers are updated

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-03T16:56:07Z – unknown – shell_pid=5484 – lane=for_review – All subtasks T026-T032 complete. Exception pattern applied to secondary services. Tests pass.
- 2026-02-03T22:32:37Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:33:39Z – codex – shell_pid=51956 – lane=planned – Moved to planned
- 2026-02-03T22:39:29Z – claude – shell_pid=34540 – lane=doing – Started implementation via workflow command
- 2026-02-03T22:47:45Z – claude – shell_pid=34540 – lane=for_review – Ready for review: Exception pattern applied to secondary services, all 3493 tests pass
- 2026-02-03T22:48:47Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:49:31Z – codex – shell_pid=51956 – lane=planned – Moved to planned
