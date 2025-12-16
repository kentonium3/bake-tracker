# TD-003: Fix test_catalog_import_service.py Schema Mismatch

## Context

Refer to `.kittify/memory/constitution.md` for project principles.

## Issue

19 pre-existing test failures in `tests/test_catalog_import_service.py` due to schema field naming mismatch.

**Root cause:** Tests reference `purchase_unit` but schema uses `package_unit`.

This is part of the broader naming consistency work identified in Feature 021 (Field Naming Consistency) where:
- `purchase_unit` / `purchase_quantity` → `package_unit` / `package_unit_quantity`

## Scope

1. Update `tests/test_catalog_import_service.py` to use correct field names:
   - `purchase_unit` → `package_unit`
   - `purchase_quantity` → `package_unit_quantity`

2. Verify no other test files have the same mismatch

3. Ensure all 19 failures are resolved

## Prerequisites

- Complete TD-002 (Unit Standardization) first to avoid merge conflicts in test files

## Deliverables

1. Updated `tests/test_catalog_import_service.py` with corrected field names
2. All tests passing

## Testing

Run full test suite — all tests must pass, including the 19 previously failing tests.
