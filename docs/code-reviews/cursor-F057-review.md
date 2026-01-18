# Code Review Report: F057 - Purchase Management with Provisional Products

**Reviewer:** Cursor (independent)
**Date:** 2026-01-17
**Spec:** `/Users/kentgale/Vaults-repos/bake-tracker/kitty-specs/057-purchase-management-provisional-products/spec.md`

## Verification
- Tests: `pytest src/tests/services/test_product_catalog_service.py -v -k "Provisional" --tb=short` ✅

## Findings (ordered by severity)

1) No product slug generation/storage (FR-007, FR-008)
   Products still have no `slug` column or generation path, and provisional creation (`create_provisional_product`) does not compute or persist any slug or collision-safe identifier. Spec requires product_catalog_service to generate unique slugs for provisional products (with suffixing on collisions). Without slugs, exports/imports and deduping rely solely on loose brand/qty/unit combinations.
   ```20:143:src/models/product.py
   class Product(BaseModel):
       ...  # fields include ingredient_id/brand/package_unit/package_unit_quantity but no slug field
   ```

2) Purchase service bypasses required service boundaries (FR-020/FR-021/FR-023/FR-024)
   `record_purchase` queries Product directly, creates Suppliers inline, and never delegates product lookup, provisional creation, or supplier handling to `product_catalog_service` / `supplier_service`. This violates the service-boundary requirements and makes it impossible for purchase recording to hook into provisional creation or shared supplier logic.
   ```143:181:src/services/purchase_service.py
   product = session.query(Product).filter_by(id=product_id).first()
   ...
   supplier = session.query(Supplier).filter(Supplier.name == store_name).first()
   if not supplier:
       supplier = Supplier(name=store_name, city="Unknown", state="XX", zip_code="00000")
       session.add(supplier)
   ```

3) Review UI does not highlight missing/incomplete fields (FR-013)
   Products tab only prefixes `[REVIEW]` and applies a tag; there is no field-level highlighting to indicate which attributes are incomplete for provisional products. The spec calls for clearly highlighting missing fields during review.
   ```471:490:src/ui/products_tab.py
   if p.get("is_provisional"):
       product_name = f"[REVIEW] {product_name}" if product_name else "[REVIEW]"
   ... tags.append("provisional")
   ```

4) JSON purchase import UI absent (FR-015–FR-019)
   No UI entry point was added for uploading purchase JSON files or navigating to the provisional review queue post-import. Dialogs and menus remain unchanged; the only import behavior lives in services/tests. This leaves the P3 user story unimplemented.

5) Provisional creation lacks slug/collision handling and minimal validation (FR-006/FR-007)
   `create_provisional_product` accepts brand/unit/quantity but performs no slug generation or collision detection and does not validate quantity > 0. Duplicate provisional products with the same brand/unit can be created silently, and spec-mandated slug uniqueness is not enforceable.
   ```203:285:src/services/product_service.py
   product = Product(... is_provisional=True, package_unit=package_unit, package_unit_quantity=package_unit_quantity)
   # no slug generation or uniqueness handling
   ```

## Recommendations
- Add a `slug` field to Product, generate slugs (via product_catalog_service) for all creations—including provisional—with suffixing for collisions; update export/import to use slugs consistently.
- Refactor purchase flows to delegate product lookup/provisional creation and supplier handling to the catalog/supplier services; keep purchase_service focused on purchase + inventory transactions.
- Enhance Products tab review UX to surface missing/incomplete fields (e.g., highlight empty brand/package_unit_quantity/package_type) instead of only prefixing names.
- Implement the UI flow for JSON purchase import with results, provisional creation counts, and navigation to the Needs Review queue.
- Validate `package_unit_quantity > 0` in provisional creation and prevent silent duplicates (slug uniqueness or stronger uniqueness constraint).

## Overall Assessment
Not ready to ship. Core spec items (product slugging, service boundaries, UI import flow, review highlighting) are missing, and provisional creation lacks uniqueness/validation safeguards.***
