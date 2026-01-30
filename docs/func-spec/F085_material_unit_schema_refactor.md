# F085: MaterialUnit Schema Refactor

**Version**: 1.0
**Date**: 2026-01-29
**Priority**: HIGH
**Type**: Schema Enhancement + Service Layer + UI

---

## Executive Summary

MaterialUnits currently reference abstract Materials instead of specific MaterialProducts, which prevents product-specific unit definitions and breaks the mental model for how materials are consumed in FinishedGoods assembly.

Current gaps:
- ❌ MaterialUnit.material_id references abstract Material (not specific product)
- ❌ Cannot distinguish between different ribbon widths from different products
- ❌ Forces all products of same Material to share MaterialUnits (inappropriate duplication prevention)
- ❌ No auto-generation for "each" type products (bags, boxes require manual unit creation)
- ❌ Composition model allows generic Material placeholder (ambiguous at assembly time)

This spec makes MaterialUnit a child of MaterialProduct (not Material), adds auto-generation for per-unit products, and removes generic Material references from Composition model.

---

## Problem Statement

**Current State (ABSTRACT):**
```
Material Model
├─ ✅ Material definition (Red Satin Ribbon)
├─ ✅ base_unit_type field
└─ MaterialUnits (children)
    ├─ ✅ 6-inch Red Ribbon → material_id
    ├─ ✅ 12-inch Red Ribbon → material_id
    └─ ❌ SHARED by all products of this material

MaterialProduct Model
├─ ✅ Michaels 1/4-inch Red Satin 25m → material_id
├─ ✅ Joann 1-inch Red Satin 50m → material_id
└─ ❌ No direct relationship to MaterialUnits

Composition Model (FinishedGoods components)
├─ ✅ material_unit_id (specific unit)
├─ ❌ material_id (generic placeholder - ambiguous)
└─ 5-way XOR constraint

Problems:
- Cannot have product-specific MaterialUnits
- All "Clear Bags" products share same "1 bag" unit
- Manual unit creation required for ALL products
- Generic material references resolved only at assembly time
```

**Target State (PRODUCT-SPECIFIC):**
```
Material Model
├─ ✅ Material definition (taxonomy only)
├─ ✅ base_unit_type field
└─ ❌ NO MaterialUnits relationship

MaterialProduct Model
├─ ✅ Michaels 1/4-inch Red Satin 25m
├─ ✅ Joann 1-inch Red Satin 50m
└─ MaterialUnits (children) - product-specific
    ├─ Auto-generated for package_count products
    ├─ Manual creation for linear/area products
    └─ Specific to THIS product's inventory

MaterialUnit Model
├─ ✅ material_product_id FK (replaces material_id)
├─ ✅ Auto-generated for "each" type products
└─ ✅ Product-specific consumption definitions

Composition Model (FinishedGoods components)
├─ ✅ material_unit_id (specific unit only)
├─ ❌ material_id REMOVED
└─ 4-way XOR constraint

Benefits:
- Product-specific MaterialUnits enable accurate inventory
- Auto-generation reduces user toil for majority case
- No ambiguity - all components are concrete
- Accept duplication - simpler schema, clearer semantics
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current MaterialUnit Model**
   - Find: `src/models/material_unit.py` - Current FK to Material
   - Find: `src/models/material.py` - Current parent relationship
   - Find: `src/models/material_product.py` - Target parent for MaterialUnits
   - Note: MaterialProduct already has inventory tracking via MaterialInventoryItem

2. **Composition Model Pattern**
   - Find: `src/models/composition.py` - Study XOR constraint
   - Find: Factory methods: `create_material_unit_composition()`, `create_material_placeholder_composition()`
   - Note: material_id will be removed, XOR changes from 5-way to 4-way

3. **Auto-Generation Patterns**
   - Find: `src/services/recipe_service.py` - Study slug auto-generation
   - Find: `src/services/finished_unit_service.py` - Study creation hooks
   - Pattern: Auto-create related record on parent creation

4. **MaterialProduct Service**
   - Find: `src/services/material_product_service.py` - Current CRUD operations
   - Note: Where to add MaterialUnit auto-generation logic
   - Note: How to determine product type (package_count vs package_length_m vs package_sq_m)

5. **UI Sub-Form Patterns**
   - Find: `src/ui/tabs/recipes_tab.py` - Study how FinishedUnits sub-form works on Recipe
   - Find: Material Products UI - Where to add MaterialUnits sub-section
   - Pattern: List + Add/Edit within parent form

---

## Requirements Reference

This specification addresses architectural gap identified in F086 planning discussions:
- MaterialUnit must be child of MaterialProduct for product-specific consumption units
- Composition model must only reference concrete MaterialUnits (no generic placeholders)
- Auto-generation must reduce user toil for majority "each" type products

---

## Functional Requirements

### FR-1: Change MaterialUnit Parent from Material to MaterialProduct

**What it must do:**
- Change MaterialUnit.material_id FK to MaterialUnit.material_product_id
- Update MaterialUnit model to reference MaterialProduct parent
- Remove Material.units relationship
- Add MaterialProduct.material_units relationship with cascade delete
- Update all MaterialUnit queries to join via MaterialProduct

**Pattern reference:** Study how FinishedUnit references Recipe as parent

**Success criteria:**
- [ ] MaterialUnit model has material_product_id FK (NOT NULL, indexed, ondelete CASCADE)
- [ ] MaterialUnit model does NOT have material_id field
- [ ] MaterialProduct model has material_units relationship
- [ ] Material model does NOT have units relationship
- [ ] All existing MaterialUnit service methods work with new FK

---

### FR-2: Auto-Generate MaterialUnit for "Each" Type Products

**What it must do:**
- Detect when MaterialProduct has package_count (per-unit type)
- Auto-create MaterialUnit on MaterialProduct creation
- Name: "1 {product.name}"
- Quantity per unit: 1.0
- Slug: auto-generated from name
- Update MaterialUnit name when parent product name changes
- Do NOT auto-generate for package_length_m or package_sq_m products

**Pattern reference:** Study how Recipe variants auto-create related records

**Business rules:**
- Auto-generate ONLY if package_count is NOT NULL
- Do NOT auto-generate if package_length_m is populated
- Do NOT auto-generate if package_sq_m is populated
- Sync auto-generated MaterialUnit name when product name updates
- Handle slug conflicts with numeric suffix (-2, -3, etc.)

**Success criteria:**
- [ ] MaterialProduct with package_count=100 auto-creates MaterialUnit "1 {name}"
- [ ] MaterialProduct with package_length_m does NOT auto-create MaterialUnit
- [ ] MaterialProduct name update syncs to auto-generated MaterialUnit name
- [ ] Slug conflicts handled correctly with suffixes
- [ ] Service tests cover auto-generation for all product types

---

### FR-3: Remove Generic Material References from Composition

**What it must do:**
- Remove material_id field from Composition model
- Remove create_material_placeholder_composition() factory method
- Update XOR constraint from 5-way to 4-way (finished_unit_id, finished_good_id, packaging_product_id, material_unit_id)
- Update CompositionService to reject material_id in validation
- Update component_type property to not return "material"

**Pattern reference:** Study existing Composition XOR constraint for finished_unit_id, finished_good_id

**Success criteria:**
- [ ] Composition model does NOT have material_id field
- [ ] XOR constraint validates exactly one of 4 component types
- [ ] Factory method for material placeholder removed
- [ ] Validation rejects attempts to set material_id
- [ ] All Composition tests pass with 4-way XOR

---

### FR-4: Add MaterialUnits Sub-Section to MaterialProduct Form

**What it must do:**
- Add MaterialUnits list display in MaterialProduct create/edit form
- Show columns: Name, Quantity per Unit, Available Inventory
- For linear/area products: Show "Add Unit" button
- For per-unit products: Hide "Add Unit" button (auto-generated unit present)
- Enable edit/delete of MaterialUnits from product form
- Validate deletion prevents removal if MaterialUnit referenced by Composition

**Pattern reference:** Study how Recipe form displays FinishedUnits sub-section

**UI Requirements:**
- List of MaterialUnits must be visible in product form context
- Add/Edit MaterialUnit forms must be accessible from product form
- User must understand which products get auto-generated units vs manual creation
- Deletion must be prevented with clear error if unit is in use

**Success criteria:**
- [ ] MaterialProduct form displays MaterialUnits sub-section
- [ ] "Add Unit" button visible for linear/area products only
- [ ] Auto-generated unit visible but not manually editable for per-unit products
- [ ] Edit/Delete work correctly from product form
- [ ] Validation prevents deletion of in-use units

---

### FR-5: Update Materials → Units Tab to Read-Only List

**What it must do:**
- Remove "Add Unit" button from Materials → Units tab
- Display comprehensive list of all MaterialUnits across all products
- Show columns: Name, Material, Product, Quantity per Unit, Available Inventory
- Make rows clickable, navigating to parent MaterialProduct form
- Add filters: Material category, subcategory, product name
- Keep tab as useful reference view, but creation happens on product form

**Pattern reference:** Study how other tabs display read-only reference lists

**Success criteria:**
- [ ] Units tab has NO "Add Unit" button
- [ ] Units tab displays all MaterialUnits with product context
- [ ] Clicking row navigates to MaterialProduct form
- [ ] Filters work correctly for category/subcategory/product
- [ ] Tab serves as useful overview for all units

---

### FR-6: Data Migration - Export Transformation

**What it must do:**
- Export current MaterialUnits with both material_id and inferred material_product_id
- For each Material with N products and M MaterialUnits: create N×M MaterialUnit records (duplication)
- Flag MaterialUnits where Material has zero products (unmigrateable)
- Export Compositions with material_id flagged for manual review
- Include migration log with duplication count, conflict count, error count

**Pattern reference:** Study how Recipe slug migration handled existing data

**Business rules:**
- Accept duplication: if Material has 3 products, create 3 copies of each MaterialUnit
- Materials with no products → MaterialUnits cannot be migrated (flag as error)
- Compositions with material_id → cannot auto-migrate (manual product selection required)
- Log all migration decisions for audit trail

**Success criteria:**
- [ ] Export includes transformation logic for material_id → material_product_id
- [ ] Duplication strategy creates MaterialUnits for each product
- [ ] Orphaned MaterialUnits (no products) flagged in migration log
- [ ] Composition material_id records flagged for manual review
- [ ] Migration log documents all transformations

---

### FR-7: Update Export/Import for MaterialUnits

**What it must do:**
- Export MaterialUnits with material_product_slug (not material_slug)
- Import MaterialUnits by resolving material_product_slug to material_product_id
- Fail MaterialUnit import with clear error if material_product_slug doesn't resolve
- Export Compositions with material_unit_slug only (no material_slug)
- Import Compositions by resolving material_unit_slug to material_unit_id

**Pattern reference:** Study how Product export/import resolves ingredient_slug

**Success criteria:**
- [ ] MaterialUnits export with material_product_slug reference
- [ ] MaterialUnits import resolves material_product_slug correctly
- [ ] Import fails gracefully for invalid material_product_slug
- [ ] Compositions export with material_unit_slug only
- [ ] Round-trip export/import preserves MaterialUnit relationships

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ F086 FinishedGoods Creation UX (depends on this feature)
- ❌ MaterialUnit cost calculation logic (handled by existing service methods)
- ❌ Inventory availability calculation (already exists via MaterialInventoryItem)
- ❌ Multi-tenant support (deferred to web phase)
- ❌ MaterialUnit categories or taxonomy (MaterialProduct hierarchy sufficient)
- ❌ Automatic substitution of equivalent MaterialUnits (user selects explicitly)

---

## Success Criteria

**Complete when:**

### Schema & Migration
- [ ] MaterialUnit.material_product_id FK exists and works correctly
- [ ] MaterialUnit.material_id field completely removed
- [ ] Composition.material_id field completely removed
- [ ] XOR constraint validates 4-way (not 5-way)
- [ ] Migration successfully transforms existing MaterialUnits
- [ ] Zero MaterialUnits with NULL material_product_id after migration
- [ ] Zero Compositions with material_id after migration

### Service Layer
- [ ] MaterialProduct creation auto-generates MaterialUnit for package_count products
- [ ] MaterialProduct update syncs auto-generated MaterialUnit name
- [ ] MaterialUnit creation validates material_product_id NOT NULL
- [ ] MaterialUnit deletion prevented if referenced by Composition
- [ ] All service tests pass with new schema

### UI
- [ ] MaterialProduct form displays MaterialUnits sub-section
- [ ] "Add Unit" button shown/hidden correctly based on product type
- [ ] Materials → Units tab is read-only with no "Add Unit" button
- [ ] Units tab navigation to product form works
- [ ] All UI tests pass with new workflow

### Export/Import
- [ ] MaterialUnits export with material_product_slug
- [ ] MaterialUnits import resolves material_product_slug correctly
- [ ] Compositions export with material_unit_slug only
- [ ] Round-trip preserves all MaterialUnit relationships
- [ ] Migration log documents all transformation decisions

### Quality
- [ ] Zero failing tests after implementation
- [ ] Export→Import→Export produces identical data
- [ ] Auto-generation performance acceptable (<100ms per product)
- [ ] Error messages clear for migration conflicts
- [ ] Service layer tests >80% coverage

---

## Architecture Principles

### Product-Specific MaterialUnits

**MaterialUnit belongs to exactly one MaterialProduct:**
- Enables product-specific consumption units (6" narrow ribbon vs 6" wide ribbon)
- Inventory calculations specific to purchased product
- Costing calculations specific to product's FIFO lots
- Accept duplication across equivalent products for simplicity

### Auto-Generation for Majority Case

**Reduce toil for "each" type products:**
- MaterialProduct with package_count → auto-create "1 {name}" MaterialUnit
- User sees MaterialUnit immediately available for FinishedGoods
- No manual unit creation for bags, boxes, labels (majority case)
- Linear/area products still require manual definition (inherent complexity)

### Remove Ambiguity from Composition

**Composition only references concrete MaterialUnits:**
- No generic Material placeholders
- Every FinishedGood component is fully specified at definition time
- Assembly feasibility checks use real product inventory
- Cost calculations use actual product costs

### Migration Strategy: Accept Duplication

**Duplicate MaterialUnits across products for simplicity:**
- If Material has 3 products and 2 MaterialUnits → create 6 MaterialUnits total
- Simpler than many-to-many bridge table
- Matches user mental model (units specific to products)
- Enables future per-product customization

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design**
- Auto-generation reduces toil for majority use case
- Product-specific units match mental model
- MaterialUnits created in context (on product form)

✅ **Principle II: Data Integrity & FIFO Accuracy**
- Product-specific MaterialUnits enable accurate inventory tracking
- Composition references concrete units (no ambiguity)
- Migration preserves all existing MaterialUnit data

✅ **Principle III: Future-Proof Schema**
- Accept duplication now, simpler than future refactor
- Product-specific units enable web multi-tenant patterns
- Export/import uses slugs for portability

✅ **Principle VI: Schema Change Strategy**
- Uses export → reset → import workflow (desktop phase)
- Migration transformation script documents all changes
- Clear validation of post-migration state

✅ **Principle VII: Pragmatic Aspiration**
- Build for desktop today (simple duplication strategy)
- Architect for tomorrow (product-specific enables future features)
- Auto-generation proves toil reduction before AI assistance

---

## Risk Considerations

**Risk: Migration creates too many duplicate MaterialUnits**
- Context: If average Material has 5 products and 3 units → 15 duplicates per Material
- Mitigation: Migration log shows duplication count; user can consolidate products if needed

**Risk: Auto-generation creates unwanted MaterialUnits for "each" products**
- Context: Some per-unit products might not want default "1 unit"
- Mitigation: Allow deletion of auto-generated unit if not in use; user can recreate manually

**Risk: Users confused about which product's MaterialUnit to select in FinishedGoods**
- Context: Three identical ribbon products now have three separate MaterialUnits
- Mitigation: FinishedGoods UI shows product name in MaterialUnit dropdown for clarity

**Risk: Existing Compositions with material_id cannot auto-migrate**
- Context: Generic Material references require manual product selection
- Mitigation: Flag in migration log; document manual resolution process; provide guidance

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study Recipe.slug auto-generation → apply to MaterialUnit.slug for auto-generated units
- Study FinishedUnit.recipe_id FK → apply to MaterialUnit.material_product_id FK
- Study Composition XOR constraint → understand how to change from 5-way to 4-way
- Study Recipe form FinishedUnits sub-section → apply to MaterialProduct form MaterialUnits sub-section

**Key Patterns to Copy:**
- FK relationship: FinishedUnit→Recipe pattern → MaterialUnit→MaterialProduct pattern
- Auto-generation: Recipe variant creation hooks → MaterialUnit auto-creation hooks
- Sub-form UI: Recipe→FinishedUnits display → MaterialProduct→MaterialUnits display
- Export/import: Product ingredient_slug resolution → MaterialUnit material_product_slug resolution

**Focus Areas:**
- Schema migration testing with real data exports
- Auto-generation triggered only for correct product types
- Composition XOR constraint validation with 4 types
- UI clarity about auto-generated vs manual MaterialUnits

---

**END OF SPECIFICATION**
