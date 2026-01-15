# F052: Ingredient/Material Display & Hierarchy Admin MVP

**Version**: 1.0
**Priority**: HIGH
**Type**: UI Enhancement + Service Layer

---

## Executive Summary

Current ingredient and material listings conflate hierarchy management with normal user usage, showing bare L1 and L2 items mixed together which confuses users. Users need to see only L2 (leaf) items with their L0/L1 parent context for reference. Additionally, there's no way to perform basic administrative tasks (add new items, rename, reparent) without manual database manipulation.

Current gaps:
- ❌ Listings show L1+L2 mixed together (confusing - what's usable vs structural?)
- ❌ L0/L1 context not visible (user can't tell flour hierarchy at a glance)
- ❌ No admin UI for adding new ingredients/materials
- ❌ No admin UI for renaming items
- ❌ No admin UI for reparenting items
- ❌ Changes don't propagate to related entities (Products, Recipes dangling)

This spec provides L2-only listings with parent context and MVP admin functions for hierarchy management.

---

## Problem Statement

**Current State (CONFUSING):**
```
Ingredients Tab Display
├─ Shows mixed L1 and L2 items in single grid
├─ User can't distinguish structural (L1) from usable (L2)
├─ No parent context visible (which wheat flour? which sugar?)
└─ Same issue in Materials tab

Admin Functions
└─ ❌ NONE - must edit database directly

Hierarchy Management
├─ ❌ Can't add new L2 items (all-purpose flour alternatives)
├─ ❌ Can't rename items (fix typos, standardize names)
├─ ❌ Can't reparent items (move item to different L1/L0)
└─ ❌ No propagation to Products/Recipes (leaves dangling refs)
```

**Target State (CLEAR):**
```
Ingredients/Materials Tab Display
├─ ✅ L2 items only in main listing
├─ ✅ L0 column (top-level category visible)
├─ ✅ L1 column (subcategory visible)
├─ ✅ L2 column (actual ingredient/material name)
└─ ✅ User sees: "Flours & Starches | Wheat Flours | All-Purpose Flour"

Hierarchy Admin Mode (NEW)
├─ ✅ Add new L2 items (select L1 parent, name, properties)
├─ ✅ Rename any item (L0, L1, L2)
├─ ✅ Reparent items (move L2 to new L1, move L1 to new L0)
└─ ✅ Propagation service updates Products/Recipes automatically

Out of Scope (Initial MVP)
├─ ❌ Remove items (deferred - requires complex dependency handling)
├─ ❌ Import/remap (F054 - separate feature)
└─ ❌ OPML integration (external workflow TBD)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Ingredients Tab UI**
   - File: `src/ui/catalog/ingredients_tab.py`
   - Study current grid display structure
   - Note how hierarchy columns currently implemented
   - Understand filter patterns

2. **Materials Tab UI**
   - File: `src/ui/catalog/materials_tab.py`
   - Should match Ingredients pattern (F048 made them parallel)
   - Same grid structure expected
   - Same filter approach

3. **Ingredient Hierarchy Service**
   - Find ingredient hierarchy service (likely `ingredient_hierarchy_service.py`)
   - Study how parent/child relationships work
   - Note validation functions (can_change_parent, get_product_count, get_child_count)
   - Understand hierarchy_level (0=L0, 1=L1, 2=L2)

4. **Material Hierarchy (if exists)**
   - Check if materials have hierarchy service
   - Likely needs to be created paralleling ingredients
   - Materials have category/subcategory (similar to L0/L1)

5. **Product/Recipe Services**
   - Find product service methods referencing ingredients
   - Find recipe service methods referencing ingredients
   - Understand FK relationships for propagation

---

## Requirements Reference

This specification addresses user testing feedback:
- **Issue**: "Listing of bare L2 and L1 items is confusing to user"
- **Issue**: "Ingredient and Materials listings should show L2 items only, with associated L0/L1 parents for reference"
- **Issue**: "Management of these lists should be separate from using these lists"

From: `catalog_mgmt_mode_refactor.md`

---

## Functional Requirements

### FR-1: L2-Only Display with Parent Context

**What it must do:**
- Display only L2 (leaf) items in main Ingredients tab grid
- Display only materials (leaf level) in main Materials tab grid
- Show L0 parent in dedicated column (e.g., "Flours & Starches")
- Show L1 parent in dedicated column (e.g., "Wheat Flours")
- Show L2 name in dedicated column (e.g., "All-Purpose Flour")
- Filter L1 items out of main display (structural only, not usable)
- Maintain existing filter functionality (by L0, by L1)

**Pattern reference:** Current hierarchy columns exist - modify query to exclude L1 items

**Success criteria:**
- [ ] Ingredients tab shows only L2 items
- [ ] Materials tab shows only materials (not categories/subcategories)
- [ ] L0 column displays top-level parent
- [ ] L1 column displays intermediate parent
- [ ] L2 column displays item name
- [ ] User sees complete hierarchy path at a glance
- [ ] No structural items (L1) visible in main listing

---

### FR-2: Add New L2 Items (Admin Function)

**What it must do:**
- Provide admin UI to create new L2 ingredients
- Provide admin UI to create new materials
- Require selection of L1 parent (cascading selector: L0 → L1 → new L2)
- Require L2 name input
- Validate name uniqueness within sibling group
- Set hierarchy_level = 2 automatically
- Create ingredient/material record with parent reference

**UI location:** Admin submenu in Catalog mode (separate from main listings)

**Pattern reference:** Existing ingredient edit form has parent selection logic

**Success criteria:**
- [ ] Admin can create new L2 ingredient under any L1 parent
- [ ] Admin can create new material under any subcategory
- [ ] Cascading selector prevents invalid parent selection
- [ ] Name uniqueness validated (siblings can't have same name)
- [ ] Created items immediately appear in main L2 listing
- [ ] Created items available in Product/Recipe dropdowns

---

### FR-3: Rename Items (Admin Function)

**What it must do:**
- Provide admin UI to rename any item (L0, L1, or L2 for ingredients)
- Provide admin UI to rename categories, subcategories, or materials
- Show current name
- Require new name input
- Validate new name uniqueness within sibling group
- Update display_name field
- Propagate name change to related entities (read-only display fields)

**Propagation targets:**
- Products referencing ingredient/material (display purposes)
- Recipes referencing ingredient (display purposes)
- Historical snapshots should NOT change (F037 immutability)

**Pattern reference:** Ingredient edit form has rename capability - extract to admin

**Success criteria:**
- [ ] Admin can rename any L0, L1, or L2 ingredient
- [ ] Admin can rename any category, subcategory, or material
- [ ] Name change visible immediately in all listings
- [ ] Products display updated ingredient/material names
- [ ] Recipes display updated ingredient names
- [ ] Historical snapshots preserve original names (immutable)

---

### FR-4: Reparent Items (Admin Function)

**What it must do:**
- Provide admin UI to move L2 items to different L1 parent
- Provide admin UI to move L1 items to different L0 parent
- Provide admin UI to move materials to different subcategory
- Show current parent hierarchy
- Provide cascading selector for new parent
- Validate move doesn't create cycles (L2 can't become parent of its L1)
- Update parent_ingredient_id / parent FK
- Propagate change to dependent entities

**Propagation implications:**
- Products linked to L2 keep same ingredient (FK unchanged)
- Recipes linked to L2 keep same ingredient (FK unchanged)
- Display context changes (new L0/L1 path shows in dropdowns)

**Pattern reference:** Ingredient hierarchy service has can_change_parent validation

**Success criteria:**
- [ ] Admin can move L2 ingredient to new L1 parent
- [ ] Admin can move L1 ingredient to new L0 parent
- [ ] Admin can move material to new subcategory
- [ ] Cycle detection prevents invalid moves
- [ ] Products/Recipes maintain correct references
- [ ] New hierarchy path displays correctly everywhere

---

### FR-5: Hierarchy Admin UI

**What it must do:**

**UI Requirements:**
- Add "Hierarchy Admin" option to Catalog mode menu
- Hierarchy Admin opens admin interface (separate from main listings)
- Admin interface shows:
  - Current hierarchy tree view (expandable/collapsible)
  - Selected item details (name, parent, level, usage count)
  - Action buttons: Add L2 Item, Rename Item, Reparent Item
- Each action opens dialog with relevant form
- Validation errors display clearly before commit
- Success confirmation after each action

**UI should solve:**
- Current problem: No admin UI exists (must edit database)
- Current problem: User listings conflate admin and usage
- Current problem: Can't tell what depends on an item

**Note:** Exact UI design (tree widget vs grid vs hybrid) determined during planning phase. Focus on WHAT the UI needs to accomplish.

**Success criteria:**
- [ ] Hierarchy Admin accessible from Catalog mode menu
- [ ] Tree view shows complete hierarchy (L0 → L1 → L2)
- [ ] Selected item shows usage counts (products, recipes)
- [ ] Add/Rename/Reparent actions available
- [ ] Validation prevents invalid operations
- [ ] Changes immediately reflected in main listings

---

## Out of Scope

**Explicitly NOT included in F052 MVP:**
- ❌ Remove items (F054 - requires dependency handling, remap tracking)
- ❌ Import hierarchies with remap (F054 - separate feature)
- ❌ OPML integration (external workflow TBD)
- ❌ Semantic versioning (F054 - with import/remap)
- ❌ L0 add/remove (MVP focuses on L2 user needs)
- ❌ Bulk operations (one-at-a-time sufficient for MVP)
- ❌ Undo/redo (can add later if needed)

---

## Success Criteria

**Complete when:**

### L2-Only Display
- [ ] Ingredients tab shows only L2 items (no L1 structural items)
- [ ] Materials tab shows only materials (no categories/subcategories)
- [ ] Three columns visible: L0 | L1 | L2
- [ ] User can see complete hierarchy path at a glance
- [ ] Filters still work (by L0, by L1)

### Admin Functions
- [ ] Can add new L2 ingredient under any L1 parent
- [ ] Can add new material under any subcategory
- [ ] Can rename any item (L0, L1, L2, categories, subcategories, materials)
- [ ] Can reparent L2 items (move to new L1)
- [ ] Can reparent materials (move to new subcategory)

### Propagation
- [ ] Renamed items display correctly in Products
- [ ] Renamed items display correctly in Recipes
- [ ] Reparented items show new hierarchy in dropdowns
- [ ] Historical snapshots unchanged (immutable)

### UI Quality
- [ ] Hierarchy Admin accessible from Catalog menu
- [ ] Tree view shows complete hierarchy
- [ ] Usage counts visible (products, recipes using item)
- [ ] Validation prevents invalid operations
- [ ] Error messages clear and actionable
- [ ] Success confirmations after changes

### Code Quality
- [ ] Materials hierarchy admin matches Ingredients pattern
- [ ] No code duplication between Ingredients/Materials
- [ ] Validation consistent (names, cycles, relationships)
- [ ] Comprehensive error handling

---

## Architecture Principles

### Display Principle: L2-Only Listings

**User listings show only usable items:**
- Ingredients tab: L2 items only (leaf nodes)
- Materials tab: Materials only (not categories/subcategories)
- L0/L1 context visible for reference
- Structural items (L1) hidden from main view

**Rationale**: User doesn't care about "Wheat Flours" (L1) as a concept, they care about "All-Purpose Flour" (L2). Showing L1 in listings is confusing.

### Admin Principle: Separate from Usage

**Admin functions in separate interface:**
- Main listings for selecting/using items
- Hierarchy Admin for managing structure
- Clear separation prevents accidental changes
- Usage counts inform admin decisions

**Rationale**: Managing hierarchy is administrative task, not daily workflow. Separate UI prevents confusion and accidental modifications.

### Pattern Matching

**Materials must match Ingredients exactly:**
- Same L2-only display logic
- Same admin UI structure
- Same validation rules
- Same propagation behavior
- Materials use "Material" instead of "Ingredient" in UI labels

**Ingredients hierarchy:**
- L0 = top category (e.g., "Flours & Starches")
- L1 = subcategory (e.g., "Wheat Flours")
- L2 = actual ingredient (e.g., "All-Purpose Flour")

**Materials hierarchy:**
- Category = L0 equivalent (e.g., "Boxes")
- Subcategory = L1 equivalent (e.g., "Window Boxes")
- Material = L2 equivalent (e.g., "10x10 Cake Box")

### Propagation Rules

**Name changes propagate to:**
- Product display (for reference)
- Recipe display (for reference)
- Any UI showing ingredient/material name

**Name changes do NOT propagate to:**
- Historical recipe snapshots (F037 immutability)
- Archived production runs (immutable history)

**Reparent changes affect:**
- Hierarchy path display (new L0 → L1 → L2)
- Cascading dropdowns (item appears under new parent)
- Filter results (item appears in new L0/L1 filters)

**Reparent changes do NOT affect:**
- Product FKs (still reference same ingredient_id)
- Recipe FKs (still reference same ingredient_id)
- Any actual data relationships (only display context changes)

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Validation prevents invalid hierarchy changes
- Propagation maintains referential integrity
- Historical data remains immutable

✅ **Principle II: Future-Proof Architecture**
- L2-only display aligns with multi-tenant model (system catalogs)
- Admin separation prepares for role-based access control
- Hierarchy management framework supports future import/remap (F054)

✅ **Principle III: Layered Architecture**
- Service layer handles hierarchy logic
- UI layer delegates to services
- Clear separation of concerns

✅ **Principle IV: Separation of Concerns**
- Display logic separate from admin logic
- Validation separate from persistence
- Propagation separate from user actions

✅ **Principle V: User-Centric Design**
- L2-only display matches user mental model
- Admin functions accessible but separate
- Usage counts inform decisions

✅ **Principle VI: Pragmatic Aspiration**
- MVP focuses on essential operations (add, rename, reparent)
- Defers complex operations (remove, import) to F054
- Builds foundation without over-engineering

---

## Risk Considerations

**Risk: Propagation breaks existing references**
- Products/Recipes reference by ID (stable)
- Display name updates don't affect FKs
- Historical snapshots immutable (F037)

**Risk: L2-only display hides needed information**
- L0/L1 context visible in dedicated columns
- Filters still allow browsing by L0/L1
- Tree view available in Hierarchy Admin

**Risk: Materials hierarchy doesn't exist yet**
- Materials have category/subcategory (similar structure)
- Copy Ingredients hierarchy service pattern
- Same validation rules apply

**Risk: Admin UI too complex for MVP**
- Focus on essential three operations (add, rename, reparent)
- Defer remove operations (complex dependency handling)
- Simple forms sufficient for MVP

**Risk: Reparenting breaks expectations**
- Validation prevents cycles
- Usage counts show impact before commit
- Can be undone by reparenting back

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study ingredients_tab.py → modify query to filter L1 items
- Study ingredient hierarchy service → copy validation patterns
- Study materials_tab.py → apply same L2-only logic
- Study ingredient edit form → extract admin functions

**Key Implementation Areas:**

**Display Changes:**
- Ingredients tab: Add WHERE hierarchy_level = 2 to query
- Materials tab: Exclude categories/subcategories from query
- Keep existing L0/L1/L2 columns (already implemented F032/F048)

**Hierarchy Admin UI:**
- New menu item: "Hierarchy Admin" in Catalog mode
- Tree view widget showing complete hierarchy
- Item details panel (usage counts from service queries)
- Action dialogs (Add L2, Rename, Reparent)

**Service Layer:**
- Hierarchy service methods: add_l2_item(), rename_item(), reparent_item()
- Validation methods: validate_name_unique(), validate_no_cycles()
- Propagation methods: propagate_name_change(), propagate_reparent()
- Materials hierarchy service (copy Ingredients pattern if doesn't exist)

**Focus Areas:**
- L2-only query filters (simplest change, biggest impact)
- Admin UI separation (tree view + action dialogs)
- Materials parallels Ingredients exactly
- Propagation maintains immutability (snapshots unchanged)

---

**END OF SPECIFICATION**

### Immutability Principle: Definition Layer Only

**All changes affect definition layer only:**
- Ingredient/Material catalog definitions
- Product definitions (display names only)
- Recipe templates (display references only)

**Instantiated data remains completely untouched:**
- Recipe snapshots (F037 immutability - frozen at creation)
- Production runs (historical records - immutable)
- Purchases (historical transactions - immutable)
- Inventory records (actual stock - unaffected)
- Consumption records (FIFO ledger - immutable)
- Assembly runs (historical assembly - immutable)

**Rationale**: 
- Historical data must remain accurate to what actually happened
- Recipe snapshot captured ingredient name at time of production
- COGS calculations depend on immutable purchase/production history
- Audit trail requires unchangeable transactional records

**Implementation Note**: 
- Renames update `ingredient.display_name` only
- Products/Recipes reference by FK (ID never changes)
- Display layer pulls current name for future use
- Historical snapshots preserve original names frozen at creation time

**This ensures:**
- User can rename "All-Purpose Flour" to "AP Flour" today
- But yesterday's production run still shows "All-Purpose Flour" (what it was called then)
- Financial reports remain accurate to historical costs
- No risk of corrupting transactional data

---

