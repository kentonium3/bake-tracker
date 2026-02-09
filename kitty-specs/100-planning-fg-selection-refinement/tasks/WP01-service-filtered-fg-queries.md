---
work_package_id: WP01
title: Service Layer - Filtered FG Queries
lane: "done"
dependencies: []
base_branch: main
base_commit: 999b93111f5aba3ee46c2e633469cd4c0d06fa18
created_at: '2026-02-09T21:32:13.250058+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "22118"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-09T21:25:52Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 -- Service Layer - Filtered FG Queries

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - branches from main.

---

## Objectives & Success Criteria

Add two new service functions to `src/services/event_service.py` that support the Planning tab's filter-first FG selection:

1. `get_filtered_available_fgs()` - Returns available FGs for an event filtered by recipe category, assembly type, and/or yield type
2. `get_available_recipe_categories_for_event()` - Returns distinct recipe categories that have at least one available FG for the event

**Success Criteria:**
- Both functions follow the session parameter pattern (inherits session from caller)
- Both functions include docstrings with args, returns, raises, and transaction boundary documentation
- All filter combinations produce correct results (AND logic)
- Yield type filter correctly excludes BUNDLE FGs when a specific yield type is selected
- Unit tests cover: no filters, single filter, two filters, three filters, empty results, yield_type with BUNDLE exclusion

## Context & Constraints

- **Spec**: `kitty-specs/100-planning-fg-selection-refinement/spec.md` (FR-004 through FR-007)
- **Plan**: `kitty-specs/100-planning-fg-selection-refinement/plan.md` (Design Decision D1, D4)
- **Data Model**: `kitty-specs/100-planning-fg-selection-refinement/data-model.md`
- **Research**: `kitty-specs/100-planning-fg-selection-refinement/research.md` (R1, R2, R3)
- **Constitution**: `.kittify/memory/constitution.md` - Session parameter pattern (III.C.1), Exception-based errors (VI.A)

**Key Constraints:**
- `get_available_finished_goods()` already exists at `src/services/event_service.py:435` - reuse its logic
- `Recipe.category` is a plain string field (not FK to RecipeCategory)
- `FinishedUnit.yield_type` is a string field ("EA" or "SERVING")
- `FinishedGood.assembly_type` is an enum (`AssemblyType.BARE` or `AssemblyType.BUNDLE`)
- BARE FGs wrap a single FinishedUnit via Composition; BUNDLE FGs may have multiple components

## Subtasks & Detailed Guidance

### Subtask T001 -- Add `get_filtered_available_fgs()` to event_service.py

- **Purpose**: Provide a filtered version of `get_available_finished_goods()` that accepts optional recipe_category, assembly_type, and yield_type parameters.
- **Files**: `src/services/event_service.py`
- **Parallel?**: No (T002 can start after this)

**Steps**:

1. Add the function after `get_available_finished_goods()` (around line 480):

```python
def get_filtered_available_fgs(
    event_id: int,
    session: Session,
    recipe_category: Optional[str] = None,
    assembly_type: Optional[str] = None,
    yield_type: Optional[str] = None,
) -> List[FinishedGood]:
    """
    Get available FGs for an event with optional filters.

    Extends get_available_finished_goods() with AND-combinable filters.

    Transaction boundary: Inherits session from caller (required parameter).

    Args:
        event_id: The event to check availability for
        session: Database session (required)
        recipe_category: Filter by recipe category name (e.g., "Cookies"). None = all.
        assembly_type: Filter by assembly type ("bare" or "bundle"). None = all.
        yield_type: Filter by yield type ("EA" or "SERVING"). None = all.
                    When specified, only BARE FGs are included (BUNDLEs have no yield_type).

    Returns:
        List of FinishedGood objects matching all active filters

    Raises:
        ValidationError: If event_id not found
    """
```

2. Implementation logic:
   - Start with `available_fgs = get_available_finished_goods(event_id, session)`
   - Apply each filter sequentially (AND logic):

   **recipe_category filter**:
   - For each FG, get its component FinishedUnits (via Composition where `finished_unit_id IS NOT NULL`)
   - Check if any component FU's recipe has `recipe.category == recipe_category`
   - For BARE FGs: single FU, check its recipe category
   - For BUNDLE FGs: check if ANY component FU's recipe matches the category

   **assembly_type filter**:
   - Compare `fg.assembly_type == AssemblyType(assembly_type)`

   **yield_type filter**:
   - Only applies to BARE FGs (assembly_type == BARE)
   - Get the single FinishedUnit component
   - Check `finished_unit.yield_type == yield_type`
   - BUNDLE FGs are excluded when yield_type is specified

3. Return the filtered list.

**Notes**:
- Import `AssemblyType` from `src.models.assembly_type`
- Import `Composition` from `src.models.composition`
- Import `FinishedUnit` from `src.models.finished_unit`
- Import `Recipe` from `src.models.recipe`
- The function needs to load compositions to traverse FG -> FU -> Recipe relationships
- Use `session.query()` for the traversal queries, staying within the caller's session

### Subtask T002 -- Add `get_available_recipe_categories_for_event()` to event_service.py

- **Purpose**: Return distinct recipe categories that have at least one available FG for the event. Used to populate the FG-level recipe category filter dropdown.
- **Files**: `src/services/event_service.py`
- **Parallel?**: No (depends on understanding from T001)

**Steps**:

1. Add the function after `get_filtered_available_fgs()`:

```python
def get_available_recipe_categories_for_event(
    event_id: int,
    session: Session,
) -> List[str]:
    """
    Get distinct recipe categories with available FGs for an event.

    Returns category names that have at least one available FG, suitable
    for populating filter dropdown options.

    Transaction boundary: Inherits session from caller (required parameter).

    Args:
        event_id: The event to check
        session: Database session (required)

    Returns:
        Sorted list of distinct recipe category names

    Raises:
        ValidationError: If event_id not found
    """
```

2. Implementation:
   - Call `get_available_finished_goods(event_id, session)` to get all available FGs
   - For each FG, traverse to its component FinishedUnits and collect `recipe.category`
   - Return `sorted(set(categories))` — deduplicated and alphabetically sorted

### Subtask T003 -- Write tests for `get_filtered_available_fgs()`

- **Purpose**: Verify all filter combinations produce correct results.
- **Files**: `src/tests/services/test_event_service.py` (add new test class)
- **Parallel?**: [P] Can run alongside T004

**Test Cases** (add as a new `TestFilteredAvailableFGs` class):

1. **test_no_filters_returns_all_available**: No filters applied, returns same as `get_available_finished_goods()`
2. **test_filter_by_recipe_category**: Set recipe_category="Cookies", verify only cookie-recipe FGs returned
3. **test_filter_by_assembly_type_bare**: Set assembly_type="bare", verify only BARE FGs returned
4. **test_filter_by_assembly_type_bundle**: Set assembly_type="bundle", verify only BUNDLE FGs returned
5. **test_filter_by_yield_type_ea**: Set yield_type="EA", verify only BARE FGs with EA yield returned
6. **test_filter_by_yield_type_excludes_bundles**: Set yield_type="EA", verify BUNDLE FGs are excluded
7. **test_combined_category_and_type**: Set recipe_category + assembly_type, verify AND logic
8. **test_all_three_filters**: Set all three, verify AND logic with yield_type excluding BUNDLEs
9. **test_no_matches_returns_empty**: Filters that match nothing return empty list
10. **test_no_recipes_selected_returns_empty**: Event with no recipe selections returns empty

**Setup**: Create test fixtures with:
- A RecipeCategory "Cookies" and a Recipe with category="Cookies"
- A FinishedUnit with recipe_id pointing to the cookie recipe, yield_type="EA"
- A BARE FinishedGood with a Composition linking to that FinishedUnit
- A BUNDLE FinishedGood with compositions
- EventRecipe linking the event to the recipe
- Use `test_db` fixture (CRITICAL - see MEMORY.md production DB wipe bug)

### Subtask T004 -- Write tests for `get_available_recipe_categories_for_event()`

- **Purpose**: Verify category enumeration returns correct distinct sorted list.
- **Files**: `src/tests/services/test_event_service.py` (add to same or new test class)
- **Parallel?**: [P] Can run alongside T003

**Test Cases**:

1. **test_returns_distinct_categories**: Multiple FGs from same category return category once
2. **test_returns_sorted**: Categories returned in alphabetical order
3. **test_no_available_fgs_returns_empty**: Event with no available FGs returns empty list
4. **test_multiple_categories**: FGs from different categories all represented

## Test Strategy

- All tests use the `test_db` fixture (CRITICAL - prevents production DB wipe)
- Tests go in `src/tests/services/test_event_service.py`
- Test class: `TestFilteredAvailableFGs` and `TestAvailableRecipeCategoriesForEvent`
- Run with: `./run-tests.sh src/tests/services/test_event_service.py -v -k "TestFilteredAvailable or TestAvailableRecipeCategories"`

## Risks & Mitigations

- **Risk**: Recipe.category might not match RecipeCategory.name exactly (case sensitivity, trailing spaces)
  - **Mitigation**: Use exact string match; existing data should be consistent
- **Risk**: get_available_finished_goods() is expensive (queries all FGs) for large catalogs
  - **Mitigation**: Current catalog is ~100 FGs; acceptable performance. Optimize later if needed.
- **Risk**: Composition lazy loading could cause N+1 queries
  - **Mitigation**: Use joined loading or batch the query; profile if tests show slowness

## Definition of Done Checklist

- [ ] `get_filtered_available_fgs()` added with full docstring and session parameter
- [ ] `get_available_recipe_categories_for_event()` added with full docstring and session parameter
- [ ] All filter combinations (none, single, double, triple) produce correct results
- [ ] Yield type filter correctly excludes BUNDLE FGs
- [ ] 10+ test cases passing for filtered FG query
- [ ] 4+ test cases passing for recipe categories query
- [ ] All existing tests still pass (no regressions)

## Review Guidance

- Verify session parameter pattern is followed correctly
- Verify AND logic: each filter narrows results, not widens
- Verify yield_type + BUNDLE interaction: BUNDLEs excluded when yield_type specified
- Check test coverage: empty results, single filter, combined filters
- Ensure `test_db` fixture is used on all test methods

## Activity Log

- 2026-02-09T21:25:52Z -- system -- lane=planned -- Prompt created.
- 2026-02-09T21:32:13Z – claude-opus – shell_pid=22118 – lane=doing – Assigned agent via workflow command
- 2026-02-09T21:39:24Z – claude-opus – shell_pid=22118 – lane=for_review – Ready for review: get_filtered_available_fgs() and get_available_recipe_categories_for_event() with 19 passing tests
- 2026-02-09T21:58:02Z – claude-opus – shell_pid=22118 – lane=done – Review passed: 19/19 tests pass, full suite (3663) passes with no regressions. Session pattern correct (required param, delegates to get_available_finished_goods). AND logic verified across all filter combos. yield_type correctly excludes BUNDLEs. test_db fixture present on all tests. Docstrings complete with args/returns/raises/transaction boundary docs.
