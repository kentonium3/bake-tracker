# F050: Supplier Portable Identification (Slug Support)

**Version**: 1.0
**Priority**: MEDIUM
**Type**: Data Model + Service Layer + Import/Export

---

## Executive Summary

Current gaps:
- ❌ Suppliers lack portable identifiers (ID-based references fail across environments)
- ❌ Product import/export cannot reliably preserve supplier associations
- ❌ Supplier import/export functionality doesn't exist
- ❌ Import services use fragile name/city/state tuple matching

This spec adds slug-based identification to suppliers, enabling reliable cross-environment data portability and aligning with existing ingredient/material slug patterns.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Supplier Model
├─ ✅ name, city, state, zip_code fields
├─ ✅ supplier_type (physical/online)
├─ ✅ Physical vs online validation
└─ ❌ NO slug field (ID-based only)

Product Model
├─ ✅ preferred_supplier_id (FK to Supplier)
└─ ❌ NO slug-based supplier resolution

Import/Export Service
├─ ✅ Exports/imports 6 entities (ingredients, products, recipes, etc.)
├─ ❌ DOES NOT export/import suppliers
└─ ❌ Product import uses fragile ID mapping for suppliers
```

**Target State (COMPLETE):**
```
Supplier Model
├─ ✅ All existing fields
└─ ✅ slug field (unique, indexed, non-nullable)

Product Model
├─ ✅ preferred_supplier_id (FK to Supplier)
└─ ✅ Slug-based supplier resolution in import/export

Import/Export Service
├─ ✅ Exports/imports 7 entities (adds suppliers)
├─ ✅ Suppliers matched by slug (not name/city/state)
└─ ✅ Products resolve preferred_supplier_slug → preferred_supplier_id
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Ingredient Slug Pattern**
   - Find `src/models/ingredient.py` - study `slug` field implementation
   - Study `src/services/ingredient_service.py` - note slug generation in `create_ingredient()`
   - Note unique constraint, index, immutability pattern

2. **Material Slug Pattern**
   - Find `src/models/material.py` - study `slug` field implementation
   - Study `src/services/material_catalog_service.py` - note slug generation
   - Note conflict resolution (numeric suffix approach)

3. **Supplier Model Current State**
   - Find `src/models/supplier.py` - understand current structure
   - Study `supplier_type` validation (physical vs online)
   - Note required fields for each type (city/state/zip for physical, website_url for online)

4. **Product-Supplier Relationship**
   - Find `src/models/product.py` - study `preferred_supplier_id` FK
   - Study `preferred_supplier` relationship definition
   - Note optional nature (products can exist without preferred supplier)

5. **Import/Export Patterns**
   - Find `src/services/enhanced_import_service.py` - study FK resolution patterns
   - Study how ingredient_slug resolution works in product import
   - Note dry-run, skip-on-error, merge modes
   - Find `src/services/denormalized_export_service.py` - study export structure

6. **Test Data Structure**
   - Find `test_data/suppliers.json` - study current export format (6 suppliers)
   - Note fields: id, name, display_name, location, full_address, is_active, notes
   - Understand this needs slug augmentation

---

## Requirements Reference

This specification implements:
- **REQ-SUP-001 through REQ-SUP-007**: Supplier slug field requirements
- **REQ-SUP-008 through REQ-SUP-011**: Product export requirements
- **REQ-SUP-012 through REQ-SUP-016**: Product import requirements
- **REQ-SUP-017 through REQ-SUP-021**: Supplier import/export requirements
- **REQ-SUP-022 through REQ-SUP-026**: Migration requirements
- **REQ-SUP-NFR-001 through REQ-SUP-NFR-010**: Non-functional requirements

From: `docs/requirements/req_suppliers.md` (v2.0)

---

## Functional Requirements

### FR-1: Add Slug Field to Supplier Model

**What it must do:**
- Add `slug` field to Supplier model (String, max 100 chars, unique, indexed, non-nullable)
- Auto-generate slug on supplier creation
- Validate slug uniqueness before saving
- Prevent slug modification after creation (immutable)

**Pattern reference:** Study `src/models/ingredient.py` and `src/models/material.py` slug implementations - copy pattern exactly

**Slug generation rules:**
- Physical suppliers: `{name}_{city}_{state}` (e.g., `wegmans_burlington_ma`)
- Online suppliers: `{name}` (e.g., `king_arthur_baking`)
- Normalization: lowercase, spaces→underscores, remove non-alphanumeric except underscores
- Conflict resolution: append `_2`, `_3`, etc. if slug exists

**Success criteria:**
- [ ] Supplier model includes slug field with unique constraint and index
- [ ] Slug auto-generates on supplier creation via service layer
- [ ] Physical supplier slug follows `{name}_{city}_{state}` pattern
- [ ] Online supplier slug follows `{name}` pattern
- [ ] Slug conflicts resolve automatically with numeric suffixes
- [ ] Slug validation prevents empty/invalid characters
- [ ] Slug immutability enforced (cannot modify after creation)

---

### FR-2: Migrate Existing Suppliers with Slugs

**What it must do:**
- Generate slugs for all existing suppliers in database
- Handle slug conflicts with numeric suffixes
- Log all conflict resolutions for review
- Update `test_data/suppliers.json` with generated slugs
- Validate all suppliers have unique slugs after migration

**Pattern reference:** Study how ingredient/material migrations handle data updates

**Business rules:**
- Slug generation must be deterministic (same inputs → same output)
- "Unknown" supplier (id=1) gets slug `unknown_unknown_xx`
- Conflict log must identify which suppliers received suffixes

**Success criteria:**
- [ ] All existing suppliers have unique slugs
- [ ] Test data file includes slug field for all 6 suppliers
- [ ] Conflict log generated and reviewed
- [ ] No null slugs in database after migration
- [ ] Migration script validates uniqueness

---

### FR-3: Export Suppliers in JSON Format

**What it must do:**
- Add supplier export to import/export service
- Export suppliers with slug field
- Include all supplier fields (name, city, state, zip, type, url, notes, is_active)
- Export format matches ingredient/material patterns

**Pattern reference:** Study `_export_ingredients()` and `_export_materials()` in export service - copy structure

**Export format:**
```json
{
  "suppliers": [
    {
      "slug": "wegmans_burlington_ma",
      "name": "Wegmans",
      "supplier_type": "physical",
      "city": "Burlington",
      "state": "MA",
      "zip_code": "01803",
      "street_address": "53 Third Avenue",
      "website_url": null,
      "is_active": true,
      "notes": null
    },
    {
      "slug": "king_arthur_baking",
      "name": "King Arthur Baking",
      "supplier_type": "online",
      "website_url": "https://www.kingarthurbaking.com",
      "city": null,
      "state": null,
      "zip_code": null,
      "street_address": null,
      "is_active": true,
      "notes": null
    }
  ],
  "metadata": {
    "exported_at": "2026-01-12",
    "count": 2
  }
}
```

**Success criteria:**
- [ ] Export service includes supplier export capability
- [ ] suppliers.json file created in export directory
- [ ] Export includes slug field
- [ ] Export format matches ingredient/material patterns
- [ ] Metadata includes count and timestamp

---

### FR-4: Import Suppliers with Slug Matching

**What it must do:**
- Add supplier import to import/export service
- Match suppliers by slug (not name/city/state tuple)
- Support merge mode (update existing + add new)
- Support skip mode (add new only)
- Validate supplier data before import

**Pattern reference:** Study ingredient import in enhanced_import_service.py - copy FK resolution pattern

**Business rules:**
- Slug match = existing supplier (update or skip based on mode)
- No slug match = new supplier (create)
- Physical suppliers must have city/state/zip
- Online suppliers must have website_url
- Validation errors prevent import of that supplier (skip-on-error mode)

**Success criteria:**
- [ ] Import service matches suppliers by slug
- [ ] Merge mode updates existing suppliers
- [ ] Skip mode ignores existing suppliers
- [ ] New suppliers created with slug
- [ ] Validation prevents incomplete supplier records
- [ ] Import works with test_data/suppliers.json

---

### FR-5: Export Products with Supplier Slug References

**What it must do:**
- Add `preferred_supplier_slug` to product export
- Add `preferred_supplier_name` for human readability
- Maintain `preferred_supplier_id` for backward compatibility
- Handle products without preferred supplier (export null/None)

**Pattern reference:** Study how products currently export ingredient_slug references

**Export format update:**
```json
{
  "products": [
    {
      "ingredient_slug": "bread_flour",
      "brand": "King Arthur",
      "product_name": "All-Purpose Flour",
      "preferred_supplier_id": 3,
      "preferred_supplier_slug": "wegmans_burlington_ma",
      "preferred_supplier_name": "Wegmans"
    }
  ]
}
```

**Success criteria:**
- [ ] Product export includes preferred_supplier_slug
- [ ] Product export includes preferred_supplier_name
- [ ] Product export maintains preferred_supplier_id
- [ ] Products without supplier export null values
- [ ] Backward compatibility maintained (old exports still import)

---

### FR-6: Import Products with Supplier Slug Resolution

**What it must do:**
- Resolve `preferred_supplier_slug` to `preferred_supplier_id` during import
- Fall back to `preferred_supplier_id` if slug not present (legacy support)
- Log warnings when supplier slug cannot be resolved
- Allow products to import without supplier (optional field)
- Validate supplier exists before linking

**Pattern reference:** Study ingredient_slug → ingredient_id resolution in product import

**Resolution logic:**
1. If `preferred_supplier_slug` present → resolve to supplier ID
2. If slug not found → log warning, skip supplier association
3. If `preferred_supplier_slug` absent but `preferred_supplier_id` present → use ID (legacy)
4. If both absent → product imports without supplier

**Success criteria:**
- [ ] Product import resolves preferred_supplier_slug correctly
- [ ] Product import falls back to ID for legacy files
- [ ] Missing supplier warnings are actionable (include supplier slug/name)
- [ ] Products import without suppliers when not specified
- [ ] Import validates supplier exists

---

### FR-7: Support Import/Export Dry-Run and Validation

**What it must do:**
- Support dry-run mode for supplier import (preview without DB changes)
- Validate supplier slugs before import
- Preview supplier resolutions (new vs existing)
- Report validation errors without failing import

**Pattern reference:** Study dry-run implementation in enhanced_import_service.py

**Success criteria:**
- [ ] Dry-run mode previews supplier import without DB changes
- [ ] Validation identifies missing/invalid suppliers
- [ ] Preview shows which suppliers are new vs existing
- [ ] Validation errors reported clearly

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Supplier slug editing UI (slugs are immutable)
- ❌ Supplier merge/deduplication tools (future Phase 5)
- ❌ Slug aliases (multiple slugs → one supplier) (future enhancement)
- ❌ Bulk slug regeneration with reference migration (manual SQL only)
- ❌ Supplier slug history tracking (future enhancement)
- ❌ Shopping list supplier organization (future feature - placeholder in requirements)
- ❌ Web version e-commerce integration (future phase - placeholder in requirements)
- ❌ Supplier advertising platform (future phase - placeholder in requirements)

---

## Success Criteria

**Complete when:**

### Supplier Model
- [ ] Slug field added with unique constraint and index
- [ ] Slug auto-generates on creation
- [ ] Slug conflicts resolve with numeric suffixes
- [ ] Slug immutability enforced
- [ ] Validation prevents empty/invalid slugs

### Migration
- [ ] All existing suppliers have unique slugs
- [ ] Test data file updated with slugs
- [ ] Conflict log generated and reviewed
- [ ] No null slugs in database

### Export
- [ ] Supplier export creates suppliers.json
- [ ] Product export includes preferred_supplier_slug
- [ ] Export format matches ingredient/material patterns
- [ ] Backward compatibility maintained

### Import
- [ ] Supplier import matches by slug
- [ ] Product import resolves supplier slug → ID
- [ ] Merge/skip modes work correctly
- [ ] Legacy imports (without slugs) still function
- [ ] Validation errors are actionable

### Testing
- [ ] Unit tests for slug generation and validation
- [ ] Integration tests for supplier import/export
- [ ] Integration tests for product supplier resolution
- [ ] Round-trip test: export → fresh DB → import → verify associations
- [ ] Legacy import test: old file without slugs still works

### Quality
- [ ] Code follows ingredient/material slug patterns exactly
- [ ] Error handling matches existing import/export patterns
- [ ] Service layer naming conventions consistent
- [ ] No code duplication (DRY principle)

---

## Architecture Principles

### Slug Generation

**Immutability Principle:**
- Slugs are generated once at creation and never modified
- Slug represents supplier identity at creation time, not current state
- If supplier name/city/state changes, slug remains unchanged

**Rationale:** Maintains referential integrity across exports. Product exports referencing supplier slugs remain valid even if supplier details change.

### Pattern Matching

**Ingredient/Material Slug Pattern Consistency:**
Supplier slugs must match ingredient/material slug patterns exactly:
- Same normalization rules (lowercase, spaces→underscores)
- Same conflict resolution (numeric suffixes)
- Same immutability enforcement
- Same validation rules
- Same service layer slug generation approach

**Rationale:** Consistency reduces cognitive load, makes codebase predictable, enables code reuse.

### Import/Export Architecture

**Slug-Based FK Resolution:**
- Portable references use slugs (ingredient_slug, material_slug, supplier_slug)
- Database references use IDs (ingredient_id, material_id, preferred_supplier_id)
- Import resolves slug → ID at import time
- Export includes both slug (portable) and ID (backward compat)

**Rationale:** Enables cross-environment data portability while maintaining database referential integrity.

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Slugs enforce uniqueness via database constraint
- FK resolution validates supplier exists before linking
- Migration validates all suppliers have unique slugs
- Import validation prevents incomplete supplier records

✅ **Principle II: Layered Architecture**
- Service layer handles slug generation (not model)
- Import/export logic in service layer (not mixed with UI)
- FK resolution through fk_resolver_service pattern
- Model validation separate from business logic

✅ **Principle VII: Pragmatic Aspiration**
- Builds for today (desktop import/export) while architecting for tomorrow (web/mobile sync)
- Slug-based identification enables future multi-environment workflows
- Backward compatibility ensures smooth transition
- Immutable slugs prevent future migration headaches

✅ **Principle VIII: Pattern Consistency**
- Follows ingredient/material slug patterns exactly
- Reuses FK resolution patterns from enhanced_import_service
- Export format matches existing entity patterns
- Service layer naming conventions consistent

---

## Risk Considerations

**Risk: Slug conflicts during migration**
- Context: 6 existing suppliers, potential for name collisions
- Mitigation: Numeric suffix resolution, conflict logging for manual review

**Risk: Legacy import files without slugs break**
- Context: Existing export files may not have supplier_slug fields
- Mitigation: Fall back to ID-based resolution, maintain backward compatibility

**Risk: Product imports fail if supplier missing**
- Context: Product catalogs may reference suppliers not in target database
- Mitigation: Validation warnings (not errors), allow import without supplier link

**Risk: Slug generation inconsistency across environments**
- Context: Different environments might generate different slugs for same supplier
- Mitigation: Deterministic slug generation, clear normalization rules, comprehensive tests

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `src/models/ingredient.py` slug field → apply to Supplier model
- Study `src/services/ingredient_service.py` slug generation → apply to SupplierService
- Study `src/services/enhanced_import_service.py` FK resolution → apply to supplier/product import
- Study `src/services/denormalized_export_service.py` export patterns → apply to supplier export

**Key Patterns to Copy:**
- Ingredient slug generation → Supplier slug generation (exact parallel)
- Material slug conflict resolution → Supplier conflict resolution (exact parallel)
- ingredient_slug in Product export → preferred_supplier_slug in Product export (exact parallel)
- ingredient_slug → ingredient_id resolution → preferred_supplier_slug → preferred_supplier_id resolution

**Focus Areas:**
- Slug field implementation must match ingredient/material exactly (unique constraint, index, immutability)
- Migration script must be idempotent (safe to run multiple times)
- Import/export must maintain backward compatibility (existing files still work)
- Test data update critical (test_data/suppliers.json needs slugs)
- FK resolution warnings must be actionable (include supplier name/slug for debugging)

**Migration Workflow:**
```
1. Add slug column (nullable initially)
2. Generate slugs for existing suppliers
3. Update test data file with slugs
4. Make slug non-nullable
5. Add unique constraint and index
6. Validate all suppliers have unique slugs
```

**Testing Strategy:**
- Unit test slug generation for physical suppliers (name_city_state)
- Unit test slug generation for online suppliers (name)
- Unit test conflict resolution (numeric suffixes)
- Integration test supplier export (creates suppliers.json)
- Integration test supplier import (matches by slug)
- Integration test product import (resolves supplier slug)
- Round-trip test (export → import → verify associations)
- Legacy test (old export without slugs still imports)

---

**END OF SPECIFICATION**
