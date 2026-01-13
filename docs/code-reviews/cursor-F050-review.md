# Code Review Report: F050 - Supplier Slug Support

**Reviewer:** Cursor (Independent Review)
**Date:** 2026-01-13
**Feature Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/050-supplier-slug-support/kitty-specs/050-supplier-slug-support/spec.md`

## Executive Summary
Adds slug support for suppliers plus slug-based import/export resolution. Core behaviors are partially implemented, but imports currently reject online suppliers and “merge” mode never updates existing suppliers, breaking key acceptance scenarios.

## Review Scope

**Primary Files Modified:**
- `.worktrees/050-supplier-slug-support/src/models/supplier.py`
- `.worktrees/050-supplier-slug-support/src/services/supplier_service.py`
- `.worktrees/050-supplier-slug-support/src/services/import_export_service.py`
- `.worktrees/050-supplier-slug-support/src/services/enhanced_import_service.py`
- `.worktrees/050-supplier-slug-support/src/services/fk_resolver_service.py`
- `.worktrees/050-supplier-slug-support/src/utils/slug_utils.py`
- `.worktrees/050-supplier-slug-support/src/tests/services/test_supplier_service.py`
- `.worktrees/050-supplier-slug-support/src/tests/integration/test_import_export_027.py`
- `.worktrees/050-supplier-slug-support/src/tests/models/test_supplier_model.py`

**Additional Code Examined:**
- Test data (`test_data/suppliers.json`, `test_data/sample_data_all.json`)
- Slug utilities and FK resolver helpers reused across imports

## Environment Verification

**Setup Process:**
```bash
cd /Users/kentgale/Vaults-repos/bake-tracker/.worktrees/050-supplier-slug-support
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -c "from src.services.supplier_service import generate_supplier_slug; print('Import OK')"
/Users/kentgale/Vaults-repos/bake-tracker/venv/bin/python -m pytest src/tests/services/test_supplier_service.py::TestSupplierSlugGeneration::test_physical_supplier_slug -v
```

**Results:**
- Initial attempt failed in sandbox due to venv permission (`pyvenv.cfg`); reran with full permissions and succeeded.
- Import check passed (`Import OK`), and targeted pytest passed (1 test).

---

## Findings

### Critical Issues

**Online supplier imports are blocked**
- **Location:** `import_export_service.py` supplier import path
- **Problem:** Import requires `city` and `state` for every supplier, even when `supplier_type` is `online`, causing valid online suppliers with name-only slugs to be rejected.
- **Impact:** Online suppliers cannot be imported or restored from backups, failing FR-002/FR-008 and acceptance scenario 4 in the spec.
- **Recommendation:** Relax validation to allow name-only records when `supplier_type == "online"` and generate slugs from name only. Ensure downstream lookups/slug maps handle online suppliers.
```2736:2794:.worktrees/050-supplier-slug-support/src/services/import_export_service.py
                        import_slug = supplier_data.get("slug")
                        supplier_type = supplier_data.get("supplier_type", "physical")

                        if not name or not city or not state:
                            result.add_error(
                                "supplier",
                                name or "unknown",
                                "Missing required fields: name, city, or state"
                            )
                            continue
...
                        slug = import_slug
                        if not slug:
                            slug = generate_supplier_slug(
                                name=name,
                                supplier_type=supplier_type,
                                city=city,
                                state=state,
                                session=session,
                            )
```

**“Merge” mode never updates existing suppliers (acts as skip-only)**
- **Location:** `import_export_service.py` supplier import path
- **Problem:** In merge mode (`skip_duplicates=True`), existing suppliers matched by slug or name/city/state are always skipped; no fields are merged. FR-009 requires merge mode to update explicitly provided fields while adding new suppliers. Current behavior is effectively “skip” mode only.
- **Impact:** Supplier updates in imports are ignored; round-trips can’t propagate supplier changes, violating spec and degrading data portability.
- **Recommendation:** Implement sparse updates for existing suppliers in merge mode (respect slug immutability). Skip-only behavior should be a separate mode.
```2620:2626:.worktrees/050-supplier-slug-support/src/services/import_export_service.py
    if mode not in ("merge", "replace"):
        raise ValueError(...)
    result = ImportResult()
    skip_duplicates = mode == "merge"
```
```2748:2767:.worktrees/050-supplier-slug-support/src/services/import_export_service.py
                        if skip_duplicates:
                            # Feature 050: Prefer slug-based matching, fallback to name+city+state
                            existing = None
                            if import_slug:
                                existing = session.query(Supplier).filter_by(slug=import_slug).first()
                            if not existing:
                                existing = session.query(Supplier).filter_by(
                                    name=name,
                                    city=city,
                                    state=state,
                                ).first()
                            if existing:
                                result.add_skip("supplier", f"{name} ({city}, {state})", "Already exists")
                                ...
                                continue
```

**FK resolver / context-rich import also blocks online suppliers**
- **Location:** `enhanced_import_service.py` supplier creation helper
- **Problem:** FK resolution path requires `city`, `state`, and `zip_code` for every supplier, regardless of `supplier_type`, so online suppliers cannot be created during FK resolution or context-rich imports.
- **Impact:** Slug-based FK resolution fails for online suppliers, breaking cross-environment portability for those records.
- **Recommendation:** Allow name-only for online suppliers and generate slugs with the online pattern; only enforce city/state/zip for physical suppliers.
```840:879:.worktrees/050-supplier-slug-support/src/services/enhanced_import_service.py
            name = record.get("supplier_name") or record.get("name")
            city = record.get("city")
            state = record.get("state")
            zip_code = record.get("zip_code") or record.get("zip")
            supplier_type = record.get("supplier_type", "physical")

            if not name:
                return ("failed", "Missing required field: name")
            if not city:
                return ("failed", "Missing required field: city")
            if not state:
                return ("failed", "Missing required field: state")
            if not zip_code:
                return ("failed", "Missing required field: zip_code")

            # Feature 050: Generate slug for supplier
            # Prefer slug from record if provided, otherwise generate
            slug = record.get("slug")
            if not slug:
                slug = generate_supplier_slug(
                    name=name,
                    supplier_type=supplier_type,
                    city=city,
                    state=state,
                    session=session,
                )
```

### Major Concerns
None beyond the critical items above.

### Minor Issues
None observed beyond the above blocking gaps.

### Positive Observations
- Slug immutability is enforced at the service layer with clear error messaging, preventing accidental slug drift on updates.
```433:446:.worktrees/050-supplier-slug-support/src/services/supplier_service.py
    # Feature 050: Slug immutability enforcement
    if "slug" in kwargs:
        new_slug = kwargs["slug"]
        if new_slug != supplier.slug:
            raise ValueError(
                f"Slug cannot be modified after creation. "
                f"Current: '{supplier.slug}', Attempted: '{new_slug}'. "
                f"Slugs are immutable to preserve data portability."
            )
```

## Spec Compliance Analysis
- Core slug generation and export wiring are present (supplier slug field, product exports include `preferred_supplier_slug`/`preferred_supplier_name`, slug-based lookup precedence with ID fallback).
- Import paths violate acceptance scenarios for online suppliers (User Story 1 & 4) and don’t honor merge semantics (FR-009).
- Dry-run preview exists and returns counts without DB changes (FR-014), but underlying supplier handling still suffers from the above blocking gaps.
- Migration helper to generate slugs exists but is not exercised here; primary risk remains import behavior.

## Code Quality Assessment
**Consistency with Codebase:** Slug generation reuses existing ingredient/material patterns; immutability guard follows established service validation style.
**Maintainability:** Supplier import logic is centralized but currently conflates merge vs skip; once fixed, sparse-update handling should stay localized.
**Test Coverage:** New tests cover slug generation, immutability, and slug-based round-trips for physical suppliers. No coverage for online supplier imports or merge-mode updates, leaving the critical gaps undetected.
**Dependencies & Integration:** Product imports/export correctly include slug-based supplier resolution and legacy ID fallback; FK resolver aligns with slug approach but needs online allowance.

## Recommendations Priority
**Must Fix Before Merge:**
1. Allow online suppliers (name-only) in all import paths: normalized import/export (`import_export_service`), context-rich/FK resolution (`enhanced_import_service`), and FK resolver creation helpers. Generate slugs with the online pattern when supplier_type is online.
2. Implement true merge semantics for supplier import: when merge mode is requested, update existing suppliers with explicitly provided fields (excluding slug), rather than skipping them.

**Should Fix Soon:**
1. Add tests for online supplier import (normalized and context-rich) and for merge-mode updates to prevent regressions.

**Consider for Future:**
1. Ensure the slug migration helper is invoked via a migration script/command so existing deployments gain slugs automatically.

## Overall Assessment
Needs revision. Slug fields and exports are wired, but imports currently reject online suppliers and never merge updates, so the feature does not meet the spec’s core portability and merge requirements. Fixing the import validation/merge semantics and adding coverage for these cases is required before shipping.
