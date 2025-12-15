# Work Packages: Field Naming Consistency Refactor

**Inputs**: Design documents from `/kitty-specs/021-field-naming-consistency/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Scope Note**: Two terminology refactors:
1. Rename `purchase_unit`/`purchase_quantity` to `package_unit`/`package_unit_quantity` (~35 files)
2. Rename remaining `pantry` references to `inventory` in test files (~40+ occurrences in ~5 files)

Note: Model layer (`InventoryItem`) and service layer (`inventory_item_service.py`) are already correctly named. User-facing "Pantry" UI labels are preserved.

**Tests**: Existing test suite must pass after updates; no new tests required.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- All paths relative to repository root.

---

## Work Package WP01: Model Layer Changes (Priority: P0) 🎯 Foundation

**Goal**: Rename database columns and SQLAlchemy attributes in the Product model.
**Independent Test**: `grep -n "package_unit\|package_unit_quantity" src/models/product.py` returns column definitions.
**Prompt**: `tasks/planned/WP01-model-layer-changes.md`

### Included Subtasks
- [ ] T001 Rename `purchase_unit` column to `package_unit` in `src/models/product.py`
- [ ] T002 Rename `purchase_quantity` column to `package_unit_quantity` in `src/models/product.py`
- [ ] T003 Update Product model docstrings and comments to reflect new field names

### Implementation Notes
- This is the foundational change; all other work packages depend on it.
- Column names: `purchase_unit` -> `package_unit`, `purchase_quantity` -> `package_unit_quantity`
- Update docstring at class level and field-level comments.
- Do NOT change any relationships or other fields.

### Parallel Opportunities
- None - single file change, must be done first.

### Dependencies
- None (starting package).

### Risks & Mitigations
- Risk: Database schema mismatch after code change.
- Mitigation: Per Constitution v1.2.0, use export/reset/import cycle (handled in WP06).

---

## Work Package WP02: Service Layer Changes (Priority: P0)

**Goal**: Update all service files that reference the old field names.
**Independent Test**: `grep -rn "purchase_unit\|purchase_quantity" src/services/` returns zero matches.
**Prompt**: `tasks/planned/WP02-service-layer-changes.md`

### Included Subtasks
- [ ] T004 [P] Update `src/services/product_service.py` field references
- [ ] T005 [P] Update `src/services/import_export_service.py` export logic (lines ~233-234, ~1084-1085)
- [ ] T006 [P] Update `src/services/import_export_service.py` import logic (lines ~2298-2299)
- [ ] T007 [P] Update `src/services/recipe_service.py` field references
- [ ] T008 [P] Update `src/services/inventory_item_service.py` field references
- [ ] T009 [P] Update `src/services/finished_unit_service.py` field references
- [ ] T010 [P] Update `src/services/event_service.py` field references
- [ ] T011 [P] Update `src/services/catalog_import_service.py` field references
- [ ] T012 [P] Update `src/services/assembly_service.py` field references

### Implementation Notes
- Use find-and-replace: `purchase_unit` -> `package_unit`, `purchase_quantity` -> `package_unit_quantity`
- Preserve variable naming patterns (e.g., if var was `purchase_unit`, rename to `package_unit`)
- In import_export_service.py, update both the export JSON keys AND import field mappings

### Parallel Opportunities
- All subtasks can proceed in parallel (different files).

### Dependencies
- Depends on WP01 (model must be updated first for imports to resolve).

### Risks & Mitigations
- Risk: Aliasing logic in import/export may need adjustment.
- Mitigation: Verify JSON field names match model attributes exactly.

---

## Work Package WP03: UI Layer Changes (Priority: P1)

**Goal**: Update UI code variable names (not user-facing labels).
**Independent Test**: `grep -rn "purchase_unit\|purchase_quantity" src/ui/` returns zero matches.
**Prompt**: `tasks/planned/WP03-ui-layer-changes.md`

### Included Subtasks
- [ ] T013 [P] Update `src/ui/inventory_tab.py` variable names
- [ ] T014 [P] Update `src/ui/ingredients_tab.py` variable names
- [ ] T015 [P] Update `src/ui/forms/recipe_form.py` field references
- [ ] T016 [P] Update `src/ui/forms/ingredient_form.py` field references
- [ ] T017 [P] Update `src/ui/widgets/data_table.py` field references
- [ ] T018 [P] Update `src/utils/validators.py` field references

### Implementation Notes
- **CRITICAL**: Only rename INTERNAL variable names and field references.
- **DO NOT** change any user-facing string literals (labels, button text, messages).
- User should still see "Pantry" in the UI, not "Inventory".

### Parallel Opportunities
- All subtasks can proceed in parallel (different files).

### Dependencies
- Depends on WP01 (model attributes).

### Risks & Mitigations
- Risk: Accidentally changing user-facing labels.
- Mitigation: Only change variable names that reference the model fields; leave string literals alone.

---

## Work Package WP04: Test Updates (Priority: P1)

**Goal**: Update all test files for both terminology changes:
1. `purchase_unit`/`purchase_quantity` -> `package_unit`/`package_unit_quantity`
2. `pantry` -> `inventory` (function names, variables, docstrings)

**Independent Test**:
- `grep -rn "purchase_unit\|purchase_quantity" src/tests/` returns zero matches
- `grep -rni "pantry" src/tests/` returns only acceptable matches (skip reasons with historical context)

**Prompt**: `tasks/planned/WP04-test-updates.md`

### Included Subtasks

#### Part A: purchase_* -> package_* field references
- [ ] T019 [P] Update `src/tests/conftest.py` test fixtures
- [ ] T020 [P] Update `src/tests/test_models.py`
- [ ] T021 [P] Update `src/tests/test_validators.py`
- [ ] T022 [P] Update `src/tests/test_catalog_import_service.py`
- [ ] T023 [P] Update `src/tests/test_batch_production_service.py`
- [ ] T024 [P] Update `src/tests/test_assembly_service.py`
- [ ] T025 [P] Update `src/tests/services/test_recipe_service.py`
- [ ] T026 [P] Update `src/tests/services/test_production_service.py`
- [ ] T027 [P] Update `src/tests/services/test_product_recommendation_service.py`
- [ ] T028 [P] Update `src/tests/services/test_inventory_item_service.py`
- [ ] T029 [P] Update `src/tests/services/test_ingredient_service.py`
- [ ] T030 [P] Update `src/tests/services/test_event_service_products.py`
- [ ] T031 [P] Update `src/tests/services/test_event_service_packaging.py`
- [ ] T032 [P] Update `src/tests/services/test_composition_service.py`
- [ ] T033 [P] Update `src/tests/integration/test_purchase_flow.py`
- [ ] T034 [P] Update `src/tests/integration/test_packaging_flow.py`
- [ ] T035 [P] Update `src/tests/integration/test_inventory_flow.py`
- [ ] T036 [P] Update `src/tests/integration/test_fifo_scenarios.py`

#### Part B: pantry -> inventory terminology in tests
- [ ] T053 [P] Rename `pantry` -> `inventory` in `src/tests/services/test_recipe_service.py` (~30 occurrences: function names, variables, docstrings)
- [ ] T054 [P] Rename `pantry` -> `inventory` in `src/tests/services/test_production_service.py` (~1 occurrence)
- [ ] T055 [P] Rename `pantry` -> `inventory` in `src/tests/test_validators.py` (skip reason - preserve historical context)
- [ ] T056 [P] Rename `pantry` -> `inventory` in `src/tests/test_services.py` (~6 occurrences in skip reasons - preserve historical context)

### Implementation Notes

**Part A (purchase_* -> package_*):**
- Use find-and-replace across all test files.
- Update fixture data, assertions, and any inline test data dictionaries.
- Tests should validate the same behavior, just with new field names.

**Part B (pantry -> inventory):**
- Rename function names: `test_*_pantry_*` -> `test_*_inventory_*`
- Rename variables: `pantry_state`, `qty_before`/`qty_after` context -> `inventory_*`
- Update docstrings: "Pantry quantities" -> "Inventory quantities"
- **EXCEPTION**: Skip reason strings that explain historical schema changes (e.g., "TD-001: quantity moved to PantryItem") may be preserved as they document history, OR updated to say "moved to InventoryItem (formerly PantryItem)"

### Parallel Opportunities
- All subtasks can proceed in parallel (different files).

### Dependencies
- Depends on WP01 (model), WP02 (services), WP03 (UI) for tests to pass.

### Risks & Mitigations
- Risk: Missed references cause test failures.
- Mitigation: Run `pytest` after updates to catch any remaining issues.
- Risk: Overzealous renaming breaks historical context in skip reasons.
- Mitigation: Review skip reasons carefully; preserve or annotate historical references.

---

## Work Package WP05: Documentation & Sample Data (Priority: P2)

**Goal**: Update import/export specification and all sample JSON files.
**Independent Test**: `grep -rn "purchase_unit\|purchase_quantity" docs/ examples/ test_data/` returns zero matches (excluding archive).
**Prompt**: `tasks/planned/WP05-documentation-and-sample-data.md`

### Included Subtasks
- [ ] T037 Update `docs/design/import_export_specification.md` to v3.4 with changelog entry
- [ ] T038 [P] Update `examples/import/README.md`
- [ ] T039 [P] Update `examples/import/ai_generated_sample.json`
- [ ] T040 [P] Update `examples/import/combined_import.json`
- [ ] T041 [P] Update `examples/import/simple_ingredients.json`
- [ ] T042 [P] Update `examples/import/test_errors.json`
- [ ] T043 [P] Update `examples/test_data.json`
- [ ] T044 [P] Update `examples/test_data_v2.json`
- [ ] T045 [P] Update `examples/test_data_v2_original.json`
- [ ] T046 [P] Update `test_data/sample_catalog.json`
- [ ] T047 [P] Update `test_data/sample_data.json`
- [ ] T048 [P] Update `test_data/README.md`

### Implementation Notes
- **Import/Export Spec**: Bump version from 3.3 to 3.4, add changelog entry documenting field renames.
- **JSON files**: Replace `"purchase_unit"` with `"package_unit"` and `"purchase_quantity"` with `"package_unit_quantity"`.
- **README files**: Update any documentation referencing the old field names.

### Parallel Opportunities
- All JSON file updates (T038-T048) can proceed in parallel.

### Dependencies
- Should align with WP02 (import/export service changes).

### Risks & Mitigations
- Risk: Missed JSON files cause import failures.
- Mitigation: Run grep verification after updates.

---

## Work Package WP06: Verification & Validation (Priority: P2)

**Goal**: Verify all changes are complete and data integrity is preserved.
**Independent Test**: All success criteria from spec.md are met.
**Prompt**: `tasks/planned/WP06-verification-and-validation.md`

### Included Subtasks
- [ ] T049 Run full test suite (`pytest src/tests -v`) and verify 100% pass rate
- [ ] T050 Verify export/import cycle preserves data integrity (per quickstart.md checklist)
- [ ] T051 Verify UI "Pantry" labels are preserved (manual inspection)
- [ ] T052 Run grep validation for zero `purchase_unit`/`purchase_quantity` matches in Python code
- [ ] T057 Run grep validation for `pantry` - verify only acceptable matches remain (UI strings, historical skip reasons)

### Implementation Notes
- Follow the verification checklist in `quickstart.md`.
- Export existing data, delete database, import to fresh database, compare record counts.
- Manually verify "Pantry" appears in UI tabs and forms.
- For T057, acceptable `pantry` matches are:
  - UI string literals like `"My Pantry"`, `"pantry items"` in user-facing messages
  - Skip reason strings explaining historical context (if preserved)
  - Comments in `src/models/inventory_item.py` explaining the rename history

### Parallel Opportunities
- T049 and T052 can run in parallel.
- T050 and T051 require sequential steps.

### Dependencies
- Depends on WP01-WP05 completion.

### Risks & Mitigations
- Risk: Data loss during export/import.
- Mitigation: Keep backup of export file; verify record counts match.

---

## Dependency & Execution Summary

```
WP01 (Model) ─┬─> WP02 (Services) ─┬─> WP04 (Tests) ─┬─> WP06 (Verification)
              │                    │                 │
              └─> WP03 (UI) ───────┴─> WP05 (Docs) ──┘
```

- **Sequence**: WP01 → {WP02, WP03} (parallel) → {WP04, WP05} (parallel) → WP06
- **Parallelization**: WP02/WP03 can proceed in parallel after WP01; WP04/WP05 can proceed in parallel after WP02/WP03.
- **MVP Scope**: WP01 + WP02 + WP04 + WP06 constitute the minimal release (model, services, tests, verification).

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Rename purchase_unit column | WP01 | P0 | No |
| T002 | Rename purchase_quantity column | WP01 | P0 | No |
| T003 | Update Product model docstrings | WP01 | P0 | No |
| T004 | Update product_service.py | WP02 | P0 | Yes |
| T005 | Update import_export_service.py (export) | WP02 | P0 | Yes |
| T006 | Update import_export_service.py (import) | WP02 | P0 | Yes |
| T007 | Update recipe_service.py | WP02 | P0 | Yes |
| T008 | Update inventory_item_service.py | WP02 | P0 | Yes |
| T009 | Update finished_unit_service.py | WP02 | P0 | Yes |
| T010 | Update event_service.py | WP02 | P0 | Yes |
| T011 | Update catalog_import_service.py | WP02 | P0 | Yes |
| T012 | Update assembly_service.py | WP02 | P0 | Yes |
| T013 | Update inventory_tab.py | WP03 | P1 | Yes |
| T014 | Update ingredients_tab.py | WP03 | P1 | Yes |
| T015 | Update recipe_form.py | WP03 | P1 | Yes |
| T016 | Update ingredient_form.py | WP03 | P1 | Yes |
| T017 | Update data_table.py | WP03 | P1 | Yes |
| T018 | Update validators.py | WP03 | P1 | Yes |
| T019 | Update conftest.py | WP04 | P1 | Yes |
| T020 | Update test_models.py | WP04 | P1 | Yes |
| T021 | Update test_validators.py | WP04 | P1 | Yes |
| T022 | Update test_catalog_import_service.py | WP04 | P1 | Yes |
| T023 | Update test_batch_production_service.py | WP04 | P1 | Yes |
| T024 | Update test_assembly_service.py | WP04 | P1 | Yes |
| T025 | Update test_recipe_service.py | WP04 | P1 | Yes |
| T026 | Update test_production_service.py | WP04 | P1 | Yes |
| T027 | Update test_product_recommendation_service.py | WP04 | P1 | Yes |
| T028 | Update test_inventory_item_service.py | WP04 | P1 | Yes |
| T029 | Update test_ingredient_service.py | WP04 | P1 | Yes |
| T030 | Update test_event_service_products.py | WP04 | P1 | Yes |
| T031 | Update test_event_service_packaging.py | WP04 | P1 | Yes |
| T032 | Update test_composition_service.py | WP04 | P1 | Yes |
| T033 | Update test_purchase_flow.py | WP04 | P1 | Yes |
| T034 | Update test_packaging_flow.py | WP04 | P1 | Yes |
| T035 | Update test_inventory_flow.py | WP04 | P1 | Yes |
| T036 | Update test_fifo_scenarios.py | WP04 | P1 | Yes |
| T037 | Update import_export_specification.md | WP05 | P2 | No |
| T038 | Update examples/import/README.md | WP05 | P2 | Yes |
| T039 | Update ai_generated_sample.json | WP05 | P2 | Yes |
| T040 | Update combined_import.json | WP05 | P2 | Yes |
| T041 | Update simple_ingredients.json | WP05 | P2 | Yes |
| T042 | Update test_errors.json | WP05 | P2 | Yes |
| T043 | Update examples/test_data.json | WP05 | P2 | Yes |
| T044 | Update test_data_v2.json | WP05 | P2 | Yes |
| T045 | Update test_data_v2_original.json | WP05 | P2 | Yes |
| T046 | Update sample_catalog.json | WP05 | P2 | Yes |
| T047 | Update sample_data.json | WP05 | P2 | Yes |
| T048 | Update test_data/README.md | WP05 | P2 | Yes |
| T049 | Run full test suite | WP06 | P2 | Yes |
| T050 | Verify export/import cycle | WP06 | P2 | No |
| T051 | Verify UI labels preserved | WP06 | P2 | No |
| T052 | Run grep validation (purchase_*) | WP06 | P2 | Yes |
| T053 | Rename pantry->inventory in test_recipe_service.py | WP04 | P1 | Yes |
| T054 | Rename pantry->inventory in test_production_service.py | WP04 | P1 | Yes |
| T055 | Rename pantry->inventory in test_validators.py | WP04 | P1 | Yes |
| T056 | Rename pantry->inventory in test_services.py | WP04 | P1 | Yes |
| T057 | Run grep validation (pantry) | WP06 | P2 | Yes |
