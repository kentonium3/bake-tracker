---
work_package_id: "WP05"
subtasks:
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Documentation Update"
phase: "Phase 5 - Documentation Update (P3)"
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

# Work Package Prompt: WP05 - Documentation Update

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

Update CLI module documentation to cover all new commands:

1. Update module-level docstring with complete command reference
2. Add usage examples for all workflows
3. Ensure all commands have accurate help text
4. Document AI workflow patterns

**Success Criteria**:
- `python -m src.utils.import_export_cli --help` shows all 16+ commands
- Each command's `--help` is accurate and actionable
- Module docstring includes examples for backup, aug, and catalog workflows
- AI workflow pattern documented (aug-export -> modify -> aug-import)

## Context & Constraints

**Reference Documents**:
- `kitty-specs/054-cli-import-export-parity/spec.md` - FR-6xx requirements
- `src/utils/import_export_cli.py` - Lines 1-43 for existing docstring

**Documentation Requirements** (from spec):
- FR-601: Module docstring MUST document all commands with examples
- FR-602: Help text MUST be accurate and actionable for all commands
- FR-603: AI workflow patterns MUST be documented

## Subtasks & Detailed Guidance

### T035 - Update module-level docstring

**Purpose**: Comprehensive command reference at top of module.

**Steps**:
1. Update docstring at lines 1-43
2. Add sections for new command groups:
   - Backup/Restore commands
   - Aug (context-rich) commands
   - Catalog commands
   - Entity-specific exports

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
"""
Import/Export CLI Utility

Simple command-line interface for exporting and importing data.
No UI required - designed for programmatic and testing use.

BACKUP/RESTORE COMMANDS (16-entity coordinated backup):

    # Create timestamped backup
    python -m src.utils.import_export_cli backup -o ./backups/

    # Create backup as ZIP archive
    python -m src.utils.import_export_cli backup -o ./backups/ --zip

    # Restore from backup
    python -m src.utils.import_export_cli restore ./backups/backup_20260115/

    # List available backups
    python -m src.utils.import_export_cli backup-list --dir ./backups/

    # Validate backup integrity
    python -m src.utils.import_export_cli backup-validate ./backups/backup_20260115/

CONTEXT-RICH AUG COMMANDS (AI workflow support):

    # Export products with human-readable context
    python -m src.utils.import_export_cli aug-export -t products -o aug_products.json

    # Export all entity types
    python -m src.utils.import_export_cli aug-export -t all -o ./aug_exports/

    # Import with automatic FK resolution
    python -m src.utils.import_export_cli aug-import aug_products.json

    # Import with interactive FK resolution
    python -m src.utils.import_export_cli aug-import aug_products.json --interactive

    # Validate aug file format
    python -m src.utils.import_export_cli aug-validate aug_products.json

CATALOG COMMANDS (selective entity operations):

    # Export specific catalog entities
    python -m src.utils.import_export_cli catalog-export --entities ingredients,products

    # Export all catalog entities
    python -m src.utils.import_export_cli catalog-export -o ./catalog/

    # Import catalog with augment mode
    python -m src.utils.import_export_cli catalog-import ./catalog/ --mode augment

    # Validate catalog before import
    python -m src.utils.import_export_cli catalog-validate ./catalog/

ENTITY-SPECIFIC EXPORTS:

    # Export individual entity types
    python -m src.utils.import_export_cli export-materials materials.json
    python -m src.utils.import_export_cli export-material-products material_products.json
    python -m src.utils.import_export_cli export-material-categories categories.json
    python -m src.utils.import_export_cli export-material-subcategories subcategories.json
    python -m src.utils.import_export_cli export-suppliers suppliers.json
    python -m src.utils.import_export_cli export-purchases purchases.json

LEGACY COMMANDS (v3.2 format):

    # Export all data (v3.2 format)
    python -m src.utils.import_export_cli export test_data.json

    # Export ingredients only
    python -m src.utils.import_export_cli export-ingredients ingredients.json

    # Import all data (requires v3.2 format)
    python -m src.utils.import_export_cli import test_data.json

    # Import with replace mode (clears existing data first)
    python -m src.utils.import_export_cli import test_data.json --mode replace

F030 COMMANDS (coordinated export/view):

    # Export complete database with manifest
    python -m src.utils.import_export_cli export-complete -o ./export_dir

    # Export denormalized view
    python -m src.utils.import_export_cli export-view -t products -o view_products.json

    # Validate export checksums
    python -m src.utils.import_export_cli validate-export ./export_dir

    # Import denormalized view
    python -m src.utils.import_export_cli import-view view_products.json --interactive
"""
```

### T036 - Add backup/restore workflow examples

**Purpose**: Document backup/restore usage patterns.

**Steps**:
1. Include in module docstring (T035)
2. Also add to CLI epilog for `--help` output

**Files**: `src/utils/import_export_cli.py`

**Notes**: Backup workflow: create backup -> verify with backup-validate -> restore when needed

### T037 - Add aug workflow examples

**Purpose**: Document AI-assisted workflow pattern.

**Steps**:
1. Include in module docstring (T035)
2. Document the complete AI workflow:
   1. `aug-export -t products` - Export with context
   2. External modification (AI or manual)
   3. `aug-import` - Re-import with FK resolution

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Key Pattern**:
```
AI Workflow:
1. Export: aug-export -t products -o aug_products.json
2. Modify: (external tool or AI modifies the JSON)
3. Import: aug-import aug_products.json --skip-on-error
```

### T038 - Add catalog operation examples

**Purpose**: Document catalog import/export usage.

**Steps**:
1. Include in module docstring (T035)
2. Document selective export and import modes

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

### T039 - Verify all commands have accurate help strings

**Purpose**: Ensure every subparser has descriptive help text.

**Steps**:
1. Review all `add_parser()` calls
2. Verify `help=` argument is descriptive and accurate
3. Check argument help strings

**Files**: `src/utils/import_export_cli.py`

**Parallel?**: Yes

**Verification Checklist**:
- [ ] backup: "Create timestamped 16-entity backup with manifest"
- [ ] restore: "Restore database from backup directory"
- [ ] backup-list: "List available backups in directory"
- [ ] backup-validate: "Validate backup checksums"
- [ ] aug-export: "Export context-rich data for AI workflows"
- [ ] aug-import: "Import context-rich data with FK resolution"
- [ ] aug-validate: "Validate aug file format"
- [ ] catalog-export: "Export catalog data (7 entity types)"
- [ ] catalog-import: "Import catalog with mode selection"
- [ ] catalog-validate: "Validate catalog before import"
- [ ] export-materials: "Export materials only"
- [ ] export-material-products: "Export material products only"
- [ ] export-material-categories: "Export material categories only"
- [ ] export-material-subcategories: "Export material subcategories only"
- [ ] export-suppliers: "Export suppliers only"
- [ ] export-purchases: "Export purchases only"

### T040 - Update CLI epilog with comprehensive examples

**Purpose**: Ensure `--help` output includes useful examples.

**Steps**:
1. Update `epilog` in ArgumentParser (around line 600)
2. Add examples for new command groups
3. Keep examples concise but representative

**Files**: `src/utils/import_export_cli.py`

**Code Pattern**:
```python
parser = argparse.ArgumentParser(
    description="Import/Export utility for Seasonal Baking Tracker",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  Backup/Restore:
    python -m src.utils.import_export_cli backup -o ./backups/
    python -m src.utils.import_export_cli restore ./backups/backup_20260115/

  AI Workflow (aug commands):
    python -m src.utils.import_export_cli aug-export -t products
    python -m src.utils.import_export_cli aug-import aug_products.json --interactive

  Catalog Operations:
    python -m src.utils.import_export_cli catalog-export --entities ingredients,products
    python -m src.utils.import_export_cli catalog-import ./catalog/ --mode augment

  Entity Exports:
    python -m src.utils.import_export_cli export-materials materials.json
    python -m src.utils.import_export_cli export-suppliers suppliers.json

  Legacy Commands:
    python -m src.utils.import_export_cli export all_data.json
    python -m src.utils.import_export_cli import all_data.json --mode replace

Note: Use 'aug-' commands for AI-assisted workflows. These exports include
human-readable context fields and support automatic FK resolution on import.
""",
)
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Documentation out of sync with implementation | Update docs after commands verified working |
| Help text too verbose | Keep concise; detailed docs in module docstring |

## Definition of Done Checklist

- [ ] Module docstring updated with all command groups
- [ ] Backup/restore examples included
- [ ] Aug workflow examples included
- [ ] Catalog operation examples included
- [ ] All subparsers have accurate help text
- [ ] CLI epilog updated with examples
- [ ] `--help` displays all commands
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Run `python -m src.utils.import_export_cli --help` to verify
- Run each new command with `--help` to check arguments
- Verify module docstring is readable and complete

## Activity Log

- 2026-01-15T18:00:00Z - system - lane=planned - Prompt created.
- 2026-01-15T23:51:12Z – unknown – lane=doing – Starting implementation
- 2026-01-15T23:54:05Z – unknown – lane=for_review – All documentation tasks complete: docstring updated, help strings verified, CLI epilog updated with comprehensive F054 examples
- 2026-01-16T00:40:35Z – agent – lane=doing – Started review via workflow command
- 2026-01-16T00:40:55Z – unknown – lane=done – Review passed: Comprehensive documentation with all command groups documented
