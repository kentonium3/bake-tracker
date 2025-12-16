# Cursor Code Review Prompt - Feature 021: Field Naming Consistency

## Role

You are a senior software engineer performing an independent code review of Feature 021 (field-naming-consistency). This feature refactored field names for consistency between the SQLAlchemy model and JSON import/export format.

## Feature Summary

**Two terminology refactors:**
1. `purchase_unit` → `package_unit` and `purchase_quantity` → `package_unit_quantity` (in Product model and all dependent code)
2. `pantry` → `inventory` in test function names, variables, and docstrings (internal terminology alignment)

**Scope:**
- Model layer: Product class column names
- Service layer: 9 service files updated
- UI layer: 5 UI files + validators.py
- Test layer: 18+ test files
- Documentation: import_export_specification.md bumped to v3.4
- Sample data: All JSON files in examples/ and test_data/

## Files to Review

### Model Layer (WP01)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/models/product.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/models/recipe.py`

### Service Layer (WP02)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/product_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/import_export_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/recipe_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/inventory_item_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/finished_unit_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/event_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/catalog_import_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/services/assembly_service.py`

### UI Layer (WP03)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/ui/inventory_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/ui/ingredients_tab.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/ui/forms/recipe_form.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/ui/forms/ingredient_form.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/ui/widgets/data_table.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/utils/validators.py`

### Test Layer (WP04) - Key Files
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/conftest.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/test_models.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/test_validators.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/test_services.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/services/test_recipe_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/services/test_production_service.py`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/src/tests/services/test_inventory_item_service.py`

### Documentation (WP05)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/docs/design/import_export_specification.md`

### Sample Data Files (WP05)
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/examples/import/README.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/examples/import/ai_generated_sample.json`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/examples/import/combined_import.json`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/examples/test_data.json`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/test_data/sample_catalog.json`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/test_data/sample_data.json`

### Specification Documents
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/kitty-specs/021-field-naming-consistency/spec.md`
- `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/kitty-specs/021-field-naming-consistency/plan.md`

## Review Checklist

### 1. Completeness
- [ ] All `purchase_unit` references replaced with `package_unit` in Python code
- [ ] All `purchase_quantity` references replaced with `package_unit_quantity` in Python code
- [ ] All `pantry` references in test function names/variables replaced with `inventory`
- [ ] JSON field names in import_export_service.py match model attributes exactly
- [ ] Import/export spec version is 3.4 with proper changelog

### 2. Consistency
- [ ] No mixed old/new terminology in any file
- [ ] All JSON sample files use new field names
- [ ] Documentation examples match implementation

### 3. Correctness
- [ ] No logic changes beyond field name updates
- [ ] UI still displays "Pantry" to users (user-facing strings preserved)
- [ ] Type hints updated where applicable
- [ ] No new lint errors introduced

### 4. Verification Commands

Run these commands to verify the refactor is complete:

```bash
# Should return zero matches
grep -rn "purchase_unit\|purchase_quantity" src/ --include="*.py"
grep -rn "purchase_unit\|purchase_quantity" docs/design/
grep -rn "purchase_unit\|purchase_quantity" examples/ test_data/

# Should return only UI string literals and historical comments
grep -rni "pantry" src/ --include="*.py"

# All tests should pass
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency
python3 -m pytest src/tests -v
```

## Output Format

Please output your findings to:
`/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/021-field-naming-consistency/docs/code-reviews/cursor-F021-review.md`

Use this format:

```markdown
# Cursor Code Review: Feature 021 - Field Naming Consistency

**Date:** [DATE]
**Reviewer:** Cursor (AI Code Review)
**Feature:** 021-field-naming-consistency
**Branch:** 021-field-naming-consistency

## Summary

[Brief overview of findings]

## Verification Results

### grep Validation
- `purchase_unit`/`purchase_quantity` in src/: [PASS/FAIL - count]
- `purchase_unit`/`purchase_quantity` in docs/: [PASS/FAIL - count]
- `purchase_unit`/`purchase_quantity` in examples/test_data/: [PASS/FAIL - count]
- `pantry` in tests (unacceptable matches): [PASS/FAIL - count]

### Test Results
- pytest result: [PASS/FAIL - X passed, Y skipped, Z failed]

## Findings

### Critical Issues
[Any blocking issues that must be fixed]

### Warnings
[Non-blocking concerns]

### Observations
[General observations about code quality]

## Files Reviewed

[List of files reviewed with disposition]

| File | Status | Notes |
|------|--------|-------|
| src/models/product.py | ✅ Approved | [notes] |
| ... | ... | ... |

## Conclusion

[APPROVED / APPROVED WITH CHANGES / NEEDS REVISION]

[Final summary]
```

## Additional Context

- The project uses SQLAlchemy 2.x with type hints
- CustomTkinter for UI
- pytest for testing (689 tests pass, 12 skipped as expected)
- The worktree is isolated from main branch
- Known issue: 19 tests in test_catalog_import_service.py may fail due to pre-existing test isolation issue (not related to this feature)
