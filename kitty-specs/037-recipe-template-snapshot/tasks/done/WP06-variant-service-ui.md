---
work_package_id: "WP06"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "Variant Service & UI"
phase: "Phase 2 - Scaling & Variants"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "97164"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Variant Service & UI

## Objectives & Success Criteria

Enable recipe variants with base_recipe relationship and grouped display.

**Success Criteria**:
- Create variant linked to base recipe via base_recipe_id
- Recipe list shows variants indented under base
- Variants orphan gracefully when base deleted (ON DELETE SET NULL)
- Service functions: get_recipe_variants(), create_recipe_variant()
- UI: base_recipe dropdown, variant_name field in recipe form

## Context & Constraints

**Key References**:
- `src/services/recipe_service.py` - Add variant functions
- `src/ui/forms/recipe_form.py` - Add variant fields
- `src/ui/recipes_tab.py` - Add indentation display
- `kitty-specs/037-recipe-template-snapshot/spec.md` - User Story 4

**User Story 4 Acceptance**:
- "Given a base recipe 'Thumbprint Cookies', When I create a variant 'Raspberry Thumbprint', Then the variant is linked to the base via base_recipe_id."
- "Given a base recipe with variants, When I view the recipe list, Then variants are displayed grouped under their base recipe."

**UI Pattern**: Indented list (consistent with ingredient hierarchy)

## Subtasks & Detailed Guidance

### Subtask T022 - Add get_recipe_variants() [PARALLEL]

**Purpose**: Query all variants of a base recipe.

**File**: `src/services/recipe_service.py`

**Implementation**:
```python
def get_recipe_variants(base_recipe_id: int, session=None) -> list:
    """
    Get all variants of a base recipe.

    Args:
        base_recipe_id: The base recipe ID
        session: Optional session

    Returns:
        List of variant recipe dicts
    """
    if session is not None:
        return _get_recipe_variants_impl(base_recipe_id, session)

    with session_scope() as session:
        return _get_recipe_variants_impl(base_recipe_id, session)


def _get_recipe_variants_impl(base_recipe_id: int, session) -> list:
    variants = (
        session.query(Recipe)
        .filter_by(base_recipe_id=base_recipe_id, is_archived=False)
        .order_by(Recipe.variant_name, Recipe.name)
        .all()
    )

    return [
        {
            "id": v.id,
            "name": v.name,
            "variant_name": v.variant_name,
            "category": v.category,
            "is_production_ready": v.is_production_ready,
        }
        for v in variants
    ]
```

---

### Subtask T023 - Add create_recipe_variant() [PARALLEL]

**Purpose**: Create a variant linked to a base recipe.

**Implementation**:
```python
def create_recipe_variant(
    base_recipe_id: int,
    variant_name: str,
    name: str = None,
    copy_ingredients: bool = True,
    session=None
) -> dict:
    """
    Create a variant of an existing recipe.

    Args:
        base_recipe_id: The recipe to create a variant of
        variant_name: Name distinguishing this variant (e.g., "Raspberry")
        name: Full recipe name (defaults to "Base Name - Variant Name")
        copy_ingredients: If True, copy ingredients from base recipe
        session: Optional session

    Returns:
        Created variant recipe dict
    """
    if session is not None:
        return _create_recipe_variant_impl(
            base_recipe_id, variant_name, name, copy_ingredients, session
        )

    with session_scope() as session:
        return _create_recipe_variant_impl(
            base_recipe_id, variant_name, name, copy_ingredients, session
        )


def _create_recipe_variant_impl(
    base_recipe_id: int,
    variant_name: str,
    name: str,
    copy_ingredients: bool,
    session
) -> dict:
    # Get base recipe
    base = session.query(Recipe).filter_by(id=base_recipe_id).first()
    if not base:
        raise ValueError(f"Base recipe {base_recipe_id} not found")

    # Generate name if not provided
    if not name:
        name = f"{base.name} - {variant_name}"

    # Create variant
    variant = Recipe(
        name=name,
        category=base.category,
        source=base.source,
        yield_quantity=base.yield_quantity,
        yield_unit=base.yield_unit,
        yield_description=base.yield_description,
        estimated_time_minutes=base.estimated_time_minutes,
        notes=f"Variant of {base.name}",
        base_recipe_id=base_recipe_id,
        variant_name=variant_name,
        is_production_ready=False,  # Variants start experimental
    )

    session.add(variant)
    session.flush()

    # Copy ingredients if requested
    if copy_ingredients:
        for ri in base.recipe_ingredients:
            new_ri = RecipeIngredient(
                recipe_id=variant.id,
                ingredient_id=ri.ingredient_id,
                quantity=ri.quantity,
                unit=ri.unit,
                notes=ri.notes,
            )
            session.add(new_ri)

    session.commit()

    return {
        "id": variant.id,
        "name": variant.name,
        "variant_name": variant.variant_name,
        "base_recipe_id": variant.base_recipe_id,
    }
```

---

### Subtask T024 - Extend get_all_recipes() for Grouping [PARALLEL]

**Purpose**: Return recipes sorted with variants grouped under base.

**Modify**: `get_all_recipes()` in `src/services/recipe_service.py`

**Implementation**:
```python
def get_all_recipes(
    category: str = None,
    name_search: str = None,
    include_archived: bool = False,
    group_variants: bool = True,  # NEW PARAMETER
    session=None
) -> list:
    """Get all recipes with optional variant grouping."""
    # ... existing implementation ...

    if group_variants:
        # Sort: base recipes first, then variants under their base
        return _group_recipes_with_variants(recipes)

    return recipes


def _group_recipes_with_variants(recipes: list) -> list:
    """
    Sort recipes so variants appear indented under their base.

    Order:
    1. Base recipes (base_recipe_id is None) sorted by name
    2. Variants immediately after their base, sorted by variant_name
    """
    # Separate base recipes and variants
    base_recipes = [r for r in recipes if r.get("base_recipe_id") is None]
    variants = [r for r in recipes if r.get("base_recipe_id") is not None]

    # Build variant lookup by base_recipe_id
    variant_map = {}
    for v in variants:
        base_id = v["base_recipe_id"]
        if base_id not in variant_map:
            variant_map[base_id] = []
        variant_map[base_id].append(v)

    # Sort variants within each group
    for base_id in variant_map:
        variant_map[base_id].sort(key=lambda x: x.get("variant_name") or x.get("name"))

    # Build result with variants under base
    result = []
    for base in sorted(base_recipes, key=lambda x: x.get("name", "")):
        base["_is_base"] = True
        base["_variant_count"] = len(variant_map.get(base["id"], []))
        result.append(base)

        # Add variants indented
        for variant in variant_map.get(base["id"], []):
            variant["_is_variant"] = True
            variant["_indent_level"] = 1
            result.append(variant)

    # Add orphaned variants (base was deleted)
    orphaned = [v for v in variants if v["base_recipe_id"] not in [b["id"] for b in base_recipes]]
    for v in orphaned:
        v["_is_orphaned_variant"] = True
        result.append(v)

    return result
```

---

### Subtask T025 - Add base_recipe Dropdown to Form [PARALLEL]

**Purpose**: Allow selecting a base recipe when creating variant.

**File**: `src/ui/forms/recipe_form.py`

**Steps**:
1. Add dropdown for base recipe selection (optional)
2. Populate with existing recipes (exclude self if editing)
3. When base selected, enable variant_name field

**Code**:
```python
# In form setup, add after basic fields:

# Variant Section
variant_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
variant_frame.pack(fill="x", padx=20, pady=10)

variant_label = ctk.CTkLabel(variant_frame, text="Recipe Variant (Optional)")
variant_label.pack(anchor="w")

# Base recipe dropdown
base_frame = ctk.CTkFrame(variant_frame, fg_color="transparent")
base_frame.pack(fill="x", pady=5)

base_label = ctk.CTkLabel(base_frame, text="Base Recipe:", width=100)
base_label.pack(side="left")

self.base_recipe_var = ctk.StringVar(value="(None - standalone recipe)")
self.base_recipe_dropdown = ctk.CTkComboBox(
    base_frame,
    variable=self.base_recipe_var,
    values=self._get_base_recipe_options(),
    width=300,
    command=self._on_base_recipe_changed
)
self.base_recipe_dropdown.pack(side="left", padx=5)


def _get_base_recipe_options(self) -> list:
    """Get list of recipes that can be bases (exclude self if editing).

    IMPORTANT: Only base recipes (base_recipe_id is None) should appear
    in this list. Variants of variants are discouraged per spec FR-011.
    """
    recipes = recipe_service.get_all_recipes(group_variants=False)
    options = ["(None - standalone recipe)"]

    for r in recipes:
        # Exclude self if editing
        if self.recipe_id and r["id"] == self.recipe_id:
            continue
        # CRITICAL: Exclude existing variants to prevent multi-level nesting
        # Per spec FR-011: "UI should discourage variants of variants"
        if r.get("base_recipe_id") is not None:
            continue
        options.append(f"{r['name']} (ID: {r['id']})")

    return options


def _on_base_recipe_changed(self, selection):
    """Handle base recipe selection change."""
    if selection == "(None - standalone recipe)":
        self.variant_name_entry.configure(state="disabled")
        self.variant_name_var.set("")
    else:
        self.variant_name_entry.configure(state="normal")
```

---

### Subtask T026 - Add variant_name Field [PARALLEL]

**Purpose**: Allow entering variant distinguisher.

**Code** (continue from T025):
```python
# Variant name entry (below base dropdown)
variant_name_frame = ctk.CTkFrame(variant_frame, fg_color="transparent")
variant_name_frame.pack(fill="x", pady=5)

variant_name_label = ctk.CTkLabel(variant_name_frame, text="Variant Name:", width=100)
variant_name_label.pack(side="left")

self.variant_name_var = ctk.StringVar()
self.variant_name_entry = ctk.CTkEntry(
    variant_name_frame,
    textvariable=self.variant_name_var,
    width=200,
    placeholder_text="e.g., Raspberry, Strawberry"
)
self.variant_name_entry.pack(side="left", padx=5)
self.variant_name_entry.configure(state="disabled")  # Enable when base selected

variant_hint = ctk.CTkLabel(
    variant_name_frame,
    text="(Distinguishes this variant from others)",
    text_color="gray"
)
variant_hint.pack(side="left", padx=5)
```

---

### Subtask T027 - Update Recipe List with Variant Indentation

**Purpose**: Display variants indented under base recipes.

**File**: `src/ui/recipes_tab.py`

**Steps**:
1. Modify _get_row_values() to add indentation
2. Use "  └─" prefix for variants
3. Show variant count badge for base recipes

**Code**:
```python
def _get_row_values(self, recipe: dict) -> list:
    """Get display values for a recipe row."""
    name = recipe.get("name", "")

    # Add indentation for variants
    if recipe.get("_is_variant"):
        name = f"  └─ {name}"
    elif recipe.get("_is_base") and recipe.get("_variant_count", 0) > 0:
        count = recipe["_variant_count"]
        name = f"{name} ({count} variant{'s' if count > 1 else ''})"

    # ... rest of existing implementation
    return [
        name,
        recipe.get("category", ""),
        # ... other columns
    ]
```

---

### Subtask T028 - Sort Variants Under Base

**Purpose**: Ensure consistent sorting in UI.

**Already Covered**: The `_group_recipes_with_variants()` function in T024 handles this.

---

### Subtask T029 - Create Unit Tests for Variants

**Purpose**: Verify variant functionality.

**File**: `src/tests/services/test_recipe_service.py`

**Tests to Add**:
1. `test_get_recipe_variants_empty` - Base with no variants returns []
2. `test_get_recipe_variants_found` - Returns correct variants
3. `test_create_recipe_variant_basic` - Creates linked variant
4. `test_create_recipe_variant_copy_ingredients` - Ingredients copied
5. `test_variant_orphaned_on_base_delete` - base_recipe_id becomes None
6. `test_get_all_recipes_grouped` - Variants appear under base

## Test Strategy

- Run: `pytest src/tests/services/test_recipe_service.py -v -k variant`
- Manual UI testing for indentation display

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI clutter with many variants | Indentation provides visual hierarchy |
| Orphaned variants confusing | Show "(orphaned)" indicator |
| Circular references | CHECK constraint prevents |

## Definition of Done Checklist

- [ ] get_recipe_variants() implemented
- [ ] create_recipe_variant() implemented
- [ ] get_all_recipes() groups variants under base
- [ ] Recipe form has base_recipe dropdown
- [ ] Recipe form has variant_name field
- [ ] Recipe list shows indentation for variants
- [ ] Base recipes show variant count
- [ ] Unit tests pass (6 tests)

## Review Guidance

- Verify indentation matches ingredient hierarchy pattern
- Check orphaned variants display correctly
- Confirm base_recipe_id != id constraint works
- **CRITICAL**: Verify base_recipe dropdown excludes existing variants (prevents multi-level nesting per FR-011)

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
- 2026-01-04T18:56:22Z – gemini – shell_pid=69362 – lane=doing – Started parallel implementation
- 2026-01-04T19:02:44Z – gemini – shell_pid=72255 – lane=for_review – Service layer complete: T022-T024, T029 (variant functions + tests)
- 2026-01-05T03:20:23Z – claude-reviewer – shell_pid=97164 – lane=done – Code review approved: Variant service and base_recipe_id/variant_name fields verified
