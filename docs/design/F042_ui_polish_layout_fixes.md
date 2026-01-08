# UI Polish & Layout Fixes - Feature Specification

**Feature ID**: F042
**Feature Name**: UI Polish & Layout Fixes
**Priority**: P0 - BLOCKING (blocks foundational workflows F043-F047)
**Status**: Design Specification
**Created**: 2026-01-08
**Dependencies**: F038 (UI Mode Restructure) ✅
**Constitutional References**: Principle I (User-Centric Design), Principle VII (Pragmatic Aspiration)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, UI mockups, and implementation patterns. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification

**The user testing feedback is the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

**Problem**: User testing (2026-01-07) identified critical UI/UX issues blocking effective use of the application:
- Header areas consume excessive vertical space (50%+ of screen)
- Data grids only 2 rows high (unmanageable for 400+ ingredients, 150+ products)
- Ingredient hierarchy concatenated (L0|L1|L2 unreadable, should be separate columns)
- Stats display "0" despite data existing (calculation or refresh bug)
- Filter UI inconsistent across tabs (should match Product Catalog pattern)

**Impact**: Features are functional but unusable. User cannot browse catalogs, find items, or validate data effectively.

**Solution**: Systematic UI polish pass addressing layout, spacing, column design, and filter consistency. Mode terminology cleanup (Shop→Purchase, Produce→Make).

**Scope**:
- Compact headers to 3-4 lines max (all modes)
- Expand data grids to use available vertical space
- Separate ingredient hierarchy into L0/L1/L2 columns
- Fix stats calculation/display bugs
- Standardize filter UI across all tabs (match Product Catalog)
- Rename modes: Shop→Purchase, Produce→Make

---

## 1. Problem Statement

### 1.1 User Testing Results (2026-01-07)

**Critical Issues Identified:**

```
❌ BLOCKING: Headers consume 8-12 lines of vertical space
   → Data grids only 2-3 rows visible
   → User cannot browse 400+ ingredients or 150+ products effectively

❌ BLOCKING: Ingredient hierarchy concatenated "Grain|Flour|All-Purpose"
   → Unreadable in Inventory tab
   → Cannot filter by hierarchy level
   → Breaks user mental model (expect separate columns)

❌ BLOCKING: Stats show "0" even after clicking Refresh
   → "0 ingredients" when 413 loaded
   → Breaks user confidence in data accuracy

❌ BLOCKING: Filter UI inconsistent
   → Ingredients tab: "Subcategory filters very odd implementation"
   → Should match Product Catalog cascading dropdown pattern
   → Users confused by different filter UX in each tab
```

**User Feedback Quotes:**
- "Header area way too large" (repeated for ALL modes)
- "Ingredient listing only two rows high... unmanageable as is"
- "Very odd implementation" (subcategory filters)
- "Stats shown in header summary area are all '0'"

### 1.2 Mode Terminology Issues

```
Current Mode Names:
- Shop → Ambiguous (shopping? browsing?)
- Produce → Ambiguous (produce vegetables? produce goods?)

Expected Mode Names:
- Purchase → Clear action (buying ingredients)
- Make → Clear action (making finished goods)
```

**Rationale**: Mode names should be unambiguous verbs that clearly describe the primary action in that mode.

---

## 2. Proposed Solution

### 2.1 Header Compaction Strategy

**Current Problem:**
```
┌─ CATALOG Mode (Current) ─────────────────────────────────┐
│                                                           │ ← Line 1: Empty
│  📊 CATALOG                                               │ ← Line 2: Mode name
│  Manage ingredients, products, and recipes                │ ← Line 3: Subtitle
│                                                           │ ← Line 4: Empty
│  🔍 Quick Stats                                           │ ← Line 5: Section header
│  • 0 ingredients (🔴 Stale)                               │ ← Line 6: Stat
│  • 0 products (🔴 Stale)                                  │ ← Line 7: Stat
│  • 0 recipes (🔴 Stale)                                   │ ← Line 8: Stat
│                                                           │ ← Line 9: Spacer
│  [Refresh Stats]                                          │ ← Line 10: Button
│  ──────────────────────────────────────────────────       │ ← Line 11: Separator
│                                                           │ ← Line 12: Empty
│  ╔═════════════════════════════════════════════════╗     │
│  ║ INGREDIENTS TAB                                 ║     │
│  ║ (Only 2 rows visible here!)                     ║     │
│  ╚═════════════════════════════════════════════════╝     │
└───────────────────────────────────────────────────────────┘
```

**Proposed Solution:**
```
┌─ CATALOG Mode (Compact) ─────────────────────────────────┐
│  📊 CATALOG  •  413 ingredients  •  153 products  •  87 recipes │ ← Line 1: Inline stats
│  [My Ingredients] [Product Catalog] [Recipes]            │ ← Line 2: Tabs
│  ──────────────────────────────────────────────────       │ ← Line 3: Separator
│                                                           │
│  ╔═════════════════════════════════════════════════╗     │
│  ║ INGREDIENTS TAB                                 ║     │
│  ║                                                 ║     │
│  ║  (20-30 rows visible here)                      ║     │
│  ║                                                 ║     │
│  ║                                                 ║     │
│  ║                                                 ║     │
│  ╚═════════════════════════════════════════════════╝     │
└───────────────────────────────────────────────────────────┘
```

**Key Changes:**
- **Inline stats** in mode header (not separate section)
- **Remove subtitles** (unnecessary noise)
- **Remove refresh button** (stats auto-calculate on tab switch)
- **Remove empty lines** (wasted space)
- **Result**: 12 lines → 3 lines (9 lines reclaimed for data grid)

### 2.2 Data Grid Expansion

**Goal**: Data grids should occupy 70-80% of available vertical space.

**Current**: Grids are 2-3 rows high (150px fixed height?)
**Target**: Grids expand to fill available space (400-600px, ~20-30 rows)

**Implementation Pattern** (CustomTkinter):
```python
# Bad: Fixed height
grid_frame = ctk.CTkScrollableFrame(parent, height=150)

# Good: Expand to fill
grid_frame = ctk.CTkScrollableFrame(parent)
grid_frame.pack(fill="both", expand=True)
```

### 2.3 Ingredient Hierarchy Column Separation

**Current Problem** (Inventory tab):
```
┌─ My Pantry ───────────────────────────────────────────┐
│  Ingredient           Product          Qty    Fresh   │
│  ────────────────      ──────────────   ───    ─────  │
│  Grain|Flour|AP       King Arthur 25lb  10c    🟢     │ ← Unreadable!
│  Dairy|Milk|Whole     Organic Valley    1gal   🟡     │
└───────────────────────────────────────────────────────┘
```

**Proposed Solution**:
```
┌─ My Pantry ───────────────────────────────────────────────────┐
│  L0      L1      L2              Product          Qty   Fresh │
│  ───     ───     ──────────────   ─────────────   ───   ───── │
│  Grain   Flour   All-Purpose     King Arthur 25lb 10c   🟢    │
│  Dairy   Milk    Whole            Organic Valley  1gal  🟡    │
│  Leavener Yeast  Active Dry       Red Star        2oz   🟢    │
└───────────────────────────────────────────────────────────────┘
```

**Column Headers:**
- **L0**: Top-level category (Grain, Dairy, Leavener)
- **L1**: Mid-level category (Flour, Milk, Yeast)
- **L2**: Leaf ingredient (All-Purpose, Whole, Active Dry)

**Rationale**:
- Matches Product Catalog column layout (consistency)
- Enables sorting/filtering by hierarchy level
- Human-readable (not concatenated string)

### 2.4 Filter UI Standardization

**Standard Pattern** (Product Catalog - already correct):
```
┌─ Product Catalog ─────────────────────────────────────────┐
│  [🔍 Search...] [☑ Show Hidden] [+ Add Product]          │ ← Single row
│                                                            │
│  [L0: All ▼] [L1: All ▼] [L2: All ▼]                     │ ← Cascading filters
│                                                            │
│  ╔═══════════════════════════════════════════════════╗    │
│  ║ L0      L1      L2              Product           ║    │
│  ║ ───     ───     ──────────────   ──────────────   ║    │
│  ╚═══════════════════════════════════════════════════╝    │
└────────────────────────────────────────────────────────────┘
```

**Apply Same Pattern To:**

**My Ingredients Tab:**
```
┌─ My Ingredients ──────────────────────────────────────────┐
│  [🔍 Search...] [☑ Show Hidden] [+ Add Ingredient]        │
│  [L0: All ▼] [L1: All ▼] [L2: All ▼]                     │
│                                                            │
│  413 ingredients loaded                                    │ ← Inline count
│                                                            │
│  ╔═══════════════════════════════════════════════════╗    │
│  ║ L0      L1      L2              Name              ║    │
│  ╚═══════════════════════════════════════════════════╝    │
└────────────────────────────────────────────────────────────┘
```

**My Pantry (Inventory) Tab:**
```
┌─ My Pantry ───────────────────────────────────────────────┐
│  [🔍 Search...] [Freshness: All ▼] [+ Add Purchase]       │
│  [L0: All ▼] [L1: All ▼] [L2: All ▼]                     │
│                                                            │
│  ╔═══════════════════════════════════════════════════╗    │
│  ║ L0      L1      L2              Product    Qty    ║    │
│  ╚═══════════════════════════════════════════════════╝    │
└────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Cascading dropdowns**: L0 → L1 → L2 (L1 filtered by L0 selection, L2 by L1)
- **Consistent positioning**: Always same row, same order
- **Search bar**: First element, left-aligned
- **Action buttons**: Right-aligned
- **No custom widget layouts** per tab (reuse common filter bar component)

### 2.5 Stats Calculation Fix

**Current Bug**: Stats show "0" even when data exists.

**Root Cause Investigation** (likely causes):
```
1. Stats not refreshing on tab load
   → Fix: Auto-refresh stats when mode/tab activated

2. Stats query incorrect (filtering out valid data)
   → Fix: Review SQL queries in dashboard services

3. Stats cached incorrectly
   → Fix: Force stats recalculation on relevant data changes

4. UI binding issue (stats calculated but not displayed)
   → Fix: Verify UI update mechanism
```

**Solution Approach**:
```python
class CatalogDashboard:
    def on_show(self):
        """Called when dashboard becomes visible."""
        self.refresh_stats()

    def refresh_stats(self):
        """Recalculate all stats from database."""
        stats = self.catalog_service.get_stats()
        self.update_stats_display(stats)
```

**Testing**:
- Load 413 ingredients → Header shows "413 ingredients"
- Add 1 ingredient → Header updates to "414 ingredients"
- Switch to Products tab → Stats show "153 products" (not "0")

---

## 3. Mode Terminology Changes

### 3.1 Rename: Shop → Purchase

**Current**: SHOP mode
**New**: PURCHASE mode

**Rationale**:
- "Shop" is ambiguous (shopping for ideas? browsing?)
- "Purchase" is clear action (buying ingredients)
- Matches sub-tab name "Purchases" (consistency)

**Impact**:
- Mode switcher button: "Shop" → "Purchase"
- Keyboard shortcut: Ctrl+3 (unchanged)
- Mode dashboard class: `ShopDashboard` → `PurchaseDashboard`
- File rename: `shop_dashboard.py` → `purchase_dashboard.py`

### 3.2 Rename: Produce → Make

**Current**: PRODUCE mode
**New**: MAKE mode

**Rationale**:
- "Produce" is ambiguous (produce vegetables? produce goods?)
- "Make" is clear action (making finished goods)
- Matches user mental model (baking = making things)

**Impact**:
- Mode switcher button: "Produce" → "Make"
- Keyboard shortcut: Ctrl+4 (unchanged)
- Mode dashboard class: `ProduceDashboard` → `MakeDashboard`
- File rename: `produce_dashboard.py` → `make_dashboard.py`

---

## 4. Functional Requirements

### 4.1 Header Compaction

**REQ-F042-001:** Mode headers SHALL NOT exceed 3-4 lines of vertical space
**REQ-F042-002:** Stats SHALL be displayed inline with mode name (single line)
**REQ-F042-003:** Subtitles SHALL be removed (unnecessary redundancy)
**REQ-F042-004:** Empty lines SHALL be removed from headers
**REQ-F042-005:** Refresh buttons SHALL be removed (auto-refresh on load)

### 4.2 Data Grid Layout

**REQ-F042-006:** Data grids SHALL expand to fill 70-80% of available vertical space
**REQ-F042-007:** Grids SHALL display minimum 20 rows without scrolling (1080p display)
**REQ-F042-008:** Grid height SHALL be dynamic (not fixed pixel height)
**REQ-F042-009:** Grid scrolling SHALL be smooth and performant

### 4.3 Ingredient Hierarchy Columns

**REQ-F042-010:** Inventory tab SHALL display hierarchy as separate L0/L1/L2 columns
**REQ-F042-011:** Hierarchy columns SHALL be sortable
**REQ-F042-012:** Hierarchy columns SHALL support click-to-filter
**REQ-F042-013:** Column headers SHALL be labeled "L0", "L1", "L2" (not verbose names)

### 4.4 Filter UI Standardization

**REQ-F042-014:** All tabs SHALL use cascading dropdowns for hierarchy filtering
**REQ-F042-015:** Filter dropdowns SHALL be positioned consistently (same row, same order)
**REQ-F042-016:** L1 dropdown SHALL be filtered by L0 selection
**REQ-F042-017:** L2 dropdown SHALL be filtered by L1 selection
**REQ-F042-018:** Search bar SHALL be positioned first (left-aligned)
**REQ-F042-019:** Action buttons SHALL be positioned last (right-aligned)

### 4.5 Stats Display

**REQ-F042-020:** Stats SHALL calculate correctly from database
**REQ-F042-021:** Stats SHALL auto-refresh when mode/tab activated
**REQ-F042-022:** Stats SHALL display actual counts (not "0" when data exists)
**REQ-F042-023:** Stats freshness indicators SHALL be accurate (🟢/🟡/🔴)

### 4.6 Mode Terminology

**REQ-F042-024:** "Shop" mode SHALL be renamed "Purchase"
**REQ-F042-025:** "Produce" mode SHALL be renamed "Make"
**REQ-F042-026:** Keyboard shortcuts SHALL remain unchanged (Ctrl+3, Ctrl+4)
**REQ-F042-027:** Mode switcher SHALL display new names

---

## 5. Non-Functional Requirements

### 5.1 Usability

**REQ-F042-NFR-001:** UI changes SHALL be immediately obvious to existing users
**REQ-F042-NFR-002:** Grid scrolling SHALL feel responsive (<16ms frame time)
**REQ-F042-NFR-003:** Filter dropdowns SHALL update in <100ms
**REQ-F042-NFR-004:** Stats recalculation SHALL complete in <200ms

### 5.2 Visual Consistency

**REQ-F042-NFR-005:** All mode headers SHALL follow identical layout pattern
**REQ-F042-NFR-006:** All tabs SHALL use identical filter bar layout
**REQ-F042-NFR-007:** Column headers SHALL use consistent styling
**REQ-F042-NFR-008:** Spacing SHALL be consistent across all UI elements

### 5.3 Backward Compatibility

**REQ-F042-NFR-009:** Mode renames SHALL NOT break keyboard shortcuts
**REQ-F042-NFR-010:** Layout changes SHALL NOT affect data model
**REQ-F042-NFR-011:** Filter changes SHALL NOT affect existing queries

---

## 6. Implementation Approach

### 6.1 Header Compaction

**Implementation Steps:**

1. **Remove subtitle labels** (all modes)
   ```python
   # Before
   subtitle = ctk.CTkLabel(header, text="Manage ingredients, products, and recipes")
   subtitle.pack()

   # After
   # Delete subtitle completely
   ```

2. **Inline stats in mode header**
   ```python
   # Before
   mode_label = ctk.CTkLabel(header, text="📊 CATALOG")
   stats_section = StatsWidget(...)  # Separate widget, 5+ lines

   # After
   header_text = f"📊 CATALOG  •  {stats['ingredients']} ingredients  •  {stats['products']} products  •  {stats['recipes']} recipes"
   mode_label = ctk.CTkLabel(header, text=header_text)
   ```

3. **Remove refresh button**
   ```python
   # Before
   refresh_btn = ctk.CTkButton(header, text="Refresh Stats", command=self.refresh)

   # After
   # Delete button, call refresh() in on_show() instead
   ```

4. **Remove empty lines/spacers**
   ```python
   # Before
   spacer1 = ctk.CTkFrame(header, height=10)
   spacer1.pack()

   # After
   # Delete all spacer frames
   ```

### 6.2 Data Grid Expansion

**Implementation Steps:**

1. **Use pack/grid with expand=True**
   ```python
   # Before
   grid_frame = ctk.CTkScrollableFrame(parent, height=150)
   grid_frame.pack()

   # After
   grid_frame = ctk.CTkScrollableFrame(parent)
   grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
   ```

2. **Remove fixed height constraints**
   ```python
   # Search for: height=150, height=200, etc.
   # Replace with: (no height parameter)
   ```

3. **Ensure parent frame expands**
   ```python
   # Container must also expand
   content_frame = ctk.CTkFrame(dashboard)
   content_frame.pack(fill="both", expand=True)
   ```

### 6.3 Hierarchy Column Separation

**Implementation Steps:**

1. **Add L0/L1/L2 columns to Inventory grid**
   ```python
   # Before
   columns = [
       {"key": "ingredient_name", "label": "Ingredient", "width": 200},
       {"key": "product_name", "label": "Product", "width": 200},
       ...
   ]

   # After
   columns = [
       {"key": "l0", "label": "L0", "width": 100},
       {"key": "l1", "label": "L1", "width": 100},
       {"key": "l2", "label": "L2", "width": 150},
       {"key": "product_name", "label": "Product", "width": 200},
       ...
   ]
   ```

2. **Modify data query to include hierarchy**
   ```python
   # InventoryService
   def get_inventory_items(self):
       items = session.query(
           InventoryItem,
           Ingredient.parent_l0,  # New
           Ingredient.parent_l1,  # New
           Ingredient.display_name.label("l2")  # New
       ).join(...)
       return items
   ```

3. **Remove concatenated ingredient name column**
   ```python
   # Before
   "ingredient_name": f"{item.l0}|{item.l1}|{item.l2}"

   # After
   "l0": item.l0,
   "l1": item.l1,
   "l2": item.l2
   ```

### 6.4 Filter UI Standardization

**Implementation Steps:**

1. **Create reusable filter bar component**
   ```python
   class HierarchyFilterBar(ctk.CTkFrame):
       def __init__(self, parent, on_filter_change):
           super().__init__(parent)

           # Search
           self.search_entry = ctk.CTkEntry(self, placeholder_text="🔍 Search...")
           self.search_entry.pack(side="left", padx=5)

           # Cascading dropdowns
           self.l0_dropdown = ctk.CTkComboBox(self, values=["All"] + l0_options)
           self.l0_dropdown.configure(command=self.on_l0_change)
           self.l0_dropdown.pack(side="left", padx=5)

           self.l1_dropdown = ctk.CTkComboBox(self, values=["All"])
           self.l1_dropdown.configure(command=self.on_l1_change)
           self.l1_dropdown.pack(side="left", padx=5)

           self.l2_dropdown = ctk.CTkComboBox(self, values=["All"])
           self.l2_dropdown.configure(command=self.on_l2_change)
           self.l2_dropdown.pack(side="left", padx=5)

       def on_l0_change(self, value):
           """Update L1 dropdown based on L0 selection."""
           l1_options = get_l1_for_l0(value)
           self.l1_dropdown.configure(values=["All"] + l1_options)
           self.l1_dropdown.set("All")
   ```

2. **Replace custom filters in each tab**
   ```python
   # Before (custom layout per tab)
   filter_frame = build_custom_filter_widgets()

   # After (reusable component)
   filter_bar = HierarchyFilterBar(parent, on_filter_change=self.apply_filters)
   filter_bar.pack(fill="x", padx=10, pady=5)
   ```

### 6.5 Stats Calculation Fix

**Implementation Steps:**

1. **Add auto-refresh on dashboard show**
   ```python
   class CatalogDashboard(BaseDashboard):
       def on_show(self):
           """Called when dashboard becomes visible."""
           self.refresh_stats()

       def refresh_stats(self):
           """Recalculate stats from database."""
           stats = self.catalog_service.get_stats()
           self.update_header(stats)
   ```

2. **Fix stats queries (if incorrect)**
   ```python
   # CatalogService
   def get_stats(self, session):
       ingredient_count = session.query(Ingredient).filter(
           Ingredient.hierarchy_level == 2  # Only count leaf ingredients
       ).count()

       product_count = session.query(Product).count()

       recipe_count = session.query(Recipe).count()

       return {
           "ingredients": ingredient_count,
           "products": product_count,
           "recipes": recipe_count
       }
   ```

3. **Test stats accuracy**
   ```python
   def test_stats_accuracy():
       # Create 3 ingredients
       session.add_all([ing1, ing2, ing3])
       session.commit()

       # Get stats
       stats = catalog_service.get_stats(session)
       assert stats["ingredients"] == 3  # Not 0!
   ```

### 6.6 Mode Terminology Changes

**Implementation Steps:**

1. **Rename dashboard classes**
   ```
   src/ui/dashboards/shop_dashboard.py → purchase_dashboard.py
   src/ui/dashboards/produce_dashboard.py → make_dashboard.py

   class ShopDashboard → class PurchaseDashboard
   class ProduceDashboard → class MakeDashboard
   ```

2. **Update mode enum**
   ```python
   class UIMode(str, Enum):
       CATALOG = "catalog"
       PLAN = "plan"
       PURCHASE = "purchase"  # Was: SHOP
       MAKE = "make"          # Was: PRODUCE
       OBSERVE = "observe"
   ```

3. **Update mode switcher**
   ```python
   # Mode buttons
   buttons = {
       UIMode.CATALOG: "📊 CATALOG",
       UIMode.PLAN: "📅 PLAN",
       UIMode.PURCHASE: "🛒 PURCHASE",  # Was: SHOP
       UIMode.MAKE: "🍪 MAKE",          # Was: PRODUCE
       UIMode.OBSERVE: "📈 OBSERVE"
   }
   ```

4. **Update keyboard shortcuts** (no changes needed, but verify)
   ```python
   # Ctrl+3 → PURCHASE (was SHOP)
   # Ctrl+4 → MAKE (was PRODUCE)
   ```

---

## 7. Testing Strategy

### 7.1 Visual Testing

**Header Compaction:**
```
✓ Catalog mode header: ≤3 lines
✓ Plan mode header: ≤3 lines
✓ Purchase mode header: ≤3 lines
✓ Make mode header: ≤3 lines
✓ Observe mode header: ≤3 lines
✓ Stats inline with mode name
✓ No subtitles visible
✓ No refresh buttons visible
```

**Data Grid Expansion:**
```
✓ Ingredients grid: 20+ rows visible (1080p display)
✓ Products grid: 20+ rows visible
✓ Recipes grid: 20+ rows visible
✓ Inventory grid: 20+ rows visible
✓ Grid scrolling smooth
✓ Grid height dynamic (resizes with window)
```

**Hierarchy Columns:**
```
✓ Inventory tab shows L0/L1/L2 columns (not concatenated)
✓ Columns sortable
✓ Columns readable (not truncated)
✓ Data accurate (matches ingredient hierarchy)
```

**Filter UI:**
```
✓ Ingredients tab: cascading dropdowns present
✓ Products tab: cascading dropdowns present
✓ Inventory tab: cascading dropdowns present
✓ L1 dropdown filtered by L0 selection
✓ L2 dropdown filtered by L1 selection
✓ Search bar positioned consistently
✓ Action buttons positioned consistently
```

**Stats Display:**
```
✓ Catalog mode: "413 ingredients" (not "0")
✓ Purchase mode: accurate inventory counts
✓ Stats update when switching tabs
✓ Stats update when adding/removing items
```

**Mode Terminology:**
```
✓ Mode switcher shows "PURCHASE" (not "SHOP")
✓ Mode switcher shows "MAKE" (not "PRODUCE")
✓ Ctrl+3 activates Purchase mode
✓ Ctrl+4 activates Make mode
```

### 7.2 User Acceptance Tests

**UAT-001: Browse Ingredient Catalog**
```
Given: 413 ingredients loaded
When: User opens Catalog → My Ingredients
Then: Header is ≤3 lines
And: Grid shows 20+ rows without scrolling
And: User can browse catalog effectively
```

**UAT-002: Filter by Hierarchy**
```
Given: User viewing Product Catalog
When: User selects L0="Grain"
Then: L1 dropdown shows only flour/rice/etc (not dairy/spice)
When: User selects L1="Flour"
Then: L2 dropdown shows only AP/bread/cake flour
When: User selects L2="All-Purpose"
Then: Grid shows only AP flour products
```

**UAT-003: Verify Stats Accuracy**
```
Given: Database has 413 ingredients, 153 products, 87 recipes
When: User opens Catalog mode
Then: Header shows "413 ingredients • 153 products • 87 recipes"
When: User adds 1 ingredient
Then: Header updates to "414 ingredients"
```

**UAT-004: Navigate with Keyboard**
```
Given: User in any mode
When: User presses Ctrl+3
Then: Purchase mode activates (not Shop)
When: User presses Ctrl+4
Then: Make mode activates (not Produce)
```

---

## 8. Implementation Phases

### Phase 1: Header Compaction (High Priority)
**Effort:** 2-3 hours

**Scope:**
- Inline stats in all mode headers
- Remove subtitles
- Remove refresh buttons
- Remove spacers/empty lines

**Deliverables:**
- ✓ All mode headers ≤3 lines
- ✓ Stats displayed inline
- ✓ Auto-refresh on mode/tab switch

### Phase 2: Data Grid Expansion (High Priority)
**Effort:** 2-3 hours

**Scope:**
- Remove fixed heights from all grids
- Configure pack/grid with expand=True
- Ensure parent frames expand
- Test on 1080p/1440p/4K displays

**Deliverables:**
- ✓ Grids expand to 70-80% of vertical space
- ✓ 20+ rows visible on 1080p display
- ✓ Smooth scrolling performance

### Phase 3: Hierarchy Columns (High Priority)
**Effort:** 3-4 hours

**Scope:**
- Add L0/L1/L2 columns to Inventory grid
- Modify queries to include hierarchy data
- Remove concatenated ingredient name
- Test sorting/filtering

**Deliverables:**
- ✓ L0/L1/L2 columns visible and readable
- ✓ Columns sortable
- ✓ Data accurate

### Phase 4: Filter UI Standardization (Medium Priority)
**Effort:** 4-5 hours

**Scope:**
- Create reusable HierarchyFilterBar component
- Replace custom filters in Ingredients/Inventory tabs
- Implement cascading dropdown logic
- Test filter accuracy

**Deliverables:**
- ✓ Consistent filter UI across all tabs
- ✓ Cascading dropdowns functional
- ✓ Search + hierarchy filters work together

### Phase 5: Stats Fix + Mode Renames (Medium Priority)
**Effort:** 2-3 hours

**Scope:**
- Debug stats calculation
- Add auto-refresh on dashboard.on_show()
- Rename Shop→Purchase, Produce→Make
- Update keyboard shortcuts display

**Deliverables:**
- ✓ Stats display accurate counts
- ✓ Modes renamed consistently
- ✓ Keyboard shortcuts functional

### Phase 6: Polish + Testing (Low Priority)
**Effort:** 2-3 hours

**Scope:**
- Visual consistency pass
- User acceptance testing
- Performance optimization
- Documentation updates

**Deliverables:**
- ✓ All UAT tests passing
- ✓ User testing complete
- ✓ Feature documentation updated

### Total Effort Estimate
**14-20 hours** (2-3 working days)

---

## 9. Success Criteria

**Must Have:**
- [ ] All mode headers ≤3 lines
- [ ] Data grids show 20+ rows (1080p display)
- [ ] Inventory tab uses L0/L1/L2 columns (not concatenated)
- [ ] Stats display accurate counts (not "0")
- [ ] Filter UI consistent across all tabs (cascading dropdowns)
- [ ] Modes renamed: Shop→Purchase, Produce→Make
- [ ] Keyboard shortcuts functional (Ctrl+3, Ctrl+4)

**Should Have:**
- [ ] Grid scrolling smooth (<16ms frame time)
- [ ] Filter dropdowns update quickly (<100ms)
- [ ] Stats auto-refresh on mode/tab switch
- [ ] Visual consistency across all modes

**Nice to Have:**
- [ ] Grid column widths optimized for content
- [ ] Filter dropdowns remember last selection
- [ ] Keyboard shortcuts displayed in tooltips

---

## 10. Rollout Plan

**Pre-Rollout:**
1. Complete all phases (14-20 hours)
2. Pass all visual tests
3. Pass all UAT tests
4. User testing with primary user (wife)

**Rollout:**
1. Merge to main branch
2. Generate installer
3. Deploy to user's desktop
4. Observe first session (watch for confusion)

**Post-Rollout:**
1. Collect user feedback (48 hours)
2. Address critical issues (if any)
3. Document lessons learned
4. Plan F043 (Purchases Tab Implementation)

**Rollback Plan:**
- If critical bugs discovered, revert to F041 release
- No data model changes, so rollback is safe

---

## 11. Risks & Mitigations

**Risk 1: Fixed layout patterns break with dynamic sizing**
- *Mitigation:* Test on multiple display sizes (1080p, 1440p, 4K)
- *Mitigation:* Use pack/grid expand=True consistently

**Risk 2: Stats calculation bug is deeper than expected**
- *Mitigation:* Isolate stats calculation in unit tests
- *Mitigation:* Log stats queries for debugging

**Risk 3: Filter cascading logic complex**
- *Mitigation:* Implement as reusable component with tests
- *Mitigation:* Reference Product Catalog (already working)

**Risk 4: Mode renames break existing workflows**
- *Mitigation:* Keyboard shortcuts unchanged
- *Mitigation:* User testing before rollout

---

## 12. Future Enhancements (Out of Scope)

**Advanced Layout:**
- Resizable columns (drag to resize)
- Column reordering (drag to reorder)
- Column visibility toggles (show/hide columns)

**Advanced Filtering:**
- Multi-select filters (select multiple L0 categories)
- Filter presets (save/load filter combinations)
- Filter history (recent filter selections)

**Performance:**
- Virtual scrolling (load 1000+ rows efficiently)
- Lazy loading (load data on scroll)
- Client-side caching (reduce database queries)

---

## 13. Constitutional Compliance

**Principle I (User-Centric Design):**
- ✓ UI changes driven by real user testing feedback
- ✓ Focus on usability (browsing 400+ items effectively)
- ✓ Workflow validation (filter patterns match user expectations)

**Principle VII (Pragmatic Aspiration):**
- ✓ Desktop-native layout patterns (CustomTkinter best practices)
- ✓ Web-ready structure (separate filter bar component, cascading logic)
- ✓ Migration cost documented (layout changes are UI-only)

---

## 14. Related Documents

- **User Testing:** `docs/user_testing/usr_testing_2026_01_07.md` (blocking issues)
- **Feature Roadmap:** `docs/feature_roadmap.md` (F042-F047 sequence)
- **Dependencies:** `docs/design/F038_ui_mode_restructure.md` (mode structure)
- **Constitution:** `.kittify/memory/constitution.md` (user-centric design)

---

**END OF SPECIFICATION**
