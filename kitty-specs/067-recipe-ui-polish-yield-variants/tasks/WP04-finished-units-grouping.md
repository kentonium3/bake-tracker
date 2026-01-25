---
work_package_id: "WP04"
subtasks:
  - "T011"
  - "T012"
title: "Finished Units Grid Variant Grouping"
phase: "Phase 2 - Grid Grouping"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "52282"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP02"]
history:
  - timestamp: "2026-01-25T18:09:19Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Finished Units Grid Variant Grouping

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Display variant finished units visually grouped under their base finished units in the Finished Units grid, mirroring the Recipe Catalog behavior.

**Success Criteria**:
- [ ] Variant finished units appear indented under their base finished unit with "↳" indicator
- [ ] Grouping is by recipe relationship (variant FUs under base recipe's FUs)
- [ ] Base FUs sorted alphabetically (or by recipe name)
- [ ] Variant FUs sorted alphabetically within each group
- [ ] Existing Finished Units grid functionality unchanged

## Context & Constraints

**Feature**: F067 - Recipe UI Polish - Yield Information and Variant Grouping
**User Story**: US5 - Finished Units Grid Variant Grouping (Priority: P3)
**Spec Reference**: `kitty-specs/067-recipe-ui-polish-yield-variants/spec.md` (FR-011, FR-012)

**Key Constraints**:
- UI-layer only - no service or model changes
- Mirror the pattern from WP02 (RecipeDataTable variant grouping)
- Variant relationship determined via `row_data.recipe.base_recipe_id`

**Related Files**:
- `src/ui/widgets/data_table.py` - FinishedGoodDataTable class (lines 396-458)
- `kitty-specs/067-recipe-ui-polish-yield-variants/research.md` - Grid investigation

**Dependency**: This WP mirrors the pattern from WP02. Review WP02 implementation for the sorting/prefix approach before starting.

**Research Findings** (from research.md):
- `FinishedGoodDataTable` at lines 396-458
- Columns: Name (280px) | Recipe (220px) | Category (120px) | Type (100px) | Yield Info (180px)
- Row values from `_get_row_values()` at lines 433-458
- Currently flat list - no hierarchical grouping

## Subtasks & Detailed Guidance

### Subtask T011 – Implement Variant-Aware Sorting in FinishedGoodDataTable

**Purpose**: Group finished units so that variant FUs appear under their corresponding base FUs, making the relationship immediately visible.

**Current State**:
- `FinishedGoodDataTable` class at lines 396-458 in `data_table.py`
- Inherits from base `DataTable` class
- No sorting logic for variant grouping

**Relationship Model**:
```
FinishedUnit -> recipe -> Recipe
                          Recipe.base_recipe_id -> parent Recipe (if variant)
```

A FinishedUnit is a "variant FU" if its parent recipe is a variant (has non-null `base_recipe_id`).

**Steps**:

1. **Locate FinishedGoodDataTable** in `src/ui/widgets/data_table.py` (line 396)

2. **Mirror the WP02 pattern** - override `load_data()` with variant-aware sorting:

   ```python
   def load_data(self, data):
       """Load finished unit data with variant grouping."""
       if not data:
           super().load_data(data)
           return

       # Separate base FUs and variant FUs based on recipe relationship
       base_fus = []
       variant_fus = []

       for fu in data:
           if fu.recipe and fu.recipe.base_recipe_id is not None:
               variant_fus.append(fu)
           else:
               base_fus.append(fu)

       # Sort base FUs by recipe name, then by FU display_name
       base_fus.sort(key=lambda fu: (
           fu.recipe.name.lower() if fu.recipe else "",
           fu.display_name.lower()
       ))

       # Group variant FUs by their recipe's base_recipe_id
       variants_by_base_recipe = {}
       for vfu in variant_fus:
           base_recipe_id = vfu.recipe.base_recipe_id
           if base_recipe_id not in variants_by_base_recipe:
               variants_by_base_recipe[base_recipe_id] = []
           variants_by_base_recipe[base_recipe_id].append(vfu)

       # Sort variants within each group
       for base_id in variants_by_base_recipe:
           variants_by_base_recipe[base_id].sort(key=lambda fu: (
               fu.recipe.name.lower() if fu.recipe else "",
               fu.display_name.lower()
           ))

       # Build final sorted list
       sorted_data = []
       processed_base_recipes = set()

       for base_fu in base_fus:
           sorted_data.append(base_fu)

           # Add variant FUs that belong to variants of this base FU's recipe
           if base_fu.recipe:
               base_recipe_id = base_fu.recipe.id
               if base_recipe_id in variants_by_base_recipe and base_recipe_id not in processed_base_recipes:
                   sorted_data.extend(variants_by_base_recipe[base_recipe_id])
                   processed_base_recipes.add(base_recipe_id)

       # Add any orphaned variant FUs
       for base_id, vfus in variants_by_base_recipe.items():
           if base_id not in processed_base_recipes:
               sorted_data.extend(vfus)

       super().load_data(sorted_data)
   ```

3. **Consider edge cases**:
   - FU with no recipe (orphaned) - sort to end
   - Multiple FUs per recipe - all should stay together
   - Variant recipe with multiple FUs - all appear under base

**Files**:
- `src/ui/widgets/data_table.py` (modify `FinishedGoodDataTable.load_data()`)

**Validation**:
- [ ] Base FUs appear grouped by recipe
- [ ] Variant FUs appear after their base recipe's FUs
- [ ] Sorting is alphabetical within groups

---

### Subtask T012 – Add "↳ " Indicator for Variant-Sourced Finished Units

**Purpose**: Visual indicator makes the variant relationship immediately clear.

**Current State**:
- `_get_row_values()` method at lines 433-458
- Returns: `[display_name, recipe.name, category, type_display, yield_info]`
- No variant detection

**Steps**:

1. **Locate `_get_row_values()`** in `FinishedGoodDataTable` (line 433)

2. **Add variant detection and prefix**:

   ```python
   def _get_row_values(self, row_data: Any) -> List[str]:
       # F067: Detect if this FU belongs to a variant recipe
       display_name = row_data.display_name
       if row_data.recipe and row_data.recipe.base_recipe_id is not None:
           display_name = f"↳ {display_name}"

       if row_data.yield_mode.value == "discrete_count":
           yield_info = f"{row_data.items_per_batch} {row_data.item_unit}/batch"
           type_display = "Discrete Items"
       else:
           yield_info = f"{row_data.batch_percentage}% of batch"
           type_display = "Batch Portion"

       return [
           display_name,
           row_data.recipe.name if row_data.recipe else "N/A",
           row_data.category or "",
           type_display,
           yield_info,
       ]
   ```

3. **Verify the Name column width** (280px per research) can accommodate the prefix

**Files**:
- `src/ui/widgets/data_table.py` (modify `FinishedGoodDataTable._get_row_values()`)

**Validation**:
- [ ] Variant FUs display with "↳ " prefix
- [ ] Base FUs display without prefix
- [ ] Column width accommodates the prefix

---

## Test Strategy

**Manual Testing Required**:

1. **Finished Units grid with variants**:
   - Have a base recipe "Chocolate Chip Cookie" with FU "Chocolate Chip Cookie"
   - Have a variant recipe "Large Chocolate Chip Cookie" with FU "Large Cookie"
   - View Finished Units grid and verify:
     - Base FU "Chocolate Chip Cookie" appears first
     - "↳ Large Cookie" appears below with indicator

2. **Multiple FUs per recipe**:
   - If a recipe has 2 FUs, both should appear together
   - Variant FUs should appear after all base FUs for that recipe

3. **Grid without variants**:
   - If no variant recipes exist, grid displays normally without indicators

4. **Double-click navigation**:
   - Double-clicking a variant FU should still open its parent recipe for editing (existing functionality)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Recipe relationship not eager-loaded | Verify query includes recipe join |
| Sorting complexity with multiple FUs | Test with recipes having 2-3 FUs each |
| Performance with large FU lists | Sorting is O(n log n), should be fine |

## Definition of Done Checklist

- [ ] T011: Variant-aware sorting implemented
- [ ] T012: "↳ " indicator added to variant FU names
- [ ] Manual testing completed for all scenarios
- [ ] No regressions in Finished Units grid functionality
- [ ] Double-click navigation still works

## Review Guidance

**Reviewers should verify**:
1. Create base + variant recipes with finished units
2. Check Finished Units grid displays grouping correctly
3. Verify sorting is alphabetical
4. Test double-click opens correct recipe

**Pattern Reference**: Compare implementation to WP02's RecipeDataTable changes for consistency.

## Activity Log

- 2026-01-25T18:09:19Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---
- 2026-01-25T18:23:55Z – claude-opus – shell_pid=50955 – lane=doing – Started implementation via workflow command
- 2026-01-25T18:25:16Z – claude-opus – shell_pid=50955 – lane=for_review – Implemented: Finished Units grid variant grouping with sorting and prefix indicator
- 2026-01-25T18:29:09Z – claude-opus – shell_pid=52282 – lane=doing – Started review via workflow command
- 2026-01-25T18:29:27Z – claude-opus – shell_pid=52282 – lane=done – Review passed: T011 variant-aware sorting correct, T012 prefix indicator works, pattern matches WP02

## Implementation Command

**Depends on WP02** - use WP02 branch as base:

```bash
spec-kitty implement WP04 --base WP02 --feature 067-recipe-ui-polish-yield-variants
```

Or if WP02 is already merged to main:
```bash
spec-kitty implement WP04 --feature 067-recipe-ui-polish-yield-variants
```

After implementation:
```bash
spec-kitty agent tasks move-task WP04 --to for_review --note "Ready for review: finished units grid variant grouping"
```
