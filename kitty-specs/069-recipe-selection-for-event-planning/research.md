# Research: Recipe Selection for Event Planning

**Feature**: 069-recipe-selection-for-event-planning
**Date**: 2026-01-26
**Status**: Complete

## Research Questions

### RQ-001: How to identify base vs variant recipes?

**Decision**: Use `Recipe.base_recipe_id` field

**Rationale**:
- `base_recipe_id IS NULL` → Base recipe
- `base_recipe_id IS NOT NULL` → Variant recipe (references its base)
- `variant_name` field provides variant-specific label (e.g., "Raspberry", "Strawberry")

**Source**: `src/models/recipe.py` - Self-referential FK pattern

**Alternatives Considered**:
- Separate base/variant tables: Rejected - existing model already implements this elegantly
- Category-based distinction: Rejected - doesn't capture parent-child relationship

### RQ-002: How to load all recipes for selection?

**Decision**: Use `recipe_service.get_all_recipes(include_archived=False)`

**Rationale**:
- Returns all non-archived recipes ordered by name
- Existing method, no new implementation needed
- Can add filters later if needed (category, production_ready)

**Source**: `src/services/recipe_service.py` lines 216-290

**Alternatives Considered**:
- Direct query in UI: Rejected - violates layered architecture
- New method with variant grouping: Rejected - flat list is spec requirement

### RQ-003: How does EventRecipe junction table work?

**Decision**: Use existing F068 model as-is

**Structure**:
```python
EventRecipe(BaseModel):
    event_id: FK to events.id (CASCADE delete)
    recipe_id: FK to recipes.id (RESTRICT delete)
    created_at: DateTime
    UniqueConstraint(event_id, recipe_id)
```

**Source**: `src/models/event_recipe.py`

**Key Behaviors**:
- Deleting event cascades to delete all associated event_recipes
- Cannot delete recipe that is referenced by event_recipe (RESTRICT)
- Unique constraint prevents duplicate selections

### RQ-004: How to implement "replace not append" for selections?

**Decision**: Delete existing records, then insert new ones in single transaction

**Implementation Pattern**:
```python
def set_event_recipes(session, event_id, recipe_ids):
    # Delete all existing for this event
    session.query(EventRecipe).filter(
        EventRecipe.event_id == event_id
    ).delete()

    # Insert new selections
    for recipe_id in recipe_ids:
        session.add(EventRecipe(event_id=event_id, recipe_id=recipe_id))

    session.flush()
```

**Rationale**:
- Atomic operation ensures consistency
- Simpler than diff-based update
- Follows F068 patterns

**Alternatives Considered**:
- Diff-based (add missing, remove extra): More complex, same result
- Soft-delete: Overkill for junction table

### RQ-005: Where in PlanningTab to embed recipe selection?

**Decision**: Below the event table, visible when event is selected

**Layout**:
```
PlanningTab
├─ Row 0: Action buttons (Create, Edit, Delete, Refresh)
├─ Row 1: PlanningEventDataTable (events list)
├─ Row 2: RecipeSelectionFrame (NEW - shown when event selected)
│   ├─ Header: "Recipe Selection for [Event Name]"
│   ├─ Counter: "X of Y recipes selected"
│   ├─ Scrollable checkbox list
│   └─ Save/Cancel buttons
└─ Row 3: Status bar
```

**Source**: `src/ui/planning_tab.py` current structure analysis

**Rationale**:
- Matches user's selected option 1 (embedded in tab)
- Natural top-to-bottom flow: select event → configure recipes
- Keeps all planning context visible

### RQ-006: How to visually distinguish base vs variant?

**Decision**: Indentation prefix + "(variant)" label

**Display Format**:
```
☑ Chocolate Chip Cookies
    ☑ Chocolate Chip Cookies (variant: Raspberry)
    ☐ Chocolate Chip Cookies (variant: Strawberry)
☐ Sugar Cookies
```

**Implementation**:
```python
if recipe.base_recipe_id:
    # Variant - indent and label
    display_name = f"    {recipe.name} (variant: {recipe.variant_name})"
else:
    # Base - normal display
    display_name = recipe.name
```

**Rationale**:
- Simple text-based distinction (no icons needed)
- Clear parent-child visual hierarchy
- Works within CustomTkinter CTkCheckBox

**Alternatives Considered**:
- Icon-based: More complex, requires image assets
- Color-based: Accessibility concerns
- Separate sections: Violates "flat list" spec requirement

### RQ-007: Existing checkbox patterns in codebase?

**Decision**: Follow CTkCheckBox with BooleanVar pattern

**Pattern from codebase**:
```python
self.var = ctk.BooleanVar(value=False)
self.checkbox = ctk.CTkCheckBox(
    parent,
    text="Label",
    variable=self.var,
    command=self._on_change,  # Optional callback
)
```

**Source**: `src/ui/forms/recipe_form.py` line 714

**For list of checkboxes**:
```python
self.recipe_vars: Dict[int, ctk.BooleanVar] = {}

for recipe in recipes:
    var = ctk.BooleanVar(value=False)
    self.recipe_vars[recipe.id] = var
    checkbox = ctk.CTkCheckBox(
        scrollable_frame,
        text=display_name,
        variable=var,
        command=self._update_count,
    )
    checkbox.pack(anchor="w", pady=2)
```

### RQ-008: Session management for recipe selection?

**Decision**: Follow F068 pattern - query within session_scope, expunge for UI

**Pattern**:
```python
# Loading recipes for display
with session_scope() as session:
    recipes = recipe_service.get_all_recipes()
    # Recipes can be used outside session (simple objects)

# Saving selections
with session_scope() as session:
    set_event_recipes(session, event_id, selected_recipe_ids)
    session.commit()
```

**Source**: `src/ui/planning_tab.py` existing patterns

**Key Insight**: Recipe objects from `get_all_recipes()` are already detached, safe for UI use.

## Summary

All research questions resolved. No clarifications needed. Implementation can proceed with:

1. **Service methods**: `set_event_recipes()`, `get_event_recipe_ids()` in event_service.py
2. **UI component**: `RecipeSelectionFrame` with CTkCheckBox list in scrollable frame
3. **Integration**: Embed in PlanningTab below event table, show on event selection
