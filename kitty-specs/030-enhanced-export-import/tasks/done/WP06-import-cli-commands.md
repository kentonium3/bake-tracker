---
work_package_id: "WP06"
subtasks:
  - "T030"
  - "T031"
  - "T032"
title: "Import CLI Commands"
phase: "Phase 2 - Import Services"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "reviewed"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Import CLI Commands

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Add CLI command for import operations with interactive FK resolution support.

**Success Criteria**:
1. `import-view` command with --mode, --interactive, --skip-on-error, --dry-run flags
2. Interactive mode prompts user for FK resolution via text menu
3. CLI default is fail-fast (error on missing FK without --interactive)
4. CLI smoke tests pass

## Context & Constraints

**Owner**: Claude (Track B - Import)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-017, FR-029
- `src/utils/import_export_cli.py`: Existing CLI patterns
- WP05: enhanced_import_service.py

**Constraints**:
- MUST extend existing CLI (not create new)
- MUST follow existing argparse patterns
- CLI default is fail-fast per FR-025

**Dependencies**: WP05 (Enhanced Import Service)

## Subtasks & Detailed Guidance

### Subtask T030 - Add import-view command

**Purpose**: CLI command to import denormalized view files.

**Steps**:
1. Add `import-view` to argparse choices
2. Add arguments:
   - `file`: Input file path (positional)
   - `--mode` or `-m`: Import mode (choices: merge, skip_existing; default: merge)
   - `--interactive` or `-i`: Enable interactive FK resolution (flag)
   - `--skip-on-error` or `-s`: Skip records with errors (flag)
   - `--dry-run` or `-d`: Preview changes without modifying database (flag)
3. Implement handler:
   ```python
   def import_view(file_path: str, mode: str, interactive: bool, skip_on_error: bool, dry_run: bool):
       print(f"Importing view from {file_path} (mode: {mode})...")

       from src.services.enhanced_import_service import import_view as do_import

       resolver = None
       if interactive:
           resolver = CLIFKResolver()  # Defined in T031

       result = do_import(
           file_path,
           mode=mode,
           resolver=resolver,
           skip_on_error=skip_on_error,
           dry_run=dry_run
       )

       print(result.get_summary())
       return 0 if result.base_result.failed == 0 else 1
   ```

**Files**: `src/utils/import_export_cli.py`
**Parallel?**: No

### Subtask T031 - Implement CLI interactive FK resolution

**Purpose**: Text-based prompts for FK resolution.

**Steps**:
1. Create CLIFKResolver class implementing FKResolverCallback:
   ```python
   class CLIFKResolver:
       def resolve(self, missing: MissingFK) -> Resolution:
           print(f"\nMissing {missing.entity_type}: '{missing.missing_value}'")
           print(f"  Affects {missing.affected_record_count} records")

           # Show options
           print("\nOptions:")
           print("  [C] Create new entity")
           print("  [M] Map to existing entity")
           print("  [S] Skip these records")

           while True:
               choice = input("\nEnter choice (C/M/S): ").strip().upper()

               if choice == 'C':
                   return self._handle_create(missing)
               elif choice == 'M':
                   return self._handle_map(missing)
               elif choice == 'S':
                   return Resolution(
                       choice=ResolutionChoice.SKIP,
                       entity_type=missing.entity_type,
                       missing_value=missing.missing_value
                   )
               else:
                   print("Invalid choice. Enter C, M, or S.")
   ```
2. Implement `_handle_create(missing)`:
   - Prompt for required fields based on entity type
   - Supplier: name, city, state, zip
   - Ingredient: slug, display_name, category
   - Product: ingredient_slug, brand, package_unit, package_unit_quantity
   - Return Resolution with created_entity dict
3. Implement `_handle_map(missing)`:
   - Show fuzzy search results
   - Let user select by number
   - Return Resolution with mapped_id

**Files**: `src/utils/import_export_cli.py`
**Parallel?**: No

### Subtask T032 - Write CLI smoke tests

**Purpose**: Verify CLI import command works.

**Steps**:
1. Add tests to CLI test file
2. Test cases:
   - `import-view file.json` with valid file (merge mode default)
   - `import-view file.json --mode skip_existing`
   - `import-view file.json --dry-run` makes no changes
   - `import-view file.json --skip-on-error` creates skipped log
   - Error case: missing FK without --interactive returns error
3. Use subprocess or mock input for interactive tests

**Files**: `src/tests/utils/test_import_export_cli.py`
**Parallel?**: No

## Test Strategy

- Smoke tests for each flag combination
- Mock input() for interactive testing
- Verify exit codes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Interactive testing | Mock input() function |
| Path handling | Use Path objects consistently |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] `import-view` command works with all flags
- [ ] Interactive mode prompts work correctly
- [ ] Fail-fast default works (error without --interactive)
- [ ] CLI smoke tests pass
- [ ] tasks.md updated with status change

## Review Guidance

- Verify argparse patterns match existing CLI
- Verify interactive prompts are clear
- Verify fail-fast is default behavior
- Verify exit codes: 0 success, 1 failure

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T02:45:06Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-26T02:55:45Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-26T03:37:50Z – system – shell_pid= – lane=done – Code review passed: All CLI tests pass
