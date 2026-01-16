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
  - "T008"
  - "T009"
title: "Backup/Restore Commands"
phase: "Phase 1 - Backup/Restore Commands (P1)"
lane: "done"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-15T18:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Backup/Restore Commands

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

Implement 4 backup/restore CLI commands that wrap `coordinated_export_service` for 16-entity coordinated backup operations:

1. `backup` - Create timestamped 16-entity backup with manifest
2. `restore` - Import from backup directory with mode selection
3. `backup-list` - List available backups in a directory
4. `backup-validate` - Verify backup integrity via checksums

**Success Criteria**:
- All 4 commands registered as subparsers with correct arguments
- `backup` creates 16 entity JSON files + manifest.json
- `restore` imports all entities in dependency order
- `backup-validate` reports checksum validation results
- `backup-list` displays backup metadata from manifest.json files
- Exit codes: 0 for success, 1 for failure

## Context & Constraints

**Reference Documents**:
- `kitty-specs/054-cli-import-export-parity/plan.md` - Phase 1 details
- `kitty-specs/054-cli-import-export-parity/research.md` - Service function signatures
- `src/utils/import_export_cli.py` - Existing CLI patterns

**Architecture Constraints**:
- CLI wraps services only - no business logic in CLI
- Follow existing argparse subparser pattern
- Reuse `export_complete_cmd()` pattern (line 194) as reference
- All imports at function level to avoid circular dependencies

**Service Functions** (from research.md):
```python
from src.services.coordinated_export_service import (
    export_complete,      # Returns ExportManifest
    import_complete,      # Returns Dict with counts
    validate_export,      # Returns Dict with validation results
)
```

## Subtasks & Detailed Guidance

### T001 - Add `backup` subparser

**Purpose**: Register the `backup` command with its arguments.

**Steps**:
1. Add subparser after existing F030 commands (around line 700)
2. Define arguments:
   - `-o, --output`: Output directory (default: `./backups/backup_{timestamp}`)
   - `--zip`: Create compressed archive (store_true)

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
# Backup command
backup_parser = subparsers.add_parser(
    "backup",
    help="Create timestamped 16-entity backup with manifest"
)
backup_parser.add_argument(
    "-o", "--output",
    dest="output_dir",
    help="Output directory (default: ./backups/backup_{timestamp})"
)
backup_parser.add_argument(
    "--zip",
    dest="create_zip",
    action="store_true",
    help="Create compressed ZIP archive"
)
```

### T002 - Implement `backup_cmd()` function

**Purpose**: Execute the backup command by calling the coordinated export service.

**Steps**:
1. Add function after existing F030 command functions (around line 340)
2. Import `export_complete` from `coordinated_export_service`
3. Generate default output directory if not provided
4. Call `export_complete()` and print summary
5. Return 0 on success, 1 on failure

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
def backup_cmd(output_dir: str = None, create_zip: bool = False) -> int:
    """
    Create timestamped 16-entity backup with manifest.

    Args:
        output_dir: Output directory (default: ./backups/backup_{timestamp})
        create_zip: Whether to create a ZIP archive

    Returns:
        0 on success, 1 on failure
    """
    from src.services.coordinated_export_service import export_complete

    # Generate default output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"./backups/backup_{timestamp}"

    print(f"Creating backup in {output_dir}...")

    try:
        manifest = export_complete(output_dir, create_zip=create_zip)

        # Print summary
        total_records = sum(f.record_count for f in manifest.files)
        print(f"\nBackup Complete")
        print(f"---------------")
        print(f"Output directory: {output_dir}")
        print(f"Export date: {manifest.export_date}")
        print(f"Files exported: {len(manifest.files)}")
        print(f"Total records: {total_records}")
        print()
        for f in manifest.files:
            print(f"  {f.filename}: {f.record_count} records")

        if create_zip:
            zip_path = Path(output_dir).with_suffix(".zip")
            print(f"\nZIP archive: {zip_path}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 1
```

### T003 - Add `restore` subparser

**Purpose**: Register the `restore` command with its arguments.

**Steps**:
1. Add subparser after `backup` command
2. Define arguments:
   - `backup_dir`: Positional argument for backup directory path
   - `--mode`: Import mode (add/augment/replace), default "add"
   - `--interactive`: Enable FK resolution prompts (store_true)

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes - can be developed alongside T004-T008

**Code Pattern**:
```python
# Restore command
restore_parser = subparsers.add_parser(
    "restore",
    help="Restore database from backup directory"
)
restore_parser.add_argument(
    "backup_dir",
    help="Path to backup directory with manifest.json"
)
restore_parser.add_argument(
    "-m", "--mode",
    dest="restore_mode",
    choices=["add", "augment", "replace"],
    default="add",
    help="Import mode: 'add' (default) skip existing, 'augment' update nulls, 'replace' clear first"
)
restore_parser.add_argument(
    "-i", "--interactive",
    action="store_true",
    help="Enable interactive FK resolution"
)
```

### T004 - Implement `restore_cmd()` function

**Purpose**: Execute restore by importing from backup directory.

**Steps**:
1. Add function after `backup_cmd()`
2. Import `import_complete` from coordinated_export_service
3. Validate backup directory exists and contains manifest.json
4. Call `import_complete()` with mode parameter
5. Print import summary and return exit code

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Notes**: The `import_complete()` function may need mode parameter - verify signature. If not available, may need to use `catalog_import_service.import_catalog()` instead.

### T005 - Add `backup-list` subparser

**Purpose**: Register the `backup-list` command.

**Steps**:
1. Add subparser after `restore` command
2. Define arguments:
   - `--dir`: Directory to scan for backups (default: `./backups/`)

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

### T006 - Implement `backup_list_cmd()` function

**Purpose**: List available backups by scanning for manifest.json files.

**Steps**:
1. Add function after `restore_cmd()`
2. Scan specified directory for subdirectories containing `manifest.json`
3. For each backup found:
   - Parse manifest.json
   - Display: directory name, export_date, file count, total records
4. Sort by export_date descending (newest first)

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Code Pattern**:
```python
def backup_list_cmd(backups_dir: str = "./backups/") -> int:
    """List available backups."""
    import json

    backups_path = Path(backups_dir)
    if not backups_path.exists():
        print(f"Directory not found: {backups_dir}")
        return 1

    backups = []
    for subdir in backups_path.iterdir():
        if subdir.is_dir():
            manifest_path = subdir / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                backups.append({
                    "dir": subdir.name,
                    "date": manifest.get("export_date", "Unknown"),
                    "files": len(manifest.get("files", [])),
                    "records": sum(f.get("record_count", 0) for f in manifest.get("files", []))
                })

    if not backups:
        print(f"No backups found in {backups_dir}")
        return 0

    # Sort by date descending
    backups.sort(key=lambda x: x["date"], reverse=True)

    print(f"Available Backups in {backups_dir}")
    print("-" * 60)
    for b in backups:
        print(f"  {b['dir']}")
        print(f"    Date: {b['date']}")
        print(f"    Files: {b['files']}, Records: {b['records']}")

    return 0
```

### T007 - Add `backup-validate` subparser

**Purpose**: Register the `backup-validate` command.

**Steps**:
1. Add subparser after `backup-list` command
2. Define arguments:
   - `backup_dir`: Positional argument for backup directory path

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

### T008 - Implement `backup_validate_cmd()` function

**Purpose**: Validate backup checksums using existing service.

**Steps**:
1. Add function after `backup_list_cmd()`
2. This can largely reuse existing `validate_export_cmd()` logic
3. Call `validate_export()` from coordinated_export_service
4. Display validation results

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Notes**: Consider whether this should just alias `validate-export` or have separate function.

### T009 - Wire all 4 commands in `main()` dispatch logic

**Purpose**: Connect subparsers to handler functions in main().

**Steps**:
1. Add elif branches in `main()` after existing command handlers (around line 780)
2. Map: backup -> backup_cmd(), restore -> restore_cmd(), etc.
3. Pass correct arguments from args namespace

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
elif args.command == "backup":
    return backup_cmd(args.output_dir, args.create_zip)
elif args.command == "restore":
    return restore_cmd(args.backup_dir, args.restore_mode, args.interactive)
elif args.command == "backup-list":
    return backup_list_cmd(args.backups_dir if hasattr(args, 'backups_dir') else "./backups/")
elif args.command == "backup-validate":
    return backup_validate_cmd(args.backup_dir)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `import_complete()` function may not exist | Check coordinated_export_service; may need catalog_import_service |
| Restore mode parameter not supported | Verify service signature; adapt or document limitation |
| Backup directory structure assumptions | Review manifest structure in coordinated_export_service |

## Definition of Done Checklist

- [ ] All 4 subparsers registered with correct arguments
- [ ] All 4 command functions implemented
- [ ] Commands wired in main() dispatch
- [ ] `backup` creates 16 entity files + manifest.json
- [ ] `restore` imports from valid backup directory
- [ ] `backup-list` displays backup metadata
- [ ] `backup-validate` reports checksum results
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify commands follow existing CLI patterns
- Check service function calls match signatures from research.md
- Test with empty database (should create empty files, not fail)
- Verify exit codes (0=success, 1=failure)

## Activity Log

- 2026-01-15T18:00:00Z - system - lane=planned - Prompt created.
- 2026-01-15T23:32:23Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-15T23:40:09Z – unknown – lane=for_review – All 4 backup/restore commands implemented and tested
- 2026-01-16T00:38:09Z – agent – lane=doing – Started review via workflow command
- 2026-01-16T00:39:03Z – unknown – lane=done – Review passed: All 4 backup/restore commands implemented correctly with proper exit codes and error handling
