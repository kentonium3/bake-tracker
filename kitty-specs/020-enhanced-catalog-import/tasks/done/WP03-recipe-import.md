---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Recipe Import with FK Validation"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "63528"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Recipe Import with FK Validation

## IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: Update `review_status: acknowledged` when addressing feedback.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Implement `import_recipes()` with comprehensive FK validation, collision detection, and circular reference detection.

**Success Criteria**:
- Recipes created with all RecipeIngredients and RecipeComponents
- FK validation for both ingredient references and component recipe references
- Name collision provides detailed error (existing vs import recipe info)
- Circular recipe references detected and rejected
- Unit tests cover all validation scenarios

---

## Context & Constraints

**Reference Documents**:
- `kitty-specs/020-enhanced-catalog-import/spec.md` - FR-023, FR-024, FR-025
- `kitty-specs/020-enhanced-catalog-import/data-model.md` - Recipe field mapping
- `src/models/recipe.py` - Recipe, RecipeIngredient, RecipeComponent models

**Prerequisites**:
- WP01 complete (CatalogImportResult class)

**Architectural Constraints**:
1. Recipe unique key: `name` (not slug - model uses name)
2. Collision error must include: existing recipe name, yield info vs import recipe info
3. Circular detection: A->B->C->A must be caught before any recipes created

---

## Subtasks & Detailed Guidance

### T013 - Implement import_recipes() with ADD_ONLY mode

**Purpose**: Create recipe import function with full relationship handling.

**Steps**:
1. Add model imports:
   ```python
   from src.models.recipe import Recipe, RecipeIngredient, RecipeComponent
   ```
2. Define function signature matching pattern
3. Implementation flow:
   - Build ingredient slug->id lookup
   - Build recipe name->id lookup (for components)
   - For each recipe:
     - Validate all FKs first (fail-fast)
     - Create Recipe
     - Create RecipeIngredients
     - Create RecipeComponents
     - Track success/failure

**Files**: `src/services/catalog_import_service.py`

---

### T014 - Validate RecipeIngredient FKs

**Purpose**: Ensure all ingredient_slug references in recipe ingredients exist.

**Steps**:
1. For each recipe, extract all ingredient_slugs from `ingredients` array
2. Check each against slug->id lookup
3. Collect all missing slugs before failing:
   ```python
   missing = [slug for slug in ingredient_slugs if slug not in slug_to_id]
   if missing:
       result.add_error(
           "recipes",
           recipe_name,
           "fk_missing",
           f"Missing ingredients: {', '.join(missing)}",
           "Import these ingredients first or remove from recipe"
       )
       continue
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T015 - Validate RecipeComponent FKs

**Purpose**: Ensure all component recipe references exist.

**Steps**:
1. For each recipe, extract all `recipe_name` from `components` array
2. Check against recipe name->id lookup
3. Handle ordering: if importing A which references B, B must either:
   - Exist in database already, OR
   - Appear earlier in import file
4. Error format:
   ```python
   result.add_error(
       "recipes",
       recipe_name,
       "fk_missing",
       f"Component recipe '{component_name}' not found",
       "Import the component recipe first or remove from components"
   )
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T016 - Circular reference detection

**Purpose**: Detect and reject circular recipe dependencies.

**Steps**:
1. Build directed graph of recipe->component relationships
2. Use DFS or topological sort to detect cycles
3. Implementation:
   ```python
   def _detect_cycles(recipes_data: List[Dict]) -> Optional[List[str]]:
       """Return cycle path if found, None otherwise."""
       graph = {}
       for r in recipes_data:
           name = r["name"]
           components = [c["recipe_name"] for c in r.get("components", [])]
           graph[name] = components

       visited = set()
       path = []

       def dfs(node):
           if node in path:
               cycle_start = path.index(node)
               return path[cycle_start:] + [node]
           if node in visited:
               return None
           visited.add(node)
           path.append(node)
           for neighbor in graph.get(node, []):
               cycle = dfs(neighbor)
               if cycle:
                   return cycle
           path.pop()
           return None

       for recipe_name in graph:
           cycle = dfs(recipe_name)
           if cycle:
               return cycle
       return None
   ```
4. Error format:
   ```python
   result.add_error(
       "recipes",
       cycle[0],
       "circular_reference",
       f"Circular reference detected: {' -> '.join(cycle)}",
       "Remove circular dependency to import"
   )
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T017 - Name collision detection

**Purpose**: Reject duplicate recipe names with detailed error.

**Steps**:
1. Query existing recipe names before import
2. For each recipe, check if name exists
3. If collision, query existing recipe details:
   ```python
   existing = session.query(Recipe).filter_by(name=recipe_name).first()
   result.add_error(
       "recipes",
       recipe_name,
       "collision",
       f"Recipe '{recipe_name}' already exists. "
       f"Existing: yields {existing.yield_quantity} {existing.yield_unit}. "
       f"Import: yields {import_yield_quantity} {import_yield_unit}.",
       "Delete existing recipe or rename import"
   )
   ```

**Files**: `src/services/catalog_import_service.py`

---

### T018 - Test: test_import_recipes_add_mode [P]

**Purpose**: Verify new recipes created with all relationships.

**Steps**:
1. Pre-create 2 ingredients
2. Create recipe data with 2 ingredients
3. Call `import_recipes(data)`
4. Assert added == 1
5. Query database, verify recipe has 2 RecipeIngredients

**Files**: `src/tests/test_catalog_import_service.py`

---

### T019 - Test: test_import_recipes_fk_validation [P]

**Purpose**: Verify FK validation catches missing ingredients.

**Steps**:
1. Create recipe referencing non-existent ingredient "missing_vanilla"
2. Call `import_recipes(data)`
3. Assert failed == 1
4. Assert error mentions "missing_vanilla"

**Files**: `src/tests/test_catalog_import_service.py`

---

### T020 - Test: test_import_recipes_collision [P]

**Purpose**: Verify collision error includes detailed info.

**Steps**:
1. Pre-create recipe "Chocolate Cake" with yield_quantity=12, yield_unit="servings"
2. Create import data for "Chocolate Cake" with yield_quantity=24, yield_unit="pieces"
3. Call `import_recipes(data)`
4. Assert failed == 1
5. Assert error contains "yields 12 servings" and "yields 24 pieces"

**Files**: `src/tests/test_catalog_import_service.py`

---

### T021 - Test: test_import_recipes_circular_detection

**Purpose**: Verify circular references detected.

**Steps**:
1. Create import data:
   - Recipe A with component B
   - Recipe B with component C
   - Recipe C with component A
2. Call `import_recipes(data)`
3. Assert error contains "Circular reference"
4. Assert error shows cycle path

**Files**: `src/tests/test_catalog_import_service.py`

---

## Test Strategy

**Required Tests**:
- `test_import_recipes_add_mode` - Happy path with relationships
- `test_import_recipes_fk_validation` - Missing ingredient error
- `test_import_recipes_collision` - Detailed collision error
- `test_import_recipes_circular_detection` - Cycle detection

**Commands**:
```bash
pytest src/tests/test_catalog_import_service.py -k "recipe" -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Recipe uses `name` not `slug` | Confirmed: model uses `name` as unique key |
| Component order matters | Process in file order, update lookup after each create |
| Complex cycle detection | Use standard DFS algorithm, test with known cycles |

---

## Definition of Done Checklist

- [ ] T013: `import_recipes()` function implemented
- [ ] T014: RecipeIngredient FK validation
- [ ] T015: RecipeComponent FK validation
- [ ] T016: Circular reference detection
- [ ] T017: Name collision with detailed error
- [ ] T018: `test_import_recipes_add_mode` passes
- [ ] T019: `test_import_recipes_fk_validation` passes
- [ ] T020: `test_import_recipes_collision` passes
- [ ] T021: `test_import_recipes_circular_detection` passes
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

**Reviewer Checkpoints**:
1. Collision error includes both existing and import yield info
2. Circular detection correctly identifies cycle path
3. RecipeIngredients and RecipeComponents created correctly
4. Partial success: valid recipes created even if some fail

---

## Activity Log

- 2025-12-14T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-15T02:51:28Z – claude – shell_pid=56445 – lane=doing – Started implementation
- 2025-12-15T02:54:26Z – claude – shell_pid=56445 – lane=for_review – Ready for review
- 2025-12-15T03:24:01Z – claude-reviewer – shell_pid=63528 – lane=done – Code review: APPROVED - Recipe import with FK validation, circular reference detection, collision handling
