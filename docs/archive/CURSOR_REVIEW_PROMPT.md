# Independent Code Review Request: Feature 019 - Unit Conversion Simplification

## Role

You are a **senior software engineer** conducting a thorough, independent code review of a significant architectural change. Your review should be critical, detail-oriented, and focus on production readiness. Do not assume the changes are correct - verify them.

## Feature Summary

**Feature 019: Unit Conversion Simplification** removes the `UnitConversion` model and `Ingredient.recipe_unit` field from a baking inventory management application. The previous design required explicit unit conversion records per ingredient; the new design uses a 4-field density model directly on the `Ingredient` model.

### Key Changes

1. **Model Deletion**: Removed `UnitConversion` SQLAlchemy model entirely
2. **Field Removal**: Removed `recipe_unit` from `Ingredient` model
3. **Import/Export Format**: Updated from v3.2 to v3.3 (no longer accepts v3.2)
4. **Service Layer**: Updated `consume_fifo()` to accept `target_unit` parameter instead of relying on `Ingredient.recipe_unit`
5. **Test Updates**: All tests updated to new signatures and format

## Files to Review

### Critical (Model & Schema)
- `src/models/ingredient.py` - Verify `recipe_unit` field removed, density fields present
- `src/models/__init__.py` - Verify `UnitConversion` not exported

### Critical (Services)
- `src/services/import_export_service.py` - v3.3 format handling, version rejection logic
- `src/services/inventory_item_service.py` - `consume_fifo()` signature change
- `src/services/recipe_service.py` - How target_unit is passed through
- `src/services/unit_converter.py` - Density-based conversion logic

### Important (Tests)
- `src/tests/services/test_import_export_service.py` - v3.3 validation tests
- `src/tests/services/test_recipe_service.py` - Recipe aggregation tests
- `src/tests/integration/test_fifo_scenarios.py` - FIFO consumption tests

### Documentation
- `docs/design/import_export_specification.md` - v3.3 format spec
- `docs/feature_proposal_catalog_import.md` - Updated format examples

## Review Checklist

### 1. Correctness
- [ ] Does `consume_fifo()` correctly convert between units using the new density model?
- [ ] Are there any code paths that still expect `UnitConversion` records?
- [ ] Are there any code paths that still read `Ingredient.recipe_unit`?
- [ ] Does v3.2 format rejection work correctly on import?
- [ ] Are there any edge cases where unit conversion could fail silently?

### 2. Data Integrity
- [ ] Could any existing data be corrupted by this migration?
- [ ] Are there foreign key references to `UnitConversion` that weren't cleaned up?
- [ ] Is there any business logic that depended on `recipe_unit` semantics?

### 3. Backward Compatibility
- [ ] Is v3.2 → v3.3 rejection intentional and documented?
- [ ] Are there any exported JSON files that will break?
- [ ] Could users lose data during upgrade?

### 4. Test Coverage
- [ ] Are the new `consume_fifo(target_unit=...)` calls tested with different unit combinations?
- [ ] Is there a test that verifies v3.2 imports are rejected?
- [ ] Are density-based conversions tested for edge cases (missing density values)?

### 5. Code Quality
- [ ] Are there any TODO/FIXME comments that need attention?
- [ ] Are there any dead code paths left behind?
- [ ] Is error handling adequate for conversion failures?
- [ ] Are the changes consistent across all modified files?

### 6. Security
- [ ] Could malformed v3.3 imports cause issues?
- [ ] Are there any injection risks in the import/export logic?

## Commands to Run

```bash
# View the full diff
git diff main..HEAD

# View specific file changes
git diff main..HEAD -- src/services/inventory_item_service.py
git diff main..HEAD -- src/services/import_export_service.py

# Run all tests
cd /Users/kentgale/Vaults-repos/bake-tracker && source venv/bin/activate && cd .worktrees/019-unit-conversion-simplification && pytest src/tests -v

# Search for any remaining references
grep -rn "recipe_unit" src/ --include="*.py" | grep -v "test"
grep -rn "UnitConversion" src/ --include="*.py"
grep -rn "unit_conversions" src/ --include="*.py"
```

## Expected Output

Please provide:

1. **Executive Summary**: Overall assessment (APPROVE / NEEDS CHANGES / REJECT)

2. **Critical Issues**: Any bugs, data integrity risks, or breaking changes found

3. **Concerns**: Non-blocking issues that should be tracked

4. **Questions**: Clarifications needed before approval

5. **Positive Observations**: What was done well

## Context

- **Tech Stack**: Python 3.10+, SQLAlchemy 2.x, SQLite, CustomTkinter
- **Test Status**: 706 tests pass, 12 expected skips
- **Application Type**: Desktop app for personal use (single user)
- **Branch**: `019-unit-conversion-simplification` (worktree)

## Important Notes

- The `baking_ingredients_v32.json` file in the main repo will need to be converted to v3.3 at merge time
- Some files (like `catalog_import_status.md`) don't exist in this worktree
- Archive files may still contain `unit_conversions` references (acceptable - historical)

---

*This review is for Feature 019 of the bake-tracker project. The goal is to catch any issues before merging to main.*
