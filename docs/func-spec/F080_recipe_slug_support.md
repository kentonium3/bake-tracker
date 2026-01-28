# F080: Recipe Slug Support

**Version**: 1.0
**Date**: 2026-01-28
**Priority**: CRITICAL
**Type**: Schema Enhancement + Service Layer

---

## Executive Summary

Recipes currently use `name` field only for identification, which is not unique and creates fragile references across the system. This breaks data integrity and creates collision risks for future web deployment.

Current gaps:
- ❌ Recipe.name is not unique (indexed but not unique constraint)
- ❌ Recipe references use name-based lookups (FinishedUnit, ProductionRun, EventProductionTarget, RecipeComponent)
- ❌ Export/import uses recipe_name which will fail in multi-tenant scenarios
- ❌ No portable identifier for recipes across data migrations

This spec adds unique slug field to Recipe model and updates all FK resolution to use slugs, matching the existing pattern used for Supplier, Product, Ingredient, FinishedGood, Material entities.

---

## Problem Statement

**Current State (FRAGILE):**
```
Recipe Model
├─ ✅ name field (indexed)
├─ ❌ name NOT unique (collision risk)
└─ ❌ No slug field

References TO Recipe:
├─ FinishedUnit.recipe_id → exports as recipe_name
├─ EventProductionTarget.recipe_id → exports as recipe_name  
├─ ProductionRun.recipe_id → exports as recipe_name
├─ RecipeComponent.component_recipe_id → exports as component_recipe_name
└─ RecipeSnapshot.recipe_id → FK only

Export/Import:
├─ coordinated_export_service exports recipe_name
├─ enhanced_import_service resolves via recipe_name lookup
└─ ❌ Name collisions break import in multi-tenant future
```

**Target State (PORTABLE):**
```
Recipe Model
├─ ✅ name field (indexed, display name)
├─ ✅ slug field (UNIQUE, indexed, portable identifier)
└─ ✅ Slug generation with collision handling

References TO Recipe:
├─ All FK exports include both recipe_name AND recipe_slug
├─ All FK imports prefer slug, fallback to name
└─ ✅ Multi-tenant ready

Export/Import:
├─ recipes.json exports both name and slug
├─ Import prefers slug resolution
└─ ✅ Backward compatible with existing name-only exports
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Existing Slug Patterns**
   - Find: `src/models/supplier.py` - Study slug field definition
   - Find: `src/models/product.py` - Study slug generation in service
   - Find: `src/models/ingredient.py` - Study unique constraint pattern
   - Note: All have `slug = Column(String(200), nullable=False, unique=True, index=True)`

2. **Slug Generation Service**
   - Find: `src/services/supplier_service.py` - Study `generate_slug()` method
   - Find: `src/services/product_service.py` - Study collision handling (append -2, -3, etc.)
   - Understand: How existing services generate slugs with suffix for uniqueness

3. **Export/Import FK Resolution**
   - Find: `src/services/coordinated_export_service.py` - Study how _export_recipes() exports recipe_name
   - Find: `src/services/enhanced_import_service.py` - Study _resolve_recipe() method
   - Note: Pattern of exporting both name and slug, resolving via slug first

4. **Recipe Service Layer**
   - Find: `src/services/recipe_service.py` - Current recipe CRUD operations
   - Study: Where recipe creation/update happens
   - Note: Where to add slug generation logic

---

## Requirements Reference

This specification addresses critical gaps identified in:
- Data Portability Review (2026-01-28) Section 1: "Entities MISSING Slugs (CRITICAL GAPS)" - Recipe (CRITICAL)

Implements recommendations for:
- Adding unique slug field to Recipe model
- Generating slugs for existing recipes
- Updating FK references to use slug resolution
- Export/import support for recipe slugs

---

## Functional Requirements

### FR-1: Add Slug Field to Recipe Model

**What it must do:**
- Add `slug` field to Recipe model: `Column(String(200), nullable=False, unique=True, index=True)`
- Create database migration to add slug column
- Generate initial slugs for all existing recipes based on recipe names
- Handle slug collisions by appending suffixes (-2, -3, etc.)

**Pattern reference:** Copy slug field definition from Supplier, Product, Ingredient models exactly

**Success criteria:**
- [ ] Recipe model has slug field with unique constraint
- [ ] Database migration successfully adds slug column
- [ ] All existing recipes have generated slugs
- [ ] No slug collisions exist after migration
- [ ] Slug generation tested with collision scenarios

---

### FR-2: Slug Generation in Recipe Service

**What it must do:**
- Add `generate_slug(name: str)` method to RecipeService
- Generate slug from recipe name (lowercase, spaces to hyphens, alphanumeric only)
- Check for existing slugs and append suffix if collision detected
- Integrate slug generation into create_recipe() and update_recipe() methods
- Never allow manual slug override (always auto-generated from name)

**Pattern reference:** Study SupplierService.generate_slug() - copy logic exactly

**Business rules:**
- Slug auto-generated from name field
- Slug format: lowercase, hyphens for spaces, alphanumeric-and-hyphens only
- Collision handling: append `-2`, `-3`, etc. until unique
- Slug updates when recipe renamed (regenerate with collision check)

**Success criteria:**
- [ ] generate_slug() method exists and works correctly
- [ ] create_recipe() generates slug automatically
- [ ] update_recipe() regenerates slug when name changes
- [ ] Collision handling appends numeric suffixes correctly
- [ ] Service tests cover slug generation and collisions

---

### FR-3: Update Recipe Export to Include Slugs

**What it must do:**
- Modify `_export_recipes()` in coordinated_export_service.py
- Export both `name` and `slug` fields in recipes.json
- Include slug in manifest metadata
- Maintain backward compatibility (name still exported)

**Pattern reference:** Study how ingredients.json exports slug field

**Success criteria:**
- [ ] recipes.json contains both name and slug for each recipe
- [ ] Export tests verify slug field presence
- [ ] Existing exports still work (name field preserved)
- [ ] Manifest includes slug field metadata

---

### FR-4: Update Recipe Import to Resolve via Slug

**What it must do:**
- Modify `_import_recipes()` in enhanced_import_service.py
- Resolve recipe by slug first, fallback to name if slug not found
- Log when fallback to name occurs (migration support)
- Create import validation tests

**Pattern reference:** Study how _import_ingredients() resolves via slug

**Business rules:**
- Prefer slug-based resolution for imports
- Fallback to name-based resolution for backward compatibility
- Log fallback to name for migration tracking
- Fail import if neither slug nor name resolves

**Success criteria:**
- [ ] Import resolves recipes via slug when available
- [ ] Import falls back to name for legacy data
- [ ] Fallback events are logged
- [ ] Import tests cover slug and name resolution paths

---

### FR-5: Update FK Exports to Include Recipe Slugs

**What it must do:**
- Modify FinishedUnit export to include `recipe_slug` field
- Modify EventProductionTarget export to include `recipe_slug` field
- Modify ProductionRun export to include `recipe_slug` field
- Modify RecipeComponent export to include `component_recipe_slug` field
- Maintain backward compatibility (recipe_name still exported)

**Pattern reference:** Study how product exports include both ingredient_slug and ingredient_name

**Success criteria:**
- [ ] FinishedUnit exports include recipe_name AND recipe_slug
- [ ] EventProductionTarget exports include recipe_name AND recipe_slug
- [ ] ProductionRun exports include recipe_name AND recipe_slug
- [ ] RecipeComponent exports include component_recipe_name AND component_recipe_slug
- [ ] Export tests verify both fields present

---

### FR-6: Update FK Imports to Resolve via Recipe Slug

**What it must do:**
- Modify _import_finished_units() to resolve recipe_id via slug first
- Modify _import_production_runs() to resolve recipe_id via slug first
- Modify _import_recipe_components() to resolve component_recipe_id via slug first
- Add slug-based resolution to any other recipe FK references
- Fallback to name-based resolution for backward compatibility

**Pattern reference:** Study how _import_products() resolves ingredient_id via slug

**Success criteria:**
- [ ] All recipe FK imports resolve via slug when available
- [ ] All recipe FK imports fallback to name for legacy data
- [ ] Import tests cover slug and name resolution paths
- [ ] Error messages clarify slug vs name resolution failures

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ tenant_id field (multi-tenant support deferred to web phase)
- ❌ Composite unique constraint (tenant_id, slug) - desktop is single-user
- ❌ RecipeSnapshot slug support (snapshots reference by FK only, not exportable)
- ❌ Event or Package slugs (separate features)
- ❌ UI display of slugs (slugs are internal identifiers)
- ❌ Manual slug editing in UI (always auto-generated)

---

## Success Criteria

**Complete when:**

### Schema & Migration
- [ ] Recipe model has slug field with unique constraint
- [ ] Migration script successfully adds slug column
- [ ] Migration generates slugs for all existing recipes
- [ ] Migration handles slug collisions correctly
- [ ] Migration tested on real database export

### Service Layer
- [ ] RecipeService.generate_slug() works correctly
- [ ] create_recipe() generates unique slugs
- [ ] update_recipe() regenerates slugs when name changes
- [ ] Collision handling appends numeric suffixes
- [ ] Service tests cover slug generation

### Export/Import
- [ ] recipes.json exports both name and slug
- [ ] Recipe import resolves via slug first, name fallback
- [ ] All FK exports include recipe_slug fields
- [ ] All FK imports resolve via slug first, name fallback
- [ ] Export/import round-trip preserves slug data

### Quality
- [ ] Zero failing tests after implementation
- [ ] Export→Import→Export produces identical data
- [ ] Slug generation performance acceptable (<100ms per recipe)
- [ ] Error messages clarify slug vs name resolution
- [ ] Migration script documented and reversible

---

## Architecture Principles

### Slug Generation Pattern

**Follow Existing Pattern Exactly:**
- Use same slugification logic as Supplier, Product, Ingredient
- Use same collision detection and suffix appending
- Use same unique constraint and indexing
- Use same service layer method signature

### Export/Import Dual-Field Strategy

**Both name AND slug in exports:**
- Enables backward compatibility with name-only imports
- Enables forward compatibility with slug-only imports
- Supports gradual migration from name to slug resolution
- Preserves human-readable name for debugging

### Fallback Resolution

**Prefer slug, fallback to name:**
- Slug resolution is primary path (fast, unique)
- Name resolution is fallback (legacy compatibility)
- Log fallback to name for migration tracking
- Fail if neither resolves (data integrity)

---

## Constitutional Compliance

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Unique slug constraint prevents recipe collision
- Slug-based FK resolution ensures correct recipe references
- Migration preserves all existing recipe data

✅ **Principle III: Future-Proof Schema, Present-Simple Implementation**
- Slug field supports future multi-tenant migration
- Current implementation simple (no tenant_id yet)
- Schema ready for (tenant_id, slug) composite unique constraint

✅ **Principle VII: Pragmatic Aspiration**
- Desktop phase: Simple unique slug constraint
- Web phase: Ready for tenant-scoped slugs
- Migration cost: Medium effort now prevents high cost later

---

## Risk Considerations

**Risk: Slug generation collisions during migration**
- Context: Many recipes might have similar names ("Chocolate Chip Cookies")
- Mitigation: Use numeric suffix appending (-2, -3, etc.) like existing pattern

**Risk: Breaking existing export/import workflows**
- Context: Current exports use recipe_name only
- Mitigation: Maintain recipe_name in exports, add recipe_slug alongside

**Risk: Performance of slug uniqueness checking**
- Context: Checking for slug collisions requires database query per recipe
- Mitigation: Use batch slug generation with in-memory collision detection

**Risk: Recipe rename invalidates slug references**
- Context: Slug regenerated when name changes
- Mitigation: This is desired behavior - slug always reflects current name

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study Supplier slug implementation → apply to Recipe
- Study Product slug generation → copy for Recipe
- Study Ingredient export/import → pattern match for Recipe

**Key Patterns to Copy:**
- Supplier slug field definition → Recipe slug field
- Product generate_slug() logic → RecipeService.generate_slug()
- Ingredient export/import slug handling → Recipe export/import

**Focus Areas:**
- Migration script must handle large recipe datasets (100+ recipes)
- Slug collision handling must be deterministic and repeatable
- Export/import must preserve backward compatibility
- All FK references must update (FinishedUnit, ProductionRun, EventProductionTarget, RecipeComponent)

**Critical Files to Modify:**
- `src/models/recipe.py` - Add slug field
- `src/services/recipe_service.py` - Add generate_slug() method
- `src/services/coordinated_export_service.py` - Export recipe slugs
- `src/services/enhanced_import_service.py` - Import recipe slugs
- `migrations/migration_fXXX_add_recipe_slugs.py` - Create migration script

---

**END OF SPECIFICATION**
