# F082: Product Unique Slug Implementation

**Version**: 2.0
**Date**: 2026-01-28
**Priority**: HIGH
**Type**: Data Model Enhancement

---

## Executive Summary

Product entities currently use composite slug format `{ingredient_slug}:{brand}:{qty}:{unit}` which **fails to uniquely identify products** when products differ by attributes not in the composite (flavor, shape, color, etc.).

**Current-model collision risk (EXISTS NOW):**
- ❌ Two products: same ingredient, brand, qty, unit BUT different flavor → identical composite slug
- ❌ Example: "chocolate-chips:ghirardelli:12.0:oz" (milk chocolate) vs "chocolate-chips:ghirardelli:12.0:oz" (dark chocolate)
- ❌ Internal relationships cannot reliably reference products

**Solution: Follow established entity patterns**
- ✅ Add proper `slug` field (unique identifier, auto-generated from composite + differentiator)
- ✅ Add `previous_slug` for migration support (matches recipe pattern)
- ✅ Use slug for all internal relationships and FK references
- ✅ Export/import services handle product slug like other entities
- ✅ Solving this now automatically covers future multi-tenant scenarios

---

## Problem Statement

**Current State (SINGLE-TENANT BROKEN):**
```
Product Composite Slug
├─ Format: "{ingredient_slug}:{brand}:{qty}:{unit}"
├─ Example: "chocolate-chips:ghirardelli:12.0:oz"
├─ Assumption: Four fields uniquely identify a product
└─ BROKEN: Products can differ by flavor, shape, color, etc.

Collision Examples (CURRENT MODEL):
├─ "chocolate-chips:ghirardelli:12.0:oz" → Milk Chocolate
├─ "chocolate-chips:ghirardelli:12.0:oz" → Dark Chocolate
├─ "sprinkles:wilton:3.0:oz" → Rainbow
├─ "sprinkles:wilton:3.0:oz" → Red/Green Holiday
└─ ❌ Same composite slug, different products!

Impact:
├─ Inventory tracking: Cannot distinguish between variants
├─ Purchase history: Which variant was bought?
├─ Recipe requirements: Which specific product is needed?
└─ Import/export: Data loss on collision
```

**Pattern Comparison (Other Entities):**
```
Recipe Entity (CORRECT PATTERN):
├─ slug: "chocolate-chip-cookies" (unique identifier)
├─ previous_slug: "choc-chip" (migration support)
├─ Composite fields: name + category (for display/search)
└─ FK references: Use slug, not composite

Product Entity (BROKEN PATTERN):
├─ No dedicated slug field
├─ Composite slug: "{ingredient}:{brand}:{qty}:{unit}"
├─ Missing attributes: flavor, shape, color, variant
└─ FK references: Use error-prone composite
```

**Target State (FOLLOWS ENTITY PATTERNS):**
```
Product Entity (FIXED):
├─ slug: "chocolate-chips-ghirardelli-12oz-dark" (unique)
├─ previous_slug: for migration support
├─ Composite fields: ingredient_slug, brand, qty, unit (search/display)
├─ Variant attributes: flavor, shape, color (model fields)
└─ FK references: Use slug consistently

Benefits:
├─ Current-model: Products distinguishable by variant
├─ Import/export: Reliable round-trip via slug
├─ Internal relationships: Consistent with other entities
└─ Future multi-tenant: Automatically covered
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe Slug Pattern (REFERENCE IMPLEMENTATION)**
   - Find: `src/models/recipe.py` - Study slug and previous_slug fields
   - Find: `src/services/recipe_service.py` - Study slug methods (get_by_slug, update_slug)
   - Note: This is the pattern Product should follow

2. **Slug Generation Utility**
   - Find: `src/utils/slug_utils.py` - Study create_slug_for_model()
   - Note: This utility handles uniqueness checking with auto-increment

3. **Current Product Model**
   - Find: `src/models/product.py` - Understand current structure
   - Find: `src/services/product_service.py` - Study create_product() method
   - Note: Where to add slug/previous_slug fields and methods

4. **Recipe Export Pattern (REFERENCE)**
   - Find: `src/services/coordinated_export_service.py` - Study _export_recipes()
   - Note: How slug + previous_slug + name are exported together

5. **Recipe Import Pattern (REFERENCE)**
   - Find: `src/services/enhanced_import_service.py` - Study _import_recipes()
   - Note: Multi-level fallback resolution (slug → previous_slug → name)

6. **Product FK Resolution**
   - Search: coordinated_export_service.py for product_slug usage
   - Note: Where product references are exported (purchases, inventory, etc.)

---

## Requirements Reference

This specification addresses issues identified in:
- Data Portability Review (2026-01-28) Section 6: "Other Data Portability Issues" - Issue 1: Composite Foreign Keys (Product)

**Primary drivers (CURRENT MODEL):**
- Product variants (flavor, shape, color) cannot be uniquely identified
- Internal relationships use error-prone composite slugs
- Import/export fails on variant collision
- Inconsistent with entity patterns (Recipe, Ingredient, FinishedGood use proper slugs)

**Secondary benefit (FUTURE):**
- Multi-tenant web deployment automatically covered
- Tenant-scoped product resolution ready
- Portable product identification across tenants

---

## Functional Requirements

### FR-1: Add Unique Slug Field to Product Model

**What it must do:**
- Add `slug` field to Product model (unique, indexed)
- Add `previous_slug` field for migration support (nullable, matches Recipe pattern)
- Generate slug using `create_slug_for_model()` from `src/utils/slug_utils.py`
- Slug format: composite + differentiator when needed
- Auto-generate on product creation if not provided

**Slug Generation Strategy:**
```
Base: "{ingredient_slug}_{brand_slug}_{qty}_{unit}"
Example: "chocolate_chips_ghirardelli_12_oz"

On collision (flavor/variant differs):
  Add differentiator: "chocolate_chips_ghirardelli_12_oz_dark"
  Auto-increment: "chocolate_chips_ghirardelli_12_oz_1"
```

**Pattern reference:** Study Recipe.slug implementation and create_slug_for_model() usage

**Success criteria:**
- [ ] Product model has `slug` field (String, unique, indexed)
- [ ] Product model has `previous_slug` field (String, nullable)
- [ ] Slug auto-generated on create using create_slug_for_model()
- [ ] Slug uniqueness enforced at database level
- [ ] Existing products migrated with generated slugs

---

### FR-2: Update Product Service for Slug Operations

**What it must do:**
- Modify `create_product()` to auto-generate slug
- Add `get_product_by_slug()` method
- Add `update_product_slug()` method (updates slug, saves old to previous_slug)
- Update any composite-slug lookups to use proper slug field

**Service Methods:**
```python
def create_product(..., slug: str = None) -> Product:
    """If slug not provided, auto-generate from composite fields."""

def get_product_by_slug(slug: str) -> Optional[Product]:
    """Primary lookup method for internal relationships."""

def update_product_slug(product_id: int, new_slug: str) -> Product:
    """Update slug, preserve old in previous_slug."""
```

**Pattern reference:** Study recipe_service.py slug methods

**Success criteria:**
- [ ] create_product() auto-generates unique slug
- [ ] get_product_by_slug() implemented
- [ ] update_product_slug() implemented with previous_slug preservation
- [ ] All service methods use slug for product identification

---

### FR-3: Update Internal Relationships to Use Product Slug

**What it must do:**
- Audit all FK references to Product
- Update FK storage to use slug (like other entities)
- Update FK resolution to use slug lookup

**Entities Referencing Product:**
```
InventoryItem.product_id → Consider adding product_slug for portability
Purchase.product_id → Consider adding product_slug for portability
RecipeIngredient (if exists) → Use product_slug
```

**Pattern reference:** Study how recipe_slug is used in FinishedUnit, RecipeSnapshot

**Success criteria:**
- [ ] All product FK references audited
- [ ] product_slug added where needed for data portability
- [ ] Internal lookups use slug-based resolution
- [ ] Relationships consistent with other entity patterns

---

### FR-4: Update Export Service for Product Slug

**What it must do:**
- Modify `_export_products()` to export proper `slug` field
- Export `previous_slug` for migration support
- Maintain backward compatibility with `product_slug` (composite) for legacy imports
- Export `ingredient_slug` as separate field

**Export Format:**
```json
{
  "slug": "chocolate_chips_ghirardelli_12_oz_dark",
  "previous_slug": null,
  "product_slug": "chocolate-chips:ghirardelli:12.0:oz",
  "ingredient_slug": "chocolate_chips",
  "brand": "Ghirardelli",
  "package_qty": 12.0,
  "package_unit": "oz",
  "flavor": "Dark",
  ...
}
```

**Pattern reference:** Study recipe export format (slug + previous_slug + name)

**Success criteria:**
- [ ] products.json exports `slug` field (proper unique identifier)
- [ ] products.json exports `previous_slug` field
- [ ] Legacy `product_slug` still exported for backward compatibility
- [ ] `ingredient_slug` exported as separate field
- [ ] Export tests verify all slug fields present

---

### FR-5: Update Import Service for Product Slug Resolution

**What it must do:**
- Modify `_import_products()` to resolve via slug field first
- Add fallback resolution chain for legacy imports
- Handle slug migration (import may have old slug format)

**Import Resolution Priority:**
```python
# Priority 1: Direct slug match (new format)
product = get_product_by_slug(record.get("slug"))

# Priority 2: Previous slug match (migration support)
if not product and record.get("previous_slug"):
    product = get_product_by_slug(record["previous_slug"])

# Priority 3: Composite match (legacy format)
if not product and record.get("product_slug"):
    product = find_by_composite_slug(record["product_slug"])

# Priority 4: Component match (oldest format)
if not product:
    product = find_by_components(ingredient_slug, brand, qty, unit)
```

**Pattern reference:** Study _import_recipes() and _import_finished_units() resolution chains

**Success criteria:**
- [ ] Import resolves slug field first
- [ ] Import falls back to previous_slug
- [ ] Import falls back to composite product_slug
- [ ] Import falls back to component matching
- [ ] All fallback events logged
- [ ] Import tests cover all resolution paths

---

### FR-6: Data Migration for Existing Products

**What it must do:**
- Generate slugs for all existing products
- Handle collision resolution during migration
- Preserve data integrity (no product loss)

**Migration Strategy:**
```python
for product in all_products:
    if not product.slug:
        base = f"{product.ingredient.slug}_{slugify(product.brand)}_{product.package_qty}_{product.package_unit}"
        product.slug = create_slug_for_model(base, Product, session)
```

**Success criteria:**
- [ ] All existing products have unique slug after migration
- [ ] Migration handles collisions with numeric suffixes
- [ ] Migration is idempotent (safe to run multiple times)
- [ ] Migration logged for audit trail

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ tenant_id field addition (web phase only, not needed now)
- ❌ Multi-tenant unique constraints (automatically covered by slug)
- ❌ UI changes for slug management (slugs auto-generated)
- ❌ User-visible slug editing (slugs are internal identifiers)
- ❌ Breaking changes to existing exports (backward compatibility maintained)

---

## Success Criteria

**Complete when:**

### Data Model
- [ ] Product model has `slug` field (unique, indexed)
- [ ] Product model has `previous_slug` field (nullable)
- [ ] Slug auto-generated using create_slug_for_model()
- [ ] Database migration adds new fields
- [ ] All existing products have unique slugs

### Service Layer
- [ ] create_product() auto-generates slug
- [ ] get_product_by_slug() implemented
- [ ] update_product_slug() implemented with previous_slug preservation
- [ ] All product lookups use slug-based resolution

### Export Format
- [ ] products.json exports `slug` field (proper unique identifier)
- [ ] products.json exports `previous_slug` field
- [ ] Legacy `product_slug` still exported (backward compatibility)
- [ ] `ingredient_slug` exported as separate field
- [ ] Export tests verify all slug fields present

### Import Resolution
- [ ] Import resolves slug field first (priority 1)
- [ ] Import falls back to previous_slug (priority 2)
- [ ] Import falls back to composite product_slug (priority 3)
- [ ] Import falls back to component matching (priority 4)
- [ ] All fallback events logged
- [ ] Import tests cover all resolution paths

### Data Portability
- [ ] Export → Import → Export preserves all data
- [ ] Variant products (different flavor/shape) correctly distinguished
- [ ] Round-trip tests pass with variant products
- [ ] Legacy import files still work (backward compatibility)

### Quality
- [ ] Zero failing tests
- [ ] No performance degradation
- [ ] Backward compatibility maintained
- [ ] Pattern consistency with Recipe, Ingredient, FinishedGood entities

---

## Architecture Principles

### Follow Established Entity Patterns

**Consistency Across Entities:**
- Product follows same slug pattern as Recipe, Ingredient, FinishedGood
- `slug` field: unique identifier for the entity
- `previous_slug` field: migration support (rename tracking)
- Internal relationships use slug, not composite keys
- Import/export services handle slug like other entities

### Additive Changes with Backward Compatibility

**No Breaking Changes:**
- New `slug` field added (doesn't replace existing composite)
- Export includes both `slug` and legacy `product_slug`
- Import resolves via slug first, falls back to legacy formats
- All existing data preserved through migration

### Solve Current Problems First

**Current Model Fixed:**
- Products distinguishable by variant attributes (flavor, shape, color)
- Import/export reliable for variant products
- Internal relationships unambiguous
- **Bonus:** Multi-tenant automatically supported (slug uniqueness scales)

---

## Constitutional Compliance

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Product slug follows established entity patterns (Recipe, Ingredient)
- Export format includes all necessary fields for any future scenario
- Multi-tenant automatically covered by unique slug

✅ **Principle IV: Entity Pattern Consistency**
- Product aligns with other entities (slug + previous_slug)
- Import/export services treat Product like other entities
- Internal relationships use consistent slug-based resolution

✅ **Principle VII: Pragmatic Aspiration**
- Solves real current-model problem (variant product collision)
- Implementation follows proven patterns (Recipe slug was F080)
- Migration cost: Medium now, prevents data corruption later

---

## Risk Considerations

**Risk: Migration generates duplicate slugs**
- Context: Existing products with same composite but different variants could collide
- Mitigation: create_slug_for_model() auto-increments on collision (_1, _2, etc.)

**Risk: Four-level fallback chain adds complexity**
- Context: Import has 4 resolution paths (slug → previous_slug → composite → components)
- Mitigation: Clear logging at each fallback, tests cover all paths

**Risk: Breaking existing workflows during migration**
- Context: Any change to product identification could break inventory/purchase tracking
- Mitigation: Migration preserves all existing IDs, slug is additive field

**Risk: Slug generation for existing products is non-deterministic**
- Context: Collision handling may assign _1 vs _2 depending on processing order
- Mitigation: Document that slug assignment order is not guaranteed, always export/import via slug

**Risk: Performance impact from slug index**
- Context: Adding unique index on slug column
- Mitigation: Products table is small (~hundreds of rows), index overhead negligible

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study Recipe model slug implementation (`src/models/recipe.py`)
- Study recipe_service.py slug methods
- Study _export_recipes() format (slug + previous_slug)
- Study _import_recipes() resolution chain
- Study create_slug_for_model() usage in other services

**Key Patterns to Copy:**
- Model slug fields → Copy from Recipe (slug, previous_slug)
- Slug generation → Use create_slug_for_model() from slug_utils.py
- Export format → Copy from recipe exports (multiple slug fields)
- Import resolution chain → Copy from _import_recipes() / _import_finished_units()
- Fallback logging → Copy from existing import patterns

**Existing Utility to Use:**
```python
from src.utils.slug_utils import create_slug_for_model

# Generate unique slug for product
slug = create_slug_for_model(base_name, Product, session)
```

**Focus Areas:**
- Add slug/previous_slug fields to Product model
- Implement service methods following recipe_service pattern
- Update export to include all slug fields
- Update import with multi-level fallback chain
- Migrate existing products with generated slugs
- Test backward compatibility rigorously

**Critical Files to Modify:**
- `src/models/product.py` - Add slug, previous_slug fields
- `src/services/product_service.py` - Add slug methods
- `src/services/coordinated_export_service.py` - Export slug fields
- `src/services/enhanced_import_service.py` - Add slug resolution chain
- `src/tests/` - Add tests for all new functionality

**Migration Considerations:**
- Existing products need slugs generated
- Collision handling via numeric suffix (_1, _2)
- previous_slug remains null for initial migration
- Migration should be idempotent

---

**END OF SPECIFICATION**
