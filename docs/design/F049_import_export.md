# F049: Import/Export System - Phase 1 Foundation

**Version**: 4.0
**Priority**: HIGH
**Type**: Service Layer + UI Enhancement

---

## Executive Summary

Current import/export system has critical gaps preventing backup/restore, AI augmentation, and transaction data entry:
- ❌ Full backup missing 8 entities (can't restore complete state)
- ❌ Catalog import doesn't support materials/material_products (silently fails)
- ❌ Context-rich export only supports 3 entities (needs ingredients, materials, recipes)
- ❌ No transaction imports (purchases, inventory adjustments)
- ❌ Import/export UI doesn't distinguish between export types or import purposes

This spec completes backup/restore, adds materials support, expands context-rich exports, and enables transaction imports.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Full Backup Export (Normalized)
├─ ✅ 6 entities (ingredients, products, recipes, suppliers, purchases, inventory_items)
└─ ❌ Missing 8 entities

Context-Rich Export
├─ ✅ 3 entities (inventory, products, purchases)
└─ ❌ Missing ingredients, materials, recipes

Catalog Import
├─ ✅ ingredients, products, recipes
└─ ❌ materials, material_products (fails silently)

Transaction Imports
└─ ❌ DOESN'T EXIST (no purchase import, no inventory adjustment import)

Import/Export UI
└─ ❌ Doesn't distinguish export types or import purposes
```

**Target State (COMPLETE):**
```
Full Backup Export
└─ ✅ All 14 entities (complete state restoration)

Context-Rich Export
└─ ✅ All catalog entities (ingredients, products, materials, material_products, recipes)

Catalog Import
└─ ✅ All catalog entities including materials

Transaction Imports (NEW)
├─ ✅ Purchase imports (food + materials)
└─ ✅ Inventory adjustment imports

Import/Export UI
├─ Export: Clear type selection (Full Backup | Catalog-Normalized | Catalog-Context-Rich)
└─ Import: Purpose-based selection (Backup Restore | Catalog | Purchases | Inventory Adjustments)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current export service**
   - Find full backup export (creates folder with manifest.json)
   - Find context-rich export (creates view_*.json files)
   - Study existing export patterns (how ingredients.json is created)
   - Note which entities currently supported

2. **Current import service**
   - Find catalog import service (handles ingredients, products, recipes)
   - Study ingredient import pattern (slug resolution, ADD_ONLY/AUGMENT)
   - Note error handling and validation approaches

3. **Material services**
   - Find material catalog service methods
   - Understand how to query materials, material_products, material_units
   - Note material hierarchy structure (category/subcategory)

4. **Purchase/inventory services**
   - Find purchase service (for transaction imports)
   - Find inventory service (for adjustment imports)
   - Understand how purchases affect inventory
   - Note validation rules (positive purchases, negative adjustments only)

5. **Current import/export UI**
   - Find existing dialogs
   - Understand current user flow
   - Note patterns to preserve or enhance

---

## Requirements Reference

This specification implements:
- **FR-1**: Full Backup and Restore (complete entity coverage)
- **FR-3**: Catalog Import (materials support)
- **FR-4**: AI-Friendly Catalog Export (expand to all catalog entities)
- **FR-5**: Transactional Import - Purchases
- **FR-6**: Inventory Adjustments

From: `docs/requirements/req_import_export.md` (v2.0)

---

## Functional Requirements

### FR-1: Complete Full Backup Export

**What it must do:**
- Export ALL 14 entities (add missing 8: materials, material_products, material_units, material_purchases, finished_goods, events, production_runs, consumption_records)
- Create timestamped folder with manifest.json
- Use slug-based references (not database IDs)
- Include entity counts in manifest for validation

**Pattern reference:** Study how ingredients.json export works, copy for materials entities

**Success criteria:**
- Backup folder contains all 14 entity files
- Manifest includes all counts
- Empty entities export as empty arrays (not skipped)

---

### FR-2: Expand Context-Rich Export

**What it must do:**
- Add ingredients to context-rich export (currently missing)
- Add materials to context-rich export (currently missing)
- Add recipes to context-rich export (currently missing)
- Include full context: hierarchy paths, nested relationships, computed values (inventory, costs), human-readable formats

**Pattern reference:** Study view_products.json structure, copy for ingredients/materials/recipes

**Context requirements (what to include):**
- Full hierarchy paths (e.g., "Flours & Starches > Wheat Flours > All-Purpose")
- Related entities embedded (products for ingredients, ingredients for recipes)
- Computed values (current inventory totals, average costs)
- Human-readable formats (descriptions, formatted units)
- Metadata section indicating editable vs readonly fields

**Success criteria:**
- Context-rich export available for ingredients, materials, recipes
- Exports include hierarchy paths (not just parent_id)
- Exports include nested related entities
- Exports include computed values for context
- Structure matches existing view_*.json pattern

---

### FR-3: Add Materials to Catalog Import

**What it must do:**
- Support importing materials catalog
- Support importing material_products catalog
- Resolve material_slug to material_id (like ingredient pattern)
- Support ADD_ONLY mode (skip existing)
- Support AUGMENT mode (update existing)
- Report created/updated/skipped/errors

**Pattern reference:** Study _import_ingredients() method, copy for materials

**Success criteria:**
- Materials import creates records in database
- Materials display in Materials tab after import
- Material products slug resolution works correctly
- Import respects ADD_ONLY vs AUGMENT mode

---

### FR-4: Add Context-Rich Import Support

**What it must do:**
- Auto-detect context-rich format (vs normalized format)
- Extract augmented/editable fields only (ignore computed/readonly fields)
- Merge augmented data with existing records
- Don't break relationships or duplicate records

**Pattern reference:** Study how normalized import works, add format detection

**Success criteria:**
- Import auto-detects format (shows to user, doesn't require selection)
- Context-rich import extracts augmented fields
- Context-rich import ignores computed fields (hierarchy, inventory, etc.)
- Augmented data merges correctly with existing records

---

### FR-5: Add Purchase Transaction Imports (NEW)

**What it must do:**
- Import food purchase transactions (product-based)
- Import material purchase transactions (material_product-based)
- Create purchase records in database
- Update inventory (increase quantities)
- Recalculate weighted average costs
- Validate product references (resolve slugs)
- Prevent duplicate purchases

**Business rules:**
- Purchases must have positive quantities
- Purchases must reference valid products
- Purchases create inventory increases

**Success criteria:**
- Purchase import creates purchase records
- Inventory increased correctly after import
- Costs recalculated (weighted average)
- Duplicate detection works (same product/date/cost)

---

### FR-6: Add Inventory Adjustment Imports (NEW)

**What it must do:**
- Import inventory adjustment transactions
- Support negative quantities ONLY (decreases)
- Require reason code (spoilage, waste, correction, other)
- Create adjustment records in database
- Update inventory (decrease quantities)
- Validate sufficient inventory exists

**Business rules:**
- Adjustments must have negative quantities (increases only via purchases)
- Adjustments require reason code
- Adjustments cannot create negative inventory

**Success criteria:**
- Adjustment import creates adjustment records
- Inventory decreased correctly after import
- Positive adjustments rejected with clear error
- Reason code required and validated

---

### FR-7: Redesign Import/Export UI

**What it must do:**

**Export UI Requirements:**
- Clearly distinguish 3 export types with purpose explanations:
  - Full Backup: "Everything (for complete restore)"
  - Catalog (Normalized): "Selected entities (for import/sharing)"
  - Catalog (Context-Rich): "Selected entities with full context (for AI/analysis)"
- For catalog exports: Entity selection (which entities to export)
- For full backup: No entity selection (always exports all)
- Format selection only for catalog exports (Normalized vs Context-Rich)

**Import UI Requirements:**
- Clearly distinguish import purposes:
  - Backup Restore: "Restore complete system state"
  - Catalog Import: "Add/update catalog definitions"
  - Purchase Import: "Import purchase transactions"
  - Inventory Adjustment Import: "Import inventory adjustments"
- Auto-detect file format (display to user for confirmation)
- Entity selection only relevant for catalog import
- Mode selection (ADD_ONLY/AUGMENT) only for catalog import

**UI should solve these problems:**
- Current UI doesn't distinguish export types → User confused about which export to use
- Current UI doesn't support transaction imports → User can't import purchases from mobile
- Entity checkboxes allow nonsensical combinations → Better approach needed

**Note:** Exact UI design (dropdowns vs radios vs auto-detection) determined during planning phase. Focus on WHAT the UI needs to accomplish, not HOW to implement it.

**Success criteria:**
- User can clearly choose between export types
- User understands purpose of each export type
- User can import purchases and inventory adjustments
- Format auto-detection works (user doesn't need to guess)
- Materials import works from UI

---

## Out of Scope

**Explicitly NOT included in Phase 1:**
- ❌ Finished goods import (deferred - not needed yet)
- ❌ Recipe import (deferred - catalog import sufficient for now)
- ❌ Production runs export (deferred - full backup includes if needed)
- ❌ Schema version validation (removed - "complies or doesn't" approach preferred)
- ❌ Initial inventory import (separate feature, not part of Phase 1)

---

## Success Criteria

**Complete when:**

### Full Backup
- [ ] All 14 entity types exported
- [ ] Manifest includes all entity counts
- [ ] Can restore complete system state from backup

### Context-Rich Export
- [ ] Ingredients exportable with full context
- [ ] Materials exportable with full context
- [ ] Recipes exportable with full context
- [ ] Exports include hierarchy paths, relationships, computed values

### Catalog Import
- [ ] Materials import works from UI
- [ ] Materials appear in Materials tab after import
- [ ] Material products slug resolution works

### Transaction Imports
- [ ] Purchase import creates purchase records
- [ ] Purchase import increases inventory
- [ ] Inventory adjustment import creates adjustment records
- [ ] Inventory adjustment import decreases inventory
- [ ] Positive adjustments rejected

### UI
- [ ] Export dialog supports all 3 export types
- [ ] Import dialog supports all 4 import purposes
- [ ] Format auto-detection works
- [ ] User flow is clear and intuitive

### Quality
- [ ] All exports use slug references (not IDs)
- [ ] Error messages clear and actionable
- [ ] Materials pattern matches ingredients exactly
- [ ] No code duplication

---

## Architecture Principles

### Export Types (3 distinct types)

**Type 1: Full Backup (Normalized)**
- Purpose: Complete backup/restore
- Format: Folder with 14 entity files + manifest
- References: Slug-based
- Scope: Everything

**Type 2: Catalog Export (Normalized)**
- Purpose: Batch operations, sharing, mobile sync
- Format: Single JSON file
- References: Slug-based
- Scope: Selected catalog entities

**Type 3: Catalog Export (Context-Rich)**
- Purpose: AI augmentation, external analysis
- Format: Single JSON file with embedded context
- References: Slug-based with nested relationships
- Scope: Selected catalog entities with full context

### Import Types (4 distinct types)

**Type 1: Backup Restore**
- Purpose: Restore complete system state
- Mode: Replace all (restore exact state)
- Validation: Manifest entity counts

**Type 2: Catalog Import (Normalized)**
- Purpose: Add/update catalog definitions
- Mode: ADD_ONLY or AUGMENT
- Validation: Slug references resolve

**Type 3: Catalog Import (Context-Rich)**
- Purpose: Import AI-augmented data
- Mode: AUGMENT (extract editable fields only)
- Validation: Ignore computed fields

**Type 4: Transaction Import**
- Purpose: Import purchases or inventory adjustments
- Mode: Append (add new transactions)
- Validation: Business rules (positive purchases, negative adjustments)

### Pattern Matching

**Materials must match ingredients exactly:**
- Same service call structure
- Same slug resolution approach
- Same error handling
- Same validation logic
- Same ADD_ONLY/AUGMENT behavior

**Context-rich exports must match view_*.json structure:**
- Metadata section (editable/readonly)
- Nested relationships
- Computed values
- Human-readable formats

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Slug-based references maintain integrity across export/import
- Business rules enforced (negative adjustments, positive purchases)

✅ **Principle II: Future-Proof Architecture**
- Complete backup enables safe schema migration via external transformation
- Context-rich exports enable AI augmentation workflows

✅ **Principle III: Layered Architecture**
- Services handle all export/import logic
- UI delegates to services
- Clear separation of concerns

✅ **Principle IV: Separation of Concerns**
- Export service separate from import service
- Transaction imports separate from catalog imports
- Format detection separate from import execution

✅ **Principle V: User-Centric Design**
- Clear UI distinguishing export types and import purposes
- Format auto-detection (user doesn't need to guess)
- Clear error messages

✅ **Principle VI: Pragmatic Aspiration**
- Builds on existing patterns (minimal disruption)
- No schema version tracking (external transformation approach)
- Appropriate for current development phase

---

## Risk Considerations

**Risk: Context-rich format inconsistent across entities**
- Study view_products.json first to understand pattern
- Match structure exactly for new entities

**Risk: Materials import breaks existing workflows**
- Copy ingredient pattern exactly
- Test thoroughly before considering complete

**Risk: Transaction imports bypass business rules**
- Validate purchases positive, adjustments negative
- Use existing service layer (don't bypass)

**Risk: UI redesign confuses users**
- Keep changes minimal where possible
- Clear labeling and purpose explanations
- Consider current user workflows

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study ingredients export → apply to materials
- Study view_products.json → apply to ingredients/materials/recipes context-rich
- Study _import_ingredients → apply to materials import
- Study purchase service → understand transaction import requirements

**Key Patterns to Copy:**
- Ingredient → Material (exact parallel)
- view_products.json → view_ingredients.json, view_materials.json, view_recipes.json
- Normalized import → Context-rich import (add format detection)

**Focus Areas:**
- Context-rich exports need full hierarchy paths (not just parent_id)
- Materials import must resolve slugs correctly
- Transaction imports must enforce business rules
- UI must clearly distinguish purposes

---

**END OF SPECIFICATION**
