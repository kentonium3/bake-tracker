# Cursor Code Review Prompt - Feature 040: Import/Export v4.0 Upgrade

## Your Role

You are a senior software engineer performing an independent code review. Approach this as if discovering the feature for the first time. Read the spec first, form your own expectations, then evaluate the implementation.

## Feature Context

**Feature:** 040 - Import/Export v4.0 Upgrade
**User Goal:** Upgrade export/import system to preserve new F037/F039 fields and enable mobile UPC-based purchase/inventory workflows
**Spec File:** `kitty-specs/040-import-export-v4/spec.md`

## Files to Review

```
src/services/import_export_service.py
src/services/recipe_service.py
src/ui/forms/upc_resolution_dialog.py
src/tests/integration/test_import_export_v4.py
src/tests/services/test_import_export_service.py
test_data/sample_data.json
test_data/bt_mobile_purchase_sample.json
test_data/bt_mobile_inventory_sample.json
```

## Spec Files (Read First)

```
kitty-specs/040-import-export-v4/spec.md
kitty-specs/040-import-export-v4/data-model.md
```

## Verification Commands

Run from worktree: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/040-import-export-v4`

```bash
source /Users/kentgale/Vaults-repos/bake-tracker/venv/bin/activate

# Imports
PYTHONPATH=. python3 -c "
from src.services.import_export_service import export_all_to_json, import_all_from_json_v4, import_purchases_from_bt_mobile, import_inventory_updates_from_bt_mobile
from src.ui.forms.upc_resolution_dialog import UPCResolutionDialog
print('All imports successful')
"

# Tests
PYTHONPATH=. python3 -m pytest src/tests/integration/test_import_export_v4.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests/services/test_import_export_service.py -v --tb=short
PYTHONPATH=. python3 -m pytest src/tests -v --tb=short 2>&1 | tail -50
```

**If ANY verification fails, STOP and report as blocking issue.**

## Review Instructions

1. **Read the spec** (`spec.md`) to understand intended behavior
2. **Form expectations** about how this SHOULD work before reading code
3. **Run verification commands** - stop if failures
4. **Review implementation** comparing against your expectations
5. **Write report** to `docs/code-reviews/cursor-F040-review.md`

Focus on:
- Logic gaps or edge cases
- Data integrity risks
- User workflow friction
- Deviation from codebase patterns
- Session management (see CLAUDE.md)

## Report Template

Write your report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F040-review.md`

```markdown
# Code Review Report: F040 - Import/Export v4.0 Upgrade

**Reviewer:** Cursor (Independent Review)
**Date:** [YYYY-MM-DD]
**Feature Spec:** kitty-specs/040-import-export-v4/spec.md

## Executive Summary
[2-3 sentences: What this feature does, overall assessment, key concerns if any]

## Review Scope
**Files Modified:**
- src/services/import_export_service.py
- src/services/recipe_service.py
- src/ui/forms/upc_resolution_dialog.py
- src/tests/integration/test_import_export_v4.py
- src/tests/services/test_import_export_service.py
- test_data/*.json

**Dependencies Reviewed:**
- [any related systems, services, or data models examined]

## Environment Verification
**Commands Run:**
```bash
[list verification commands executed]
```

**Results:**
- [ ] All imports successful
- [ ] All tests passed
- [ ] Database migrations valid (if applicable)

[If any failed: STOP - blocking issues must be resolved before continuing]

## Findings

### Critical Issues
[Issues that could cause data loss, corruption, crashes, or security problems]

**[Issue Title]**
- **Location:** [file:line or general area]
- **Problem:** [what's wrong]
- **Impact:** [what could happen]
- **Recommendation:** [how to fix]

### Major Concerns
[Issues affecting core functionality, user workflows, or maintainability]

### Minor Issues
[Code quality, style inconsistencies, optimization opportunities]

### Positive Observations
[What was done well - good patterns, clever solutions, solid error handling]

## Spec Compliance
- [ ] Meets stated requirements
- [ ] Handles edge cases appropriately
- [ ] Error handling adequate
- [ ] User workflow feels natural

[Note any gaps between spec and implementation]

## Code Quality Assessment

**Consistency with Codebase:**
[Does this follow established patterns? Any deviations and why they matter?]

**Maintainability:**
[How easy will this be for future developers to understand and modify?]

**Test Coverage:**
[Are the right things tested? Any obvious gaps?]

## Recommendations Priority

**Must Fix Before Merge:**
1. [Critical/blocking items]

**Should Fix Soon:**
1. [Important but not blocking]

**Consider for Future:**
1. [Nice-to-haves, refactoring opportunities]

## Overall Assessment
[Pass/Pass with minor fixes/Needs revision/Major rework needed]

[Final paragraph: Would you ship this to users? Why or why not?]
```

## Context Notes

- SQLAlchemy 2.x, CustomTkinter UI, pytest
- Recipe/Event models use `name` not `slug` for identification
- F037 fields: `base_recipe_slug`, `variant_name`, `is_production_ready`
- F039 field: `output_mode` enum (BUNDLED, BULK_COUNT, null)
- BT Mobile = hypothetical mobile app for UPC scanning
- Session management pattern is CRITICAL - see CLAUDE.md
