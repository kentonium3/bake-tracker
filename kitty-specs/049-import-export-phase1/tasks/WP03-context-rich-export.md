---
work_package_id: "WP03"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
title: "Context-Rich Export"
phase: "Phase 2 - Wave 1"
lane: "done"
assignee: ""
agent: "gemini"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Context-Rich Export

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `denormalized_export_service.py` with context-rich view exports for ingredients, materials, and recipes.

**Success Criteria**:
- SC-003: Context-rich export available for ingredients, materials, and recipes with hierarchy paths
- FR-005: System MUST support context-rich export for ingredients, materials, and recipes
- FR-006: System MUST include hierarchy paths in context-rich exports
- FR-007: System MUST include nested relationships in context-rich exports
- FR-008: System MUST include computed values (inventory, costs) in context-rich exports

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 3)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Existing code: `src/services/denormalized_export_service.py`
- Existing spec: `docs/design/spec_import_export.md` (Appendix E)

**Pattern to Follow**: `export_products_view()` in denormalized_export_service.py

**View Structure**:
```json
{
  "view_type": "ingredients",
  "export_date": "2026-01-12T12:00:00Z",
  "record_count": 150,
  "_meta": {
    "editable_fields": ["description", "notes", "density_*"],
    "readonly_fields": ["id", "slug", "category_hierarchy", "product_count", "inventory_total"]
  },
  "records": [...]
}
```

**Purpose of Context-Rich Exports**:
- Enable AI tools to understand data with full context
- Include computed values AI can reference but not modify
- `_meta` section enables format auto-detection for import

---

## Subtasks & Detailed Guidance

### Subtask T020 - Add `export_ingredients_view()`

**Purpose**: Export ingredients with hierarchy paths, products, and inventory.

**Steps**:
1. Open `src/services/denormalized_export_service.py`
2. Study `export_products_view()` as pattern
3. Create `export_ingredients_view(output_path: str) -> str`:
```python
def export_ingredients_view(output_path: str) -> str:
    """Export ingredients with context for AI augmentation."""
    with session_scope() as session:
        ingredients = session.query(Ingredient).options(
            joinedload(Ingredient.products),
            joinedload(Ingredient.category)
        ).all()

        records = []
        for ing in ingredients:
            record = {
                # Editable fields
                "description": ing.description,
                "notes": ing.notes,
                "density_volume_value": float(ing.density_volume_value) if ing.density_volume_value else None,
                # ... other editable

                # Readonly/computed fields
                "id": ing.id,
                "slug": ing.slug,
                "display_name": ing.display_name,
                "category_hierarchy": build_hierarchy_path(ing),
                "product_count": len(ing.products),
                "inventory_total": calculate_inventory_total(ing, session),
                "average_cost": calculate_average_cost(ing, session),
            }
            records.append(record)

        return write_view_file("ingredients", records, output_path, _meta)
```

**Files**: `src/services/denormalized_export_service.py`

### Subtask T021 - Include hierarchy paths

**Purpose**: Build full category hierarchy paths like "Flours & Starches > Wheat Flours > All-Purpose".

**Steps**:
1. Create helper function:
```python
def build_hierarchy_path(entity) -> str:
    """Build full category path from leaf to root."""
    path_parts = []
    current = entity.category if hasattr(entity, 'category') else entity

    while current:
        path_parts.insert(0, current.display_name or current.name)
        current = getattr(current, 'parent', None)

    return " > ".join(path_parts) if path_parts else ""
```
2. Handle missing categories gracefully (return empty string)

**Files**: `src/services/denormalized_export_service.py`

### Subtask T022 - Include related products as nested array

**Purpose**: Embed product data within ingredient records.

**Steps**:
1. For each ingredient, include nested products:
```python
record["products"] = [
    {
        "brand": p.brand,
        "product_name": p.product_name,
        "package_size": p.package_size,
        "is_preferred": p.is_preferred,
        "last_purchase_price": get_last_price(p),
    }
    for p in ing.products
]
```
2. Products are readonly context (not editable on import)

**Files**: `src/services/denormalized_export_service.py`

### Subtask T023 - Include computed inventory totals and costs

**Purpose**: Add computed values for AI context.

**Steps**:
1. Create helper functions:
```python
def calculate_inventory_total(ingredient, session) -> float:
    """Sum current_quantity across all inventory items for ingredient's products."""
    total = session.query(func.sum(InventoryItem.current_quantity)).join(
        Product
    ).filter(
        Product.ingredient_id == ingredient.id,
        InventoryItem.current_quantity > 0
    ).scalar()
    return float(total) if total else 0.0

def calculate_average_cost(ingredient, session) -> float:
    """Calculate weighted average cost per unit."""
    # Query inventory items and compute weighted average
    pass
```
2. Include in readonly fields

**Files**: `src/services/denormalized_export_service.py`

### Subtask T024 - Add `export_materials_view()` with hierarchy paths

**Purpose**: Export materials with context (mirrors ingredients).

**Steps**:
1. Create `export_materials_view(output_path: str) -> str`
2. Include:
   - Editable: description, notes
   - Readonly: id, slug, display_name, category_hierarchy, product_count
3. Follow same pattern as ingredients view

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes, after T020-T023 establish pattern

### Subtask T025 - Add `export_recipes_view()` with embedded ingredients

**Purpose**: Export recipes with full ingredient details and costs.

**Steps**:
1. Create `export_recipes_view(output_path: str) -> str`
2. Include:
   - Editable: instructions, notes, prep_time_minutes, cook_time_minutes
   - Readonly: id, slug, name, category, yield_*, computed_cost
3. Embed ingredients:
```python
record["ingredients"] = [
    {
        "ingredient_slug": ri.ingredient.slug,
        "ingredient_name": ri.ingredient.display_name,
        "quantity": float(ri.quantity),
        "unit": ri.unit,
        "estimated_cost": calculate_ingredient_cost(ri),
    }
    for ri in recipe.recipe_ingredients
]
```

**Files**: `src/services/denormalized_export_service.py`
**Parallel?**: Yes, after T020-T023 establish pattern

### Subtask T026 - Include computed recipe costs

**Purpose**: Calculate total recipe cost from ingredient costs.

**Steps**:
1. Create helper:
```python
def calculate_recipe_cost(recipe, session) -> float:
    """Sum ingredient costs for recipe based on current inventory prices."""
    total = 0.0
    for ri in recipe.recipe_ingredients:
        unit_cost = get_ingredient_unit_cost(ri.ingredient, ri.unit, session)
        total += float(ri.quantity) * unit_cost
    return round(total, 2)
```
2. Handle missing price data gracefully

**Files**: `src/services/denormalized_export_service.py`

### Subtask T027 - Add `_meta` section with editable/readonly field lists

**Purpose**: Enable format auto-detection and import field filtering.

**Steps**:
1. Define metadata for each view:
```python
INGREDIENTS_META = {
    "editable_fields": [
        "description", "notes",
        "density_volume_value", "density_volume_unit",
        "density_weight_value", "density_weight_unit"
    ],
    "readonly_fields": [
        "id", "uuid", "slug", "display_name", "category",
        "category_hierarchy", "product_count", "products",
        "inventory_total", "average_cost"
    ]
}
```
2. Include `_meta` in view output
3. WP06 will use this for import filtering

**Files**: `src/services/denormalized_export_service.py`

### Subtask T028 - Add unit tests

**Purpose**: Test all new view exports.

**Steps**:
1. Open `src/tests/services/test_denormalized_export_service.py`
2. Add tests:
   - `test_export_ingredients_view_includes_hierarchy()`
   - `test_export_ingredients_view_includes_products()`
   - `test_export_ingredients_view_includes_inventory_total()`
   - `test_export_materials_view_structure()`
   - `test_export_recipes_view_includes_ingredients()`
   - `test_export_recipes_view_computed_cost()`
   - `test_view_meta_section_present()`

**Files**: `src/tests/services/test_denormalized_export_service.py`

---

## Test Strategy

**Unit Tests** (required):
- Test hierarchy path generation
- Test nested product inclusion
- Test computed values accuracy
- Test `_meta` section structure

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_denormalized_export_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance on large datasets | Use eager loading, batch queries |
| Missing category hierarchy | Handle null parents gracefully |
| Cost calculation errors | Verify against existing cost services |

---

## Definition of Done Checklist

- [ ] `export_ingredients_view()` with hierarchy, products, inventory
- [ ] `export_materials_view()` with hierarchy
- [ ] `export_recipes_view()` with embedded ingredients, costs
- [ ] All views include `_meta` section
- [ ] Hierarchy paths formatted as "Parent > Child > Leaf"
- [ ] Computed values accurate
- [ ] All unit tests pass

## Review Guidance

**Reviewers should verify**:
1. `_meta` section correctly categorizes editable vs readonly
2. Hierarchy paths work for all nesting levels
3. Computed values match manual calculations
4. Views follow existing `export_products_view()` pattern

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:19:41Z – gemini – lane=doing – Starting context-rich export implementation
- 2026-01-12T17:28:01Z – gemini – lane=for_review – All 50 tests passing. Context-rich exports for ingredients, materials, recipes complete.
- 2026-01-12T21:55:00Z – claude – shell_pid=13882 – lane=done – Approved: All 50 tests pass. Views include hierarchy paths, embedded products, computed values, and _meta sections.
