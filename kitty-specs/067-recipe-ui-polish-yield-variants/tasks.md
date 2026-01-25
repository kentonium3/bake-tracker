# Work Packages: Recipe UI Polish - Yield Information and Variant Grouping

**Inputs**: Design documents from `kitty-specs/067-recipe-ui-polish-yield-variants/`
**Prerequisites**: plan.md, spec.md, research.md

**Tests**: Manual UI verification only (no automated tests required for UI polish).

**Organization**: 12 subtasks (`T001`-`T012`) roll up into 4 work packages (`WP01`-`WP04`). Each work package is independently deliverable and targets a single UI component.

**Parallel Execution Strategy**: WP01, WP02, WP03 are fully independent and can execute in parallel. WP04 depends on WP02 pattern but can start once WP02 pattern is established.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- All subtasks in this feature are UI-layer only in `src/ui/`.

---

## Work Package WP01: Edit Recipe Yield Section Polish (Priority: P1)

**Goal**: Add column labels and improve help text in Edit Recipe dialog yield section.
**Independent Test**: Open Edit Recipe dialog, verify column labels visible and help text updated.
**Prompt**: `tasks/WP01-recipe-yield-labels.md`
**Estimated Size**: ~250 lines (3 subtasks)

### Included Subtasks
- [x] T001 [P] Add column labels row above yield inputs in `src/ui/forms/recipe_form.py`
- [x] T002 [P] Update help text to spec wording in `src/ui/forms/recipe_form.py`
- [x] T003 [P] Reduce vertical spacing after section title in `src/ui/forms/recipe_form.py`

### Implementation Notes
- All changes in `_create_yield_section()` method (around line 730-798)
- Column labels: "Finished Unit Name" | "Unit" | "Qty/Batch"
- Help text: "Each row defines a Finished Unit and quantity per batch for this recipe."
- Use `ctk.CTkLabel` with grid layout matching existing YieldTypeRow columns

### Parallel Opportunities
- All 3 subtasks modify the same file section but can be done in sequence within one session.
- **WP01 is fully independent** - can run in parallel with WP02, WP03.

### Dependencies
- None (starting package).

### Risks & Mitigations
- Column alignment may need adjustment; test with multiple yield rows.

---

## Work Package WP02: Recipe Catalog Variant Grouping (Priority: P1)

**Goal**: Display variant recipes indented under their base recipe with "↳" indicator.
**Independent Test**: View Recipe Catalog with base+variant recipes, verify variants grouped with indicator.
**Prompt**: `tasks/WP02-recipe-catalog-grouping.md`
**Estimated Size**: ~300 lines (3 subtasks)

### Included Subtasks
- [x] T004 [P] Implement variant-aware sorting in `src/ui/widgets/data_table.py` RecipeDataTable
- [x] T005 [P] Add "↳ " prefix to variant names in `_get_row_values()` method
- [x] T010 [P] Set production_ready=True default in `src/ui/forms/recipe_form.py`

### Implementation Notes
- Sorting: Base recipes alphabetically, variants grouped under their base (also alphabetical)
- Detect variants via `row_data.base_recipe_id` (truthy = variant)
- T010 included here as it's in the same form file and small scope

### Parallel Opportunities
- All subtasks target different methods/locations.
- **WP02 is fully independent** - can run in parallel with WP01, WP03.

### Dependencies
- None.

### Risks & Mitigations
- Sorting may require access to base recipe name for proper grouping; may need to join data.
- Unicode "↳" should render correctly per spec assumptions.

---

## Work Package WP03: Create Variant Dialog Polish (Priority: P2)

**Goal**: Clean up Create Variant dialog layout and terminology.
**Independent Test**: Open Create Variant dialog, verify section title, no "Base:" labels, proper layout.
**Prompt**: `tasks/WP03-variant-dialog-polish.md`
**Estimated Size**: ~350 lines (4 subtasks)

### Included Subtasks
- [x] T006 [P] Change section header from "Variant Yields:" to "Finished Unit Name(s):" in `src/ui/forms/variant_creation_dialog.py`
- [x] T007 [P] Remove "Base:" label prefix from FU row labels
- [x] T008 [P] Left-justify input fields in FU section
- [x] T009 [P] Restructure variant name section layout (label above field, help text between)

### Implementation Notes
- Section header at line 143: change text string
- FU row labels at line 213: remove "Base: " prefix
- Layout changes in `_create_variant_name_section()` and `_create_fu_row()` methods
- Follow CustomTkinter best practices for label-above-field pattern

### Parallel Opportunities
- All subtasks modify the same file but different sections.
- **WP03 is fully independent** - can run in parallel with WP01, WP02.

### Dependencies
- None.

### Risks & Mitigations
- Layout restructuring may affect dialog sizing; test with various FU counts.

---

## Work Package WP04: Finished Units Grid Grouping (Priority: P3)

**Goal**: Display variant finished units indented under their base finished unit with "↳" indicator.
**Independent Test**: View Finished Units grid with base+variant FUs, verify variants grouped with indicator.
**Prompt**: `tasks/WP04-finished-units-grouping.md`
**Estimated Size**: ~280 lines (2 subtasks)

### Included Subtasks
- [x] T011 [P] Implement variant-aware sorting in `src/ui/widgets/data_table.py` FinishedGoodDataTable
- [x] T012 [P] Add "↳ " indicator for variant-sourced finished units in `_get_row_values()`

### Implementation Notes
- Mirror the pattern established in WP02 for RecipeDataTable
- Variant relationship determined via `row_data.recipe.base_recipe_id`
- Sort by base recipe name, then group variants under their base

### Parallel Opportunities
- Can start once WP02 pattern is established (copy approach).
- Subtasks target different methods in same class.

### Dependencies
- Depends on WP02 (pattern reuse, but can start in parallel if agent reads WP02 approach first).

### Risks & Mitigations
- May need to eager-load recipe relationship to access base_recipe_id.

---

## Dependency & Execution Summary

- **Sequence**: WP01, WP02, WP03 can all start immediately (no dependencies).
- **WP04**: Technically depends on WP02 pattern, but can start in parallel.
- **Parallelization**: **All 4 WPs can run in parallel** for maximum Codex utilization.
- **MVP Scope**: WP01 + WP02 (P1 priorities) constitute minimal release.

### Parallel Execution Plan (Codex)

```
Time 0: Start WP01, WP02, WP03, WP04 in parallel (4 Codex instances)
        └── WP01: recipe_form.py yield section
        └── WP02: data_table.py RecipeDataTable + recipe_form.py default
        └── WP03: variant_creation_dialog.py
        └── WP04: data_table.py FinishedGoodDataTable

Time N: All complete, merge branches
```

**File Conflict Analysis**:
- `recipe_form.py`: WP01 (yield section) and WP02 (production_ready default) - different sections, may need merge
- `data_table.py`: WP02 (RecipeDataTable) and WP04 (FinishedGoodDataTable) - different classes, safe
- `variant_creation_dialog.py`: WP03 only - no conflict

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add column labels to yield section | WP01 | P1 | Yes |
| T002 | Update yield help text | WP01 | P1 | Yes |
| T003 | Reduce yield section spacing | WP01 | P1 | Yes |
| T004 | Recipe catalog variant sorting | WP02 | P1 | Yes |
| T005 | Add "↳" prefix to variant names | WP02 | P1 | Yes |
| T006 | Change "Variant Yields" to "Finished Unit Name(s)" | WP03 | P2 | Yes |
| T007 | Remove "Base:" label prefix | WP03 | P2 | Yes |
| T008 | Left-justify FU input fields | WP03 | P2 | Yes |
| T009 | Restructure variant name section | WP03 | P2 | Yes |
| T010 | Default production_ready=True | WP02 | P2 | Yes |
| T011 | Finished units variant sorting | WP04 | P3 | Yes |
| T012 | Add "↳" indicator for variant FUs | WP04 | P3 | Yes |
