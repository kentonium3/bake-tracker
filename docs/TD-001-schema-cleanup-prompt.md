# TD-001: Schema Cleanup Execution Prompt

**Purpose:** Direct Claude Code to execute the TD-001 schema cleanup refactoring.

**Context:** This refactoring was partially started but interrupted in Claude Desktop. The codebase may be in an inconsistent state. Assess before proceeding.

**Reference:** See `docs/feature_roadmap.md` section "TD-001: Schema Cleanup" for original specification.

---

## Phase 0: Assess Current State (REQUIRED FIRST)

Before making any changes, assess the state from the interrupted refactoring:

```bash
# Check git status for uncommitted changes
git status

# Check for syntax errors in modified files
find src -name "*.py" -exec python -m py_compile {} \; 2>&1 | head -20

# Check if app can start (will reveal import errors)
./venv/bin/python -c "from src.models import *; print('Models OK')"
./venv/bin/python -c "from src.services import *; print('Services OK')"
```

**Decision point:**
- If changes are minimal/broken → `git checkout .` to reset, then proceed
- If changes are extensive and partially working → assess what's done, continue
- Report findings to user before proceeding with destructive changes

---

## Phase 1: Data Export (Safety Net)

Before any schema changes, export current data:

```bash
./venv/bin/python -m src.utils.import_export_cli export td001_backup.json
```

Verify the export succeeded and contains data before proceeding.

---

## Phase 2: Part A - Table and Model Renaming

### Goal

| Current | Target | Represents |
|---------|--------|------------|
| `Variant` model / `variants` table | `Product` model / `products` table | Brand/package specifics |
| `ingredient_new_id` in RecipeIngredient | `ingredient_id` | Single FK to Ingredient |

The `Ingredient` model / `ingredients` table remains unchanged (it's the generic concept).

### Tasks

**A1: Rename Variant → Product**
- Rename file: `src/models/variant.py` → `src/models/product.py`
- Rename class: `Variant` → `Product`
- Update `__tablename__` to `"products"`
- Note: Table is already `variants` in DB, but we're deleting DB anyway

**A2: Update All References to Variant**
- `src/models/__init__.py`: imports and __all__
- All relationship declarations referencing Variant
- `Ingredient.variants` → `Ingredient.products`
- Any `variant_id` FK columns → `product_id`

**A3: Update Services**
- Search all services for `Variant` imports and references
- Update `import_export_service.py`: 
  - JSON key `variants` → `products`
  - All Variant class references → Product

**A4: Update UI**
- Search all UI files for Variant references
- Update any user-visible labels if they mention "variant"

**A5: Fix RecipeIngredient Dual FK**
- In `src/models/recipe.py`:
  - Remove `ingredient_id` column (legacy)
  - Rename `ingredient_new_id` → `ingredient_id`
  - Update relationship declaration
- Search entire codebase for `ingredient_new_id` or `ingredient_new` and update

**A6: Update sample_data.json**
- Change `"variants":` array key to `"products":`

---

## Phase 3: Part B - Attribute Naming Consistency

### Goal

Models with `slug` use `display_name`. Models without `slug` use `name`.

### Tasks

**B1: Rename Ingredient.name → Ingredient.display_name**
- In `src/models/ingredient.py`: rename field
- Search codebase for `ingredient.name` and update to `ingredient.display_name`
- Update import_export_service.py mappings
- Update sample_data.json: `"name":` → `"display_name":` in ingredients array

**B2: Verify Product (was Variant) field naming**
- Check if it has `slug` - if yes, should use `display_name`
- Apply same pattern if needed

---

## Phase 4: Database Recreation

After all code changes:

```bash
# Delete existing database
rm ~/Documents/BakeTracker/bake_tracker.db

# Start app to recreate tables (or run a quick import)
./venv/bin/python -c "from src.services.database import init_db; init_db()"

# Reimport data (will need updated sample_data.json)
./venv/bin/python -m src.utils.import_export_cli import td001_backup.json
```

---

## Phase 5: Verification

```bash
# Run tests
./venv/bin/pytest src/tests/ -v

# Verify app starts
./venv/bin/python -m src.main &
# Test basic operations manually, then close

# If all good, commit
git add -A
git commit -m "refactor(TD-001): Schema cleanup - Variant→Product, fix dual FK, naming consistency

- Renamed Variant model to Product (variants table → products)
- Fixed RecipeIngredient dual FK (removed legacy ingredient_id, renamed ingredient_new_id)
- Renamed Ingredient.name to Ingredient.display_name for consistency
- Updated all services, UI, and import/export mappings
- Updated sample_data.json format"

git push
```

---

## Important Notes

1. **Do NOT start Phase 2 until Phase 0 assessment is complete and reported**
2. **Do NOT delete database until all code changes compile cleanly**
3. **Test incrementally** - verify imports work after each major change
4. Use `git diff` to review changes before committing
5. If something breaks badly, `git checkout .` and reassess

---

## Files Likely to Change

```
src/models/
  - variant.py → product.py
  - ingredient.py (display_name)
  - recipe.py (FK cleanup)
  - __init__.py

src/services/
  - import_export_service.py (major changes)
  - ingredient_service.py
  - Any service referencing Variant

src/ui/
  - Any UI referencing Variant
  - Forms using ingredient.name

examples/
  - sample_data.json (field renames)
```
