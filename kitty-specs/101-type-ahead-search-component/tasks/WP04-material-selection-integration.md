---
work_package_id: WP04
title: Material Selection Integration
lane: "doing"
dependencies: [WP02]
base_branch: 101-type-ahead-search-component-WP02
base_commit: fdf836dbc1a3c8d4e65269c62a74115e9d7555b6
created_at: '2026-02-10T22:22:18.151048+00:00'
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 2 - US3 Material Reuse
assignee: ''
agent: ''
shell_pid: "92063"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-10T21:59:40Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 -- Material Selection Integration

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
spec-kitty implement WP04 --base WP02
```

Depends on WP02 - branches from WP02's completed work. Can be parallelized with WP03.

---

## Objectives & Success Criteria

Integrate the `TypeAheadEntry` widget into the finished good builder for material product selection, validating the component's reusability across different data sources.

**Success Criteria:**
- Material search via type-ahead works in the FG builder's material step
- Type-ahead behavior (keyboard, visual, debounce, dismissal) is identical to ingredient type-ahead (US3-AS2)
- Same widget configuration (min_chars=3, debounce=300ms, max_results=10) used in both contexts
- Material selection integrates into the existing builder flow (Step 2: Materials)

## Context & Constraints

- **Spec**: `kitty-specs/101-type-ahead-search-component/spec.md` (US3, FR-006)
- **Plan**: `kitty-specs/101-type-ahead-search-component/plan.md` (Integration Points: Material Selection)
- **Research**: `kitty-specs/101-type-ahead-search-component/research.md` (material search APIs)
- **Constitution**: `.kittify/memory/constitution.md`

**Key Files to Understand:**
- `src/ui/builders/finished_good_builder.py` - FG builder with Step 2 (Materials) where material selection happens
- `src/services/material_catalog_service.py` - Has `list_products()`, `list_materials()` but no dedicated `search_*` function
- `src/models/` - Material/Product model structure (for understanding dict keys)

**Key Constraints:**
- `material_catalog_service` does NOT have a `search_products()` function like ingredient_hierarchy_service has `search_ingredients()`. The callback must implement search logic.
- Options for the callback:
  1. Use `list_products()` with a name filter (if it supports ilike)
  2. Load all products and filter client-side (acceptable for smaller catalogs)
  3. Write a raw query in the callback (less ideal but acceptable for UI-layer adapter)
- The TypeAheadEntry widget is the same code -- only the callbacks differ
- Material items may have different dict keys than ingredient items (use `display_key` parameter)

## Subtasks & Detailed Guidance

### Subtask T018 -- Create Material Search Callback Wrapper

- **Purpose**: Bridge the TypeAheadEntry callback interface with material catalog search.
- **Steps**:
  1. First, read `src/services/material_catalog_service.py` to understand available functions:
     - Check if any list/search function accepts a name filter parameter
     - Check the return type (ORM objects or dicts)
     - Check what fields are available (display_name, name, category, etc.)
  2. Create the callback in `finished_good_builder.py`:
     ```python
     def _search_materials_for_typeahead(self, query: str) -> List[Dict[str, Any]]:
         """Search material products for type-ahead dropdown."""
         from src.services.material_catalog_service import list_products
         # Option A: If list_products supports filtering
         products = list_products(name_filter=query, limit=10)
         return [{"display_name": p.display_name, "id": p.id, ...} for p in products]

         # Option B: If no filter support, load and filter client-side
         products = list_products()
         query_lower = query.lower()
         matches = [p for p in products if query_lower in p.display_name.lower()]
         return [{"display_name": m.display_name, "id": m.id, ...} for m in matches[:10]]
     ```
  3. Ensure the returned dicts have at least `display_name` (or whatever `display_key` is configured to) and `id`
  4. Handle errors gracefully (return empty list)

- **Files**: `src/ui/builders/finished_good_builder.py`
- **Notes**:
  - If `list_products()` returns ORM objects, convert to dicts for the callback return. The widget expects `List[Dict[str, Any]]`.
  - If client-side filtering is needed, consider implementing word-boundary prioritization (matching `TypeAheadComboBox._filter_values()` approach) for consistency.
  - If the material catalog is small (<100 items), client-side filtering is perfectly acceptable and avoids adding a new service function.

### Subtask T019 -- Add TypeAheadEntry to FG Builder Material Step

- **Purpose**: Replace or supplement the current material selection UI in Step 2 of the FG builder.
- **Steps**:
  1. Read the current Step 2 (Materials) implementation in `finished_good_builder.py`:
     - How are materials currently selected? (dropdown, dialog, list?)
     - Where is the material entry frame?
     - How does the current flow add materials to the FG?
  2. Add TypeAheadEntry to the materials step:
     ```python
     from src.ui.widgets.type_ahead_entry import TypeAheadEntry

     self._material_typeahead = TypeAheadEntry(
         master=material_entry_frame,
         items_callback=self._search_materials_for_typeahead,
         on_select_callback=self._on_typeahead_material_selected,
         min_chars=3,
         debounce_ms=300,
         max_results=10,
         placeholder_text="Type material name to search...",
         clear_on_select=True,
     )
     self._material_typeahead.pack(fill="x", padx=10, pady=5)
     ```
  3. Position the type-ahead where it makes sense in the existing materials step layout
  4. Ensure it doesn't conflict with the Step 2 accordion or scroll frame

- **Files**: `src/ui/builders/finished_good_builder.py`
- **Notes**:
  - The FG builder uses accordion steps. The TypeAheadEntry should be inside the Step 2 content frame.
  - The floating dropdown (CTkToplevel) should layer above the accordion/scroll frame correctly since it's an independent toplevel window.
  - Match the visual placement pattern of other entry fields in the builder.

### Subtask T020 -- Wire Material Selection Callback

- **Purpose**: When a material is selected via type-ahead, add it to the finished good's material list.
- **Steps**:
  1. Implement `_on_typeahead_material_selected(self, item: Dict)`:
     - Extract material data from the item dict:
       ```python
       material_id = item["id"]
       material_name = item["display_name"]
       ```
     - Call the existing mechanism for adding a material to the FG (read the builder code to find this)
     - Handle duplicate detection if the material is already added
     - Update the materials display list in Step 2
  2. After selection, the TypeAheadEntry clears automatically (`clear_on_select=True`)
  3. Set focus back to the type-ahead for rapid multi-material entry

- **Files**: `src/ui/builders/finished_good_builder.py`
- **Notes**:
  - Study how the existing material selection works in the builder. The type-ahead should integrate with the same data flow, not create a parallel one.
  - The builder may require additional fields (quantity, unit) after material selection -- wire into the existing post-selection flow.

### Subtask T021 -- Verify Identical UX Behavior

- **Purpose**: Confirm that the material type-ahead and ingredient type-ahead behave identically per US3-AS2.
- **Steps**:
  1. Create a comparison checklist and verify manually:
     - [ ] Keyboard shortcuts identical (Down/Up/Enter/Escape)
     - [ ] Visual design identical (same colors, fonts, sizes for dropdown items)
     - [ ] Debounce timing identical (both 300ms)
     - [ ] Min chars identical (both 3)
     - [ ] Max results identical (both 10)
     - [ ] Truncation message format identical
     - [ ] No-match message format identical
     - [ ] Clear-on-select behavior identical
     - [ ] Placeholder text style identical (only text differs)
  2. Both use the same `TypeAheadEntry` widget class, so behavioral identity is guaranteed by design. Verify visual consistency is not broken by different parent containers.
  3. Document any unavoidable differences (e.g., material results don't have breadcrumbs) and justify.

- **Files**: Manual verification; document in activity log
- **Notes**: Since both contexts use the exact same widget class with only callbacks and placeholder text differing, UX consistency is inherent. The main risk is parent container styling differences.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| No dedicated search function in material_catalog_service | Client-side filtering acceptable for small catalogs; or add thin service wrapper |
| Material ORM objects vs dicts mismatch | Convert to dicts in callback; widget only sees dicts |
| FG builder's accordion/scroll conflicts with floating dropdown | CTkToplevel is independent of parent layout; test layering |
| Material step has different entry pattern than ingredient step | Read builder code first; adapt integration to existing patterns |

## Definition of Done Checklist

- [ ] Material search callback returns correctly formatted results
- [ ] TypeAheadEntry added to FG builder Step 2 (Materials)
- [ ] Selecting a material adds it to the finished good
- [ ] Full keyboard workflow works (type → arrow → Enter → material added)
- [ ] Entry clears after selection, ready for next material
- [ ] UX behavior verified identical to ingredient type-ahead
- [ ] No visual or behavioral differences beyond data source
- [ ] Existing material selection flow preserved or improved

## Review Guidance

- Test US3 acceptance scenarios 1-2 from spec.md
- Compare material type-ahead side-by-side with ingredient type-ahead: keyboard shortcuts, visual style, timing
- Verify material data flows correctly into FG builder state
- Test with real material catalog data
- Verify the widget works correctly inside the accordion step frame

## Activity Log

- 2026-02-10T21:59:40Z -- system -- lane=planned -- Prompt created.
