# F082: Product Composite Slug Multi-Tenant Readiness

**Version**: 1.0  
**Date**: 2026-01-28
**Priority**: MEDIUM
**Type**: Export/Import Enhancement

---

## Executive Summary

Product entities currently use composite slug format `{ingredient_slug}:{brand}:{qty}:{unit}` which assumes global uniqueness. This will break in multi-tenant scenarios where two tenants can have identical product combinations.

Current gap:
- ❌ Product composite slug assumes global uniqueness
- ❌ Multi-tenant collision risk: two tenants → same ingredient → same brand → same qty/unit → slug collision

This spec documents the current composite slug pattern and prepares for future multi-tenant migration by adding documentation and future-ready export format.

---

## Problem Statement

**Current State (SINGLE-TENANT WORKS):**
```
Product Composite Slug
├─ Format: "{ingredient_slug}:{brand}:{qty}:{unit}"
├─ Example: "all-purpose-flour:king-arthur:5.0:lb"
├─ Assumption: Global uniqueness across all products
└─ Works for: Single-user desktop application

Export Format:
├─ product_slug includes full composite
└─ Import resolves via composite lookup

Multi-Tenant Problem:
├─ Tenant A: "all-purpose-flour:king-arthur:5.0:lb"
├─ Tenant B: "all-purpose-flour:king-arthur:5.0:lb"  
└─ ❌ Slug collision! Both tenants have identical product
```

**Target State (MULTI-TENANT READY):**
```
Product Composite Slug (Web Phase)
├─ Resolution: (tenant_id, ingredient_id, brand, qty, unit)
├─ Export: Includes ingredient_slug, brand, qty, unit separately
├─ Import: Resolves via ingredient_slug first, then composite match
└─ Ready for: Multi-tenant web deployment

Desktop Phase (This Feature):
├─ Document current composite slug pattern
├─ Add ingredient_slug to product exports (alongside composite)
├─ Update import to resolve ingredient_slug separately
└─ Prepare for web migration without breaking desktop
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Product Model**
   - Find: `src/models/product.py` - Study product slug generation
   - Find: `src/services/product_service.py` - Study create_product() method
   - Note: How composite slug is currently generated and used

2. **Product Export Pattern**
   - Find: `src/services/coordinated_export_service.py` - Study _export_products()
   - Note: Currently exports composite product_slug only

3. **Product Import Pattern**
   - Find: `src/services/enhanced_import_service.py` - Study _import_products()
   - Note: Currently resolves via composite slug lookup

4. **Product FK Resolution**
   - Search: coordinated_export_service.py for product_slug usage
   - Note: Where product references are exported (purchases, inventory, etc.)

---

## Requirements Reference

This specification addresses issues identified in:
- Data Portability Review (2026-01-28) Section 6: "Other Data Portability Issues" - Issue 1: Composite Foreign Keys (Product)

Prepares for future:
- Multi-tenant web deployment (Q3-Q4 2025)
- Tenant-scoped product resolution
- Portable product identification across tenants

---

## Functional Requirements

### FR-1: Document Current Composite Slug Pattern

**What it must do:**
- Add comprehensive inline documentation to product_service.py
- Document composite slug format: `{ingredient_slug}:{brand}:{qty}:{unit}`
- Document why composite slug works for desktop (single-user)
- Document future web requirements (tenant_id in resolution)
- Add code comments marking web migration points

**Pattern reference:** Study existing service documentation patterns

**Success criteria:**
- [ ] product_service.py has detailed composite slug documentation
- [ ] Comments explain single-tenant assumption
- [ ] Comments mark future multi-tenant changes needed
- [ ] Documentation includes examples of composite slugs

---

### FR-2: Add Ingredient Slug to Product Exports

**What it must do:**
- Modify `_export_products()` in coordinated_export_service.py
- Export `ingredient_slug` as separate field (in addition to composite product_slug)
- Export `brand`, `package_qty`, `package_unit` as separate fields (already exists)
- Maintain backward compatibility (product_slug still exported)

**Current Export Format:**
```json
{
  "product_slug": "all-purpose-flour:king-arthur:5.0:lb",
  "brand": "King Arthur",
  "package_qty": 5.0,
  "package_unit": "lb",
  ...
}
```

**New Export Format:**
```json
{
  "product_slug": "all-purpose-flour:king-arthur:5.0:lb",
  "ingredient_slug": "all-purpose-flour",
  "brand": "King Arthur",
  "package_qty": 5.0,
  "package_unit": "lb",
  ...
}
```

**Pattern reference:** Study how finished_units export both recipe_name and recipe_slug

**Success criteria:**
- [ ] products.json exports ingredient_slug field
- [ ] product_slug still exported (backward compatibility)
- [ ] Export tests verify both fields present
- [ ] Manifest updated to reflect new field

---

### FR-3: Update Product Import to Use Ingredient Slug

**What it must do:**
- Modify `_import_products()` in enhanced_import_service.py
- Resolve ingredient_slug to ingredient_id FIRST
- Then resolve product via (ingredient_id, brand, qty, unit) composite lookup
- Fallback to composite product_slug resolution for backward compatibility
- Log when fallback occurs

**Import Resolution Flow:**
```python
# New flow (preferred):
ingredient_id = resolve_ingredient_slug(ingredient_slug)
product = find_by_composite(ingredient_id, brand, qty, unit)

# Fallback flow (legacy):
if not product:
    product = find_by_product_slug(product_slug)
```

**Pattern reference:** Study _import_finished_units() dual resolution (slug + name fallback)

**Success criteria:**
- [ ] Import resolves ingredient_slug to ingredient_id first
- [ ] Import uses (ingredient_id, brand, qty, unit) composite lookup
- [ ] Import falls back to product_slug for legacy data
- [ ] Fallback events logged
- [ ] Import tests cover both resolution paths

---

### FR-4: Add Web Migration Documentation

**What it must do:**
- Create docs/web_migration_notes.md section on product resolution
- Document current desktop implementation (composite slug)
- Document future web implementation (tenant_id + composite)
- Provide migration checklist for web phase
- Include SQL examples for multi-tenant product queries

**Documentation Structure:**
```markdown
## Product Resolution: Desktop → Web Migration

### Desktop Phase (Current)
- Composite slug: {ingredient_slug}:{brand}:{qty}:{unit}
- Global uniqueness assumed

### Web Phase (Future)
- Resolution: (tenant_id, ingredient_id, brand, qty, unit)
- Slug scoped per tenant
- Migration checklist: [...]
```

**Success criteria:**
- [ ] docs/web_migration_notes.md updated with product section
- [ ] Desktop implementation documented
- [ ] Web migration path documented
- [ ] SQL examples provided for web queries
- [ ] Migration checklist included

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ tenant_id field addition (web phase only)
- ❌ Multi-tenant unique constraints (web phase only)
- ❌ Composite unique constraint (tenant_id, ingredient_id, brand, qty, unit)
- ❌ Product slug format changes (keep current format)
- ❌ Product service refactoring (minimal changes only)
- ❌ UI changes (no user-visible impact)

---

## Success Criteria

**Complete when:**

### Documentation
- [ ] product_service.py has comprehensive composite slug documentation
- [ ] Comments explain single-tenant vs multi-tenant resolution
- [ ] docs/web_migration_notes.md updated with product section
- [ ] Migration checklist created for web phase

### Export Format
- [ ] products.json exports ingredient_slug field
- [ ] product_slug still exported (backward compatibility)
- [ ] Export tests verify both fields
- [ ] Export → Import → Export preserves data

### Import Resolution
- [ ] Import resolves ingredient_slug first
- [ ] Import uses composite (ingredient_id, brand, qty, unit) lookup
- [ ] Import falls back to product_slug for legacy
- [ ] Import tests cover both paths
- [ ] Fallback events logged

### Quality
- [ ] Zero failing tests
- [ ] No performance degradation
- [ ] Backward compatibility maintained
- [ ] Documentation clear and comprehensive

---

## Architecture Principles

### Additive Changes Only

**No Breaking Changes:**
- Keep existing product_slug format
- Add ingredient_slug alongside (don't replace)
- Keep existing import resolution (add new path)
- Maintain backward compatibility throughout

### Future-Ready Export Format

**Prepare for Multi-Tenant:**
- Export ingredient_slug separately
- Enable ingredient-based resolution
- Support future tenant_id filtering
- Keep composite data for desktop

### Documentation-Driven Migration

**Document Before Building:**
- Explain current implementation clearly
- Mark future migration points explicitly
- Provide web phase migration checklist
- Include SQL examples for reference

---

## Constitutional Compliance

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Desktop keeps simple composite slug
- Export format ready for multi-tenant
- Documentation guides future migration

✅ **Principle VII: Pragmatic Aspiration**
- Desktop phase: Minimal changes (documentation + export field)
- Web phase: Ready for tenant-scoped resolution
- Migration cost: Very low now, prevents complexity later

---

## Risk Considerations

**Risk: Adding ingredient_slug breaks existing exports**
- Context: Adding new field could break consumers expecting exact format
- Mitigation: Additive change only, product_slug preserved

**Risk: Dual resolution path adds complexity**
- Context: Two resolution paths (ingredient_slug + composite vs product_slug)
- Mitigation: Clear code comments, explicit fallback logging

**Risk: Documentation gets out of sync with code**
- Context: Documented migration path may not match actual implementation
- Mitigation: Validate documentation during web phase planning

**Risk: Composite slug pattern changes before web migration**
- Context: Product slug format could evolve independently
- Mitigation: Documentation marks this as migration dependency

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study current product_service.py slug generation
- Study _export_products() current format
- Study _import_products() current resolution
- Identify all product slug usage points

**Key Patterns to Copy:**
- Dual-field export (product_slug + ingredient_slug) → Copy from recipe exports
- Dual-path import resolution → Copy from finished_unit imports
- Fallback logging → Copy from existing import patterns

**Focus Areas:**
- Keep changes minimal (low-risk)
- Add documentation thoroughly (high-value)
- Test backward compatibility rigorously
- Mark future migration points clearly

**Critical Files to Modify:**
- `src/services/product_service.py` - Add documentation
- `src/services/coordinated_export_service.py` - Add ingredient_slug to export
- `src/services/enhanced_import_service.py` - Add ingredient_slug resolution path
- `docs/web_migration_notes.md` - Create product resolution section

---

**END OF SPECIFICATION**
