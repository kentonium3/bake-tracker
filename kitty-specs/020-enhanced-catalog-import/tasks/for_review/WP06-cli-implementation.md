---
work_package_id: "WP06"
subtasks:
  - "T040"
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
title: "CLI Implementation"
phase: "Phase 3 - Interface"
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

# Work Package Prompt: WP06 - CLI Implementation

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create CLI entry point with all required flags for catalog import.

**Success Criteria**:
- `python -m src.utils.import_catalog --help` shows all options
- `--mode`, `--entity`, `--dry-run`, `--verbose` flags work correctly
- Exit codes follow spec: 0=success, 1=partial, 2=failure, 3=invalid args
- Output formatting matches user-friendly requirements

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-010 through FR-014
- `kitty-specs/020-enhanced-catalog-import/quickstart.md` - CLI usage examples
- `src/utils/import_export_cli.py` - Pattern reference

**Prerequisites**:
- WP05 complete (`import_catalog()` coordinator function exists)

**Exit Codes**:
| Code | Meaning |
|------|---------|
| 0 | Success (all records processed, may have skips) |
| 1 | Partial success (some records failed) |
| 2 | Complete failure (no records imported, or critical error) |
| 3 | Invalid arguments or file not found |

---

## Subtasks & Detailed Guidance

### T040 - Create import_catalog.py with argparse setup

**Purpose**: Establish CLI entry point with argument parsing.

**Steps**:
1. Create `src/utils/import_catalog.py`
2. Setup argparse:
   ```python
   """
   CLI for catalog import operations.

   Usage:
       python -m src.utils.import_catalog catalog.json
       python -m src.utils.import_catalog catalog.json --mode=augment
       python -m src.utils.import_catalog catalog.json --entity=ingredients
       python -m src.utils.import_catalog catalog.json --dry-run --verbose
   """

   import argparse
   import sys

   from src.services.catalog_import_service import (
       import_catalog,
       CatalogImportError,
   )


   def main():
       parser = argparse.ArgumentParser(
           description="Import catalog data (ingredients, products, recipes)",
           formatter_class=argparse.RawDescriptionHelpFormatter,
           epilog="""
   Examples:
     %(prog)s catalog.json                           # Import all entities
     %(prog)s catalog.json --entity=ingredients      # Import only ingredients
     %(prog)s catalog.json --mode=augment            # Update null fields
     %(prog)s catalog.json --dry-run                 # Preview changes
           """
       )
       parser.add_argument("file", help="Path to catalog JSON file")
       # ... more args added in subsequent subtasks ...

       args = parser.parse_args()
       # ... execution logic ...


   if __name__ == "__main__":
       main()
   ```

**Files**: `src/utils/import_catalog.py`

---

### T041 - Implement --mode flag

**Purpose**: Allow user to select ADD_ONLY or AUGMENT mode.

**Steps**:
1. Add argument:
   ```python
   parser.add_argument(
       "--mode",
       choices=["add", "augment"],
       default="add",
       help="Import mode: add (create new, skip existing) or augment (update null fields)"
   )
   ```
2. Pass to import_catalog: `mode=args.mode`

**Files**: `src/utils/import_catalog.py`

---

### T042 - Implement --entity flag (repeatable)

**Purpose**: Allow user to filter which entity types to import.

**Steps**:
1. Add argument:
   ```python
   parser.add_argument(
       "--entity",
       action="append",
       choices=["ingredients", "products", "recipes"],
       dest="entities",
       help="Entity type to import (can specify multiple times)"
   )
   ```
2. Pass to import_catalog: `entities=args.entities` (will be None if not specified, meaning all)

**Files**: `src/utils/import_catalog.py`

---

### T043 - Implement --dry-run flag

**Purpose**: Preview changes without committing.

**Steps**:
1. Add argument:
   ```python
   parser.add_argument(
       "--dry-run",
       action="store_true",
       help="Preview changes without modifying the database"
   )
   ```
2. Pass to import_catalog: `dry_run=args.dry_run`
3. Adjust output header when dry_run is True

**Files**: `src/utils/import_catalog.py`

---

### T044 - Implement --verbose flag

**Purpose**: Show detailed output for each record decision.

**Steps**:
1. Add argument:
   ```python
   parser.add_argument(
       "-v", "--verbose",
       action="store_true",
       help="Show detailed output for each record"
   )
   ```
2. In output formatting, if verbose:
   - Print each skip with reason
   - Print each error with full details
   - Print each success (if desired, or just count)

**Files**: `src/utils/import_catalog.py`

---

### T045 - Implement exit codes

**Purpose**: Return appropriate exit code based on result.

**Steps**:
1. Determine exit code:
   ```python
   def get_exit_code(result: CatalogImportResult) -> int:
       if result.has_errors:
           # Check if any succeeded
           total_added = sum(
               counts.get("added", 0)
               for counts in result.entity_counts.values()
           )
           if total_added > 0:
               return 1  # Partial success
           else:
               return 2  # Complete failure
       return 0  # Success
   ```
2. In main():
   ```python
   try:
       result = import_catalog(...)
       print(result.get_summary())
       sys.exit(get_exit_code(result))
   except FileNotFoundError as e:
       print(f"Error: {e}", file=sys.stderr)
       sys.exit(3)
   except CatalogImportError as e:
       print(f"Error: {e}", file=sys.stderr)
       sys.exit(3)
   except Exception as e:
       print(f"Unexpected error: {e}", file=sys.stderr)
       sys.exit(2)
   ```

**Files**: `src/utils/import_catalog.py`

---

### T046 - Format and print CatalogImportResult summary

**Purpose**: Display user-friendly import results.

**Steps**:
1. Ensure `CatalogImportResult.get_summary()` produces good output
2. Add dry-run header:
   ```python
   if args.dry_run:
       print("=" * 60)
       print("DRY RUN - No changes will be made")
       print("=" * 60)
   ```
3. Print result summary
4. In verbose mode, print warnings and errors with full detail

**Example Output**:
```
============================================================
Catalog Import Summary
============================================================
Mode: add
Dry Run: No

Ingredients:
  Added:    12
  Skipped:   3 (already exist)
  Failed:    0

Products:
  Added:     8
  Skipped:   5 (already exist)
  Failed:    1

Recipes:
  Added:     6
  Skipped:   2 (already exist)
  Failed:    0

Errors:
  - products: Organic Vanilla (organic_vanilla)
    Missing ingredient 'organic_vanilla'. Import the ingredient first.

============================================================
```

**Files**: `src/utils/import_catalog.py`, `src/services/catalog_import_service.py`

---

### T047 - Test: test_cli_add_mode [P]

**Purpose**: Verify full CLI flow in add mode.

**Steps**:
1. Create temp catalog file with test data
2. Run CLI via subprocess or by calling main() directly
3. Verify exit code 0
4. Verify expected records in database

**Files**: `src/tests/test_catalog_import_service.py`

---

### T048 - Test: test_cli_dry_run [P]

**Purpose**: Verify CLI dry-run produces output but no changes.

**Steps**:
1. Create temp catalog file
2. Run CLI with --dry-run
3. Capture output, verify it shows adds
4. Verify database unchanged

**Files**: `src/tests/test_catalog_import_service.py`

---

### T049 - Test: test_cli_verbose

**Purpose**: Verify verbose mode shows details.

**Steps**:
1. Create catalog with mix of valid/invalid records
2. Run CLI with --verbose
3. Capture output
4. Verify individual record decisions are shown

**Files**: `src/tests/test_catalog_import_service.py`

---

## Test Strategy

**Required Tests**:
- `test_cli_add_mode` - Full flow
- `test_cli_dry_run` - Dry-run behavior
- `test_cli_verbose` - Verbose output

**Commands**:
```bash
# Manual testing
python -m src.utils.import_catalog --help
python -m src.utils.import_catalog test_data/sample_catalog.json --dry-run

# Automated tests
pytest src/tests/test_catalog_import_service.py -k "cli" -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Wrong exit code | Test each exit code scenario |
| Output formatting breaks | Use consistent template in get_summary() |
| --entity not repeatable | Use action="append" in argparse |

---

## Definition of Done Checklist

- [ ] T040: CLI created with argparse
- [ ] T041: --mode flag working
- [ ] T042: --entity flag working (repeatable)
- [ ] T043: --dry-run flag working
- [ ] T044: --verbose flag working
- [ ] T045: Exit codes correct (0/1/2/3)
- [ ] T046: Summary output formatted correctly
- [ ] T047: `test_cli_add_mode` passes
- [ ] T048: `test_cli_dry_run` passes
- [ ] T049: `test_cli_verbose` passes
- [ ] `python -m src.utils.import_catalog --help` works
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. --help shows all options with descriptions
2. Exit codes match spec
3. Dry-run header clearly visible
4. Error messages written to stderr
5. --entity can be specified multiple times

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T03:01:42Z – claude – shell_pid=56445 – lane=doing – Started implementation
- 2025-12-15T03:05:31Z – claude – shell_pid=56445 – lane=for_review – Ready for review
