---
work_package_id: WP07
title: Production Readiness
lane: done
history:
- timestamp: '2026-01-03T06:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude-reviewer
assignee: claude
phase: Phase 3 - Production Readiness & History
review_status: ''
reviewed_by: ''
shell_pid: '97164'
subtasks:
- T030
- T031
- T032
- T033
---

# Work Package Prompt: WP07 - Production Readiness

## Objectives & Success Criteria

Add is_production_ready flag with toggle and filter support.

**Success Criteria**:
- Toggle production readiness in recipe form
- Filter recipes by readiness state
- New recipes default to experimental (not production ready)
- Production planning shows ready recipes (optional enhancement)

## Context & Constraints

**Key References**:
- `src/ui/forms/recipe_form.py` - Add checkbox
- `src/ui/recipes_tab.py` - Add filter
- `kitty-specs/037-recipe-template-snapshot/spec.md` - User Story 5

**User Story 5 Acceptance**:
- "Given a recipe, When I toggle its production readiness flag, Then the change is persisted."
- "Given recipes with mixed readiness states, When I filter by 'Production Ready', Then only ready recipes appear."
- "Given a new recipe, When it is created, Then it defaults to experimental (not production ready)."

## Subtasks & Detailed Guidance

### Subtask T030 - Add is_production_ready Checkbox [PARALLEL]

**Purpose**: Allow toggling production readiness in recipe form.

**File**: `src/ui/forms/recipe_form.py`

**Steps**:
1. Add checkbox near top of form (after basic info)
2. Default unchecked for new recipes
3. Load state when editing
4. Save state on form submit

**Code**:
```python
# After basic info section, add:

# Production Readiness
ready_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
ready_frame.pack(fill="x", padx=20, pady=10)

self.production_ready_var = ctk.BooleanVar(value=False)
self.production_ready_checkbox = ctk.CTkCheckBox(
    ready_frame,
    text="Production Ready",
    variable=self.production_ready_var,
    onvalue=True,
    offvalue=False
)
self.production_ready_checkbox.pack(side="left")

ready_hint = ctk.CTkLabel(
    ready_frame,
    text="(Uncheck for experimental/test recipes)",
    text_color="gray"
)
ready_hint.pack(side="left", padx=10)
```

**In _populate_form() for editing**:
```python
# Load production readiness state
if recipe.get("is_production_ready"):
    self.production_ready_var.set(True)
else:
    self.production_ready_var.set(False)
```

**In _on_save()**:
```python
# Include in recipe_data dict
recipe_data = {
    # ... existing fields
    "is_production_ready": self.production_ready_var.get(),
}
```

---

### Subtask T031 - Add Readiness Filter to Search [PARALLEL]

**Purpose**: Filter recipe list by production readiness.

**File**: `src/ui/recipes_tab.py`

**Steps**:
1. Add dropdown to search bar area
2. Options: "All" | "Production Ready" | "Experimental"
3. Filter results based on selection

**Code**:
```python
# In search/filter section, add:

# Readiness filter
self.readiness_var = ctk.StringVar(value="All")
self.readiness_dropdown = ctk.CTkComboBox(
    filter_frame,
    variable=self.readiness_var,
    values=["All", "Production Ready", "Experimental"],
    width=150,
    command=self._on_readiness_filter_changed
)
self.readiness_dropdown.pack(side="left", padx=5)


def _on_readiness_filter_changed(self, selection):
    """Handle readiness filter change."""
    self._refresh_recipe_list()


def _refresh_recipe_list(self):
    """Refresh recipe list with current filters."""
    # Get filter values
    category = self.category_var.get()
    name_search = self.search_var.get()
    readiness = self.readiness_var.get()

    # Build filter params
    params = {}
    if category and category != "All":
        params["category"] = category
    if name_search:
        params["name_search"] = name_search

    # Get recipes
    recipes = recipe_service.get_all_recipes(**params)

    # Apply readiness filter
    if readiness == "Production Ready":
        recipes = [r for r in recipes if r.get("is_production_ready")]
    elif readiness == "Experimental":
        recipes = [r for r in recipes if not r.get("is_production_ready")]

    # Update table
    self._populate_table(recipes)
```

---

### Subtask T032 - Default New Recipes to Experimental

**Purpose**: New recipes should not be production ready by default.

**File**: `src/services/recipe_service.py`

**Verify in create_recipe()**:
```python
def create_recipe(recipe_data: dict, ingredients_data: list = None, session=None) -> dict:
    # ... existing code ...

    recipe = Recipe(
        name=recipe_data["name"],
        category=recipe_data["category"],
        # ... other fields ...
        is_production_ready=recipe_data.get("is_production_ready", False),  # Default False
    )
```

**Note**: This is already handled by model default, but service should honor explicit value if provided.

---

### Subtask T033 - Filter Production Planning (Optional)

**Purpose**: Show only ready recipes in production planning dropdowns.

**File**: `src/ui/forms/record_production_dialog.py` (if applicable)

**This is optional** - if recipes are selected via finished units, this may not apply. Document for future enhancement if needed.

**If implementing**:
```python
# When populating recipe dropdown, filter to ready only
ready_recipes = [r for r in recipes if r.get("is_production_ready")]
```

## Test Strategy

- Manual testing: Toggle readiness, verify persisted
- Filter test: Create mix of ready/experimental, verify filter
- New recipe test: Create recipe, verify defaults to experimental

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| User confusion | Clear labeling and hint text |
| Forgetting to mark ready | Reminder in production planning |

## Definition of Done Checklist

- [ ] is_production_ready checkbox in recipe form
- [ ] Checkbox loads correct state when editing
- [ ] Checkbox state saved on submit
- [ ] Readiness filter dropdown in recipes_tab
- [ ] Filter correctly shows ready/experimental/all
- [ ] New recipes default to experimental
- [ ] (Optional) Production planning filters to ready

## Review Guidance

- Verify default is False (unchecked) for new recipes
- Check filter works with variant grouping
- Confirm checkbox state persists across edit cycles

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
- 2026-01-04T18:56:41Z – claude – shell_pid=69596 – lane=doing – Started parallel implementation
- 2026-01-04T19:01:27Z – claude – shell_pid=71271 – lane=for_review – Implementation complete: T030 checkbox, T031 filter, T032 defaults verified
- 2026-01-05T03:20:23Z – claude-reviewer – shell_pid=97164 – lane=done – Code review approved: is_production_ready flag on model with default=False verified
