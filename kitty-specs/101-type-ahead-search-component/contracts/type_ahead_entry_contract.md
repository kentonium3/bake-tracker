# Contract: TypeAheadEntry Widget

**Feature**: 101-type-ahead-search-component
**Date**: 2026-02-10

## Widget Contract

### Module
`src/ui/widgets/type_ahead_entry.py`

### Class: `TypeAheadEntry(ctk.CTkFrame)`

A reusable type-ahead search widget with floating dropdown, keyboard navigation, and configurable callbacks.

### Constructor

```python
TypeAheadEntry(
    master: Any,
    items_callback: Callable[[str], List[Dict[str, Any]]],
    on_select_callback: Callable[[Dict[str, Any]], None],
    min_chars: int = 3,
    debounce_ms: int = 300,
    max_results: int = 10,
    placeholder_text: str = "Type at least 3 characters to search...",
    clear_on_select: bool = True,
    display_key: str = "display_name",
    **kwargs,
)
```

### Callback Contracts

#### `items_callback(query: str) -> List[Dict[str, Any]]`

**Called when**: Debounce timer fires after user types >= `min_chars` characters.

**Input**: `query` -- the trimmed, raw text from the entry field. Case handling is the callback's responsibility.

**Output**: List of dicts. Each dict MUST contain a key matching `display_key` (default `"display_name"`) with a string value. All other keys are opaque and passed through to `on_select_callback`.

**Empty list**: Widget shows "No items match '{query}'" message.

**Error handling**: If the callback raises an exception, the widget catches it and shows a generic error message in the dropdown area.

#### `on_select_callback(item: Dict[str, Any]) -> None`

**Called when**: User clicks an item or presses Enter with an item highlighted.

**Input**: The full dict from the `items_callback` result list (unmodified).

**Error handling**: If the callback raises an exception, the widget logs it but does not crash.

### Public Methods

| Method | Description |
|--------|-------------|
| `clear() -> None` | Clear entry text and close dropdown |
| `get_text() -> str` | Return current entry field text |
| `set_focus() -> None` | Set keyboard focus to the entry field |
| `destroy() -> None` | Clean up all bindings and toplevel windows |

### Keyboard Bindings

| Key | Behavior |
|-----|----------|
| Any printable key | Triggers debounce → search |
| Down Arrow | Highlight next item (clamp at last) |
| Up Arrow | Highlight previous item (clamp at first) |
| Enter | Select highlighted item (no-op if none highlighted) |
| Escape | Close dropdown without selection |
| Tab | Close dropdown, default focus behavior |

### Visual Contract

- Entry field: `CTkEntry` with placeholder text, full width of parent
- Dropdown: `CTkToplevel` with `overrideredirect(True)`, positioned below entry
- Highlighted item: Visually distinct background color
- Truncation message: "Showing N of M+ results. Refine search for more."
- No match message: "No items match '{query}'"
- Below-threshold: No dropdown shown; placeholder guides user

### Invariants

1. Dropdown is never visible when entry has < `min_chars` characters
2. At most one dropdown is open at a time per widget instance
3. `on_select_callback` is called exactly once per user selection
4. `items_callback` is never called more than once per `debounce_ms` interval
5. Arrow keys at boundaries do not wrap (FR-009)
6. Enter with no highlight does nothing (FR-009)
7. Search is case-insensitive (FR-010) -- enforced by callback, not widget
8. Multiple widget instances on same form maintain independent state (edge case)
