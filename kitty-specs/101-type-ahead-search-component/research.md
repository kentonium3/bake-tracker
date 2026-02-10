# Research: Type-Ahead Search Component

**Feature**: 101-type-ahead-search-component
**Date**: 2026-02-10

## Phase 0: Codebase Research

### Existing Type-Ahead Pattern

**File**: `src/ui/widgets/type_ahead_combobox.py` (201 lines)

The codebase already has a `TypeAheadComboBox` widget that wraps `CTkComboBox` with client-side filtering. Key characteristics:

- **Client-side only**: Pre-loads all values into memory, filters on keystroke
- **Word boundary prioritization**: Splits on `[\s\-/]+`, prioritizes matches at word starts
- **Min chars threshold**: Default 2 characters before filtering
- **No debounce**: Filters synchronously on every `<KeyRelease>`
- **CTkComboBox limitation**: Uses the native combobox dropdown which has limited customization (no keyboard navigation highlighting, no result count messages)

**Why a new widget is needed**: `TypeAheadComboBox` doesn't support service-backed search (async data fetching), keyboard navigation with visual highlighting, result count truncation messages, or configurable callbacks. The existing widget is fine for small, static lists (e.g., category dropdowns) but doesn't scale to 500+ ingredient searches.

### Debounce Pattern

**File**: `src/ui/widgets/ingredient_tree_widget.py` (line 74-76)

The codebase standard for search debounce:
```python
self._search_after_id: Optional[str] = None
self._search_debounce_ms: int = 300
```

Implementation pattern:
```python
# Cancel pending search
if self._search_after_id:
    self.after_cancel(self._search_after_id)
# Schedule new search
self._search_after_id = self.after(self._search_debounce_ms, self._execute_search)
```

This pattern is well-established and should be reused exactly.

### Search Service APIs

**Ingredient search**: `ingredient_hierarchy_service.search_ingredients(query, limit, session)`
- Returns `List[Dict]` with `ancestors` field for breadcrumb display
- Case-insensitive `ilike` matching on `display_name`
- Accepts `session` parameter (constitution-compliant)
- Returns dicts with `id`, `display_name`, `slug`, `category`, `hierarchy_level`, `ancestors`

**Alternative**: `ingredient_service.search_ingredients(query, category, limit)`
- Returns `List[Ingredient]` ORM objects (not dicts)
- No session parameter (older API)
- Simpler but less information (no ancestors)

**Recommendation**: Use `ingredient_hierarchy_service.search_ingredients()` for the ingredient integration. The `ancestors` field enables breadcrumb display in results (e.g., "Chocolate Chips > Baking > Chocolate").

**Material search**: `material_catalog_service` has `list_materials()` and `list_products()` with filter parameters but no dedicated `search_*` function. A thin wrapper will be needed for the material integration.

### Existing Selection Dialog Pattern

**File**: `src/ui/forms/recipe_form.py`

Current ingredient selection uses `IngredientSelectionDialog` (a `CTkToplevel` modal) containing an `IngredientTreeWidget`. The tree provides hierarchical browsing but is slow for users who know what they want.

Integration options:
1. Add `TypeAheadEntry` inside the existing dialog (above the tree)
2. Replace the dialog entirely with inline type-ahead in the recipe form
3. Offer both: type-ahead for quick entry, tree button for browsing

Option 1 is the safest starting point - adds type-ahead without removing the tree.

### CTkToplevel Dropdown Considerations

Research on floating dropdown implementation with CustomTkinter:

- `overrideredirect(True)` removes title bar and borders (standard for dropdown overlays)
- `wm_attributes("-topmost", True)` keeps dropdown above parent window
- **macOS quirk**: `overrideredirect` windows may not receive focus events reliably on macOS; need to test click-outside detection
- **Positioning**: `winfo_rootx()` / `winfo_rooty()` give absolute screen coordinates of the entry widget
- **Cleanup**: Must explicitly destroy the toplevel on widget destruction to avoid orphaned windows

### Widget Patterns in Codebase

All reusable widgets follow this pattern:
- Inherit from `ctk.CTkFrame` (composite widget approach)
- Accept `master` and `**kwargs` in `__init__`
- Use `fg_color="transparent"` for seamless embedding
- Store callbacks as instance variables
- Clean up bindings in `destroy()` override

### Case-Insensitive Search

Both `search_ingredients` implementations use SQLAlchemy `ilike()` for case-insensitive matching. The widget itself doesn't need to handle case sensitivity -- that's the callback's responsibility. The widget passes the raw query string to the callback.

### Special Characters

FR-010 requires handling of `&`, `/`, `-`, parentheses in queries. Since `ilike()` treats these as literal characters (not SQL wildcards except `%` and `_`), no special escaping is needed. The `%` wrapper in `ilike(f"%{query}%")` handles substring matching.

However, if a user types `%` or `_`, these ARE SQL wildcards. The search service should escape these. This is a pre-existing concern in `search_ingredients()`, not a new issue for the widget.
