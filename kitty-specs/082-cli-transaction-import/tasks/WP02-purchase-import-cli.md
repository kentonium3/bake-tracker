---
work_package_id: WP02
title: Purchase Import CLI
lane: planned
dependencies: []
subtasks:
- T004
- T005
- T006
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

# Work Package Prompt: WP02 – Purchase Import CLI

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Depends on WP01** - must branch from WP01's completed work.

---

## Objectives & Success Criteria

**Goal**: Add `import-purchases` command to CLI that wraps `transaction_import_service.import_purchases()`.

**Success Criteria**:
- [ ] `app import-purchases purchases.json` imports purchase data
- [ ] `--dry-run` flag validates without database changes
- [ ] `--json` flag outputs structured JSON
- [ ] `--resolve-mode=auto|strict` controls FK resolution behavior
- [ ] CLI help text documents all flags
- [ ] Command follows catalog-import pattern exactly

## Context & Constraints

**Files to Modify**:
- `src/utils/import_export_cli.py` - Add parser, handler, and dispatch

**Pattern Reference**: Study existing `catalog-import` command (lines ~2470-2495) for exact pattern.

**Key Constraint**: CLI is thin wrapper - ALL business logic in service layer.

---

## Subtasks & Detailed Guidance

### Subtask T004 – Add import-purchases CLI parser

**Purpose**: Define command-line arguments for import-purchases command.

**Steps**:

1. Open `src/utils/import_export_cli.py`

2. Find the subparsers section (around line ~2500, after catalog commands)

3. Add parser definition following catalog-import pattern:
   ```python
   # F083: Import purchases command
   import_purchases_parser = subparsers.add_parser(
       "import-purchases",
       help="Import purchase transactions from JSON file"
   )
   import_purchases_parser.add_argument(
       "input_file",
       help="JSON file with purchase transactions"
   )
   import_purchases_parser.add_argument(
       "-d", "--dry-run",
       dest="dry_run",
       action="store_true",
       help="Validate without modifying database"
   )
   import_purchases_parser.add_argument(
       "--json",
       dest="json_output",
       action="store_true",
       help="Output results as JSON (for AI workflows)"
   )
   import_purchases_parser.add_argument(
       "--resolve-mode",
       dest="resolve_mode",
       choices=["auto", "strict"],
       default="auto",
       help="FK resolution: 'auto' (default) uses best-match, 'strict' fails on unresolved"
   )
   import_purchases_parser.epilog = (
       "Example: import-purchases receipt.json --dry-run --json"
   )
   ```

**Files**: `src/utils/import_export_cli.py`

**Validation**:
- `app import-purchases --help` shows all flags
- No syntax errors in parser definition

---

### Subtask T005 – Implement import_purchases_cmd() handler

**Purpose**: Implement the handler function that calls the service layer.

**Steps**:

1. Find the command handler section (around line ~1000-1500)

2. Add handler function:
   ```python
   def import_purchases_cmd(args) -> int:
       """Handle import-purchases command.

       Args:
           args: Parsed arguments with input_file, dry_run, json_output, resolve_mode

       Returns:
           0 on success, 1 on failure
       """
       from src.services.transaction_import_service import import_purchases

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
           result = import_purchases(
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

3. Add necessary imports at top of file if not present:
   ```python
   from pathlib import Path
   import json
   ```

**Files**: `src/utils/import_export_cli.py`

**Validation**:
- Handler correctly maps CLI args to service parameters
- JSON output includes all required fields
- Error handling is consistent

---

### Subtask T006 – Wire import-purchases to dispatch

**Purpose**: Connect the parser to the handler in main dispatch.

**Steps**:

1. Find the main dispatch section (around line ~2600-2700, the big if/elif chain)

2. Add dispatch case:
   ```python
   elif args.command == "import-purchases":
       return import_purchases_cmd(args)
   ```

3. Ensure it's placed with other import commands for consistency

**Files**: `src/utils/import_export_cli.py`

**Validation**:
- Running `app import-purchases test.json` reaches the handler
- No dispatch conflicts with existing commands

---

## Test Strategy (Manual Verification)

Create a test purchase file:
```json
{
    "schema_version": "4.0",
    "import_type": "purchases",
    "created_at": "2026-01-29T00:00:00Z",
    "source": "test",
    "purchases": []
}
```

Test commands:
```bash
# Should parse and show help
app import-purchases --help

# Should validate empty file (dry-run)
app import-purchases test.json --dry-run

# Should output JSON
app import-purchases test.json --dry-run --json

# Should use strict mode
app import-purchases test.json --dry-run --resolve-mode=strict
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Args namespace mismatch | Use consistent dest names with parser |
| Missing json import | Check imports at top of file |
| Handler not reached | Verify dispatch elif order |

---

## Definition of Done Checklist

- [ ] T004: Parser added with all flags
- [ ] T005: Handler implemented calling service layer
- [ ] T006: Dispatch wired correctly
- [ ] `app import-purchases --help` shows correct usage
- [ ] `--dry-run`, `--json`, `--resolve-mode` flags work
- [ ] No linting errors

---

## Review Guidance

**Reviewers should verify**:
1. Parser follows catalog-import pattern exactly
2. Handler is a thin wrapper (no business logic)
3. JSON output matches spec format
4. Dispatch case is in correct location
5. Error messages are clear and actionable

---

## Activity Log

- 2026-01-29T04:45:00Z – system – lane=planned – Prompt created.
