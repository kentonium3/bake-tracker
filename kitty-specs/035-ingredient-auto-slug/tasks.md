# Work Packages: Ingredient Auto-Slug & Deletion Protection

**Feature**: 035-ingredient-auto-slug
**Inputs**: Design documents from `/kitty-specs/035-ingredient-auto-slug/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: Included as WP05 per constitution requirement (>70% service layer coverage).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package must be independently deliverable and testable.

**Parallelization Strategy**: WP01 and WP02 can run in parallel. WP03 can run in parallel with WP04. WP05 tests can be parallelized across multiple agents.

## Subtask Format: `[Txxx] [P?] Description`
- **[P]** indicates the subtask can proceed in parallel (different files/components).
- Include precise file paths or modules.

---

## Work Package WP01: Schema & Denormalization Fields (Priority: P0)

**Goal**: Add three denormalization fields to SnapshotIngredient model and update FK constraint to allow nullification.
**Independent Test**: Model changes compile, database schema recreates successfully with new fields.
**Prompt**: `tasks/planned/WP01-schema-denormalization-fields.md`
**Assignee**: Claude or Gemini

### Included Subtasks
- [x] T001 Add `ingredient_name_snapshot` column (String(200), nullable) to SnapshotIngredient in `src/models/inventory_snapshot.py`
- [x] T002 Add `parent_l1_name_snapshot` column (String(200), nullable) to SnapshotIngredient
- [x] T003 Add `parent_l0_name_snapshot` column (String(200), nullable) to SnapshotIngredient
- [x] T004 Change `ingredient_id` FK from `ondelete="RESTRICT"` to `ondelete="SET NULL"`
- [x] T005 Make `ingredient_id` column nullable (`nullable=True`)
- [x] T006 Update `to_dict()` method to include new snapshot fields

### Implementation Notes
1. Edit `src/models/inventory_snapshot.py`
2. Add three new Column definitions after `quantity`
3. Modify the `ingredient_id` FK constraint
4. Per constitution: schema auto-recreates, no migration scripts needed

### Parallel Opportunities
- All subtasks in same file - sequential within this WP
- This WP can run in parallel with WP02 (different files)

### Dependencies
- None (starting package)

### Risks & Mitigations
- Schema change breaks existing data: Use export/reset/import per constitution
- New fields break import: Update import/export service if needed (FR-011)

---

## Work Package WP02: Verify Cascade Delete Configuration (Priority: P0)

**Goal**: Verify and configure cascade delete for IngredientAlias and IngredientCrosswalk models.
**Independent Test**: Delete an ingredient with aliases/crosswalks - they should auto-delete.
**Prompt**: `tasks/planned/WP02-cascade-delete-config.md`
**Assignee**: Gemini (parallel with WP01)

### Included Subtasks
- [x] T007 [P] Verify IngredientAlias FK has `ondelete="CASCADE"` in `src/models/ingredient_alias.py`
- [x] T008 [P] Verify IngredientCrosswalk FK has `ondelete="CASCADE"` in `src/models/ingredient_crosswalk.py`
- [x] T009 [P] Add cascade config if missing to either model
- [x] T010 Document findings in research.md (update if changes needed)

### Implementation Notes
1. Read `src/models/ingredient_alias.py` - check `ingredient_id` FK definition
2. Read `src/models/ingredient_crosswalk.py` - check `ingredient_id` FK definition
3. If `ondelete="CASCADE"` is missing, add it
4. No changes if already configured correctly

### Parallel Opportunities
- T007 and T008 can be verified in parallel (different files)
- WP02 can run entirely in parallel with WP01

### Dependencies
- None (can start immediately)

### Risks & Mitigations
- Cascade misconfigured: Explicit verification before relying on it

---

## Work Package WP03: Deletion Protection Service (Priority: P1) - MVP Core

**Goal**: Implement comprehensive deletion protection with validation and denormalization.
**Independent Test**: Call `can_delete_ingredient()` with various scenarios, verify correct blocking behavior.
**Prompt**: `tasks/planned/WP03-deletion-protection-service.md`
**Assignee**: Claude (main implementation)

### Included Subtasks
- [x] T011 Implement `can_delete_ingredient(ingredient_id, session=None)` in `src/services/ingredient_service.py`
  - Check Product count (block if > 0)
  - Check RecipeIngredient count (block if > 0)
  - Check child ingredient count (use existing `get_child_count`)
  - Return tuple: (can_delete: bool, reason: str, details: dict)
- [x] T012 Implement `_denormalize_snapshot_ingredients(ingredient_id, session)` helper
  - Query all SnapshotIngredient records for this ingredient
  - Copy display_name to `ingredient_name_snapshot`
  - Copy parent L1 name to `parent_l1_name_snapshot` (use `get_ancestors`)
  - Copy parent L0 name to `parent_l0_name_snapshot`
  - Set `ingredient_id` to NULL
  - Return count of records updated
- [x] T013 Implement `delete_ingredient_safe(ingredient_id, session=None)` function
  - Call `can_delete_ingredient()` first
  - If blocked, raise `IngredientInUse` with details
  - Call `_denormalize_snapshot_ingredients()`
  - Delete ingredient (cascades Alias/Crosswalk via DB)
  - Use atomic transaction
- [x] T014 Add imports for Product, RecipeIngredient, SnapshotIngredient models
- [x] T015 Follow session management pattern (accept optional session parameter)

### Implementation Notes
1. Follow existing patterns in `ingredient_service.py`
2. Use `session_scope()` when session not provided
3. Leverage existing `get_child_count()` and `get_ancestors()` from F033
4. Error messages must include counts per FR-007, FR-008, FR-009

### Parallel Opportunities
- This WP should be done by one agent (Claude) - internal dependencies
- Can run in parallel with WP04 (different functions in same file)

### Dependencies
- Depends on WP01 (schema fields must exist for denormalization)
- Depends on WP02 (cascade delete must be verified)

### Risks & Mitigations
- Transaction failure mid-delete: Use atomic transaction, rollback on error (FR-014)
- Session detachment: Follow session management patterns in CLAUDE.md

---

## Work Package WP04: Slug Field Mapping Fix (Priority: P1)

**Goal**: Fix field name mapping so UI "name" field maps to service "display_name".
**Independent Test**: Create ingredient via UI with just "name" field - slug auto-generates correctly.
**Prompt**: `tasks/planned/WP04-slug-field-mapping.md`
**Assignee**: Gemini (parallel with WP03)

### Included Subtasks
- [x] T016 [P] Add field normalization at start of `create_ingredient()` in `src/services/ingredient_service.py`:
  ```python
  # Normalize field names for backward compatibility
  if "name" in ingredient_data and "display_name" not in ingredient_data:
      ingredient_data["display_name"] = ingredient_data["name"]
  ```
- [x] T017 [P] Verify existing `create_slug()` call uses `display_name` correctly
- [x] T018 [P] Test that slug generation works with both "name" and "display_name" inputs

### Implementation Notes
1. Add normalization BEFORE validation call
2. This ensures backward compatibility - both field names work
3. Existing slug generation already works per research findings

### Parallel Opportunities
- WP04 can run entirely in parallel with WP03 (different section of same file)
- Minimal code change, good candidate for Gemini

### Dependencies
- None (independent of WP01-WP03)

### Risks & Mitigations
- Breaking existing callers: Normalization is additive, doesn't remove "display_name" support

---

## Work Package WP05: UI Delete Handler Integration (Priority: P2)

**Goal**: Update UI to use new deletion protection service and display detailed error messages.
**Independent Test**: Attempt delete via UI - see proper blocking messages with counts.
**Prompt**: `tasks/planned/WP05-ui-delete-integration.md`
**Assignee**: Claude (after WP03)

### Included Subtasks
- [x] T019 Update `_delete()` method in `src/ui/ingredients_tab.py` IngredientFormDialog class
- [x] T020 Import `delete_ingredient_safe` from ingredient_service
- [x] T021 Call `delete_ingredient_safe()` instead of current deletion
- [x] T022 Handle `IngredientInUse` exception with detailed message showing counts
- [x] T023 Display user-friendly error with counts: "Cannot delete: X products, Y recipes reference this ingredient"

### Implementation Notes
1. Find `_delete()` method in IngredientFormDialog class (~line 1370)
2. Replace call to `ingredient_service.delete_ingredient(slug)` with new safe version
3. Exception handling should extract counts from IngredientInUse
4. Message format per FR-009: clear action user must take

### Parallel Opportunities
- None within this WP
- Must wait for WP03 (needs the service function)

### Dependencies
- Depends on WP03 (delete_ingredient_safe must exist)

### Risks & Mitigations
- UI error handling: Ensure all exception types are caught gracefully

---

## Work Package WP06: Deletion & Slug Tests (Priority: P2)

**Goal**: Comprehensive test coverage for deletion protection and slug generation.
**Independent Test**: All new tests pass, existing tests still pass.
**Prompt**: `tasks/planned/WP06-deletion-slug-tests.md`
**Assignee**: Gemini (parallel test writing)

### Included Subtasks
- [x] T024 [P] Test `test_delete_blocked_by_products` in `src/tests/services/test_ingredient_service.py`
- [x] T025 [P] Test `test_delete_blocked_by_recipes` - verify RecipeIngredient blocks deletion
- [x] T026 [P] Test `test_delete_blocked_by_children` - verify child ingredients block deletion
- [x] T027 Test `test_delete_with_snapshots_denormalizes` - verify snapshot fields populated
- [x] T028 [P] Test `test_delete_cascades_aliases` - verify IngredientAlias deleted
- [x] T029 [P] Test `test_delete_cascades_crosswalks` - verify IngredientCrosswalk deleted
- [x] T030 [P] Test `test_slug_auto_generation` - verify slug from display_name
- [x] T031 [P] Test `test_slug_conflict_resolution` - verify _1, _2 suffix handling
- [x] T032 [P] Test `test_field_name_normalization` - verify "name" maps to "display_name"

### Implementation Notes
1. Follow existing test patterns in `test_ingredient_service.py`
2. Use fixtures for creating test ingredients, products, recipes
3. Tests can be written in parallel by different agents

### Parallel Opportunities
- Most tests are independent - T024-T031 can be written in parallel
- Good opportunity for multiple Gemini instances or parallel agent work

### Dependencies
- Depends on WP01-WP05 (all functionality must be implemented)

### Risks & Mitigations
- Test fixtures: Ensure proper setup/teardown to avoid test pollution

---

## Dependency & Execution Summary

```
WP01 (Schema) ──────┬──────> WP03 (Deletion Service) ──> WP05 (UI) ──┐
                    │                                                 │
WP02 (Cascade) ─────┘        WP04 (Slug Fix) ──────────────────────>├──> WP06 (Tests)
     [parallel]                   [parallel with WP03]               │
```

**Parallel Execution Plan**:
1. **Wave 1**: WP01 (Claude) + WP02 (Gemini) - run in parallel
2. **Wave 2**: WP03 (Claude) + WP04 (Gemini) - run in parallel after Wave 1
3. **Wave 3**: WP05 (Claude) - after WP03
4. **Wave 4**: WP06 (Gemini) - after all implementation complete

**MVP Scope**: WP01 + WP02 + WP03 + WP04 (deletion protection + slug fix)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Add ingredient_name_snapshot column | WP01 | P0 | No |
| T002 | Add parent_l1_name_snapshot column | WP01 | P0 | No |
| T003 | Add parent_l0_name_snapshot column | WP01 | P0 | No |
| T004 | Change FK to SET NULL | WP01 | P0 | No |
| T005 | Make ingredient_id nullable | WP01 | P0 | No |
| T006 | Update to_dict() method | WP01 | P0 | No |
| T007 | Verify IngredientAlias cascade | WP02 | P0 | Yes |
| T008 | Verify IngredientCrosswalk cascade | WP02 | P0 | Yes |
| T009 | Add cascade config if missing | WP02 | P0 | Yes |
| T010 | Document findings | WP02 | P0 | Yes |
| T011 | Implement can_delete_ingredient() | WP03 | P1 | No |
| T012 | Implement _denormalize_snapshot_ingredients() | WP03 | P1 | No |
| T013 | Implement delete_ingredient_safe() | WP03 | P1 | No |
| T014 | Add model imports | WP03 | P1 | No |
| T015 | Follow session management pattern | WP03 | P1 | No |
| T016 | Add field normalization | WP04 | P1 | Yes |
| T017 | Verify create_slug usage | WP04 | P1 | Yes |
| T018 | Test both field name inputs | WP04 | P1 | Yes |
| T019 | Update _delete() method | WP05 | P2 | No |
| T020 | Import delete_ingredient_safe | WP05 | P2 | No |
| T021 | Call new safe deletion | WP05 | P2 | No |
| T022 | Handle IngredientInUse exception | WP05 | P2 | No |
| T023 | Display user-friendly error | WP05 | P2 | No |
| T024 | Test blocked by products | WP06 | P2 | Yes |
| T025 | Test blocked by recipes | WP06 | P2 | Yes |
| T026 | Test blocked by children | WP06 | P2 | Yes |
| T027 | Test snapshot denormalization | WP06 | P2 | No |
| T028 | Test cascade aliases | WP06 | P2 | Yes |
| T029 | Test cascade crosswalks | WP06 | P2 | Yes |
| T030 | Test slug auto-generation | WP06 | P2 | Yes |
| T031 | Test slug conflict resolution | WP06 | P2 | Yes |
| T032 | Test field name normalization | WP06 | P2 | Yes |
