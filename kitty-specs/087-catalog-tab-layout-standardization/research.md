# Research: Catalog Tab Layout Standardization

**Feature**: 087-catalog-tab-layout-standardization
**Date**: 2026-01-30
**Status**: Complete

## Executive Summary

This research documents the current state of all Catalog tabs and establishes the patterns to implement for F087. The key finding is that **RecipesTab layout is the target pattern** (3-row: filters, actions, grid) but it uses a **custom RecipeDataTable that must be replaced with ttk.Treeview** from IngredientsTab for trackpad scrolling support.

---

## Pattern 1: ttk.Treeview Implementation (from IngredientsTab)

**Source**: `src/ui/ingredients_tab.py`

The IngredientsTab has the correct ttk.Treeview implementation that supports native trackpad scrolling. This pattern will be copied to RecipesTab.

### Key Implementation Details

```python
# Column definitions
columns = ("l0", "l1", "name", "density")
self.tree = ttk.Treeview(
    self.grid_container,
    columns=columns,
    show="headings",
    selectmode="browse",
)

# Column headings with click-to-sort
self.tree.heading("name", text="Ingredient", anchor="w",
                  command=lambda: self._on_header_click("name"))

# Column widths
self.tree.column("name", width=200, stretch=True)

# Scrollbar setup (enables trackpad scrolling)
y_scrollbar = ttk.Scrollbar(self.grid_container, orient="vertical", command=self.tree.yview)
self.tree.configure(yscrollcommand=y_scrollbar.set)
y_scrollbar.grid(row=0, column=1, sticky="ns")
self.tree.grid(row=0, column=0, sticky="nsew")

# Event bindings
self.tree.bind("<Double-1>", self._on_double_click)
self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
```

### Why This Works for Trackpad Scrolling

- `ttk.Treeview` is a native tkinter widget
- Native widgets receive OS-level scroll events
- `CTkScrollableFrame` (used by RecipeDataTable) is a custom widget that doesn't intercept native scroll gestures

---

## Pattern 2: 3-Row Layout (from RecipesTab)

**Source**: `src/ui/recipes_tab.py`

The RecipesTab has the cleanest layout structure, which should be copied to all tabs:

```python
# Grid configuration
self.grid_rowconfigure(0, weight=0)  # Search bar (fixed height)
self.grid_rowconfigure(1, weight=0)  # Action buttons (fixed height)
self.grid_rowconfigure(2, weight=1)  # Data table (expands)
self.grid_rowconfigure(3, weight=0)  # Status bar (fixed height)
self.grid_columnconfigure(0, weight=1)

# Row 0: Search controls
search_frame.grid(row=0, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

# Row 1: Action buttons
button_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)

# Row 2: Data grid (with weight=1 expands to fill space)
data_container.grid(row=2, column=0, sticky="nsew", padx=PADDING_MEDIUM, pady=PADDING_MEDIUM)
```

**Key Principle**: `weight=0` for fixed-height controls, `weight=1` for the data grid that should expand.

---

## Pattern 3: RecipeDataTable Current Implementation (to be replaced)

**Source**: `src/ui/widgets/data_table.py`

RecipeDataTable is a custom widget built on `CTkScrollableFrame`. Key functionality to preserve:

### Column Definitions
- Name: 330px width
- Category: 120px width
- Yield: 150px width

### Special Behavior: Variant Grouping
```python
# Variants are indented with "↳ " prefix
if row_data.get("is_variant"):
    values["Name"] = f"↳ {values['Name']}"
```

### Sorting Logic
```python
def set_data(self, data: list[dict]):
    # Sort variants to appear after their base recipes
    # Base recipes first, then variants sorted after their base
```

### Event Handlers to Preserve
- `on_select`: Called when a row is selected
- `on_double_click`: Called when a row is double-clicked (opens edit dialog)
- Column header click → sort by column

---

## Current State Analysis

### IngredientsTab (`src/ui/ingredients_tab.py`)

| Issue | Location | Fix |
|-------|----------|-----|
| Title label "My Ingredients" | Row 0 | Remove, shift rows up |
| Excessive padding | Various `pady` values | Reduce to PADDING_MEDIUM |
| Already uses ttk.Treeview | ✅ | No change needed |

**Current row structure**:
- Row 0: Title label (to be removed)
- Row 1: Search/filter controls
- Row 2: Action buttons
- Row 3: ttk.Treeview grid

**Target row structure**:
- Row 0: Search/filter controls
- Row 1: Action buttons
- Row 2: ttk.Treeview grid

---

### ProductsTab (`src/ui/products_tab.py`)

| Issue | Location | Fix |
|-------|----------|-----|
| Title label "Product Catalog" | Row 0 | Remove |
| Multiple control rows | Rows 1-3 | Consolidate to 2 rows |
| 5 total rows | Layout | Reduce to 3 rows |

**Current row structure**:
- Row 0: Title label "Product Catalog"
- Row 1: Toolbar frame
- Row 2: Filters frame
- Row 3: Search frame
- Row 4: ttk.Treeview grid

**Target row structure**:
- Row 0: Filters + Search (consolidated)
- Row 1: Action buttons
- Row 2: ttk.Treeview grid

---

### RecipesTab (`src/ui/recipes_tab.py`)

| Issue | Location | Fix |
|-------|----------|-----|
| Uses RecipeDataTable | Row 2 | Convert to ttk.Treeview |
| No trackpad scrolling | RecipeDataTable | ttk.Treeview fixes this |
| No title label | ✅ | Already correct |
| 3-row layout | ✅ | Already correct |

**Current structure** (correct layout, wrong widget):
- Row 0: Search controls ✅
- Row 1: Action buttons ✅
- Row 2: RecipeDataTable ❌ (needs ttk.Treeview)
- Row 3: Status bar ✅

---

### MaterialsTab (`src/ui/materials_tab.py`)

| Issue | Location | Fix |
|-------|----------|-----|
| Title label "Materials Catalog" | Lines 88-93 | Remove |
| Sub-tabs have inconsistent layouts | Catalog/Products/Units tabs | Apply 3-row pattern to each |

**Outer container**:
- Row 0: Title label "Materials Catalog" (to be removed)
- Row 1: CTkTabview with sub-tabs

**Sub-tabs need individual review**:
- MaterialsCatalogTab
- MaterialProductsTab
- MaterialUnitsTab

---

## Decisions

### Decision 1: RecipeDataTable Replacement Strategy

**Decision**: Replace RecipeDataTable with ttk.Treeview in RecipesTab

**Rationale**:
- ttk.Treeview provides native trackpad scrolling
- IngredientsTab already has a working pattern to copy
- Custom CTkScrollableFrame cannot intercept native scroll gestures

**Alternatives Considered**:
- Patch RecipeDataTable with scroll bindings → Rejected: Custom scroll bindings are unreliable across platforms
- Keep RecipeDataTable → Rejected: Trackpad scrolling is a P1 requirement

**Preserved Functionality**:
- Variant grouping with "↳ " prefix
- Click-to-sort column headers
- Row selection callback
- Double-click callback
- All column definitions (Name, Category, Yield)

### Decision 2: Variant Sorting in ttk.Treeview

**Decision**: Implement variant sorting in `_populate_tree()` method

**Rationale**:
- ttk.Treeview doesn't have built-in variant grouping
- Sorting must ensure variants appear immediately after their base recipe
- Same algorithm currently in RecipeDataTable.set_data()

### Decision 3: Title Label Removal Approach

**Decision**: Remove title labels, shift all subsequent rows up, update grid indices

**Rationale**:
- Tab labels already identify content
- Title labels waste vertical space
- Recipes tab (no title) is the cleanest pattern

### Decision 4: Products Tab Consolidation

**Decision**: Merge toolbar, filters, and search into 2 rows (filters+search, actions)

**Rationale**:
- 5 rows is excessive for controls
- Match the 3-row pattern from Recipes tab
- Maintain all functionality, just reorganize spatially

---

## Implementation Order

Based on dependencies and risk:

1. **RecipesTab ttk.Treeview Conversion** (P1, highest risk)
   - Most complex change
   - Must preserve variant sorting
   - Enables trackpad scrolling validation

2. **IngredientsTab Cleanup** (P2, low risk)
   - Remove title, reduce padding
   - Already uses ttk.Treeview
   - Reference pattern for other tabs

3. **ProductsTab Consolidation** (P2, medium risk)
   - Remove title
   - Consolidate control rows
   - More layout reorganization needed

4. **MaterialsTab and Sub-tabs** (P2, low-medium risk)
   - Remove outer title
   - Apply pattern to each sub-tab
   - Multiple files but similar changes

---

## PADDING_MEDIUM Value

**Source**: `src/utils/constants.py`

```python
PADDING_MEDIUM = 10  # Standard padding for consistent spacing
```

Use this value for all `pady` and `padx` between sections.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| RecipeDataTable conversion breaks functionality | Test all sorting, selection, double-click before marking complete |
| Variant grouping lost | Implement explicit sorting in _populate_tree() |
| Padding too cramped | Use PADDING_MEDIUM minimum; adjust if needed |
| Grid weight=1 not working | Test window resize; verify grid expands |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/ui/recipes_tab.py` | Replace RecipeDataTable with ttk.Treeview |
| `src/ui/ingredients_tab.py` | Remove title, reduce padding |
| `src/ui/products_tab.py` | Remove title, consolidate rows |
| `src/ui/materials_tab.py` | Remove outer title |
| `src/ui/tabs/materials_catalog_tab.py` | Apply 3-row pattern |
| `src/ui/tabs/materials_products_tab.py` | Apply 3-row pattern |
| `src/ui/tabs/materials_units_tab.py` | Apply 3-row pattern |

---

**Research Status**: Complete - Ready for plan.md generation
