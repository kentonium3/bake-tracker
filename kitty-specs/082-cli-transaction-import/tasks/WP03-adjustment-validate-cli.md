---
work_package_id: WP03
title: Adjustment & Validate CLI
lane: planned
dependencies: []
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 2 - CLI Commands
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-29T04:45:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Adjustment & Validate CLI

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP01
```

**Depends on WP01** - must branch from WP01's completed work.

**Can run in parallel with WP02** - both depend only on WP01.

---

## Objectives & Success Criteria

**Goal**: Add `import-adjustments` and `validate-import` commands to CLI.

**Success Criteria**:
- [ ] `app import-adjustments adjustments.json` imports adjustment data
- [ ] `app validate-import file.json --type=purchase` validates without database changes
- [ ] Both commands support `--dry-run`, `--json`, `--resolve-mode` flags
- [ ] validate-import supports `--type` flag for purchase/adjustment
- [ ] CLI help text documents all flags

## Context & Constraints

**Files to Modify**:
- `src/utils/import_export_cli.py` - Add parsers, handlers, and dispatch

**Pattern Reference**: Copy from WP02's import-purchases implementation.

**Key Insight**: validate-import is essentially a wrapper around the appropriate import function with dry_run=True always.

---

## Subtasks & Detailed Guidance

### Subtask T007 – Add import-adjustments CLI parser

**Purpose**: Define command-line arguments for import-adjustments command.

**Steps**:

1. Add parser after import-purchases parser:
   ```python
   # F083: Import adjustments command
   import_adjustments_parser = subparsers.add_parser(
       "import-adjustments",
       help="Import inventory adjustments from JSON file"
   )
   import_adjustments_parser.add_argument(
       "input_file",
       help="JSON file with inventory adjustments"
   )
   import_adjustments_parser.add_argument(
       "-d", "--dry-run",
       dest="dry_run",
       action="store_true",
       help="Validate without modifying database"
   )
   import_adjustments_parser.add_argument(
       "--json",
       dest="json_output",
       action="store_true",
       help="Output results as JSON (for AI workflows)"
   )
   import_adjustments_parser.add_argument(
       "--resolve-mode",
       dest="resolve_mode",
       choices=["auto", "strict"],
       default="auto",
       help="FK resolution: 'auto' (default) uses best-match, 'strict' fails on unresolved"
   )
   import_adjustments_parser.epilog = (
       "Example: import-adjustments inventory_count.json --dry-run --json"
   )
   ```

**Files**: `src/utils/import_export_cli.py`

**Validation**: `app import-adjustments --help` shows all flags

---

### Subtask T008 – Implement import_adjustments_cmd() handler

**Purpose**: Implement handler that calls transaction_import_service.import_adjustments().

**Steps**:

1. Add handler function (copy pattern from import_purchases_cmd):
   ```python
   def import_adjustments_cmd(args) -> int:
       """Handle import-adjustments command.

       Args:
           args: Parsed arguments with input_file, dry_run, json_output, resolve_mode

       Returns:
           0 on success, 1 on failure
       """
       from src.services.transaction_import_service import import_adjustments

       input_file = args.input_file
       dry_run = args.dry_run
       json_output = args.json_output
       strict_mode = args.resolve_mode == "strict"

       # Validate file exists
       if not Path(input_file).exists():
           if json_output:
               print(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
           else:
               print(f"Error: File not found: {input_file}")
           return 1

       try:
           result = import_adjustments(
               file_path=input_file,
               dry_run=dry_run,
               strict_mode=strict_mode,
           )

           if json_output:
               output = result_to_json(result)
               output["dry_run"] = dry_run
               output["resolve_mode"] = args.resolve_mode
               print(json.dumps(output, indent=2))
           else:
               print(result.get_summary())
               if dry_run:
                   print("\n[DRY RUN] No changes committed to database.")

           return 0 if result.failed == 0 else 1

       except Exception as e:
           if json_output:
               print(json.dumps({"success": False, "error": str(e)}))
           else:
               print(f"Error: {e}")
           return 1
   ```

2. Add dispatch:
   ```python
   elif args.command == "import-adjustments":
       return import_adjustments_cmd(args)
   ```

**Files**: `src/utils/import_export_cli.py`

---

### Subtask T009 – Add validate-import CLI parser

**Purpose**: Define command for schema validation without database changes.

**Steps**:

1. Add parser:
   ```python
   # F083: Validate import command
   validate_import_parser = subparsers.add_parser(
       "validate-import",
       help="Validate import file schema without modifying database"
   )
   validate_import_parser.add_argument(
       "input_file",
       help="JSON file to validate"
   )
   validate_import_parser.add_argument(
       "-t", "--type",
       dest="import_type",
       choices=["purchase", "adjustment"],
       required=True,
       help="Type of import file: 'purchase' or 'adjustment'"
   )
   validate_import_parser.add_argument(
       "--json",
       dest="json_output",
       action="store_true",
       help="Output validation results as JSON"
   )
   validate_import_parser.add_argument(
       "--resolve-mode",
       dest="resolve_mode",
       choices=["auto", "strict"],
       default="auto",
       help="FK resolution mode for validation"
   )
   validate_import_parser.epilog = (
       "Example: validate-import receipt.json --type=purchase --json"
   )
   ```

**Files**: `src/utils/import_export_cli.py`

**Validation**: `app validate-import --help` shows --type flag as required

---

### Subtask T010 – Implement validate_import_cmd() handler

**Purpose**: Validation-only handler that always uses dry_run=True.

**Steps**:

1. Add handler:
   ```python
   def validate_import_cmd(args) -> int:
       """Handle validate-import command.

       Validates import file schema without database changes.
       Internally uses import with dry_run=True.

       Args:
           args: Parsed arguments with input_file, import_type, json_output, resolve_mode

       Returns:
           0 if validation passes, 1 if validation fails
       """
       from src.services.transaction_import_service import (
           import_purchases,
           import_adjustments,
       )

       input_file = args.input_file
       import_type = args.import_type
       json_output = args.json_output
       strict_mode = args.resolve_mode == "strict"

       # Validate file exists
       if not Path(input_file).exists():
           if json_output:
               print(json.dumps({"success": False, "error": f"File not found: {input_file}"}))
           else:
               print(f"Error: File not found: {input_file}")
           return 1

       try:
           # Route to appropriate import function with dry_run=True
           if import_type == "purchase":
               result = import_purchases(
                   file_path=input_file,
                   dry_run=True,  # Always dry-run for validation
                   strict_mode=strict_mode,
               )
           else:  # adjustment
               result = import_adjustments(
                   file_path=input_file,
                   dry_run=True,  # Always dry-run for validation
                   strict_mode=strict_mode,
               )

           if json_output:
               output = result_to_json(result)
               output["validation_only"] = True
               output["import_type"] = import_type
               output["resolve_mode"] = args.resolve_mode
               print(json.dumps(output, indent=2))
           else:
               if result.failed == 0:
                   print(f"✓ Validation passed for {import_type} file")
                   print(f"  Records: {result.total_records}")
                   if result.warnings:
                       print(f"  Warnings: {len(result.warnings)}")
               else:
                   print(f"✗ Validation failed for {import_type} file")
                   print(result.get_summary())

           return 0 if result.failed == 0 else 1

       except Exception as e:
           if json_output:
               print(json.dumps({"success": False, "error": str(e)}))
           else:
               print(f"Validation error: {e}")
           return 1
   ```

2. Add dispatch:
   ```python
   elif args.command == "validate-import":
       return validate_import_cmd(args)
   ```

**Files**: `src/utils/import_export_cli.py`

**Validation**:
- validate-import always performs dry-run (no database changes)
- Output clearly indicates "validation only" mode

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Confusion between --dry-run and validate-import | validate-import doesn't have --dry-run flag (always dry) |
| Wrong import function called | Clear if/else based on --type flag |

---

## Definition of Done Checklist

- [ ] T007: import-adjustments parser added
- [ ] T008: import_adjustments_cmd() handler implemented
- [ ] T009: validate-import parser added with --type flag
- [ ] T010: validate_import_cmd() handler implemented
- [ ] All dispatch cases wired
- [ ] `app import-adjustments --help` works
- [ ] `app validate-import --help` works
- [ ] No linting errors

---

## Review Guidance

**Reviewers should verify**:
1. validate-import always uses dry_run=True (no database changes ever)
2. --type flag correctly routes to purchase vs adjustment
3. JSON output includes validation_only=true for validate-import
4. Error messages are clear about what failed validation

---

## Activity Log

- 2026-01-29T04:45:00Z – system – lane=planned – Prompt created.
