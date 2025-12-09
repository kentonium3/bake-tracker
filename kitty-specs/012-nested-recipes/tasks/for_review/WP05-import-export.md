---
work_package_id: "WP05"
subtasks:
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
title: "Import/Export Support"
phase: "Phase 2 - Core Features"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "93394"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Import/Export Support

## Objectives & Success Criteria

- Modify export functions to include recipe components
- Modify import functions to process and restore component relationships
- Handle missing component references gracefully (warn, skip, continue)
- Add unit tests for import/export with components

**Definition of Done**: Export produces JSON with components; import restores relationships; round-trip preserves data.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/data-model.md` - Export format specification
- `kitty-specs/012-nested-recipes/spec.md` - User Story 5 (Import/Export)
- `src/services/import_export_service.py` - Existing import/export patterns

**Architecture Constraints**:
- Use recipe name as identifier (not slug - recipes don't have slugs)
- Import order: All recipes first, then link components
- Graceful handling: Missing components logged as warnings, not fatal errors

**Export Format**:
```json
{
  "recipes": [
    {
      "name": "Parent Recipe",
      "category": "...",
      "ingredients": [...],
      "components": [
        {
          "recipe_name": "Child Recipe",
          "quantity": 2.0,
          "notes": "prepare day before"
        }
      ]
    }
  ]
}
```

## Subtasks & Detailed Guidance

### Subtask T028 – Modify export_recipes_to_json() to include components

**Purpose**: Include component relationships in recipe-only export.

**Steps**:
1. Find `export_recipes_to_json()` in `src/services/import_export_service.py`
2. After exporting ingredients, add components array
3. Export component recipe by name, quantity, notes

**Files**: `src/services/import_export_service.py`

**Code** (add after ingredients loop, around line 315):
```python
# In export_recipes_to_json(), after ingredients are added:

# Add components
recipe_data["components"] = []
for comp in recipe.recipe_components:
    component_data = {
        "recipe_name": comp.component_recipe.name if comp.component_recipe else None,
        "quantity": comp.quantity,
    }
    if comp.notes:
        component_data["notes"] = comp.notes

    recipe_data["components"].append(component_data)
```

**Also**: Need to import RecipeComponent model at top of file:
```python
from src.models import RecipeComponent
```

---

### Subtask T029 – Modify export_all_to_json() to include components

**Purpose**: Include component relationships in full database export.

**Steps**:
1. Find `export_all_to_json()` function
2. Add same component export logic as T028
3. Verify recipe export section includes components

**Files**: `src/services/import_export_service.py`

**Code** (similar pattern, in the recipes section around line 1043):
```python
# After exporting recipe ingredients, add components
recipe_data["components"] = []
for comp in recipe.recipe_components:
    component_data = {
        "recipe_name": comp.component_recipe.name if comp.component_recipe else None,
        "quantity": comp.quantity,
    }
    if comp.notes:
        component_data["notes"] = comp.notes

    recipe_data["components"].append(component_data)
```

---

### Subtask T030 – Modify import_recipes_from_json() to process components

**Purpose**: Restore component relationships during import.

**Steps**:
1. Find `import_recipes_from_json()` function
2. Two-pass approach:
   - First pass: Import all recipes (without components)
   - Second pass: Link components by recipe name
3. Track imported recipe names for lookup

**Files**: `src/services/import_export_service.py`

**Code**:
```python
def import_recipes_from_json(
    file_path: str, skip_duplicates: bool = True, skip_missing_ingredients: bool = True
) -> ImportResult:
    """
    Import recipes from JSON file.
    ...
    """
    # ... existing code to read file and validate ...

    recipes_data = data.get("recipes", [])

    # Track imported recipes for component linking
    imported_recipes = {}  # name -> Recipe

    # First pass: Import recipes without components
    for recipe_data in recipes_data:
        # ... existing recipe import logic ...

        # Track imported recipe
        if recipe:  # If successfully imported
            imported_recipes[recipe.name] = recipe

    # Second pass: Link components
    for recipe_data in recipes_data:
        recipe_name = recipe_data.get("name")
        components_data = recipe_data.get("components", [])

        if not components_data:
            continue

        # Find the parent recipe
        parent_recipe = imported_recipes.get(recipe_name)
        if not parent_recipe:
            # Recipe wasn't imported (maybe duplicate skipped)
            # Try to find existing recipe
            try:
                with session_scope() as session:
                    parent_recipe = session.query(Recipe).filter_by(name=recipe_name).first()
            except:
                continue

        if not parent_recipe:
            continue

        # Link each component
        for comp_data in components_data:
            component_name = comp_data.get("recipe_name")
            quantity = comp_data.get("quantity", 1.0)
            notes = comp_data.get("notes")

            if not component_name:
                continue

            # Find component recipe
            component_recipe = imported_recipes.get(component_name)
            if not component_recipe:
                # Try existing recipe
                try:
                    with session_scope() as session:
                        component_recipe = session.query(Recipe).filter_by(name=component_name).first()
                except:
                    pass

            if not component_recipe:
                result.add_warning(
                    "recipe_component",
                    f"{recipe_name} -> {component_name}",
                    f"Component recipe '{component_name}' not found, skipping"
                )
                continue

            # Add component
            try:
                add_recipe_component(
                    parent_recipe.id,
                    component_recipe.id,
                    quantity=quantity,
                    notes=notes
                )
                result.imported_count += 1
            except ValidationError as e:
                result.add_warning(
                    "recipe_component",
                    f"{recipe_name} -> {component_name}",
                    str(e)
                )
            except Exception as e:
                result.add_error(
                    "recipe_component",
                    f"{recipe_name} -> {component_name}",
                    str(e)
                )

    return result
```

**Required Import**:
```python
from src.services.recipe_service import add_recipe_component
```

---

### Subtask T031 – Handle missing component recipes gracefully

**Purpose**: Ensure import doesn't fail completely when a referenced component doesn't exist.

**Steps**:
1. This is integrated into T030
2. Use `result.add_warning()` for missing components
3. Continue processing remaining components and recipes
4. Log clear warning message identifying the missing component

**Verification**:
- Import file with component referencing non-existent recipe
- Confirm import completes successfully
- Confirm warning message identifies the missing reference
- Confirm other data imports correctly

---

### Subtask T032 – Add unit tests for export with components

**Purpose**: Verify export includes component relationships correctly.

**Files**: `src/tests/services/test_import_export_service.py` (or create new test file)

**Test Cases**:
```python
def test_export_recipe_with_components(tmp_path):
    """Export includes component relationships."""
    child = create_test_recipe("Child Recipe")
    parent = create_test_recipe("Parent Recipe")
    add_recipe_component(parent.id, child.id, quantity=2.0, notes="Test note")

    export_file = tmp_path / "export.json"
    result = export_recipes_to_json(str(export_file))

    assert result.success

    # Read and verify
    with open(export_file) as f:
        data = json.load(f)

    parent_data = next(r for r in data["recipes"] if r["name"] == "Parent Recipe")
    assert "components" in parent_data
    assert len(parent_data["components"]) == 1
    assert parent_data["components"][0]["recipe_name"] == "Child Recipe"
    assert parent_data["components"][0]["quantity"] == 2.0
    assert parent_data["components"][0]["notes"] == "Test note"


def test_export_recipe_without_components(tmp_path):
    """Recipe without components has empty components array."""
    recipe = create_test_recipe("Simple Recipe")

    export_file = tmp_path / "export.json"
    result = export_recipes_to_json(str(export_file))

    with open(export_file) as f:
        data = json.load(f)

    recipe_data = next(r for r in data["recipes"] if r["name"] == "Simple Recipe")
    assert "components" in recipe_data
    assert len(recipe_data["components"]) == 0


def test_export_all_includes_components(tmp_path):
    """Full export includes component relationships."""
    child = create_test_recipe("Child")
    parent = create_test_recipe("Parent")
    add_recipe_component(parent.id, child.id, quantity=1.5)

    export_file = tmp_path / "full_export.json"
    result = export_all_to_json(str(export_file))

    with open(export_file) as f:
        data = json.load(f)

    parent_data = next(r for r in data["recipes"] if r["name"] == "Parent")
    assert len(parent_data["components"]) == 1
```

---

### Subtask T033 – Add unit tests for import with/without existing components

**Purpose**: Verify import correctly restores component relationships.

**Files**: `src/tests/services/test_import_export_service.py`

**Test Cases**:
```python
def test_import_recipe_with_components(tmp_path, clean_db):
    """Import creates component relationships."""
    # Create export data
    export_data = {
        "version": "1.0",
        "recipes": [
            {
                "name": "Child Recipe",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": []
            },
            {
                "name": "Parent Recipe",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [
                    {
                        "recipe_name": "Child Recipe",
                        "quantity": 2.0,
                        "notes": "Test"
                    }
                ]
            }
        ]
    }

    import_file = tmp_path / "import.json"
    with open(import_file, "w") as f:
        json.dump(export_data, f)

    result = import_recipes_from_json(str(import_file))

    assert result.success

    # Verify relationship created
    parent = get_recipe_by_name("Parent Recipe")
    components = get_recipe_components(parent.id)
    assert len(components) == 1
    assert components[0].quantity == 2.0
    assert components[0].notes == "Test"


def test_import_component_missing_recipe(tmp_path, clean_db):
    """Import warns when component recipe doesn't exist."""
    export_data = {
        "version": "1.0",
        "recipes": [
            {
                "name": "Parent Recipe",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [
                    {
                        "recipe_name": "Nonexistent Recipe",
                        "quantity": 1.0
                    }
                ]
            }
        ]
    }

    import_file = tmp_path / "import.json"
    with open(import_file, "w") as f:
        json.dump(export_data, f)

    result = import_recipes_from_json(str(import_file))

    # Should succeed overall but have warning
    assert result.success
    assert len(result.warnings) > 0
    assert "Nonexistent Recipe" in str(result.warnings)


def test_import_links_existing_recipe(tmp_path, clean_db):
    """Import links to existing recipe if component already exists."""
    # Pre-create child recipe
    child = create_test_recipe("Existing Child")

    export_data = {
        "version": "1.0",
        "recipes": [
            {
                "name": "New Parent",
                "category": "Test",
                "yield_quantity": 1,
                "yield_unit": "batch",
                "ingredients": [],
                "components": [
                    {
                        "recipe_name": "Existing Child",
                        "quantity": 1.0
                    }
                ]
            }
        ]
    }

    import_file = tmp_path / "import.json"
    with open(import_file, "w") as f:
        json.dump(export_data, f)

    result = import_recipes_from_json(str(import_file))

    assert result.success

    parent = get_recipe_by_name("New Parent")
    components = get_recipe_components(parent.id)
    assert len(components) == 1
    assert components[0].component_recipe_id == child.id


def test_import_export_roundtrip(tmp_path, clean_db):
    """Export then import preserves all component relationships."""
    # Create hierarchy
    grandchild = create_test_recipe("Grandchild")
    child = create_test_recipe("Child")
    parent = create_test_recipe("Parent")

    add_recipe_component(child.id, grandchild.id, quantity=1.0)
    add_recipe_component(parent.id, child.id, quantity=2.0, notes="Double batch")

    # Export
    export_file = tmp_path / "roundtrip.json"
    export_result = export_recipes_to_json(str(export_file))
    assert export_result.success

    # Clear database
    clear_all_recipes()

    # Import
    import_result = import_recipes_from_json(str(export_file))
    assert import_result.success

    # Verify hierarchy restored
    imported_parent = get_recipe_by_name("Parent")
    parent_components = get_recipe_components(imported_parent.id)
    assert len(parent_components) == 1
    assert parent_components[0].component_recipe.name == "Child"
    assert parent_components[0].quantity == 2.0
    assert parent_components[0].notes == "Double batch"

    child_components = get_recipe_components(parent_components[0].component_recipe_id)
    assert len(child_components) == 1
    assert child_components[0].component_recipe.name == "Grandchild"
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import order issues | Two-pass: all recipes first, then components |
| Circular reference in import data | Validation catches on add_recipe_component |
| Duplicate components | Skip if already exists, log warning |

## Definition of Done Checklist

- [ ] `export_recipes_to_json()` includes components array
- [ ] `export_all_to_json()` includes components array
- [ ] `import_recipes_from_json()` creates component relationships
- [ ] Missing components logged as warnings, not errors
- [ ] Round-trip preserves all relationships
- [ ] All import/export tests passing

## Review Guidance

- Test export JSON structure manually
- Verify warning messages are clear and actionable
- Check import handles edge cases (duplicates, missing, circular)
- Test round-trip with complex hierarchies

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-09T13:53:26Z – claude – shell_pid=91930 – lane=doing – Started implementation
- 2025-12-09T14:01:30Z – claude – shell_pid=93394 – lane=for_review – Completed implementation - 7 new tests, all 544 pass
