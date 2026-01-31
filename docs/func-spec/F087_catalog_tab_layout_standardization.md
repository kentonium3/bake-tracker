# F087: Catalog Tab Layout Standardization

**Version**: 1.0
**Date**: 2026-01-30
**Priority**: HIGH
**Type**: UI Refactoring

---

## Executive Summary

Catalog mode tabs (Ingredients, Materials, Recipes) currently have inconsistent layouts with unnecessary title labels, excessive padding, and different widget types for data display, which wastes vertical space and creates inconsistent user experience across tabs.

Current gaps:
- ❌ Unnecessary title labels waste vertical space (24px bold headers)
- ❌ Inconsistent padding between sections across tabs
- ❌ Recipes tab uses custom RecipeDataTable (no trackpad scrolling)
- ❌ Action buttons positioned differently across tabs
- ❌ No established pattern for future tab development

This spec standardizes all catalog tabs to use the clean, compact Recipes tab layout pattern: search/filters at top, action buttons directly below, ttk.Treeview grid filling remaining space, with trackpad scrolling support.

---

## Problem Statement

**Current State (INCONSISTENT):**
```
Recipes Tab (cleanest, but wrong grid)
├─ ✅ No title label
├─ ✅ Search bar at top (row 0)
├─ ✅ Action buttons below (row 1)
├─ ✅ Compact vertical layout
└─ ❌ RecipeDataTable (custom widget, no trackpad scroll)

Ingredients Tab
├─ ❌ "My Ingredients" title label (row 0)
├─ ✅ Search/filter controls (row 1)
├─ ✅ Action buttons (row 2)
├─ ✅ ttk.Treeview grid (row 3)
└─ ❌ Excessive padding between rows

Products Tab
├─ ❌ "Product Catalog" title label (row 0)
├─ ❌ Toolbar frame (row 1)
├─ ❌ Filters frame (row 2)
├─ ❌ Search frame (row 3)
├─ ✅ ttk.Treeview grid (row 4)
└─ ❌ Multiple control rows waste vertical space

Materials Tab
├─ ❌ "Materials Catalog" title label (row 0)
├─ ✅ Tabview (row 1)
└─ Sub-tabs have own inconsistent layouts

User Pain
├─ Recipes tab won't scroll with trackpad gestures
├─ Vertical space wasted on redundant titles
├─ Inconsistent mental model across tabs
└─ No clear pattern for new tabs
```

**Target State (STANDARDIZED):**
```
ALL Catalog Tabs
├─ Row 0: Search/Filter Controls (weight=0, fixed)
├─ Row 1: Action Buttons (weight=0, fixed)
├─ Row 2: ttk.Treeview Grid (weight=1, fills space)
└─ Row 3: Status Bar if needed (weight=0, fixed)

Recipes Tab
├─ ✅ RecipeDataTable → ttk.Treeview
├─ ✅ Trackpad scrolling works
├─ ✅ Same layout as other tabs
└─ ✅ Pattern consistency

Ingredients Tab
├─ ✅ "My Ingredients" title removed
├─ ✅ Reduced padding
├─ ✅ Compact layout matches Recipes
└─ ✅ Already uses ttk.Treeview

Products Tab
├─ ✅ "Product Catalog" title removed
├─ ✅ Toolbar/Filter/Search consolidated
├─ ✅ Action buttons row 1
└─ ✅ Grid fills space

Materials Tab
├─ ✅ "Materials Catalog" title removed
├─ ✅ Sub-tabs follow same pattern
└─ ✅ Consistent with outer tabs

Benefits
├─ Maximum vertical space for data
├─ Trackpad scrolling everywhere
├─ Consistent muscle memory
└─ Clear pattern for future tabs (F088 Finished Goods)
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Tab Implementations**
   - Find: `src/ui/recipes_tab.py` - Target layout pattern (cleanest)
   - Find: `src/ui/ingredients_tab.py` - Title removal needed
   - Find: `src/ui/products_tab.py` - Multiple row consolidation needed
   - Find: `src/ui/materials_tab.py` - Outer title + sub-tab layouts
   - Note: Grid row configurations, padding values, widget types

2. **RecipeDataTable Widget**
   - Find: `src/ui/widgets/data_table.py` - Current custom implementation
   - Study: RecipeDataTable class and its methods
   - Note: What functionality to preserve when converting to ttk.Treeview
   - Note: Column definitions, sorting, selection handling

3. **ttk.Treeview Pattern**
   - Find: Ingredients tab ttk.Treeview implementation
   - Study: Column configuration, heading commands, scrollbar setup
   - Note: How sorting works, how selection works
   - Pattern: Header click sorting, row selection callbacks

4. **Padding Constants**
   - Find: `src/utils/constants.py` - PADDING_MEDIUM, PADDING_LARGE values
   - Note: Current padding values being used
   - Target: Minimize padding while maintaining readability

5. **Grid Configuration**
   - Study: How `grid_rowconfigure(weight=1)` makes rows expandable
   - Study: How `grid_columnconfigure(weight=1)` makes columns expandable
   - Pattern: Fixed height controls (weight=0) vs expandable grid (weight=1)

---

## Requirements Reference

This specification addresses UI consistency and usability issues identified during F086 planning:
- Need established pattern for future catalog tabs
- Vertical space optimization for data display
- Trackpad scrolling support across all tabs
- Consistent user experience in Catalog mode

---

## Functional Requirements

### FR-1: Remove Unnecessary Title Labels

**What it must do:**
- Remove "My Ingredients" title label from IngredientsTab
- Remove "Product Catalog" title label from ProductsTab
- Remove "Materials Catalog" title label from MaterialsTab
- Shift all subsequent rows up to reclaim vertical space
- Update row index references in grid() calls

**Pattern reference:** Recipes tab has no title label - copy this pattern

**Success criteria:**
- [ ] No title labels present in any catalog tab
- [ ] Search/filter controls appear at top of each tab (row 0)
- [ ] Grid row indices updated correctly
- [ ] No visual artifacts or spacing issues

---

### FR-2: Consolidate Control Rows in Products Tab

**What it must do:**
- Merge toolbar, filters, and search into fewer rows
- Move "Add Product" button to same row as filters (action buttons row)
- Reduce from 5 rows (header, toolbar, filters, search, grid) to 3 rows (filters, buttons, grid)
- Maintain all existing functionality
- Update grid row configuration

**Pattern reference:** Study how Recipes tab combines search and filters in single row

**UI Requirements:**
- Filters row should contain all filter dropdowns + search entry
- Action buttons row should contain "Add Product" and any other action buttons
- Clear visual grouping of related controls

**Success criteria:**
- [ ] Products tab uses 3-row layout (filters, actions, grid)
- [ ] All filter functionality preserved
- [ ] "Add Product" button accessible
- [ ] No functionality lost in consolidation

---

### FR-3: Standardize Grid Row Configuration

**What it must do:**
- Set all tabs to use consistent row weights:
  - Row 0: Search/Filters (weight=0)
  - Row 1: Action Buttons (weight=0)
  - Row 2: Data Grid (weight=1)
  - Row 3: Status Bar if present (weight=0)
- Ensure data grid expands to fill available vertical space
- Fixed-height controls at top, expandable grid below

**Pattern reference:** Study Ingredients tab grid_rowconfigure calls

**Success criteria:**
- [ ] All tabs use weight=0 for control rows
- [ ] All tabs use weight=1 for grid row
- [ ] Grids expand vertically when window resized
- [ ] Controls remain fixed height at top

---

### FR-4: Reduce Excessive Padding

**What it must do:**
- Reduce vertical padding between UI sections
- Use PADDING_MEDIUM consistently for row spacing
- Reduce horizontal padding where excessive
- Maintain readability while maximizing data display space
- Target compact layout matching Recipes tab

**Pattern reference:** Study Recipes tab pady values in grid() calls

**Business rules:**
- Maintain minimum padding for readability
- Ensure clear visual separation between sections
- Don't create cramped or cluttered appearance

**Success criteria:**
- [ ] Vertical padding reduced to PADDING_MEDIUM between sections
- [ ] Horizontal padding consistent across tabs
- [ ] Layout appears compact but readable
- [ ] More rows of data visible without scrolling

---

### FR-5: Convert RecipeDataTable to ttk.Treeview

**What it must do:**
- Replace custom RecipeDataTable widget with ttk.Treeview
- Preserve all column definitions (name, category, yields, etc.)
- Preserve sorting functionality (click column header to sort)
- Preserve selection callback functionality
- Preserve double-click callback functionality
- Add vertical scrollbar for trackpad scrolling support
- Maintain visual styling consistency

**Pattern reference:** Copy ttk.Treeview implementation from IngredientsTab exactly

**UI Requirements:**
- Columns: Name, Category, Yields, Production Ready, Notes
- Sortable columns (click header to toggle ascending/descending)
- Single selection mode
- Double-click opens edit dialog
- Scrollbar appears when content exceeds visible area

**Success criteria:**
- [ ] RecipeDataTable class removed or deprecated
- [ ] ttk.Treeview displays same recipe data
- [ ] Column sorting works correctly
- [ ] Row selection triggers callback
- [ ] Double-click opens recipe edit form
- [ ] Trackpad scrolling works (two-finger swipe)
- [ ] Visual appearance matches other tabs

---

### FR-6: Standardize ttk.Treeview Styling

**What it must do:**
- Ensure consistent ttk.Treeview configuration across all tabs
- Same column heading style (anchor, font, click behavior)
- Same row height and spacing
- Same selection highlighting
- Same scrollbar configuration
- Extract common styling to reusable pattern if possible

**Pattern reference:** Study IngredientsTab ttk.Treeview configuration

**Success criteria:**
- [ ] All ttk.Treeview grids have consistent visual style
- [ ] Column headers look the same across tabs
- [ ] Row selection highlighting consistent
- [ ] Scrollbars positioned identically

---

### FR-7: Update Materials Tab Sub-Tabs

**What it must do:**
- Apply same layout pattern to Materials sub-tabs:
  - Materials Catalog sub-tab
  - Material Products sub-tab
  - Material Units sub-tab
- Remove any sub-tab titles
- Standardize row configuration in each sub-tab
- Reduce padding in sub-tabs

**Pattern reference:** Each sub-tab should match the main tab pattern

**Success criteria:**
- [ ] All Materials sub-tabs follow 3-row pattern
- [ ] No title labels in sub-tabs
- [ ] Padding consistent with other tabs
- [ ] Grid fills vertical space in each sub-tab

---

### FR-8: Preserve All Existing Functionality

**What it must do:**
- Maintain all search functionality
- Maintain all filter functionality (cascading filters, clear button)
- Maintain all action button functionality (add, edit, delete)
- Maintain all grid selection and interaction
- Maintain all callbacks and event handlers
- No regression in any tab behavior

**Pattern reference:** Test existing functionality before and after changes

**Success criteria:**
- [ ] Search works in all tabs
- [ ] Filters work correctly
- [ ] Action buttons trigger correct operations
- [ ] Row selection works
- [ ] Double-click works
- [ ] All callbacks fire correctly
- [ ] No functionality lost or broken

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Adding new functionality to tabs (pure layout refactor)
- ❌ Changing filter logic or search algorithms
- ❌ Modifying service layer or data models
- ❌ Adding new columns to grids
- ❌ Changing color schemes or themes
- ❌ Refactoring Materials tab architecture (sub-tabs remain)
- ❌ F088 Finished Goods tab creation (separate feature)
- ❌ Performance optimization beyond layout changes

---

## Success Criteria

**Complete when:**

### Layout Consistency
- [ ] All catalog tabs have NO title labels
- [ ] All catalog tabs use 3-row layout (controls, actions, grid)
- [ ] All catalog tabs use weight=0 for controls, weight=1 for grid
- [ ] Padding reduced and consistent across all tabs
- [ ] Recipes tab uses ttk.Treeview (not RecipeDataTable)

### Functionality Preserved
- [ ] Search works in all tabs
- [ ] Filters work correctly in all tabs
- [ ] Action buttons work in all tabs
- [ ] Grid selection works in all tabs
- [ ] Double-click works in all tabs
- [ ] Sorting works in all tabs (click column headers)
- [ ] Zero functionality regressions

### Trackpad Scrolling
- [ ] Recipes tab scrolls with trackpad gestures
- [ ] Ingredients tab scrolls with trackpad gestures
- [ ] Products tab scrolls with trackpad gestures
- [ ] Materials sub-tabs scroll with trackpad gestures
- [ ] All ttk.Treeview grids support two-finger swipe

### Visual Quality
- [ ] No visual artifacts or spacing issues
- [ ] Layout appears compact but readable
- [ ] More data rows visible without scrolling
- [ ] Consistent visual style across tabs
- [ ] Professional appearance maintained

### Pattern Establishment
- [ ] Clear 3-row pattern documented for future tabs
- [ ] F088 Finished Goods can copy this pattern
- [ ] Maintenance easier with consistent structure
- [ ] Code comments explain the standard layout

---

## Architecture Principles

### Compact Vertical Layout

**Maximize data display space:**
- Remove redundant titles (tab label already identifies content)
- Minimize padding between controls
- Fixed-height controls at top
- Expandable grid fills remaining space
- Users see more data without scrolling

### Consistent Widget Choice

**Use ttk.Treeview for all data grids:**
- Native widget with proper OS integration
- Trackpad scrolling works automatically
- Familiar behavior across tabs
- Easier maintenance (no custom widgets)
- Better accessibility support

### Three-Row Standard Pattern

**Establish template for future tabs:**
```python
# Row 0: Search and filters (weight=0)
# Row 1: Action buttons (weight=0)
# Row 2: Data grid (weight=1)
# Optional Row 3: Status bar (weight=0)
```

### Preserve User Workflows

**Layout changes don't break muscle memory:**
- Action buttons remain in predictable locations
- Search/filter controls remain at top
- Grid interaction unchanged
- Only spacing and widget types change

---

## Constitutional Compliance

✅ **Principle I: User-Centric Design**
- Compact layout shows more data
- Trackpad scrolling improves usability
- Consistent experience across tabs
- No functionality removed

✅ **Principle V: Layered Architecture**
- UI-only changes (no service layer impact)
- Widget replacement maintains same interfaces
- Clear separation of concerns preserved

✅ **Principle VII: Pragmatic Aspiration**
- Build for desktop today (native widgets, trackpad support)
- Establish pattern for tomorrow (F088 and beyond)
- Simplify maintenance with consistency

---

## Risk Considerations

**Risk: RecipeDataTable replacement breaks existing functionality**
- Context: Custom widget may have subtle behaviors not in ttk.Treeview
- Mitigation: Thorough testing of sorting, selection, double-click; preserve all callbacks

**Risk: Padding reduction makes layout too cramped**
- Context: Removing padding could reduce readability
- Mitigation: Use PADDING_MEDIUM minimum; test with realistic data; adjust if needed

**Risk: Grid row weight changes break layouts**
- Context: Incorrect weight values could prevent grid expansion
- Mitigation: Test window resizing; verify grid expands/contracts correctly

**Risk: Materials sub-tabs become inconsistent**
- Context: Sub-tab refactoring might miss edge cases
- Mitigation: Apply pattern to each sub-tab systematically; test all three

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study Recipes tab layout → this is the target pattern (except widget type)
- Study Ingredients tab ttk.Treeview → copy this widget implementation
- Study Products tab control organization → identify consolidation opportunities
- Study Materials tab structure → understand sub-tab architecture

**Key Patterns to Copy:**
- Recipes tab 3-row layout → apply to all tabs
- Ingredients tab ttk.Treeview → apply to Recipes tab
- Ingredients tab padding → apply consistent spacing everywhere
- Ingredients tab grid configuration → standardize row weights

**Focus Areas:**
- RecipeDataTable → ttk.Treeview conversion (preserve all functionality)
- Products tab control consolidation (maintain all filters/actions)
- Padding reduction (balance compact vs readable)
- Testing trackpad scrolling (verify two-finger swipe works)

**Implementation Order:**
1. Start with Recipes tab (RecipeDataTable → ttk.Treeview)
2. Then Ingredients tab (remove title, reduce padding)
3. Then Products tab (consolidate rows, remove title)
4. Finally Materials sub-tabs (apply pattern to each)
5. Test all tabs thoroughly for regressions

---

**END OF SPECIFICATION**
