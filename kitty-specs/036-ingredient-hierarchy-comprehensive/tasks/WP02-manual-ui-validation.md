---
work_package_id: WP02
title: Manual UI Validation - Cascading Selectors
lane: done
history:
- timestamp: '2026-01-02T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 2 - Manual Testing
review_status: ''
reviewed_by: ''
shell_pid: '35839'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
---

# Work Package Prompt: WP02 - Manual UI Validation - Cascading Selectors

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Manually verify cascading selector behavior in all 4 UI locations
- Confirm L0 -> L1 -> L2 cascade works correctly
- Confirm Clear/Reset functionality works
- Document pass/fail status for each test

**Success Metrics**:
- All 4 UI locations pass cascading tests
- No unexpected behaviors or UI glitches
- Results documented

## Context & Constraints

- **Depends on**: WP01 (automated tests should pass first)
- **Reference**: `kitty-specs/036-ingredient-hierarchy-comprehensive/spec.md` - User Story 2
- **Plan**: `kitty-specs/036-ingredient-hierarchy-comprehensive/plan.md` - Phase 2: Manual UI Validation

The cascading selectors were fixed in F034. This work package verifies they work correctly in integration.

## Subtasks & Detailed Guidance

### Subtask T007 - Test Product edit form cascading selector
- **Purpose**: Verify ingredient selection in product edit uses correct cascade.
- **Steps**:
  1. Start app: `python src/main.py`
  2. Navigate to Products tab
  3. Click Edit on any product
  4. In the ingredient selector:
     - Select an L0 category (e.g., "Flour")
     - Verify L1 dropdown updates to show only children of that L0
     - Select an L1 subcategory
     - Verify L2 dropdown updates to show only children of that L1
     - Change L0 selection
     - Verify L1 and L2 reset/clear
  5. Record pass/fail
- **Files**: `src/ui/forms/product_detail_dialog.py` (not modifying, just testing)
- **Parallel?**: No - requires app interaction
- **Notes**: Test with at least 2 different L0 categories

### Subtask T008 - Test Recipe creation form cascading selector
- **Purpose**: Verify ingredient selection in recipe creation uses correct cascade and only allows L2.
- **Steps**:
  1. Navigate to Recipes tab
  2. Click Add Recipe (or Edit existing)
  3. In the Add Ingredient section:
     - Select an L0 category
     - Verify L1 updates
     - Select an L1 subcategory
     - Verify L2 updates
     - Verify only L2 ingredients can be added (not L0/L1)
  4. Record pass/fail
- **Files**: `src/ui/forms/recipe_form.py` (not modifying, just testing)
- **Parallel?**: No
- **Notes**: Verify error handling if trying to add without full selection

### Subtask T009 - Test Product tab filter cascading behavior
- **Purpose**: Verify product list filtering by ingredient hierarchy.
- **Steps**:
  1. Navigate to Products tab
  2. In the filter section:
     - Select an L0 category filter
     - Verify L1 filter updates to show only children
     - Verify product list filters to show only products with matching ingredients
     - Select L1 filter
     - Verify L2 filter updates
     - Verify product list further filters
     - Change L0 filter
     - Verify L1/L2 reset and list updates
  3. Record pass/fail
- **Files**: `src/ui/products_tab.py` (not modifying, just testing)
- **Parallel?**: No
- **Notes**: Note if filter feels responsive (<50ms perceived delay)

### Subtask T010 - Test Inventory tab filter cascading behavior
- **Purpose**: Verify inventory list filtering by ingredient hierarchy.
- **Steps**:
  1. Navigate to Inventory tab
  2. In the filter section:
     - Repeat same cascade tests as T009
     - Select L0 -> verify L1 updates
     - Select L1 -> verify L2 updates
     - Change L0 -> verify reset
  3. Record pass/fail
- **Files**: `src/ui/inventory_tab.py` (not modifying, just testing)
- **Parallel?**: No
- **Notes**: Inventory may have different filter UI than Products - note any differences

### Subtask T011 - Test Clear/Reset functionality in all filters
- **Purpose**: Verify filters can be cleared completely.
- **Steps**:
  1. For each location with filters (Product tab, Inventory tab):
     - Set L0, L1, L2 filters
     - Click Clear/Reset button (if exists) or deselect all
     - Verify all filters reset to default/empty
     - Verify list shows all items again
  2. Record pass/fail for each location
- **Files**: Various UI files
- **Parallel?**: No
- **Notes**: If no Clear button exists, note this as a potential enhancement

### Subtask T012 - Document UI test results
- **Purpose**: Create permanent record of manual testing.
- **Steps**:
  1. Update `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
  2. Add "Manual UI Test Results" section with:
     - Test matrix showing each location and pass/fail
     - Any unexpected behaviors noted
     - Performance observations
     - Screenshots if issues found
  3. Commit the update
- **Files**: `kitty-specs/036-ingredient-hierarchy-comprehensive/research.md`
- **Parallel?**: No - depends on T007-T011

## Test Strategy

Manual testing protocol for each location:

```
Location: [Product Edit / Recipe Create / Product Filter / Inventory Filter]
1. Select L0: _____________ -> L1 options: [pass/fail]
2. Select L1: _____________ -> L2 options: [pass/fail]
3. Change L0 -> L1/L2 reset: [pass/fail]
4. Clear all -> full reset: [pass/fail]
Notes: _______________
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| App crash during testing | Capture stack trace, restart and continue |
| Inconsistent behavior | Test same scenario 3 times to confirm |
| Missing test data | Ensure sample_data.json has multi-level hierarchy |
| UI freezes | Note time and conditions, may indicate infinite loop |

## Definition of Done Checklist

- [ ] Product edit form cascade tested (T007)
- [ ] Recipe creation form cascade tested (T008)
- [ ] Product tab filter cascade tested (T009)
- [ ] Inventory tab filter cascade tested (T010)
- [ ] Clear/Reset tested in all locations (T011)
- [ ] Results documented in research.md (T012)
- [ ] All locations pass or issues documented

## Review Guidance

- Verify test results are documented with pass/fail status
- If any failures, verify they are documented with details
- Check that all 4 UI locations were tested
- Confirm no critical bugs blocking user workflows

## Activity Log

- 2026-01-02T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-02T22:13:27Z – claude – shell_pid=35839 – lane=doing – Starting manual UI validation
- 2026-01-03T01:28:23Z – claude – shell_pid=35839 – lane=done – Moved to done
