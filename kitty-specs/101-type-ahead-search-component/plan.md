# Implementation Plan: Type-Ahead Search Component

**Branch**: `101-type-ahead-search-component` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/101-type-ahead-search-component/spec.md`

## Summary

Build a reusable `TypeAheadEntry` widget that provides instant filtered search with keyboard navigation. The component accepts caller-provided callbacks for data fetching and selection handling, enabling reuse across ingredient entry, material selection, and future search contexts. Uses a floating `CTkToplevel` window for the dropdown to avoid layout disruption, with 300ms debounce matching existing codebase patterns.

This replaces the current bottleneck where ingredient selection requires scrolling through 200+ items in a dropdown or navigating a multi-click tree view. Target: reduce per-ingredient selection time from 2-3 minutes to under 10 seconds.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI framework), tkinter (underlying toolkit)
**Storage**: N/A (component is stateless; data comes from caller-provided callbacks)
**Testing**: pytest (unit tests for filtering/debounce logic, integration tests with mock callbacks)
**Target Platform**: macOS desktop (primary), Windows (secondary via PyInstaller)
**Project Type**: Single project (desktop application)
**Performance Goals**: Dropdown appears within 150ms of debounce firing; smooth keyboard navigation at 60fps
**Constraints**: Debounce default 150ms per spec; max 10 results displayed; min 3 chars before search fires
**Scale/Scope**: 500+ ingredients in production data; component reused in 2+ contexts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Directly addresses user pain point (2-3x speed improvement in ingredient entry) |
| II. Data Integrity & FIFO | N/A | Pure UI component; no data mutation |
| III. Future-Proof Schema | N/A | No schema changes |
| IV. Test-Driven Development | PASS | Widget logic testable via unit tests; integration via mock callbacks |
| V. Layered Architecture | PASS | Widget lives in `src/ui/widgets/`; delegates all business logic to callbacks. No service imports in the widget itself. |
| VI-A. Error Handling | PASS | Callback errors caught and displayed gracefully |
| VI-C. Dependency & State | PASS | No service dependencies; all data via injected callbacks |
| VI-D. API Contracts | PASS | Clear interface contract: `items_callback`, `on_select_callback`, configurable params |
| VI-G. Code Organization | PASS | Single module < 500 lines; `src/ui/widgets/type_ahead_entry.py` |
| VI-H. Testing Support | PASS | Callbacks are injectable, enabling mock-based testing |
| VIII. Pragmatic Aspiration | PASS | Web migration: component pattern maps cleanly to React autocomplete |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```
kitty-specs/101-type-ahead-search-component/
├── plan.md              # This file
├── research.md          # Phase 0: codebase research findings
├── data-model.md        # Phase 1: widget interface contract
├── quickstart.md        # Phase 1: integration guide
├── contracts/           # Phase 1: callback type contracts
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── ui/
│   └── widgets/
│       ├── type_ahead_combobox.py   # EXISTING: client-side filtering (unchanged)
│       └── type_ahead_entry.py      # NEW: service-backed type-ahead with floating dropdown
└── tests/
    └── unit/
        └── test_type_ahead_entry.py # NEW: widget unit tests
```

**Structure Decision**: Single new file `src/ui/widgets/type_ahead_entry.py` for the widget. Integration into existing forms (recipe_form.py, finished_good_builder.py) happens in separate work packages. Tests in `src/tests/` following existing flat test file convention.

## Design Decisions

### D1: Floating CTkToplevel Dropdown (confirmed by user)

The dropdown list uses a `CTkToplevel` window positioned below the entry field. This avoids the layout disruption that an inline frame would cause (pushing content down on every search). The toplevel window is `overrideredirect(True)` to remove window decorations and uses `wm_attributes("-topmost", True)` to stay above the parent.

**Positioning**: Calculated from entry widget's `winfo_rootx()` / `winfo_rooty()` + `winfo_height()`. Recalculated on each dropdown show to handle window moves/resizes.

**Dismissal**: Bound to `<FocusOut>` on the entry, `<Button-1>` on root window (click-outside detection), `<Escape>` key, and `<Configure>` on the parent window (move/resize).

### D2: Callback-Based Architecture (no service imports)

The widget imports ZERO service modules. All data comes through two injected callbacks:

- `items_callback(query: str) -> List[Dict[str, Any]]`: Called with the search string, returns matching items. Each dict must have at least `"display_name"` and `"id"` keys.
- `on_select_callback(item: Dict[str, Any]) -> None`: Called when user selects an item.

This keeps the widget in the UI layer with no upward dependency violations.

### D3: Debounce Pattern (300ms, matching codebase standard)

Uses `self.after()` / `self.after_cancel()` pattern identical to `IngredientTreeWidget._search_debounce_ms`. The spec suggests 150ms default but the codebase standard is 300ms. The widget accepts `debounce_ms` as a configurable parameter (default 300ms) so callers can override.

### D4: No Wrap on Arrow Keys, No Action on Enter Without Highlight

Per user decisions during discovery:
- Arrow Down at last item: stays on last item
- Arrow Up at first item: stays on first item
- Enter with no item highlighted: does nothing

### D5: Word-Boundary Prioritization

Reuse the filtering approach from `TypeAheadComboBox._filter_values()`: word boundary matches first, then contains matches. However, since `TypeAheadEntry` delegates search to the callback, this prioritization happens in the caller's search function, not in the widget itself. The widget simply displays results in the order returned.

## Component Interface

```python
class TypeAheadEntry(ctk.CTkFrame):
    def __init__(
        self,
        master,
        items_callback: Callable[[str], List[Dict[str, Any]]],
        on_select_callback: Callable[[Dict[str, Any]], None],
        min_chars: int = 3,
        debounce_ms: int = 300,
        max_results: int = 10,
        placeholder_text: str = "Type at least 3 characters to search...",
        clear_on_select: bool = True,
        display_key: str = "display_name",
        **kwargs,
    ): ...

    def clear(self) -> None: ...
    def get_text(self) -> str: ...
    def set_focus(self) -> None: ...
    def destroy(self) -> None: ...
```

## Integration Points

### Ingredient Selection (P1 - primary integration)

In `src/ui/forms/recipe_form.py`, the current `IngredientSelectionDialog` uses `IngredientTreeWidget` for hierarchical browsing. The type-ahead component will be added as an alternative entry method (likely above or replacing the tree widget in the dialog).

Callback wiring:
```python
# items_callback wraps ingredient_hierarchy_service.search_ingredients()
def search_ingredients_for_typeahead(query: str) -> List[Dict]:
    return search_ingredients(query, limit=10)

# on_select_callback handles the selection
def on_ingredient_selected(item: Dict) -> None:
    self._selected_ingredient = item
    # ... update form state
```

### Material Selection (P2 - validates reusability)

In `src/ui/builders/finished_good_builder.py`, the material product selection can use the same component with a different callback wrapping `material_catalog_service` search functions.

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| CTkToplevel positioning edge cases (multi-monitor, window near screen edge) | Clamp dropdown position to screen bounds using `winfo_screenwidth()`/`winfo_screenheight()` |
| Focus management between entry and dropdown | Careful bind/unbind; dropdown items are CTkButtons inside the toplevel, not a separate focus chain |
| Click-outside detection reliability | Use root window `<Button-1>` binding with coordinate check, plus `<FocusOut>` as fallback |
| macOS-specific window behavior | Test `overrideredirect` and `topmost` on macOS; may need platform-specific adjustments |
