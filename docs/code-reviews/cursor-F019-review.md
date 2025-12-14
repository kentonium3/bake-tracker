## Code Review: Feature 019 — Unit Conversion Simplification

**Worktree reviewed**: `/Users/kentgale/Vaults-repos/bake-tracker/.worktrees/019-unit-conversion-simplification/`

### Feature intent (from prompt)
Feature 019 removes the `UnitConversion` model and removes `Ingredient.recipe_unit`, replacing it with a **4-field density model** on `Ingredient`.

Key expectations:
- `consume_fifo()` accepts an explicit `target_unit` (recipe unit comes from `RecipeIngredient.unit`, not `Ingredient.recipe_unit`).
- Import/Export format is updated to **v3.3** and **v3.2 is rejected**.

---

## Follow-up review (post-fix rerun)

Claude Code reported fixes were applied; I reran the checks and tests.

**Current status**: **APPROVE (with minor concerns)**.

- **Tests**: `pytest -q src/tests` from the Feature 019 worktree root now reports **706 passed, 12 skipped**.
- **Import/export**: `import_all_from_json_v3()` now accepts both `name` and `display_name` for ingredient display names and includes implementations for **inventory_items** and **purchases** (no longer a placeholder).
- **Previously reported failures**: The earlier `sample_data.json` version failures were caused by running tests from the wrong working directory (tests reference `test_data/sample_data.json` as a relative path). Running from the worktree root uses the correct fixture and passes.

### Remaining issues / minor concerns

- **Stale docstrings/comments**: Several places still mention “ingredient recipe_unit” even though the concept is removed (e.g., `src/models/recipe.py` docstring, a TODO in `src/models/inventory_item.py`). These are low-risk but misleading.
- **Legacy conversion-factor utilities still present**: `src/services/unit_converter.py` still contains conversion-factor helpers (`convert_to_recipe_units`, `validate_conversion_factor`, etc.) and top-of-file commentary mentioning conversion_factor. This is not currently breaking (tests pass) but is confusing given the new density-based design; consider removing or clearly labeling as legacy/compat-only.
- **Inventory snapshot naming**: `SnapshotIngredient.to_dict()` still emits `recipe_unit_quantity`, but it now returns raw quantity with a deprecation note. Consider renaming the field (or adding a new field) if this is user-facing.
- **Warnings**: The suite still emits many `datetime.utcnow()` deprecation warnings (Python 3.13) and a `Query.get()` legacy warning from SQLAlchemy. Not a Feature 019 blocker, but worth tracking as tech debt.

---

## 1) Executive Summary: **REJECT**

The direction is correct (density-based conversion and explicit `target_unit`), but the implementation is **not merge-ready**:

- There are **many remaining code paths** that still assume removed concepts (`recipe_unit`, `conversion_factor`, old `Ingredient` fields/methods).
- `import_all_from_json_v3()` appears **incomplete** for full restores (purchases/inventory items are marked as “handled similarly” but not implemented).
- There is an **export/import mismatch** for ingredient keys (`name` vs `display_name`).
- The worktree **test suite fails** (`5 failed, 701 passed, 12 skipped`).

---

## 2) Critical Issues (must fix)

### 2.1 Live code still depends on removed fields/methods (high risk of runtime breaks)

Even though the model is updated, multiple models/services/UI modules still reference `recipe_unit` semantics and/or old ingredient APIs that no longer exist on the new `Ingredient` model.

Examples:

- **Inventory snapshot model calls removed Ingredient APIs**
  - File: `src/models/inventory_snapshot.py`
  - `SnapshotIngredient.calculate_value()` uses `self.ingredient.unit_cost` (no longer on new `Ingredient`).
  - `SnapshotIngredient.get_recipe_unit_quantity()` calls `self.ingredient.convert_to_recipe_units(...)` (not present on new `Ingredient`).

- **Recipe UI form assumes old Ingredient API and mismatched field names**
  - File: `src/ui/forms/recipe_form.py`
  - Docstring still says unit can default to ingredient’s `recipe_unit`.
  - Uses `ingredient.purchase_unit` (purchase unit belongs to `Product`, not `Ingredient`).
  - Uses `ingredient.has_density_data()` (not present on new `Ingredient`).
  - Compares `ing.name` to selected display text; new model uses `display_name`.

- **Sample/demo constants still contain removed fields**
  - File: `src/utils/constants.py`
  - `SAMPLE_INGREDIENTS` includes `recipe_unit` and `conversion_factor`.

These indicate Feature 019 is only partially applied and will cause UI/model runtime errors.

### 2.2 Import implementation is incomplete for v3.3 full restore

- File: `src/services/import_export_service.py`
- In `import_all_from_json_v3()`, there is an explicit placeholder:
  - `# 4-5. Purchases and inventory_items handled similarly...`
  - `# (Simplified for brevity - would add full implementation)`

Given the project’s “development round-trip” workflow (export full DB → reset DB → import), this is a blocking regression if purchases/inventory items are not fully restored.

### 2.3 Export/import mismatch for ingredient name field

- File: `src/services/import_export_service.py`
- Export uses:
  - `{"name": ingredient.display_name, ...}`
- Import constructs Ingredient using:
  - `display_name=ing.get("display_name")`

This means a correctly exported v3.3 file will import ingredients with `display_name=None`.

### 2.4 Test suite failing in the worktree

Command run:
- `pytest -q /.../.worktrees/019-unit-conversion-simplification/src/tests`

Result:
- **5 failed, 701 passed, 12 skipped**

Failures:
- `src/tests/services/test_health_service.py`
  - thread does not stop within timeout
  - expected `health.json` not created
- `src/tests/services/test_import_export_service.py`
  - sample data file `test_data/sample_data.json` is still **v3.2**, but tests now assert **v3.3**.

Even if the health service failures are pre-existing, they currently fail in this worktree and must be addressed or isolated.

---

## 3) Data integrity & backward compatibility

### 3.1 v3.2 rejection appears intentional and documented

- File: `src/services/import_export_service.py`
- v3.3-only check exists and raises `ImportVersionError` with a user-friendly message.
- File: `docs/design/import_export_specification.md`
  - Explicitly states v3.3 only; older versions unsupported.

### 3.2 Sample data conversion not yet done

`test_data/sample_data.json` in this worktree is still `"version": "3.2"`, and tests expect `"3.3"`.

Prompt note aligns with this: the `baking_ingredients_v32.json` conversion needs to happen at merge time, but **tests demonstrate the worktree still depends on v3.2 sample fixtures**, so conversion needs to happen earlier (or tests updated to point at a converted fixture).

---

## 4) Correctness review: FIFO + density conversions

### 4.1 `consume_fifo()` conversion behavior is directionally correct

- File: `src/services/inventory_item_service.py`
- Signature: `consume_fifo(ingredient_slug, quantity_needed, target_unit, dry_run=False, session=None)`
- Converts lot quantities from `purchase_unit` → `target_unit`, consumes, then converts back `target_unit` → `purchase_unit` for deduction.
- Uses `convert_any_units(..., ingredient=ingredient)` so density is available for volume↔weight conversion.

### 4.2 Error handling is semantically off

`consume_fifo()` raises `ValueError` for unit conversion failure (e.g., missing density), and then wraps everything as `DatabaseError`.

Missing density is a validation/user-data issue rather than a database failure; this will make UI errors harder to interpret.

---

## 5) Test coverage observations

Positive:
- `src/tests/integration/test_fifo_scenarios.py` explicitly tests cross-type conversions using density fields.
- Recipe costing tests call `consume_fifo(..., recipe_unit, dry_run=True)` (with recipe_unit == `RecipeIngredient.unit`), which aligns with the new signature.
- Import/export tests include v3.3 version validation and density field import/export coverage.

Gaps / issues:
- Import/export tests reveal schema key mismatches (`name` vs `display_name`) and reliance on v3.2 fixtures.

---

## 6) Questions / Clarifications

1. **UI validation**: Since purchase unit is per-product (and there may be multiple products), what should recipe form validation compare against? Preferred product’s purchase unit? Or defer to costing/consumption time?
2. **InventorySnapshot**: What replaces `recipe_unit_quantity` now that there is no per-ingredient recipe unit?
3. **Import completeness**: Is v3.3 import expected to fully restore purchases + inventory items? If yes, the placeholder import code must be implemented before merge.

---

## 7) Positive observations

- `src/models/ingredient.py` cleanly introduces the 4-field density model and provides `get_density_g_per_ml()` + `format_density_display()` helpers.
- `src/services/unit_converter.py` has a clear separation between standard conversions and density-based cross-type conversions.
- v3.3 format is documented in `docs/design/import_export_specification.md` and the code includes explicit version rejection.

---

## 8) Suggested next steps (actionable)

- [ ] Fix v3.3 import ingredient key mismatch (`name` vs `display_name`) and ensure exporter/importer agree
- [ ] Implement purchases + inventory_items import in `import_all_from_json_v3()` (remove placeholder)
- [ ] Convert `test_data/sample_data.json` to v3.3 in the worktree (or update tests/fixtures accordingly)
- [ ] Sweep and update remaining references to removed concepts:
  - `InventorySnapshot` “recipe unit quantity” logic
  - recipe form density validation logic (remove `purchase_unit`/`has_density_data` assumptions)
  - any remaining legacy conversion-factor utilities and docs
- [ ] Re-run full test suite and ensure Feature 019 doesn’t introduce new unrelated failures
