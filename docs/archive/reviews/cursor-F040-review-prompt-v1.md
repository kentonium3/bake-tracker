# Cursor Code Review Prompt - Feature 040: Import/Export v4.0 Upgrade

## Role

You are a senior software engineer performing an independent code review of Feature 040 (import-export-v4). Approach this as if you are discovering this feature for the first time with no prior knowledge of the implementation decisions.

## Feature Summary

**Feature Number:** 040
**Title:** Import/Export v4.0 Upgrade
**Branch/Worktree:** `.worktrees/040-import-export-v4`

**High-Level User Goal:**
Upgrade the import/export system to version 4.0 to support:
1. Recipe variant relationships (F037 base_recipe_id, variant_name, is_production_ready)
2. Event output_mode field (F039)
3. BT Mobile workflows for purchase import via UPC scanning
4. BT Mobile workflows for inventory quantity updates via UPC scanning
5. Merge vs Replace import modes

**Problem Being Solved:**
- Export/import currently at v3.x does not preserve new F037/F039 fields
- No mobile-friendly way to import purchases from UPC scans
- No mobile-friendly way to update inventory quantities after pantry audits
- Need to preserve recipe variant relationships across export/import cycles

## Files Modified

### Service Layer
- `src/services/import_export_service.py` - Core export/import logic
- `src/services/recipe_service.py` - Recipe export serialization

### UI Layer
- `src/ui/forms/upc_resolution_dialog.py` - New dialog for resolving unknown UPCs

### Tests
- `src/tests/services/test_import_export_service.py` - Unit tests
- `src/tests/integration/test_import_export_v4.py` - Integration tests

### Sample Data
- `test_data/sample_data.json` - Updated to v4.0 format
- `test_data/bt_mobile_purchase_sample.json` - New BT Mobile purchase import sample
- `test_data/bt_mobile_inventory_sample.json` - New BT Mobile inventory update sample

## Specification Documents

Read these BEFORE looking at the implementation:

- `kitty-specs/040-import-export-v4/spec.md` - Feature specification with acceptance criteria
- `kitty-specs/040-import-export-v4/plan.md` - Implementation plan
- `kitty-specs/040-import-export-v4/data-model.md` - JSON schema definitions
- `kitty-specs/040-import-export-v4/research.md` - Key decisions and rationale

## Review Approach

1. **Read the spec first** - Understand intended behavior from `spec.md` BEFORE examining code
2. **Form expectations** - Based on the spec, what would you expect the implementation to do?
3. **Compare** - Does the implementation match your expectations? Note discrepancies
4. **Look for gaps** - Edge cases, error handling, data integrity risks the spec may not cover
5. **Check patterns** - Does the code follow existing codebase patterns?
6. **Verify** - Run the verification commands below

## Verification Commands

Run these commands from the worktree. If ANY fail, STOP and report as a blocker before continuing.

```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/040-import-export-v4

# Activate virtual environment
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Verify all modified modules import correctly
PYTHONPATH=. python3 -c "
from src.services.import_export_service import (
    export_all_to_json,
    import_all_from_json_v4,
    import_purchases_from_bt_mobile,
    import_inventory_updates_from_bt_mobile
)
from src.services.recipe_service import get_recipe
from src.ui.forms.upc_resolution_dialog import UPCResolutionDialog
print('All imports successful')
"

# Check version in export service
grep -n "version.*4.0\|\"4.0\"" src/services/import_export_service.py | head -5

# Check F037 recipe fields in export
grep -n "base_recipe_slug\|variant_name\|is_production_ready" src/services/import_export_service.py | head -10
grep -n "base_recipe_slug\|variant_name\|is_production_ready" src/services/recipe_service.py | head -10

# Check F039 event fields in export
grep -n "output_mode" src/services/import_export_service.py | head -5

# Check BT Mobile import functions exist
grep -n "def import_purchases_from_bt_mobile\|def import_inventory_updates_from_bt_mobile" src/services/import_export_service.py

# Check import modes
grep -n "mode.*merge\|mode.*replace" src/services/import_export_service.py | head -5

# Verify UPC resolution dialog exists
ls -la src/ui/forms/upc_resolution_dialog.py

# Run integration tests
PYTHONPATH=. python3 -m pytest src/tests/integration/test_import_export_v4.py -v --tb=short

# Run import/export service tests
PYTHONPATH=. python3 -m pytest src/tests/services/test_import_export_service.py -v --tb=short 2>&1 | tail -80

# Run full test suite to verify no regressions
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -100

# Validate sample data JSON files
python3 -c "import json; d=json.load(open('test_data/sample_data.json')); print(f'sample_data.json: version={d.get(\"version\")}')"
python3 -c "import json; d=json.load(open('test_data/bt_mobile_purchase_sample.json')); print(f'bt_mobile_purchase_sample.json: schema_version={d.get(\"schema_version\")}, import_type={d.get(\"import_type\")}')"
python3 -c "import json; d=json.load(open('test_data/bt_mobile_inventory_sample.json')); print(f'bt_mobile_inventory_sample.json: schema_version={d.get(\"schema_version\")}, import_type={d.get(\"import_type\")}')"

# Check git log
git log --oneline -20
```

## Areas to Evaluate

Based on the spec (which you should read first), form your own assessment of:

- **Logic gaps** - Cases the spec or implementation may not handle
- **Edge cases** - Empty data, null values, missing fields, circular references
- **Error handling** - What happens when things go wrong?
- **Data integrity** - Could import corrupt existing data?
- **UPC matching** - What if UPC exists on multiple products?
- **Session management** - Does code follow the project's session patterns?
- **User workflow friction** - Is the UPC resolution dialog usable?
- **Performance** - Any concerns with large datasets?
- **Maintainability** - Is the code clear and well-structured?

## Output Format

Write your review to:
`/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F040-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 040 - Import/Export v4.0 Upgrade

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 040-import-export-v4
**Branch/Worktree:** `.worktrees/040-import-export-v4`

## Summary

[Brief overview - did the implementation match your expectations from the spec?]

## Verification Results

### Import Validation
- import_export_service.py: [PASS/FAIL]
- recipe_service.py: [PASS/FAIL]
- upc_resolution_dialog.py: [PASS/FAIL]

### Test Results
- Integration tests: [X passed, Y failed]
- Import/export service tests: [X passed, Y failed]
- Full test suite: [X passed, Y skipped, Z failed]

## Findings

### Critical Issues
[Any blocking issues that must be fixed before merge]

### Warnings
[Non-blocking concerns that should be addressed]

### Observations
[General observations about code quality, patterns, potential improvements]

## Spec vs Implementation Analysis

| Requirement from Spec | Implemented? | Notes |
|-----------------------|--------------|-------|
| [requirement 1] | [Yes/No/Partial] | [notes] |
| [requirement 2] | [Yes/No/Partial] | [notes] |
| ... | ... | ... |

## Edge Cases Considered

| Edge Case | Handled? | How? |
|-----------|----------|------|
| [case 1] | [Yes/No] | [notes] |
| [case 2] | [Yes/No] | [notes] |
| ... | ... | ... |

## Code Quality Assessment

### Session Management
[Does the code follow project session management patterns per CLAUDE.md?]

### Layered Architecture
[Is business logic properly in services, not UI?]

### Error Handling
[Are errors handled gracefully with user-friendly messages?]

### Test Coverage
[Are the key scenarios covered?]

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/services/import_export_service.py | [status] | [notes] |
| src/services/recipe_service.py | [status] | [notes] |
| src/ui/forms/upc_resolution_dialog.py | [status] | [notes] |
| src/tests/integration/test_import_export_v4.py | [status] | [notes] |
| src/tests/services/test_import_export_service.py | [status] | [notes] |
| test_data/*.json | [status] | [notes] |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary and recommendations]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing
- Layered architecture: UI -> Services -> Models -> Database
- Session management is CRITICAL: read CLAUDE.md for the pattern
- Recipe model uses `name` for identification (NOT `slug`)
- Event model uses `name` for identification (NOT `slug`)
- Recipe variants reference base recipes via `base_recipe_id` FK
- F037 fields: `base_recipe_slug`, `variant_name`, `is_production_ready`
- F039 fields: `output_mode` (enum: BUNDLED, BULK_COUNT, or null)
- BT Mobile is a hypothetical mobile app that scans UPCs for purchases/inventory

## Important Notes

- Read the spec files FIRST before looking at implementation
- Form your own expectations about how features SHOULD work
- Note any discrepancies between spec and implementation
- Run all verification commands - if ANY fail, report as blocker
- Write report to main repo docs/code-reviews/, NOT the worktree
