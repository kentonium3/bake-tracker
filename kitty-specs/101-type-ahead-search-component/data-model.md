# Data Model: Type-Ahead Search Component

**Feature**: 101-type-ahead-search-component
**Date**: 2026-02-10

## Overview

No database schema changes. This feature is a pure UI component. The "data model" for this feature is the widget's interface contract -- the types that flow between the widget and its callers.

## Type Contracts

### TypeAheadEntry Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `master` | `Any` | required | Parent widget |
| `items_callback` | `Callable[[str], List[Dict[str, Any]]]` | required | Called with query string, returns matching items |
| `on_select_callback` | `Callable[[Dict[str, Any]], None]` | required | Called when user selects an item from dropdown |
| `min_chars` | `int` | `3` | Minimum characters before search fires (FR-001) |
| `debounce_ms` | `int` | `300` | Milliseconds to wait after last keystroke (FR-002) |
| `max_results` | `int` | `10` | Maximum items shown in dropdown (FR-003) |
| `placeholder_text` | `str` | `"Type at least 3 characters to search..."` | Placeholder in empty entry field |
| `clear_on_select` | `bool` | `True` | Whether to clear entry text after selection (FR-006) |
| `display_key` | `str` | `"display_name"` | Dict key used for display text in dropdown items |

### Search Result Item Contract

The `items_callback` returns a list of dicts. The widget requires one key (`display_key`, default `"display_name"`) for rendering. All other keys are opaque -- passed through to `on_select_callback` unchanged.

**Minimum required structure**:
```python
{
    "display_name": str,  # Shown in dropdown (key name configurable via display_key)
    # ... any additional keys passed through to on_select_callback
}
```

**Ingredient example** (from `ingredient_hierarchy_service.search_ingredients`):
```python
{
    "id": 42,
    "display_name": "Chocolate Chips",
    "slug": "chocolate-chips",
    "category": "Baking",
    "hierarchy_level": 2,
    "ancestors": [
        {"id": 1, "display_name": "Baking"},
        {"id": 5, "display_name": "Chocolate"}
    ]
}
```

**Material example** (future integration):
```python
{
    "id": 7,
    "display_name": "12x12 Cake Box",
    "category": "Packaging",
    "subcategory": "Boxes"
}
```

### Public Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `clear()` | `() -> None` | Clear entry text and close dropdown |
| `get_text()` | `() -> str` | Return current entry text |
| `set_focus()` | `() -> None` | Set keyboard focus to the entry field |
| `destroy()` | `() -> None` | Clean up bindings, destroy dropdown toplevel, call super |

### Internal State

| Attribute | Type | Description |
|-----------|------|-------------|
| `_entry` | `CTkEntry` | The text entry field |
| `_dropdown` | `CTkToplevel` or `None` | Floating dropdown window (created/destroyed as needed) |
| `_results` | `List[Dict[str, Any]]` | Current search results |
| `_highlight_index` | `int` | Currently highlighted item index (-1 = none) |
| `_debounce_id` | `str` or `None` | Pending `after()` callback ID |
| `_result_labels` | `List[CTkLabel]` | Label widgets in the dropdown |

## Event Flow

```
User types character
    → KeyRelease event
    → Cancel pending debounce (if any)
    → If len(text) < min_chars: hide dropdown, return
    → Schedule debounce callback after debounce_ms
    → [debounce fires]
    → Call items_callback(query)
    → If results empty: show "No items match" message
    → If results > max_results: show first max_results + truncation message
    → Else: show results in dropdown
    → Reset highlight_index to -1

User presses Down Arrow
    → If dropdown hidden: do nothing
    → Increment highlight_index (clamp to last item)
    → Update visual highlight

User presses Up Arrow
    → If dropdown hidden: do nothing
    → Decrement highlight_index (clamp to 0, or -1 to deselect)
    → Update visual highlight

User presses Enter
    → If dropdown hidden or highlight_index == -1: do nothing
    → Call on_select_callback(results[highlight_index])
    → If clear_on_select: clear entry text
    → Hide dropdown

User clicks item in dropdown
    → Call on_select_callback(clicked_item)
    → If clear_on_select: clear entry text
    → Hide dropdown

User presses Escape
    → Hide dropdown without selection

User clicks outside / tabs away
    → Hide dropdown without selection
```
