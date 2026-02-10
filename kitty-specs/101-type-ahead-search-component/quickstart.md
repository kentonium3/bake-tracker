# Quickstart: Type-Ahead Search Component

**Feature**: 101-type-ahead-search-component
**Date**: 2026-02-10

## Basic Usage

```python
from src.ui.widgets.type_ahead_entry import TypeAheadEntry

# Define search callback
def search_items(query: str) -> list:
    """Return matching items as list of dicts with 'display_name' key."""
    from src.services.ingredient_hierarchy_service import search_ingredients
    return search_ingredients(query, limit=10)

# Define selection callback
def on_item_selected(item: dict) -> None:
    """Handle selected item."""
    print(f"Selected: {item['display_name']} (id={item['id']})")

# Create widget
typeahead = TypeAheadEntry(
    master=parent_frame,
    items_callback=search_items,
    on_select_callback=on_item_selected,
)
typeahead.pack(fill="x", padx=10, pady=5)
```

## Configuration Options

```python
# Custom settings
typeahead = TypeAheadEntry(
    master=parent_frame,
    items_callback=search_items,
    on_select_callback=on_item_selected,
    min_chars=2,              # Start searching after 2 chars (default: 3)
    debounce_ms=150,          # Faster response (default: 300)
    max_results=15,           # Show more results (default: 10)
    placeholder_text="Search materials...",
    clear_on_select=False,    # Keep text after selection (default: True)
    display_key="name",       # Use 'name' key instead of 'display_name'
)
```

## Integration Pattern (Recipe Form)

```python
class RecipeIngredientForm(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self._typeahead = TypeAheadEntry(
            master=self,
            items_callback=self._search_ingredients,
            on_select_callback=self._on_ingredient_selected,
            placeholder_text="Type ingredient name...",
        )
        self._typeahead.pack(fill="x")

    def _search_ingredients(self, query: str) -> list:
        from src.services.ingredient_hierarchy_service import search_ingredients
        return search_ingredients(query, limit=10)

    def _on_ingredient_selected(self, item: dict) -> None:
        # item contains: id, display_name, slug, category, hierarchy_level, ancestors
        self._add_ingredient_to_recipe(item)
        self._typeahead.set_focus()  # Ready for next ingredient
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Type 3+ chars | Triggers search (after debounce) |
| Down Arrow | Move highlight down (stops at last item) |
| Up Arrow | Move highlight up (stops at first item) |
| Enter | Select highlighted item |
| Escape | Close dropdown without selecting |
| Tab | Close dropdown, move focus to next field |

## Testing

```python
# Unit test example with mock callbacks
def test_typeahead_calls_callback_on_select():
    selected = []

    def mock_search(query):
        return [{"display_name": "Flour", "id": 1}]

    def mock_select(item):
        selected.append(item)

    widget = TypeAheadEntry(
        master=root,
        items_callback=mock_search,
        on_select_callback=mock_select,
    )

    # Simulate typing and selection...
    assert len(selected) == 1
    assert selected[0]["display_name"] == "Flour"
```
