---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
  - "T008"
title: "Transformation Script"
phase: "Phase 2 - Transformation Script"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T22:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Transformation Script

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create a standalone Python script that transforms legacy recipe yield data into the new FinishedUnit structure within JSON export files.

**Success Criteria**:
1. Script reads JSON export files and transforms recipes
2. Each recipe with yield data gets a corresponding FinishedUnit entry
3. Unique slugs are generated with collision handling
4. `sample_data_min.json` and `sample_data_all.json` are successfully transformed
5. Transformed JSON passes validation (can be imported)

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/056-unified-yield-management/spec.md`
- Plan: `kitty-specs/056-unified-yield-management/plan.md`
- Data Model: `kitty-specs/056-unified-yield-management/data-model.md`
- Research: `kitty-specs/056-unified-yield-management/research.md`

**Architectural Constraints**:
- Standalone script in `scripts/` directory (not integrated into CLI)
- Constitution VI: No in-app migration; transformation is external
- Script is temporary tooling for development; not a permanent feature

**Key Design Decision**: Script transforms JSON files during export/import cycle. This is a one-time development task.

## Subtasks & Detailed Guidance

### Subtask T005 – Create transform_yield_data.py with core transformation logic

**Purpose**: Build the main transformation script structure.

**Steps**:
1. Create `scripts/transform_yield_data.py`
2. Implement main structure:
   ```python
   #!/usr/bin/env python3
   """
   Transform legacy recipe yield data to FinishedUnit structure.

   Usage:
       python scripts/transform_yield_data.py input.json output.json
   """
   import argparse
   import json
   import re
   from pathlib import Path
   from typing import Any


   def slugify(text: str) -> str:
       """Convert text to slug format."""
       text = text.lower().strip()
       text = re.sub(r'[^\w\s-]', '', text)
       text = re.sub(r'[\s_-]+', '_', text)
       return text.strip('_')


   def transform_recipe(recipe: dict, existing_slugs: set) -> tuple[dict, list[dict]]:
       """
       Transform a single recipe, extracting yield data to FinishedUnit.

       Args:
           recipe: Recipe dictionary from JSON
           existing_slugs: Set of already-used slugs (for collision detection)

       Returns:
           Tuple of (transformed_recipe, list_of_finished_units)
       """
       finished_units = []

       # Extract yield data
       yield_quantity = recipe.get('yield_quantity')
       yield_unit = recipe.get('yield_unit')
       yield_description = recipe.get('yield_description')

       if yield_quantity is not None and yield_unit:
           # Generate slug
           recipe_slug = slugify(recipe.get('name', 'unknown'))
           yield_suffix = slugify(yield_description) if yield_description else 'standard'
           base_slug = f"{recipe_slug}_{yield_suffix}"

           # Handle collision
           slug = base_slug
           counter = 2
           while slug in existing_slugs:
               slug = f"{base_slug}_{counter}"
               counter += 1
           existing_slugs.add(slug)

           # Generate display_name
           if yield_description:
               display_name = yield_description
           else:
               display_name = f"Standard {recipe.get('name', 'Recipe')}"

           # Create FinishedUnit entry
           finished_unit = {
               'slug': slug,
               'display_name': display_name,
               'recipe_name': recipe.get('name'),
               'category': recipe.get('category'),
               'yield_mode': 'discrete_count',
               'items_per_batch': int(yield_quantity) if yield_quantity else None,
               'item_unit': yield_unit,
               'batch_percentage': None,
               'portion_description': None,
               'inventory_count': 0,
               'is_archived': False
           }
           finished_units.append(finished_unit)

       # Null out legacy fields in recipe
       transformed_recipe = recipe.copy()
       transformed_recipe['yield_quantity'] = None
       transformed_recipe['yield_unit'] = None
       transformed_recipe['yield_description'] = None

       return transformed_recipe, finished_units


   def transform_data(data: dict) -> dict:
       """Transform entire export data structure."""
       result = data.copy()
       existing_slugs = set()
       all_finished_units = []

       # Transform recipes
       if 'recipes' in data:
           transformed_recipes = []
           for recipe in data['recipes']:
               transformed_recipe, finished_units = transform_recipe(recipe, existing_slugs)
               transformed_recipes.append(transformed_recipe)
               all_finished_units.extend(finished_units)
           result['recipes'] = transformed_recipes

       # Add finished_units section
       result['finished_units'] = all_finished_units

       return result


   def main():
       parser = argparse.ArgumentParser(
           description='Transform legacy recipe yield data to FinishedUnit structure'
       )
       parser.add_argument('input_file', type=Path, help='Input JSON file')
       parser.add_argument('output_file', type=Path, help='Output JSON file')
       parser.add_argument('--dry-run', action='store_true',
                           help='Print transformation summary without writing')

       args = parser.parse_args()

       # Read input
       with open(args.input_file, 'r', encoding='utf-8') as f:
           data = json.load(f)

       # Transform
       result = transform_data(data)

       # Report
       recipe_count = len(data.get('recipes', []))
       fu_count = len(result.get('finished_units', []))
       print(f"Transformed {recipe_count} recipes -> {fu_count} FinishedUnits")

       if args.dry_run:
           print("Dry run - no file written")
           return

       # Write output
       with open(args.output_file, 'w', encoding='utf-8') as f:
           json.dump(result, f, indent=2, ensure_ascii=False)

       print(f"Written to {args.output_file}")


   if __name__ == '__main__':
       main()
   ```

**Files**: `scripts/transform_yield_data.py` (NEW)
**Parallel?**: No (blocking change)
**Notes**: This is the foundation for all other subtasks in this work package.

### Subtask T006 – Implement slug generation with collision handling

**Purpose**: Ensure unique slugs even when multiple recipes have similar names or descriptions.

**Steps**:
1. The `slugify()` function is included in T005
2. Collision handling is implemented in `transform_recipe()`
3. Test cases to verify:
   - Basic slugification: "Chocolate Chip Cookies" → "chocolate_chip_cookies"
   - With description: "2-inch cookies" → "chocolate_chip_cookies_2inch_cookies"
   - Without description: uses "standard" suffix
   - Collision: append _2, _3, etc.

**Files**: `scripts/transform_yield_data.py`
**Parallel?**: No (included in T005)
**Notes**: Slug uniqueness is critical for import to succeed.

### Subtask T007 – Transform sample_data_min.json

**Purpose**: Validate transformation works on minimal test data.

**Steps**:
1. Run transformation:
   ```bash
   python scripts/transform_yield_data.py test_data/sample_data_min.json test_data/sample_data_min_transformed.json
   ```
2. Verify output:
   - Check `finished_units` array exists
   - Verify recipe yield fields are null
   - Verify FinishedUnit references match recipe names
3. Optionally overwrite original (after backup):
   ```bash
   cp test_data/sample_data_min.json test_data/sample_data_min_backup.json
   python scripts/transform_yield_data.py test_data/sample_data_min_backup.json test_data/sample_data_min.json
   ```

**Files**: `test_data/sample_data_min.json`
**Parallel?**: Yes (can run alongside T008 after T005/T006)
**Notes**: Keep backup of original file for reference.

### Subtask T008 – Transform sample_data_all.json

**Purpose**: Validate transformation works on full test data with all edge cases.

**Steps**:
1. Run transformation:
   ```bash
   python scripts/transform_yield_data.py test_data/sample_data_all.json test_data/sample_data_all_transformed.json
   ```
2. Verify output:
   - Check all recipes have corresponding FinishedUnits
   - Verify no slug collisions in output
   - Verify recipe yield fields are null
3. Optionally overwrite original (after backup):
   ```bash
   cp test_data/sample_data_all.json test_data/sample_data_all_backup.json
   python scripts/transform_yield_data.py test_data/sample_data_all_backup.json test_data/sample_data_all.json
   ```

**Files**: `test_data/sample_data_all.json`
**Parallel?**: Yes (can run alongside T007 after T005/T006)
**Notes**: This file has more recipes and may reveal edge cases.

## Test Strategy

**Required Tests**:
1. Script runs without errors on valid input
2. Slugification handles special characters correctly
3. Collision handling produces unique slugs
4. Empty yield_description generates "Standard {recipe_name}"
5. All recipe yield fields become null after transformation
6. FinishedUnit count matches recipes with yield data

**Commands**:
```bash
# Manual testing
python scripts/transform_yield_data.py test_data/sample_data_min.json /tmp/test_output.json --dry-run

# Verify JSON structure
python -c "import json; d=json.load(open('/tmp/test_output.json')); print(len(d.get('finished_units', [])))"
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Malformed JSON in test data | Script has try/except with clear error messages |
| Missing yield_unit values | Use "each" as default |
| Unicode characters in recipe names | Use ensure_ascii=False in json.dump |
| Large files slow to process | Not a concern for ~50 recipes |

## Definition of Done Checklist

- [ ] T005: `scripts/transform_yield_data.py` exists with core transformation logic
- [ ] T006: Slug generation handles collisions correctly
- [ ] T007: `sample_data_min.json` transformed successfully
- [ ] T008: `sample_data_all.json` transformed successfully
- [ ] Script has --dry-run option for safe testing
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Verify slug generation produces valid, unique slugs
2. Verify recipe yield fields are nulled in output
3. Verify FinishedUnit entries have all required fields
4. Verify script handles edge cases (missing description, special characters)

## Activity Log

- 2026-01-16T22:00:00Z – system – lane=planned – Prompt created.
- 2026-01-17T03:17:19Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-17T03:19:22Z – claude – lane=for_review – All subtasks complete: T005-T008. Transformation script created and tested. sample_data_min.json (7 recipes) and sample_data_all.json (20 recipes) transformed successfully.
- 2026-01-17T17:58:37Z – claude – lane=doing – Starting review
- 2026-01-17T17:59:30Z – claude – lane=done – Review passed: Transformation script works correctly. All test data (7 + 20 recipes) transformed to FinishedUnits with unique slugs. Dry-run option works.
