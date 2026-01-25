---
work_package_id: WP02
title: Recipe Catalog Variant Grouping + Production Ready Default
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 328768f4daee82a997d39359558c3f7d6a9c9f78
created_at: '2026-01-25T18:19:25.297635+00:00'
subtasks:
- T004
- T005
- T010
phase: Phase 1 - UI Polish
assignee: ''
agent: ''
shell_pid: "49364"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-25T18:09:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Recipe Catalog Variant Grouping + Production Ready Default

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Display variant recipes visually grouped under their base recipes in the Recipe Catalog grid, and default Production Ready checkbox to True for new recipes.

**Success Criteria**:
- [ ] Variant recipes appear indented under their base recipe with "↳" indicator
- [ ] Base recipes sorted alphabetically at top level
- [ ] Variants sorted alphabetically within each base group
- [ ] Orphaned variants (base deleted) display at top level without indicator
- [ ] New recipes default to production_ready=True
- [ ] Existing recipes preserve their current production_ready value

## Context & Constraints

**Feature**: F067 - Recipe UI Polish - Yield Information and Variant Grouping
**User Stories**:
- US2 - Recipe Catalog Variant Grouping (Priority: P1)
- US4 - Production Ready Default (Priority: P2)

**Spec Reference**: `kitty-specs/067-recipe-ui-polish-yield-variants/spec.md` (FR-004, FR-005, FR-006)

**Key Constraints**:
- UI-layer only - no service or model changes
- Use existing `base_recipe_id` field to detect variants
- Follow existing DataTable patterns (no CTkTreeview migration)

**Related Files**:
- `src/ui/widgets/data_table.py` - RecipeDataTable class (lines 336-393)
- `src/ui/forms/recipe_form.py` - Production ready default
- `kitty-specs/067-recipe-ui-polish-yield-variants/research.md` - Grid investigation

## Subtasks & Detailed Guidance

### Subtask T004 – Implement Variant-Aware Sorting in RecipeDataTable

**Purpose**: Currently recipes display in a flat list without showing the parent-child variant relationship. Sorting variants under their base recipe makes the relationship immediately visible.

**Current State** (from research.md):
- `RecipeDataTable` class at lines 336-393 in `data_table.py`
- Inherits from base `DataTable` class
- Uses `load_data(data)` method to populate rows
- No sorting logic for variant grouping currently

**Steps**:

1. **Locate RecipeDataTable** in `src/ui/widgets/data_table.py` (line 336)

2. **Understand the data flow**:
   - Data comes in via `load_data(data)` where `data` is a list of Recipe objects
   - Each Recipe has:
     - `name` - recipe name
     - `base_recipe_id` - FK to parent recipe (None for base recipes)
     - `base_recipe` - relationship to parent Recipe object (if loaded)

3. **Override `load_data()` or add sorting logic** to group variants under their base:

   ```python
   def load_data(self, data):
       """Load recipe data with variant grouping."""
       if not data:
           super().load_data(data)
           return

       # Separate base recipes and variants
       base_recipes = [r for r in data if r.base_recipe_id is None]
       variants = [r for r in data if r.base_recipe_id is not None]

       # Sort base recipes alphabetically
       base_recipes.sort(key=lambda r: r.name.lower())

       # Group variants by base_recipe_id
       variants_by_base = {}
       for v in variants:
           base_id = v.base_recipe_id
           if base_id not in variants_by_base:
               variants_by_base[base_id] = []
           variants_by_base[base_id].append(v)

       # Sort variants within each group
       for base_id in variants_by_base:
           variants_by_base[base_id].sort(key=lambda r: r.name.lower())

       # Build final sorted list: base followed by its variants
       sorted_data = []
       for base in base_recipes:
           sorted_data.append(base)
           if base.id in variants_by_base:
               sorted_data.extend(variants_by_base[base.id])

       # Add orphaned variants (base deleted) at the end
       orphaned = [v for v in variants if v.base_recipe_id not in [b.id for b in base_recipes]]
       orphaned.sort(key=lambda r: r.name.lower())
       sorted_data.extend(orphaned)

       super().load_data(sorted_data)
   ```

4. **Handle edge case**: If a variant's base recipe was deleted, it should appear at top level (no indicator). The orphan check handles this.

**Files**:
- `src/ui/widgets/data_table.py` (modify `RecipeDataTable.load_data()`)

**Validation**:
- [ ] Base recipes appear in alphabetical order
- [ ] Variants appear immediately after their base recipe
- [ ] Variants within a group are sorted alphabetically
- [ ] Base recipes with no variants display normally

---

### Subtask T005 – Add "↳ " Prefix to Variant Names

**Purpose**: Visual indicator makes the variant relationship immediately clear without needing to read other columns.

**Current State**:
- `_get_row_values()` method at lines 371-393
- Returns `[row_data.name, row_data.category, yield_info]`
- No variant detection currently

**Steps**:

1. **Locate `_get_row_values()`** in `RecipeDataTable` (line 371)

2. **Add variant detection and prefix**:

   ```python
   def _get_row_values(self, row_data: Any) -> List[str]:
       # F067: Add variant indicator
       name = row_data.name
       if row_data.base_recipe_id is not None:
           name = f"↳ {name}"

       # F056: Use FinishedUnit for yield info
       yield_info = "No yield types"
       if row_data.finished_units:
           primary_unit = row_data.finished_units[0]
           items = primary_unit.items_per_batch or 0
           unit = primary_unit.item_unit or "each"
           yield_info = f"{items:.0f} {unit}"

       return [
           name,
           row_data.category,
           yield_info,
       ]
   ```

3. **Unicode consideration**: The "↳" character (U+21B3, Downwards Arrow With Tip Rightwards) should render correctly per spec assumptions. If issues arise, fallback to "└─ " or similar ASCII art.

**Files**:
- `src/ui/widgets/data_table.py` (modify `RecipeDataTable._get_row_values()`)

**Validation**:
- [ ] Variant recipes display with "↳ " prefix
- [ ] Base recipes display without prefix
- [ ] Unicode character renders correctly
- [ ] Name column width accommodates the prefix

---

### Subtask T010 – Set Production Ready Default to True

**Purpose**: Most recipes are intended for production, so the checkbox should default to checked, saving users an extra click.

**Current State**:
- In `recipe_form.py`, the production_ready checkbox is created with some default
- Need to verify current default and ensure new recipes get `True`

**Steps**:

1. **Find the production_ready checkbox creation** in `recipe_form.py`:
   - Search for `production_ready` in the file
   - Look for where the `ctk.CTkCheckBox` is created

2. **Ensure default is True for new recipes**:
   - If editing existing recipe: preserve the existing value
   - If creating new recipe: default to True (checked)

   ```python
   # When initializing for new recipe:
   self.production_ready_var = ctk.BooleanVar(value=True)  # Default to True

   # When editing existing recipe:
   if self.recipe:
       self.production_ready_var.set(self.recipe.production_ready)
   ```

3. **Verify the checkbox widget** uses the variable:
   ```python
   self.production_ready_checkbox = ctk.CTkCheckBox(
       parent,
       text="Production Ready",
       variable=self.production_ready_var,
   )
   ```

**Files**:
- `src/ui/forms/recipe_form.py` (modify checkbox default)

**Validation**:
- [ ] New recipe: Production Ready checkbox is checked by default
- [ ] Edit existing recipe with production_ready=False: checkbox remains unchecked
- [ ] Edit existing recipe with production_ready=True: checkbox remains checked

---

## Test Strategy

**Manual Testing Required**:

1. **Recipe Catalog with variants**:
   - Create a base recipe "Chocolate Chip Cookie"
   - Create 2 variants: "Chocolate Chip Cookie (Large)", "Chocolate Chip Cookie (Mini)"
   - View Recipe Catalog and verify:
     - Base "Chocolate Chip Cookie" appears first
     - "↳ Chocolate Chip Cookie (Large)" appears below with indicator
     - "↳ Chocolate Chip Cookie (Mini)" appears below with indicator
     - Both variants sorted alphabetically

2. **Recipe Catalog without variants**:
   - View Recipe Catalog with only base recipes
   - Verify alphabetical order, no indicators

3. **New recipe creation**:
   - Open New Recipe dialog
   - Verify Production Ready checkbox is checked
   - Create recipe and verify production_ready=True saved

4. **Edit existing recipe**:
   - Edit a recipe with production_ready=False
   - Verify checkbox is unchecked
   - Don't change it, save, verify it stays False

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Sorting breaks if base_recipe relationship not loaded | Ensure Recipe queries eager-load base_recipe_id |
| Unicode rendering issues | Have ASCII fallback ready if needed |
| Orphaned variants cause errors | Handle orphan case explicitly in sorting |

## Definition of Done Checklist

- [ ] T004: Variant-aware sorting implemented
- [ ] T005: "↳ " prefix added to variant names
- [ ] T010: Production Ready defaults to True for new recipes
- [ ] Manual testing completed for all scenarios
- [ ] No regressions in recipe listing or creation

## Review Guidance

**Reviewers should verify**:
1. Create base + variant recipes and check catalog display
2. Verify sorting is alphabetical at both levels
3. Create new recipe and check Production Ready default
4. Test edge cases: only base recipes, orphaned variants

## Activity Log

- 2026-01-25T18:09:19Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---
- 2026-01-25T18:23:45Z – unknown – shell_pid=49364 – lane=for_review – Implemented: variant grouping with sorting and prefix, production ready default already present

## Implementation Command

**No dependencies** - start from main:

```bash
spec-kitty implement WP02 --feature 067-recipe-ui-polish-yield-variants
```

After implementation:
```bash
spec-kitty agent tasks move-task WP02 --to for_review --note "Ready for review: variant grouping, production ready default"
```
