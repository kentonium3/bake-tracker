---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Export CLI Commands"
phase: "Phase 1 - Export Services"
lane: "done"
assignee: "gemini"
agent: "gemini"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Export CLI Commands

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add CLI commands for coordinated and denormalized export operations.

**Success Criteria**:
1. `export-complete` command creates entity files + manifest in output directory
2. `export-view` command creates denormalized view file
3. `validate-export` command verifies manifest checksums
4. All commands return exit code 0 on success, 1 on failure
5. CLI smoke tests pass

## Context & Constraints

**Owner**: Gemini (Track A - Export)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-027, FR-028, FR-030
- `src/utils/import_export_cli.py`: Existing CLI patterns with argparse
- WP01: coordinated_export_service.py
- WP02: denormalized_export_service.py

**Constraints**:
- MUST extend existing CLI (not create new)
- MUST follow existing argparse patterns
- MUST print summary and return exit codes

**Dependencies**: WP01, WP02

## Subtasks & Detailed Guidance

### Subtask T012 - Add export-complete command

**Purpose**: CLI command to export complete database with manifest.

**Steps**:
1. Add `export-complete` to argparse choices
2. Add arguments:
   - `--output` or `-o`: Output directory (default: `export_{timestamp}`)
   - `--zip` or `-z`: Create ZIP archive (flag)
3. Implement handler:
   ```python
   def export_complete(output_dir: str, create_zip: bool = False):
       print(f"Exporting complete database to {output_dir}...")
       from src.services.coordinated_export_service import export_complete as do_export
       result = do_export(output_dir, create_zip=create_zip)
       print(result.get_summary())
       return 0 if result.success else 1
   ```
4. Wire to argparse dispatcher

**Files**: `src/utils/import_export_cli.py`
**Parallel?**: No

### Subtask T013 - Add export-view command

**Purpose**: CLI command to export denormalized views.

**Steps**:
1. Add `export-view` to argparse choices
2. Add arguments:
   - `--type` or `-t`: View type (choices: products, inventory, purchases)
   - `--output` or `-o`: Output file path (default: `view_{type}.json`)
3. Implement handler:
   ```python
   def export_view(view_type: str, output_path: str):
       print(f"Exporting {view_type} view to {output_path}...")
       from src.services.denormalized_export_service import (
           export_products_view, export_inventory_view, export_purchases_view
       )
       exporters = {
           "products": export_products_view,
           "inventory": export_inventory_view,
           "purchases": export_purchases_view,
       }
       result = exporters[view_type](output_path)
       print(result.get_summary())
       return 0 if result.success else 1
   ```

**Files**: `src/utils/import_export_cli.py`
**Parallel?**: No

### Subtask T014 - Add validate-export command

**Purpose**: CLI command to verify manifest checksums.

**Steps**:
1. Add `validate-export` to argparse choices
2. Add argument:
   - `export_dir`: Path to export directory with manifest.json
3. Implement handler:
   ```python
   def validate_export(export_dir: str):
       print(f"Validating export in {export_dir}...")
       from src.services.coordinated_export_service import validate_export as do_validate
       result = do_validate(export_dir)
       if result.all_valid:
           print("All checksums valid.")
           return 0
       else:
           print("Checksum mismatches found:")
           for mismatch in result.mismatches:
               print(f"  - {mismatch.filename}: expected {mismatch.expected}, got {mismatch.actual}")
           return 1
   ```

**Files**: `src/utils/import_export_cli.py`
**Parallel?**: No

### Subtask T015 - Write CLI smoke tests

**Purpose**: Verify CLI commands work end-to-end.

**Steps**:
1. Add tests to existing CLI test file or create new
2. Test cases:
   - `export-complete` creates directory with manifest.json
   - `export-complete --zip` creates ZIP file
   - `export-view --type products` creates view_products.json
   - `validate-export` returns 0 for valid export
   - `validate-export` returns 1 for corrupted file
3. Use subprocess or direct function calls

**Files**: `src/tests/utils/test_import_export_cli.py`
**Parallel?**: No

## Test Strategy

- Smoke tests for each command
- Verify exit codes
- Verify output files created

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Path handling | Use Path objects consistently |
| Output conflicts | Default to timestamped directories |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] `export-complete` command works with --output and --zip
- [ ] `export-view` command works with --type
- [ ] `validate-export` command works
- [ ] All commands return correct exit codes
- [ ] CLI smoke tests pass
- [ ] tasks.md updated with status change

## Review Guidance

- Verify argparse patterns match existing CLI
- Verify exit codes: 0 success, 1 failure
- Verify help text is clear

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T03:48:10Z – system – shell_pid= – lane=done – Implementation complete by Gemini CLI, reviewed and tests pass
