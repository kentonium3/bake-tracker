# Quickstart: Field Naming Consistency Refactor

## Pre-Implementation Checklist

Before starting implementation, verify:

- [ ] Database has been exported to JSON backup
- [ ] Export file saved to safe location outside project directory
- [ ] Record counts documented from current database:
  - [ ] Ingredients: ____
  - [ ] Products: ____
  - [ ] Purchases: ____
  - [ ] Inventory Items: ____
  - [ ] Recipes: ____
  - [ ] Events: ____
  - [ ] Recipients: ____

## Verification Checklist

### After Model Changes

```bash
# Verify old field names removed from Product model
grep -n "purchase_unit\|purchase_quantity" src/models/product.py
# Expected: No matches (or only in comments explaining history)

# Verify new field names present
grep -n "package_unit\|package_unit_quantity" src/models/product.py
# Expected: Column definitions found
```

### After All Code Changes

```bash
# Comprehensive check for old field names in Python code
grep -rn "purchase_unit\|purchase_quantity" src/ --include="*.py"
# Expected: No matches in code (only in comments if any)

# Verify no PantryItem references (should already be clean)
grep -rni "pantryitem\|pantry_items" src/models/ src/services/
# Expected: No matches
```

### Test Suite Validation

```bash
# Run full test suite
pytest src/tests -v

# Expected: All tests pass
# If failures: Check test file references to old field names
```

### UI Label Verification

Manual verification required:

- [ ] "Pantry" tab still visible in main window
- [ ] "Pantry" label appears in inventory forms
- [ ] No "Inventory" labels where "Pantry" should appear

### Import/Export Cycle Verification

1. **Export with new code**:
   - [ ] Export creates valid JSON
   - [ ] JSON contains `package_unit` and `package_unit_quantity` fields
   - [ ] JSON does NOT contain `purchase_unit` or `purchase_quantity`

2. **Delete database**:
   ```bash
   rm data/bake_tracker.db data/bake_tracker.db-wal data/bake_tracker.db-shm
   ```

3. **Import to fresh database**:
   - [ ] Import completes without errors
   - [ ] No validation warnings

4. **Verify record counts**:
   - [ ] Ingredients: ____ (matches pre-implementation)
   - [ ] Products: ____ (matches pre-implementation)
   - [ ] Purchases: ____ (matches pre-implementation)
   - [ ] Inventory Items: ____ (matches pre-implementation)
   - [ ] Recipes: ____ (matches pre-implementation)
   - [ ] Events: ____ (matches pre-implementation)
   - [ ] Recipients: ____ (matches pre-implementation)

## Documentation Checklist

- [ ] `docs/design/import_export_specification.md` version updated to 3.4
- [ ] Changelog entry added documenting field renames
- [ ] Products entity schema updated with new field names
- [ ] Appendix C example updated with new field names

## Sample Data Checklist

Update these files to use new field names:

### examples/import/
- [ ] `ai_generated_sample.json`
- [ ] `combined_import.json`
- [ ] `simple_ingredients.json`
- [ ] `test_errors.json`
- [ ] `test_data.json`
- [ ] `test_data_v2.json`
- [ ] `test_data_v2_original.json`
- [ ] `README.md`

### test_data/
- [ ] `sample_catalog.json`
- [ ] `sample_data.json`
- [ ] `sample_data.json.backup`
- [ ] `README.md`

## Success Criteria Validation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SC-001: Zero matches for old field names | [ ] | `grep` output |
| SC-002: Zero pantry matches in internal code | [ ] | `grep` output |
| SC-003: All tests pass | [ ] | `pytest` output |
| SC-004: UI displays "Pantry" | [ ] | Manual verification |
| SC-005: 100% data preserved | [ ] | Record counts match |
| SC-006: Import/export spec v3.4 | [ ] | File version header |

## Rollback Plan

If issues discovered after implementation:

1. Delete corrupted database files
2. Restore from pre-implementation export JSON
3. Revert code changes via git: `git checkout main -- src/`
4. Import backup JSON to restored codebase
