# F055: UI Navigation Cleanup

**Version**: 1.0
**Priority**: HIGH
**Type**: UI Enhancement

---

## Executive Summary

Current UI navigation doesn't match the user's mental model of workflow progression. Mode order is illogical, menu structure doesn't reflect natural groupings, and several UI elements are broken or wasteful of screen space. Users need clear navigation that matches how they actually work: Observe status → Manage catalog → Plan event → Purchase ingredients → Make goods → Deliver to recipients.

Current issues:
- ❌ Mode order doesn't match workflow (Catalog first, but it's not first step)
- ❌ Catalog menu structure irrational (Materials has submenu, Ingredients doesn't)
- ❌ Purchase submenu backwards (Shopping Lists first, should be last)
- ❌ Broken top section wastes 3-5 lines of screen space
- ❌ Catalog/Inventory tree view unnecessary (adds complexity, no benefit)

This spec reorders modes to match workflow, restructures menus for consistency, and removes broken/wasteful UI elements.

---

## Problem Statement

**Current State (CONFUSING):**
```
Mode Order (Top Navigation)
├─ Catalog (first, but not first workflow step)
├─ Plan
├─ Purchase
├─ Make
└─ Observe (last, but should be first - dashboard view)

Catalog Menu Structure
├─ Ingredients (no submenu - flat)
├─ Products (orphaned from Ingredients)
├─ Recipes (no submenu)
├─ Finished Units
├─ Finished Goods
├─ Packages
└─ Materials
    ├─ Materials Catalog (submenu)
    ├─ Material Products (submenu)
    └─ Material Units (submenu)

Purchase Menu Order
├─ Shopping Lists (first - but created last in workflow)
├─ Purchases (middle)
└─ Inventory (last - but checked first in workflow)

Broken/Wasteful Elements
├─ Top section shows "CATALOG 0 Ingredients 0 Products 0 Recipes" (broken counts)
├─ Catalog/Inventory tab has tree view (unused, adds complexity)
└─ Wastes 3-5 lines of vertical space
```

**Target State (CLEAR):**
```
Mode Order (Matches Workflow)
├─ Observe (dashboard - check status first)
├─ Catalog (manage definitions)
├─ Plan (create event plans)
├─ Purchase (buy ingredients)
├─ Make (produce goods)
└─ Deliver (ship to recipients)

Catalog Menu Structure (Logical Grouping)
├─ Ingredients
│   ├─ Ingredient Catalog
│   └─ Food Products
├─ Materials
│   ├─ Material Catalog
│   ├─ Material Units
│   └─ Material Products
├─ Recipes
│   ├─ Recipes Catalog
│   └─ Finished Units (defined on recipes)
└─ Packaging
    ├─ Finished Goods (Food Only)
    ├─ Finished Goods (Bundles)
    └─ Packages

Purchase Menu Order (Workflow Order)
├─ Inventory (check what you have first)
├─ Purchases (record what you bought)
└─ Shopping Lists (plan what to buy next)

Clean UI
├─ Top section removed (broken, wasteful)
└─ Tree view removed from Catalog/Inventory (unused)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Mode Navigation**
   - Find main window mode switching logic
   - Study how modes are ordered in top navigation
   - Note how mode constants are defined
   - Understand keyboard shortcuts (Ctrl+1-5 currently)

2. **Catalog Menu Structure**
   - File: Catalog mode implementation (likely `src/ui/catalog/`)
   - Study current menu/tab structure
   - Note how submenus are created
   - Understand navigation between tabs

3. **Purchase Menu Structure**
   - File: Purchase mode implementation (likely `src/ui/purchase/`)
   - Study current submenu order
   - Note how tabs are organized
   - Understand navigation patterns

4. **Top Section Display**
   - Find where "CATALOG X Ingredients Y Products" is rendered
   - Understand what it was supposed to show
   - Identify why counts are broken (likely 0s)
   - Locate removal point

5. **Tree View Component**
   - Find tree view in Catalog/Inventory tab
   - Understand what it displays
   - Note if it's used anywhere
   - Identify safe removal point

---

## Requirements Reference

This specification addresses user testing feedback:
- **Issue**: "UI still doesn't reflect realistic user mental mode"
- **Issue**: "Catalog & Observe represent library/dashboard function, not 'doing' function"
- **Issue**: "Better mental model: Observe, Catalog, Plan, Purchase, Make, Deliver"
- **Issue**: "Menu structure not rational - Materials has submenu, Ingredients doesn't"
- **Issue**: "Purchase submenu ordered Shopping Lists, Purchases, Inventory - should be flipped"
- **Issue**: "Top section not useful and uses valuable screen space"
- **Issue**: "Catalog/Inventory tree view not needed, can be removed"

From: `catalog_mgmt_mode_refactor.md`

---

## Functional Requirements

### FR-1: Reorder Modes to Match Workflow

**What it must do:**
- Change mode order from: Catalog, Plan, Purchase, Make, Observe
- To new order: Observe, Catalog, Plan, Purchase, Make, Deliver
- Update keyboard shortcuts to match new order:
  - Ctrl+1: Observe
  - Ctrl+2: Catalog
  - Ctrl+3: Plan
  - Ctrl+4: Purchase
  - Ctrl+5: Make
  - Ctrl+6: Deliver (new mode, placeholder for future)
- Update any mode constants/enums to reflect new order
- Ensure mode switching still works correctly

**Workflow rationale:**
- Observe: Check dashboard, see status (START HERE)
- Catalog: Manage definitions (ingredients, recipes, materials)
- Plan: Create event plans (what to make, when)
- Purchase: Buy ingredients/materials (shopping workflow)
- Make: Produce goods (production workflow)
- Deliver: Ship to recipients (packaging/delivery workflow)

**Pattern reference:** Existing mode switching logic - just reorder

**Success criteria:**
- [ ] Modes appear in order: Observe, Catalog, Plan, Purchase, Make, Deliver
- [ ] Keyboard shortcuts work with new order
- [ ] Mode switching functions correctly
- [ ] No broken navigation
- [ ] Deliver mode shows placeholder (not implemented yet)

---

### FR-2: Restructure Catalog Menu

**What it must do:**
- Reorganize Catalog menu with logical groupings
- Create submenus for Ingredients, Materials, Recipes, Packaging
- Structure:

**Ingredients** (submenu):
- Ingredient Catalog (current Ingredients tab)
- Food Products (current Products tab)

**Materials** (submenu - already exists, preserve):
- Material Catalog (current Materials Catalog)
- Material Units (current Material Units)
- Material Products (current Material Products)

**Recipes** (submenu):
- Recipes Catalog (current Recipes tab)
- Finished Units (current Finished Units tab - listing)

**Packaging** (submenu):
- Finished Goods (Food Only) (current FinishedGoods filtered)
- Finished Goods (Bundles) (current FinishedGoods filtered)
- Packages (current Packages tab)

**Pattern reference:** Materials submenu structure (already implemented in F047/F048)

**Success criteria:**
- [ ] Catalog menu has 4 top-level items (Ingredients, Materials, Recipes, Packaging)
- [ ] Each has submenu with relevant tabs
- [ ] Navigation between tabs works
- [ ] All existing tabs still accessible
- [ ] Structure matches Materials pattern (consistency)

---

### FR-3: Reorder Purchase Menu

**What it must do:**
- Change Purchase submenu order from: Shopping Lists, Purchases, Inventory
- To new order: Inventory, Purchases, Shopping Lists
- Update tab display order to match
- Maintain existing functionality

**Workflow rationale:**
- Inventory: Check what you have (START HERE)
- Purchases: Record what you bought (next step)
- Shopping Lists: Plan what to buy next (final step)

**Pattern reference:** Simple reordering - no logic changes

**Success criteria:**
- [ ] Purchase submenu shows: Inventory, Purchases, Shopping Lists
- [ ] Tabs display in new order
- [ ] All existing functionality works
- [ ] Navigation between tabs works

---

### FR-4: Remove Broken Top Section

**What it must do:**
- Remove top section from all mode tabs
- This is the section showing "CATALOG 0 Ingredients 0 Products 0 Recipes"
- Reclaim 3-5 lines of vertical screen space
- Ensure no broken references after removal

**What's broken:**
- Counts always show 0 (calculation broken)
- Not useful even if counts worked (user can see grid below)
- Wastes valuable screen space

**Pattern reference:** Similar to F042 dashboard header cleanup

**Success criteria:**
- [ ] Top section removed from Catalog mode
- [ ] Top section removed from other modes (if present)
- [ ] 3-5 additional lines of grid visible
- [ ] No errors after removal
- [ ] Clean appearance

---

### FR-5: Remove Tree View from Catalog/Inventory

**What it must do:**
- Remove tree view component from Catalog/Inventory tab
- This is an unused hierarchical view
- Simplify UI (one less component)
- Reclaim screen space

**Why remove:**
- Not used in current workflow
- Adds complexity without benefit
- User works with grid view only
- F052 adds Hierarchy Admin for tree view needs

**Pattern reference:** Component removal - clean deletion

**Success criteria:**
- [ ] Tree view removed from Catalog/Inventory tab
- [ ] Grid view expands to use full space
- [ ] No errors after removal
- [ ] Navigation still works
- [ ] Simpler, cleaner UI

---

### FR-6: Add Deliver Mode Placeholder

**What it must do:**
- Add Deliver mode to mode navigation
- Show placeholder dashboard (not implemented yet)
- Display message: "Delivery workflows coming soon"
- Keyboard shortcut: Ctrl+6

**Purpose:**
- Reserve space in navigation
- Complete mental model (Observe → Catalog → Plan → Purchase → Make → Deliver)
- Users can see full workflow even if not implemented

**Pattern reference:** Similar to dashboard placeholder pattern

**Success criteria:**
- [ ] Deliver mode appears in navigation
- [ ] Ctrl+6 activates Deliver mode
- [ ] Placeholder message displays
- [ ] No errors when accessing mode

---

## Out of Scope

**Explicitly NOT included in F053:**
- ❌ Deliver mode functionality (F059 - separate feature)
- ❌ Shopping Lists tab functionality (existing, preserve as-is)
- ❌ Changing any tab content (only navigation/organization)
- ❌ Filtering logic changes (only menu structure)
- ❌ Hierarchy Admin UI (F052 - separate feature)

---

## Success Criteria

**Complete when:**

### Mode Navigation
- [ ] Modes ordered: Observe, Catalog, Plan, Purchase, Make, Deliver
- [ ] Keyboard shortcuts updated (Ctrl+1-6)
- [ ] All modes accessible and functional
- [ ] Deliver mode shows placeholder

### Catalog Menu
- [ ] 4 top-level groups: Ingredients, Materials, Recipes, Packaging
- [ ] Ingredients submenu: Ingredient Catalog, Food Products
- [ ] Materials submenu: Material Catalog, Material Units, Material Products
- [ ] Recipes submenu: Recipes Catalog, Finished Units
- [ ] Packaging submenu: Finished Goods (Food), Finished Goods (Bundles), Packages
- [ ] All tabs accessible via new structure

### Purchase Menu
- [ ] Order: Inventory, Purchases, Shopping Lists
- [ ] All tabs functional
- [ ] Navigation works

### UI Cleanup
- [ ] Broken top section removed from all modes
- [ ] Tree view removed from Catalog/Inventory
- [ ] 3-5+ additional grid rows visible
- [ ] Clean, uncluttered appearance

### Quality
- [ ] No broken navigation
- [ ] No errors after changes
- [ ] Existing functionality preserved
- [ ] Consistent patterns across modes

---

## Architecture Principles

### Workflow-Aligned Navigation

**Mode order matches actual workflow:**
1. Observe: See status (dashboard)
2. Catalog: Manage definitions (setup)
3. Plan: Create event plans (what to make)
4. Purchase: Buy ingredients (shopping)
5. Make: Produce goods (production)
6. Deliver: Ship to recipients (fulfillment)

**Rationale**: User mental model follows this sequence. Navigation should match.

### Hierarchical Menu Structure

**Group related functions:**
- Ingredients: Catalog + Products
- Materials: Catalog + Units + Products
- Recipes: Catalog + Finished Units
- Packaging: Finished Goods + Packages

**Rationale**: Related items grouped together reduces cognitive load. Parallel structure (Ingredients like Materials) creates consistency.

### Progressive Disclosure

**Purchase workflow order:**
1. Check inventory (what do I have?)
2. Record purchases (what did I buy?)
3. Create shopping lists (what do I need?)

**Rationale**: Each step logically follows previous. User checks, then records, then plans.

### Minimal UI Principle

**Remove broken/unused elements:**
- Broken top section (0 counts, not useful)
- Tree view (unused, complexity without benefit)

**Rationale**: Every UI element has maintenance cost. Remove what doesn't provide value.

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- No data changes (navigation only)
- Existing functionality preserved

✅ **Principle II: Future-Proof Architecture**
- Deliver mode placeholder prepares for future
- Hierarchical structure supports role-based access (future)

✅ **Principle III: Layered Architecture**
- UI navigation changes only
- No service layer changes
- Clear separation maintained

✅ **Principle IV: Separation of Concerns**
- Navigation separate from functionality
- Menu structure separate from tab content
- Mode order separate from mode implementation

✅ **Principle V: User-Centric Design**
- Workflow-aligned navigation
- Logical groupings
- Reduced clutter

✅ **Principle VI: Pragmatic Aspiration**
- Simple reordering/restructuring
- Removes broken elements
- Prepares for future (Deliver mode) without over-engineering

---

## Risk Considerations

**Risk: Mode reordering breaks expectations**
- Users may have muscle memory for Ctrl+1 = Catalog
- Mitigation: New order more intuitive, worth brief adjustment
- Keyboard shortcut tooltips help

**Risk: Menu restructuring confuses users**
- Users know where tabs are currently
- Mitigation: Logical grouping easier to remember long-term
- Parallel structure (Ingredients like Materials) aids learning

**Risk: Removing elements breaks something**
- Top section or tree view may have hidden dependencies
- Mitigation: Planning phase identifies dependencies
- Can add back if truly needed (unlikely)

**Risk: Deliver mode placeholder confusing**
- Users might expect it to work
- Mitigation: Clear "coming soon" message
- Shows complete workflow vision

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study Materials submenu structure → copy for Ingredients/Recipes/Packaging
- Study mode switching logic → identify reordering points
- Study keyboard shortcut mapping → update for new mode order
- Find top section rendering → identify removal point

**Key Implementation Areas:**

**Mode Order:**
- Update mode enum/constants (OBSERVE=1, CATALOG=2, etc.)
- Update keyboard shortcut mapping
- Update top navigation display order
- Add Deliver mode with placeholder

**Catalog Menu:**
- Create Ingredients submenu (copy Materials pattern)
- Create Recipes submenu (copy Materials pattern)
- Create Packaging submenu (copy Materials pattern)
- Wire tabs to new menu structure

**Purchase Menu:**
- Reorder tabs: Inventory first, Shopping Lists last
- Update submenu order
- No logic changes needed

**UI Cleanup:**
- Remove top section widget/component
- Remove tree view widget from Catalog/Inventory
- Verify no broken references

**Focus Areas:**
- Mode order changes are cosmetic (no logic changes)
- Menu restructuring provides consistency
- Element removal simplifies codebase
- All existing functionality preserved

---

**END OF SPECIFICATION**
