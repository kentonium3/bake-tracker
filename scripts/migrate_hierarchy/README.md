# Ingredient Hierarchy Migration Tooling

This directory contains scripts for migrating the existing flat ingredient catalog to a three-tier hierarchical structure.

## Overview

The migration transforms 487+ ingredients from a simple category string to a parent-child hierarchy:

```
Level 0 (Root)     -> Chocolate & Cocoa
Level 1 (Mid-tier) -> Dark Chocolate, Milk Chocolate, Cocoa Powders
Level 2 (Leaf)     -> Semi-Sweet Chips, Milk Chocolate Chips, Dutch Cocoa
```

Only leaf ingredients (level 2) can have products or be used in recipes.

## Prerequisites

- Python 3.10+
- Access to the BakeTracker database (`~/Documents/BakeTracker/bake_tracker.db`)
- An AI assistant for categorization (Claude, GPT, Gemini, etc.)

## Directory Structure

```
scripts/
├── migrate_hierarchy/
│   ├── README.md                    # This file
│   ├── export_ingredients.py        # Step 1: Export current data
│   ├── transform_hierarchy.py       # Step 3: Merge AI suggestions
│   ├── validate_hierarchy.py        # Step 4: Pre-import validation
│   └── output/
│       ├── ingredients_export.json       # Exported ingredient data
│       ├── ai_hierarchy_suggestions.json # AI-generated hierarchy (you create)
│       └── transformed_ingredients.json  # Ready for import
└── prompts/
    └── hierarchy_categorization_prompt.md  # AI prompt template
```

## Migration Process

### Step 1: Export Current Ingredients

Export all ingredients from the database to JSON:

```bash
python scripts/migrate_hierarchy/export_ingredients.py

# Or with custom paths:
python scripts/migrate_hierarchy/export_ingredients.py \
    --db-path ~/Documents/BakeTracker/bake_tracker.db \
    --output scripts/migrate_hierarchy/output/ingredients_export.json
```

**Output**: `output/ingredients_export.json`

### Step 2: Generate AI Categorization

Use an external AI assistant to categorize ingredients:

1. Open `scripts/prompts/hierarchy_categorization_prompt.md`
2. Copy the prompt template
3. Paste the contents of `output/ingredients_export.json` at the end
4. Submit to your preferred AI (Claude, GPT, Gemini)
5. Save the AI's JSON response as `output/ai_hierarchy_suggestions.json`

**Important**: Review the AI's suggestions before proceeding. Edit as needed:
- Ensure all ingredients are assigned
- Verify category names make sense for your use case
- Check that packaging items are separated

### Step 3: Transform with AI Suggestions

Merge the AI suggestions with the original export:

```bash
python scripts/migrate_hierarchy/transform_hierarchy.py

# Or with custom paths:
python scripts/migrate_hierarchy/transform_hierarchy.py \
    --input output/ingredients_export.json \
    --ai-suggestions output/ai_hierarchy_suggestions.json \
    --output output/transformed_ingredients.json
```

**Output**: `output/transformed_ingredients.json`

The script will report:
- How many new categories were created
- How many ingredients were assigned
- Any ingredients that couldn't be assigned (need manual review)

### Step 4: Validate Hierarchy

Run validation checks before import:

```bash
python scripts/migrate_hierarchy/validate_hierarchy.py

# Or with custom paths and report output:
python scripts/migrate_hierarchy/validate_hierarchy.py \
    --input output/transformed_ingredients.json \
    --output output/validation_report.json
```

**Validation checks**:
- No orphan references (all parents exist)
- Valid hierarchy levels (0, 1, or 2 only)
- No cycles in parent chain
- No duplicate slugs
- Level consistency (child = parent + 1)

**Exit codes**:
- `0`: Validation passed - ready for import
- `1`: Validation failed - fix errors before import
- `2`: File or parsing errors

### Step 5: Human Review

Before importing, review the transformed data:

1. Open `output/transformed_ingredients.json`
2. Check `unassigned_ingredients` section - these need manual assignment
3. Verify category structure makes sense
4. Confirm no important ingredients are missing

### Step 6: Import to Database

Use the existing import services to load the hierarchy. This step uses the application's standard import mechanisms:

```python
# Example import code (run from src/ context)
from src.services import ingredient_hierarchy_service

# The actual import will be handled by Feature 031 import functionality
# See: src/services/ingredient_hierarchy_service.py
```

**Note**: The import service is implemented as part of Feature 031. Ensure WP02-WP04 are complete before running import.

## Troubleshooting

### "Database not found" Error

```bash
# Verify database exists:
ls -la ~/Documents/BakeTracker/bake_tracker.db

# Check with custom path:
python scripts/migrate_hierarchy/export_ingredients.py \
    --db-path /path/to/your/database.db
```

### "Parent not found" Validation Error

The AI suggestions reference a category that doesn't exist:

1. Check `ai_hierarchy_suggestions.json` for typos in category names
2. Ensure every `parent` value matches a `name` in the categories list
3. Re-run the AI prompt with corrections

### "Duplicate slug" Error

Two items have the same slug:

1. Check if the AI created a category with the same name as an existing ingredient
2. Rename one in `ai_hierarchy_suggestions.json`
3. Re-run transform

### Many Unassigned Ingredients

If many ingredients weren't assigned:

1. The AI may have missed some - check the assignments array
2. Add missing assignments manually to `ai_hierarchy_suggestions.json`
3. Re-run transform

## Rollback Plan

If the migration causes issues:

1. **Original data preserved**: The `category` field is retained on all ingredients
2. **Export backup**: Keep `ingredients_export.json` as a backup
3. **Database rollback**: Restore from backup if needed

The hierarchy fields (`parent_ingredient_id`, `hierarchy_level`) can be reset:

```sql
-- Reset hierarchy to flat (all leaves, no parents)
UPDATE ingredients SET parent_ingredient_id = NULL, hierarchy_level = 2;

-- Delete new category ingredients (have is_new_category marker in notes)
DELETE FROM ingredients WHERE notes LIKE '%is_new_category%';
```

## Example Commands

Full migration workflow:

```bash
# 1. Export
python scripts/migrate_hierarchy/export_ingredients.py

# 2. Run AI prompt (manual step - use prompt template)

# 3. Transform
python scripts/migrate_hierarchy/transform_hierarchy.py

# 4. Validate
python scripts/migrate_hierarchy/validate_hierarchy.py

# If validation passes:
echo "Ready for import!"

# If validation fails:
echo "Fix errors in ai_hierarchy_suggestions.json and re-run transform"
```

## File Formats

### ingredients_export.json

```json
{
  "metadata": {
    "export_date": "2025-12-31T12:00:00Z",
    "record_count": 487,
    "source_database": "~/Documents/BakeTracker/bake_tracker.db"
  },
  "ingredients": [
    {
      "id": 1,
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "category": "Flour",
      "is_packaging": false
    }
  ]
}
```

### ai_hierarchy_suggestions.json

```json
{
  "categories": [
    {"name": "Flour & Starches", "slug": "flour_starches", "level": 0, "children": ["White Flour"]},
    {"name": "White Flour", "slug": "white_flour", "level": 1, "parent": "Flour & Starches", "children": []}
  ],
  "assignments": [
    {"ingredient_slug": "all_purpose_flour", "parent_name": "White Flour"}
  ]
}
```

### transformed_ingredients.json

```json
{
  "metadata": {
    "transform_date": "2025-12-31T12:00:00Z",
    "original_count": 487,
    "new_categories_count": 35,
    "transformed_count": 487,
    "unassigned_count": 0
  },
  "new_categories": [
    {
      "slug": "flour_starches",
      "display_name": "Flour & Starches",
      "hierarchy_level": 0,
      "parent_slug": null,
      "is_new_category": true
    }
  ],
  "transformed_ingredients": [
    {
      "id": 1,
      "slug": "all_purpose_flour",
      "display_name": "All-Purpose Flour",
      "hierarchy_level": 2,
      "parent_slug": "white_flour"
    }
  ],
  "unassigned_ingredients": []
}
```

## Support

For issues with these scripts, check:

1. Feature specification: `kitty-specs/031-ingredient-hierarchy-taxonomy/spec.md`
2. Implementation plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
3. Work package: `kitty-specs/031-ingredient-hierarchy-taxonomy/tasks/*/WP07-migration-tooling.md`
