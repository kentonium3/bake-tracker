---
work_package_id: "WP05"
subtasks:
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "Coordinator and Dry-Run"
phase: "Phase 2 - Features"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "56445"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Coordinator and Dry-Run

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement `import_catalog()` coordinator, `validate_catalog_file()`, and dry-run mode.

**Success Criteria**:
- `validate_catalog_file()` detects format and returns parsed data
- `import_catalog()` dispatches to entity functions in correct order
- Entity filter allows importing specific entity types only
- Dry-run mode validates everything but commits nothing
- Tests verify format detection, ordering, and dry-run behavior

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-002, FR-007, FR-027
- `kitty-specs/020-enhanced-catalog-import/research.md` - Format detection logic

**Prerequisites**:
- WP01-WP04 complete (all entity import functions with both modes)

**Architectural Constraints**:
1. Format detection: `catalog_version` -> catalog import, `version: "3.x"` -> error with guidance
2. Dependency order: ingredients -> products -> recipes
3. Dry-run: perform full validation, rollback before return

---

## Subtasks & Detailed Guidance

### T031 - Implement validate_catalog_file()

**Purpose**: Load JSON file and validate format.

**Steps**:
1. Define function:
   ```python
   def validate_catalog_file(file_path: str) -> Dict:
       """
       Load and validate a catalog file.

       Returns:
           Parsed catalog data dict

       Raises:
           FileNotFoundError: If file doesn't exist
           CatalogImportError: If format invalid
       """
   ```
2. Implementation:
   ```python
   from pathlib import Path

   class CatalogImportError(Exception):
       """Raised when catalog import fails."""
       pass

   def validate_catalog_file(file_path: str) -> Dict:
       path = Path(file_path)
       if not path.exists():
           raise FileNotFoundError(f"File not found: {file_path}")

       try:
           with open(path, "r", encoding="utf-8") as f:
               data = json.load(f)
       except json.JSONDecodeError as e:
           raise CatalogImportError(f"Invalid JSON: {e}")

       if "catalog_version" in data:
           if data["catalog_version"] != "1.0":
               raise CatalogImportError(
                   f"Unsupported catalog version: {data['catalog_version']}. Expected 1.0"
               )
           return data
       elif "version" in data:
           raise CatalogImportError(
               "This appears to be a unified import file (v3.x format). "
               "Use 'Import Data...' instead of 'Import Catalog...'"
           )
       else:
           raise CatalogImportError(
               "Unrecognized file format. Expected 'catalog_version' field."
           )
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T032 - Implement import_catalog() coordinator function

**Purpose**: Main entry point that orchestrates entity imports.

**Steps**:
1. Define function:
   ```python
   def import_catalog(
       file_path: str,
       mode: str = "add",
       entities: Optional[List[str]] = None,
       dry_run: bool = False,
       session: Optional[Session] = None
   ) -> CatalogImportResult:
   ```
2. Implementation flow:
   ```python
   data = validate_catalog_file(file_path)

   if session is not None:
       return _import_catalog_impl(data, mode, entities, dry_run, session)
   with session_scope() as session:
       result = _import_catalog_impl(data, mode, entities, dry_run, session)
       if dry_run:
           session.rollback()
       return result
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T033 - Process entities in dependency order

**Purpose**: Ensure FK references exist when needed.

**Steps**:
1. In `_import_catalog_impl`:
   ```python
   result = CatalogImportResult()
   result.dry_run = dry_run
   result.mode = mode

   # Order matters: ingredients first, then products, then recipes
   if entities is None or "ingredients" in entities:
       if "ingredients" in data:
           ing_result = import_ingredients(data["ingredients"], mode, dry_run, session)
           result.merge(ing_result)

   if entities is None or "products" in entities:
       if "products" in data:
           prod_result = import_products(data["products"], mode, dry_run, session)
           result.merge(prod_result)

   if entities is None or "recipes" in entities:
       if "recipes" in data:
           recipe_result = import_recipes(data["recipes"], mode, dry_run, session)
           result.merge(recipe_result)

   return result
   ```
2. Add `merge()` method to CatalogImportResult if not already present

**Files**: `src/services/catalog_import_service.py`

---

### T034 - Implement entity filter parameter

**Purpose**: Allow importing only specific entity types.

**Steps**:
1. Parameter already defined: `entities: Optional[List[str]] = None`
2. Validation:
   ```python
   VALID_ENTITIES = {"ingredients", "products", "recipes"}
   if entities:
       invalid = set(entities) - VALID_ENTITIES
       if invalid:
           raise CatalogImportError(f"Invalid entity types: {invalid}")
   ```
3. Filter logic shown in T033 (`if entities is None or X in entities`)

**Files**: `src/services/catalog_import_service.py`

---

### T035 - Implement dry-run mode

**Purpose**: Validate and preview without committing changes.

**Steps**:
1. Dry-run flag propagated to entity functions
2. In coordinator, after all processing:
   ```python
   if dry_run:
       session.rollback()  # Discard all changes
   # session_scope will commit if not rolled back
   ```
3. Result object has `dry_run = True` flag for display purposes
4. Entity functions already handle dry_run in their signatures

**Important**: Dry-run should produce identical counts to actual run. Verify this in tests.

**Files**: `src/services/catalog_import_service.py`

---

### T036 - Test: test_validate_catalog_file_format_detection [P]

**Purpose**: Verify format detection logic.

**Steps**:
1. Create temp file with `catalog_version: "1.0"` - should succeed
2. Create temp file with `version: "3.3"` - should raise error mentioning unified import
3. Create temp file with neither - should raise unrecognized format error
4. Create invalid JSON - should raise parse error

**Files**: `src/tests/test_catalog_import_service.py`

---

### T037 - Test: test_import_catalog_dependency_order [P]

**Purpose**: Verify entities processed in correct order.

**Steps**:
1. Create catalog with product referencing ingredient in same file
2. Call `import_catalog()` - should succeed because ingredients processed first
3. Verify both ingredient and product created

**Files**: `src/tests/test_catalog_import_service.py`

---

### T038 - Test: test_dry_run_no_commit

**Purpose**: Verify dry-run makes no database changes.

**Steps**:
1. Get initial ingredient count
2. Create catalog with 5 new ingredients
3. Call `import_catalog(file, dry_run=True)`
4. Assert result shows 5 added
5. Query database, assert ingredient count unchanged
6. Call `import_catalog(file, dry_run=False)`
7. Query database, assert ingredient count increased by 5

**Files**: `src/tests/test_catalog_import_service.py`

---

### T039 - Test: test_partial_success

**Purpose**: Verify valid records committed even when some fail.

**Steps**:
1. Create catalog with:
   - 2 valid ingredients
   - 1 product referencing non-existent ingredient
2. Call `import_catalog()`
3. Assert ingredients added == 2
4. Assert products failed == 1
5. Query database, verify 2 ingredients exist

**Files**: `src/tests/test_catalog_import_service.py`

---

## Test Strategy

**Required Tests**:
- `test_validate_catalog_file_format_detection` - Format detection
- `test_import_catalog_dependency_order` - Ordering
- `test_dry_run_no_commit` - Dry-run behavior
- `test_partial_success` - Partial commit

**Commands**:
```bash
pytest src/tests/test_catalog_import_service.py -k "catalog or dry_run or partial" -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dry-run commits accidentally | Explicit rollback call, verified by test |
| Dry-run counts differ from actual | Test verifies counts match |
| File encoding issues | Specify encoding="utf-8" in open() |

---

## Definition of Done Checklist

- [ ] T031: `validate_catalog_file()` implemented with format detection
- [ ] T032: `import_catalog()` coordinator implemented
- [ ] T033: Dependency order: ingredients -> products -> recipes
- [ ] T034: Entity filter parameter working
- [ ] T035: Dry-run mode rollbacks correctly
- [ ] T036: `test_validate_catalog_file_format_detection` passes
- [ ] T037: `test_import_catalog_dependency_order` passes
- [ ] T038: `test_dry_run_no_commit` passes
- [ ] T039: `test_partial_success` passes
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. Format detection provides helpful error for unified import files
2. Dependency order ensures FK refs exist
3. Dry-run rollback happens AFTER result is built
4. Entity filter validates input
5. merge() correctly combines entity counts

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T02:57:50Z – claude – shell_pid=56445 – lane=doing – Started implementation
- 2025-12-15T03:00:17Z – claude – shell_pid=56445 – lane=for_review – Ready for review
