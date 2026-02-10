---
work_package_id: WP03
title: Ingredient Selection Integration
lane: "doing"
dependencies: [WP02]
base_branch: 101-type-ahead-search-component-WP02
base_commit: fdf836dbc1a3c8d4e65269c62a74115e9d7555b6
created_at: '2026-02-10T22:18:03.414651+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 1 - US1 Ingredient Search
assignee: ''
agent: ''
shell_pid: "90348"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-10T21:59:40Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 -- Ingredient Selection Integration

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
spec-kitty implement WP03 --base WP02
```

Depends on WP02 - branches from WP02's completed work.

---

## Objectives & Success Criteria

Integrate the `TypeAheadEntry` widget into the recipe ingredient selection workflow, enabling fast type-ahead search for ingredients with ancestor breadcrumbs.

**Success Criteria:**
- From recipe form, typing a partial ingredient name shows filtered results in type-ahead dropdown
- Each result shows the ingredient name with ancestor breadcrumbs (e.g., "Chocolate Chips (Baking > Chocolate)")
- Selecting an ingredient populates it in the recipe form
- Full keyboard-only workflow works: type → arrow → Enter → ingredient added
- Ingredient selection time < 10 seconds per ingredient (SC-001)
- Type-ahead clears after selection, ready for next ingredient search (US1-AS4)

## Context & Constraints

- **Spec**: `kitty-specs/101-type-ahead-search-component/spec.md` (US1, US2)
- **Plan**: `kitty-specs/101-type-ahead-search-component/plan.md` (Integration Points: Ingredient Selection)
- **Research**: `kitty-specs/101-type-ahead-search-component/research.md` (search service APIs, selection dialog pattern)
- **Constitution**: `.kittify/memory/constitution.md` - Layered architecture (V), Session parameter (VI.C)

**Key Files to Understand:**
- `src/services/ingredient_hierarchy_service.py` - `search_ingredients(query, limit, session)` returns `List[Dict]` with `ancestors` field
- `src/ui/forms/recipe_form.py` - Current recipe ingredient entry workflow
- `src/ui/dialogs/ingredient_selection_dialog.py` (if exists) - Current modal dialog for ingredient selection
- `src/ui/widgets/ingredient_tree_widget.py` - Current tree-based selection (reference for UX comparison)

**Key Constraints:**
- The callback wrapper lives in the UI layer (e.g., recipe_form.py) and imports the service -- the widget itself still has zero service imports
- `search_ingredients()` returns dicts with keys: `id`, `display_name`, `slug`, `category`, `hierarchy_level`, `ancestors`
- `ancestors` is a list of dicts with `id` and `display_name` keys
- The `clear_on_select=True` default means the entry clears after each selection, ready for the next ingredient

**Integration Strategy Decision:**
Before implementing, read the current ingredient selection flow in `recipe_form.py` to determine the best integration point. Options:
1. Add TypeAheadEntry above/alongside the existing tree widget in the IngredientSelectionDialog
2. Add TypeAheadEntry directly in the recipe form (inline, no modal)
3. Replace the tree widget entirely with TypeAheadEntry

Choose the approach that minimizes disruption while delivering the P1 value. Document your choice in the activity log.

## Subtasks & Detailed Guidance

### Subtask T013 -- Create Ingredient Search Callback Wrapper

- **Purpose**: Bridge the `TypeAheadEntry` callback interface with `ingredient_hierarchy_service.search_ingredients()`.
- **Steps**:
  1. In the integration file (recipe_form.py or ingredient_selection_dialog.py), create the callback:
     ```python
     def _search_ingredients_for_typeahead(self, query: str) -> List[Dict[str, Any]]:
         """Search ingredients for type-ahead dropdown.

         Wraps ingredient_hierarchy_service.search_ingredients() to match
         the TypeAheadEntry items_callback interface.
         """
         from src.services.ingredient_hierarchy_service import search_ingredients
         try:
             results = search_ingredients(query, limit=self._max_typeahead_results)
             return results
         except Exception:
             return []
     ```
  2. The callback:
     - Imports service lazily (at call time) to avoid import cycle issues
     - Uses `limit=10` (or configurable via max_results) to match spec FR-003
     - Returns empty list on error (widget handles the "no results" case)
     - Does NOT pass session -- this is a standalone read-only query

- **Files**: Integration target file (determine after reading recipe_form.py)
- **Notes**: The service already handles case-insensitive `ilike` matching and `display_name` ordering. No additional filtering needed in the callback.

### Subtask T014 -- Add TypeAheadEntry to Ingredient Selection Workflow

- **Purpose**: Place the TypeAheadEntry widget in the recipe ingredient entry UI.
- **Steps**:
  1. Read the current recipe form and ingredient selection flow to understand:
     - Where ingredients are currently added (dialog? inline form?)
     - What data is needed when an ingredient is selected (slug, id, display_name?)
     - How the recipe form tracks its ingredient list
  2. Add the TypeAheadEntry widget:
     ```python
     from src.ui.widgets.type_ahead_entry import TypeAheadEntry

     self._ingredient_typeahead = TypeAheadEntry(
         master=ingredient_entry_frame,
         items_callback=self._search_ingredients_for_typeahead,
         on_select_callback=self._on_typeahead_ingredient_selected,
         min_chars=3,
         debounce_ms=300,
         max_results=10,
         placeholder_text="Type ingredient name to search...",
         clear_on_select=True,
         display_key="display_name",
     )
     self._ingredient_typeahead.pack(fill="x", padx=10, pady=5)
     ```
  3. Ensure the TypeAheadEntry is visible and accessible (not hidden behind tabs/accordions)
  4. If using a modal dialog, ensure the floating dropdown works correctly inside CTkToplevel (dropdown-inside-dialog layering)

- **Files**: Integration target file
- **Notes**:
  - If the existing dialog uses `IngredientTreeWidget`, consider adding TypeAheadEntry as a quick-search alternative above the tree, not replacing the tree entirely (preserves browsing for discovery)
  - Set keyboard focus to the TypeAheadEntry on dialog open for immediate typing

### Subtask T015 -- Wire Selection Callback to Recipe Form

- **Purpose**: When an ingredient is selected via type-ahead, update the recipe form state.
- **Steps**:
  1. Implement `_on_typeahead_ingredient_selected(self, item: Dict)`:
     - Extract needed data from the item dict:
       ```python
       ingredient_slug = item["slug"]
       ingredient_name = item["display_name"]
       ingredient_id = item["id"]
       ```
     - Add the ingredient to the recipe's ingredient list using the existing recipe form mechanism
     - If the recipe form uses a different selection flow (e.g., opens a quantity dialog after selection), wire into that flow
     - If the dialog should close after selection, call `self.destroy()` or `self.result = item`
  2. Handle the case where the selected ingredient is already in the recipe (duplicate detection)
  3. After selection, TypeAheadEntry clears automatically (`clear_on_select=True`) and is ready for the next ingredient

- **Files**: Integration target file
- **Notes**:
  - Study how the existing tree-based selection handles the post-selection flow. The type-ahead selection should produce the same downstream behavior.
  - The `item` dict contains the full ingredient data from `search_ingredients()`, including `ancestors`, `hierarchy_level`, etc. Extract only what the recipe form needs.

### Subtask T016 -- Ancestor Breadcrumb Display

- **Purpose**: Show ingredient hierarchy context in dropdown results to help distinguish similar items (e.g., "Chocolate" could be baking chocolate or chocolate candy).
- **Steps**:
  1. Modify the search callback to format the `display_name` with breadcrumbs:
     ```python
     def _search_ingredients_for_typeahead(self, query: str) -> List[Dict[str, Any]]:
         from src.services.ingredient_hierarchy_service import search_ingredients
         results = search_ingredients(query, limit=10)
         # Add formatted display name with breadcrumbs
         for item in results:
             ancestors = item.get("ancestors", [])
             if ancestors:
                 breadcrumb = " > ".join(a["display_name"] for a in ancestors)
                 item["display_name"] = f"{item['display_name']}  ({breadcrumb})"
         return results
     ```
  2. Alternatively, use a separate `display_key` to preserve the original `display_name`:
     ```python
     item["typeahead_display"] = f"{item['display_name']}  ({breadcrumb})"
     ```
     And configure the widget with `display_key="typeahead_display"`.
  3. Handle items with no ancestors (root categories): show just the name, no breadcrumb suffix

- **Files**: Integration target file
- **Parallel?**: Yes, can be developed alongside T014/T015 as a formatting refinement.
- **Notes**:
  - Keep the original `display_name` intact for use in `on_select_callback` (the recipe form needs the clean name)
  - Use two spaces before the parenthesis for visual separation
  - Example output: `"Chocolate Chips  (Baking > Chocolate)"`
  - Long breadcrumbs should be acceptable since the dropdown width matches the entry width and text can ellipsize

### Subtask T017 -- Integration Tests

- **Purpose**: Verify the type-ahead integration works end-to-end with the ingredient service.
- **Steps**:
  1. Create test file (e.g., `src/tests/test_ingredient_typeahead_integration.py`)
  2. Test the search callback:
     - Verify it returns results matching the query
     - Verify results have required keys (`display_name`, `id`, `slug`)
     - Verify breadcrumb formatting is correct
     - Verify empty query returns empty list
     - Verify special characters don't crash
  3. Test the selection callback:
     - Verify it extracts correct ingredient data from item dict
     - Verify it integrates with recipe form state (if testable without full UI)
  4. If full UI testing is impractical, document manual test scenarios:
     - Open recipe form → type "cho" → see chocolate items → select one → verify in recipe
     - Keyboard-only: Tab → type "sug" → Down → Down → Enter → verify sugar selected

- **Files**: `src/tests/test_ingredient_typeahead_integration.py` (new file)
- **Parallel?**: Yes, can be written alongside T014/T015.
- **Notes**: Use `test_db` fixture for any tests that query the database. Remember the production DB wipe bug -- always verify fixtures are present.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Floating dropdown inside modal dialog may have z-order issues | Test early; CTkToplevel dropdown should layer above the dialog since it's also a toplevel |
| Ingredient hierarchy service returns too many results for common queries | Use `limit=10` in callback; widget shows truncation message |
| Breadcrumb strings too long for dropdown width | Text will truncate naturally; entry width determines dropdown width |
| Existing ingredient selection flow disrupted | Add type-ahead as supplement, not replacement, for tree widget initially |

## Definition of Done Checklist

- [ ] Search callback wrapper calls ingredient_hierarchy_service correctly
- [ ] TypeAheadEntry widget added to recipe ingredient selection UI
- [ ] Selecting an ingredient populates it in the recipe form
- [ ] Ancestor breadcrumbs display correctly (e.g., "Chocolate Chips (Baking > Chocolate)")
- [ ] Root-level ingredients (no ancestors) display without breadcrumb suffix
- [ ] Full keyboard-only selection workflow works (type → arrow → Enter → ingredient added)
- [ ] Entry clears after selection, ready for next search
- [ ] Integration tests pass
- [ ] Existing tree-based selection still works (if preserved)

## Review Guidance

- Test US1 acceptance scenarios 1-5 from spec.md
- Verify ingredient data flows correctly to recipe form (check slug, id, not just display name)
- Verify breadcrumb formatting with 0, 1, and 2+ ancestor levels
- Test with real production data (200+ ingredients) for realistic result sets
- Verify no service imports in `type_ahead_entry.py` (only in the callback wrapper)

## Activity Log

- 2026-02-10T21:59:40Z -- system -- lane=planned -- Prompt created.
