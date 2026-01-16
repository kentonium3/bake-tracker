# Cursor Review Prompt: F054 - CLI Import/Export Parity

## Your Role
You are a senior software engineer performing an independent code review. You are discovering this feature for the first time. Your fresh perspective is valuable for finding issues the implementer might have missed.

## Feature Overview
**Feature Number:** 054
**Title:** CLI Import/Export Parity
**User Goal:** Bring CLI import/export capabilities to full parity with the UI, enabling backup/restore, context-rich exports for AI workflows, catalog operations, and entity-specific exports through the command line.

**Key Changes:**
1. Add 4 backup/restore commands: `backup`, `restore`, `backup-list`, `backup-validate`
2. Add 3 context-rich "aug" commands: `aug-export`, `aug-import`, `aug-validate`
3. Add 3 catalog commands: `catalog-export`, `catalog-import`, `catalog-validate`
4. Add 6 entity-specific export commands for materials, suppliers, purchases
5. Update CLI documentation and help strings

## Specification File
Full spec at: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/spec.md`

Work packages:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/tasks/WP01-backup-restore-commands.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/tasks/WP02-context-rich-aug-commands.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/tasks/WP03-catalog-commands.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/tasks/WP04-entity-specific-exports.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/kitty-specs/054-cli-import-export-parity/tasks/WP05-documentation-update.md`

## Primary Files Modified

**CLI Implementation:**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/src/utils/import_export_cli.py`

**Service Layer (called by CLI, not modified but important context):**
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/src/services/coordinated_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/src/services/denormalized_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/src/services/enhanced_import_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity/src/services/catalog_import_service.py`

**Note:** These are the primary changes. Review should extend to any related code, dependencies, or callers as needed.

## Environment Verification

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/054-cli-import-export-parity

# Verify CLI runs and shows all new commands
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python src/utils/import_export_cli.py --help 2>&1 | grep -E "backup|restore|aug-|catalog-"

# Verify imports work (use main repo's venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.utils.import_export_cli import (
    backup_cmd,
    restore_cmd,
    backup_list_cmd,
    backup_validate_cmd,
    aug_export_cmd,
    aug_import_cmd,
    aug_validate_cmd,
    catalog_export_cmd,
    catalog_import_cmd,
    catalog_validate_cmd,
)
print('All CLI function imports successful')
"

# Verify service imports used by CLI
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "
from src.services.coordinated_export_service import export_complete, import_complete, validate_export
from src.services.denormalized_export_service import export_products_context_rich
from src.services.enhanced_import_service import import_context_rich_export, detect_format
from src.services.catalog_import_service import import_catalog, validate_catalog_file
print('All service imports successful')
"
```

**If ANY verification command fails, STOP immediately and report the blocker before proceeding.**

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template
Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_code_review_report.md`

## Report Output Location
Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F054-review.md`

**Important:** Write to `docs/code-reviews/` directory in the MAIN repo, NOT in the worktree.

## Areas of Interest (Not Prescriptive)

These are areas that might warrant attention, but form your own review priorities:
- Command wiring in main() dispatch logic - are all 16 new commands properly connected?
- Argument handling - are required vs optional args correctly specified?
- Service function calls - do parameter names match actual service signatures?
- Error handling - do commands return proper exit codes (0 success, 1 failure)?
- Help strings and epilog examples - are they accurate and useful?
- Entity type lists - are they consistent across export/import pairs?
- Default paths/directories - are they sensible defaults?
