# Research Decision Log

## Summary

- **Feature**: 021-field-naming-consistency
- **Date**: 2025-12-15
- **Researchers**: Claude Code
- **Open Questions**: None - scope is well-defined

## Decisions & Rationale

| Decision | Rationale | Evidence | Status |
|----------|-----------|----------|--------|
| Rename `purchase_unit` to `package_unit` | "purchase" implies transaction; "package" describes the product's physical contents | Spec requirement FR-001, FR-003 | Final |
| Rename `purchase_quantity` to `package_unit_quantity` | Matches new naming; describes quantity per package | Spec requirement FR-002, FR-003 | Final |
| Keep `InventoryItem` model name | Already correctly named (was never `PantryItem`) | Codebase search found no `PantryItem` references | Final |
| Update import/export spec to v3.4 | Document field name changes; maintain audit trail | Spec requirement FR-017, FR-019 | Final |
| No backward compatibility for old import field names | Simplicity; users must update import files | Spec edge case declaration | Final |
| Export/reset/import for schema change | Constitution v1.2.0 requires this approach (no SQL migrations) | Constitution Principle VI | Final |

## Evidence Highlights

### Codebase Analysis

**Files affected by `purchase_unit`/`purchase_quantity` rename:**

| Category | Count | Files |
|----------|-------|-------|
| Model | 1 | `src/models/product.py` |
| Services | 7 | `product_service.py`, `import_export_service.py`, `recipe_service.py`, etc. |
| Tests | 18 | Various test files in `src/tests/` |
| UI | 4 | `inventory_tab.py`, `ingredients_tab.py`, forms |
| Sample JSON | ~10 | `examples/`, `test_data/` directories |
| Documentation | 2 | `import_export_specification.md`, README |

**`InventoryItem` model state:**
- Model file exists: `src/models/inventory_item.py`
- Table name: `inventory_items` (correct)
- No `PantryItem` or `pantry_items` references found in models or services

**Import/Export Service locations requiring change** (lines):
- 233-234: Export product legacy fields
- 1084-1085: Export product current fields
- 2298-2299: Import product fields

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data loss during export/import | Low | High | Verification checklist, record count validation |
| Missed references in codebase | Medium | Medium | Comprehensive grep-based validation |
| Test failures after rename | High (expected) | Low | Update all test references systematically |

## Next Actions

1. Generate implementation plan with work packages
2. Create verification checklist for export/import cycle
3. Proceed to `/spec-kitty.plan` completion
