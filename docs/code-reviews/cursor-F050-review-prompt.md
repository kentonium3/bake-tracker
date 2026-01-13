# Cursor Code Review Prompt: Feature 050 - Supplier Slug Support

## Feature Overview

**Feature Number:** F050
**Title:** Supplier Slug Support
**User Goal:** Enable portable supplier identification across database environments by adding slug identifiers to suppliers, allowing data exports to be imported into fresh databases with all supplier references intact.

## Specification

Read the full specification before examining implementation:
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/050-supplier-slug-support/kitty-specs/050-supplier-slug-support/spec.md`

## Code Changes

**Model:**
- `src/models/supplier.py`

**Services:**
- `src/services/supplier_service.py`
- `src/services/import_export_service.py`
- `src/services/enhanced_import_service.py`
- `src/services/fk_resolver_service.py`

**Utilities:**
- `src/utils/slug_utils.py`

**Tests:**
- `src/tests/services/test_supplier_service.py`
- `src/tests/integration/test_import_export_027.py`
- `src/tests/models/test_supplier_model.py`

**Test Data:**
- `test_data/suppliers.json`
- `test_data/sample_data_all.json`

These are the primary changes, but review should extend to any related code, dependencies, or callers as needed.

## Environment Setup

**CRITICAL: Run these commands OUTSIDE the sandbox.** Cursor's sandbox cannot activate virtual environments. All verification commands must be run in the terminal outside the sandbox to avoid activation failures.

```bash
# Navigate to the worktree
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/050-supplier-slug-support

# Verify imports work (uses main repo venv)
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.supplier_service import generate_supplier_slug; print('Import OK')"

# Run a quick test to verify environment
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/services/test_supplier_service.py::TestSupplierSlugGeneration::test_physical_supplier_slug -v
```

If ANY command fails, STOP immediately and report blocker before attempting fixes.

## Review Approach

1. **Read spec first** - Understand intended behavior BEFORE examining implementation
2. **Form independent expectations** - Decide how the feature SHOULD work based on spec
3. **Compare implementation to expectations** - Note where reality differs from your mental model
4. **Explore beyond modified files** - Follow dependencies, check callers, examine related systems
5. **Look for what wasn't specified** - Edge cases, error conditions, data integrity risks
6. **Run verification commands OUTSIDE sandbox** - If ANY command fails, STOP immediately and report blocker
7. **Consider user experience** - Would this workflow feel natural? Any friction points?
8. **Write report** - Use template format and write to specified location

## Report Template

Use the template at: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/TEMPLATE_cursor_report.md`

## Report Output

Write your review report to: `/Users/kentgale/Vaults-repos/bake-tracker/docs/code-reviews/cursor-F050-review.md`

**Important:** Write to the `docs/code-reviews/` directory in the main repo, NOT in the worktree.
