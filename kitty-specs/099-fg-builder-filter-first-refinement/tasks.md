# Work Packages: FG Builder Filter-First Refinement

**Inputs**: Design documents from `kitty-specs/099-fg-builder-filter-first-refinement/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md

**Tests**: Included as validation steps within each WP, not as separate WPs.

**Organization**: 9 subtasks rolled into 2 work packages. WP01 and WP02 can be implemented in parallel (different files).

---

## Work Package WP01: Filter-First Builder Dialog (Priority: P1) MVP

**Goal**: Transform the builder dialog from auto-load-all to blank-start with filter-driven loading. Replace "Bare Items Only" with "Finished Units" / "Existing Assemblies" / "Both". Add search debounce and filter change warnings.
**Independent Test**: Open Create Finished Good dialog, verify it starts blank with filter prompts. Select each filter option, verify correct items load. Change filters with selections, verify warning shown.
**Prompt**: `tasks/WP01-filter-first-builder-dialog.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T001 Remove auto-load from `_set_initial_state()`, add placeholder label in scrollable frame
- [x] T002 Replace CTkSegmentedButton values from `["All", "Bare Items Only"]` to `["Finished Units", "Existing Assemblies", "Both"]`
- [x] T003 Update `_query_food_items()` to map new filter values to correct service calls
- [x] T004 Add 300ms search debounce using `after()` timer pattern
- [x] T005 Add previous filter value tracking (`_prev_food_type`, `_prev_food_category`)
- [ ] T006 Add filter change warning dialog when selections exist, with revert-on-cancel

### Implementation Notes
- Primary file: `src/ui/builders/finished_good_builder.py`
- No service layer changes needed — existing filters are sufficient
- Filter mapping: "Finished Units" → FinishedUnits only; "Existing Assemblies" → FGs where assembly_type=BUNDLE; "Both" → both
- Blank start: remove `_on_food_filter_changed()` call from line 213, add placeholder label
- Debounce: cancel previous `after()` timer on each keystroke, schedule new one at 300ms
- Filter change warning: use `show_confirmation()` (already imported); on cancel, revert to `_prev_*` values

### Parallel Opportunities
- WP02 (edit protection) modifies a different file and can proceed in parallel.

### Dependencies
- None (starting package).

### Risks & Mitigations
- **CTkSegmentedButton with no default selected**: May need to set initial value to empty string or handle no-selection state. Test that segmented button supports deselected state in CustomTkinter.
- **Filter revert on cancel**: Must restore both the variable value AND the widget display. Test that `CTkSegmentedButton` updates when variable changes programmatically.

---

## Work Package WP02: Edit Protection for Atomic FGs (Priority: P2)

**Goal**: Block editing of BARE (atomic) FinishedGoods from the Finished Goods tab. Show informative message directing user to edit the source recipe instead.
**Independent Test**: Select a BARE FG in the list, click Edit, verify block message shown. Select a BUNDLE FG, click Edit, verify builder opens normally. Double-click a BARE FG, verify block message shown.
**Prompt**: `tasks/WP02-edit-protection-atomic-fgs.md`
**Estimated Size**: ~250 lines

### Included Subtasks
- [ ] T007 [P] Add assembly_type guard check in `_edit_finished_good()` before opening builder
- [ ] T008 [P] Add user-facing info message for blocked edit attempts
- [ ] T009 [P] Add same guard check in `_on_row_double_click()` for double-click edit path

### Implementation Notes
- Primary file: `src/ui/finished_goods_tab.py`
- Import `AssemblyType` from `src.models.assembly_type`
- Check `fg.assembly_type == AssemblyType.BARE` after loading the FG via service
- Use existing `show_info()` or `messagebox.showinfo()` for block message
- Message text: "This item is auto-created from a recipe. Edit the recipe to change it."

### Parallel Opportunities
- All subtasks modify the same file but different methods — implement sequentially within this WP.
- Entire WP02 can proceed in parallel with WP01 (different file).

### Dependencies
- None. Independent of WP01 (different file, no shared state).

### Risks & Mitigations
- **FG missing assembly_type**: Should not happen (column has default=BUNDLE), but guard against None with `getattr(fg, 'assembly_type', None)`.
- **Double-click path may not load FG data**: Verify `_on_row_double_click()` has access to the FG's assembly_type (may need to load via service first).

---

## Dependency & Execution Summary

- **Sequence**: WP01 and WP02 can proceed in parallel (different files).
- **Parallelization**: Both WPs are safe to implement concurrently. WP01 modifies `finished_good_builder.py`; WP02 modifies `finished_goods_tab.py`.
- **MVP Scope**: WP01 is the MVP — delivers the core filter-first experience. WP02 adds edit protection polish.

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Remove auto-load, add placeholder | WP01 | P1 | No |
| T002 | Replace filter toggle values | WP01 | P1 | No |
| T003 | Update query logic for new filters | WP01 | P1 | No |
| T004 | Add 300ms search debounce | WP01 | P1 | No |
| T005 | Track previous filter values | WP01 | P1 | No |
| T006 | Add filter change warning | WP01 | P1 | No |
| T007 | Add edit guard in _edit_finished_good() | WP02 | P2 | Yes |
| T008 | Add info message for blocked edits | WP02 | P2 | Yes |
| T009 | Add double-click edit protection | WP02 | P2 | Yes |
