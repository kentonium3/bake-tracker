---
work_package_id: WP04
title: Production Display Integration
lane: planned
dependencies:
- WP01
- WP02
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 2 - Polish
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2025-01-24T07:30:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Production Display Integration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP01
```

This work package depends on WP01 (service primitives). It can run in parallel with WP02/WP03.

---

## Objectives & Success Criteria

Update production dashboard and related displays to use the new yield primitives, showing variant's display_name with base's yield info.

**Success Criteria**:
- [ ] Production dashboard uses `get_base_yield_structure()` for yield calculations
- [ ] Variant recipes show correct yield info (from base)
- [ ] Display shows variant's display_name with base's yield
- [ ] No variant-specific logic in display code (primitives handle abstraction)
- [ ] Works for base recipes, variant recipes, and multiple FinishedUnits

---

## Context & Constraints

**References**:
- Plan: `kitty-specs/063-variant-yield-inheritance/plan.md` (Phase 3)
- Spec: `kitty-specs/063-variant-yield-inheritance/spec.md` (User Story 3, FR-006, FR-007)
- Primitives: WP01 added `get_base_yield_structure()` and `get_finished_units()`

**Architectural Constraints**:
- UI layer calls service primitives (not direct model access)
- Follow FR-007: No variant-specific logic or `base_recipe_id` checks in display code
- Pattern: `get_base_yield_structure(recipe_id)` for yields, `get_finished_units(recipe_id)` for display_name

**Display Pattern**:
```python
# For a variant recipe, show:
# "Raspberry Cookie: 24 cookies per batch"
#  ↑ from get_finished_units()  ↑ from get_base_yield_structure()
```

---

## Subtasks & Detailed Guidance

### Subtask T018 – Identify production dashboard components

**Purpose**: Research which UI components display yield info and need updating.

**Steps**:
1. **Search for yield-related displays**:
   ```bash
   # Look for items_per_batch, item_unit usage in UI
   grep -r "items_per_batch\|item_unit" src/ui/
   ```

2. **Check production-related files**:
   - `src/ui/production_dashboard_tab.py`
   - `src/ui/dashboards/make_dashboard.py`
   - `src/ui/forms/finished_good_detail.py`
   - `src/ui/forms/finished_unit_detail.py`

3. **Document findings**:
   - List each file that accesses yield info
   - Note the context (list view, detail view, calculation)
   - Identify which need updating

**Expected Locations**:
- Production dashboard batch calculations
- FinishedUnit/FinishedGood detail displays
- Recipe detail view (yield section)
- Production planning views

**Files**:
- Research only; no code changes

**Validation**:
- [ ] All yield display locations identified
- [ ] Access patterns documented

---

### Subtask T019 – Replace direct yield access with `get_base_yield_structure()`

**Purpose**: Update identified components to use the primitive instead of direct FinishedUnit access.

**Steps**:
1. **For each identified location, refactor**:

   **Before** (direct access):
   ```python
   def display_yield_info(finished_unit):
       yield_text = f"{finished_unit.items_per_batch} {finished_unit.item_unit} per batch"
       return yield_text
   ```

   **After** (using primitive):
   ```python
   def display_yield_info(recipe_id, session):
       from src.services import recipe_service

       yields = recipe_service.get_base_yield_structure(recipe_id, session=session)
       if not yields:
           return "No yield defined"

       # For single FU (most common case)
       y = yields[0]
       if y["items_per_batch"] and y["item_unit"]:
           return f"{y['items_per_batch']} {y['item_unit']} per batch"
       return "Yield not specified"
   ```

2. **Handle session context**:
   ```python
   # In UI component
   from src.ui.utils import ui_session

   with ui_session() as session:
       yield_text = display_yield_info(recipe_id, session)
   ```

3. **Update production calculations**:
   ```python
   def calculate_batches_needed(recipe_id, target_quantity, session):
       yields = recipe_service.get_base_yield_structure(recipe_id, session=session)
       if not yields or not yields[0]["items_per_batch"]:
           return 0

       items_per_batch = yields[0]["items_per_batch"]
       return math.ceil(target_quantity / items_per_batch)
   ```

**Files**:
- `src/ui/production_dashboard_tab.py` (modify)
- `src/ui/dashboards/make_dashboard.py` (modify if applicable)
- Other identified files

**Validation**:
- [ ] No direct `finished_unit.items_per_batch` access in updated code
- [ ] Uses `get_base_yield_structure()` for all yield lookups
- [ ] Session passed to primitive calls

---

### Subtask T020 – Display variant's display_name with base's yield

**Purpose**: When showing a variant, display the variant's FinishedUnit display_name alongside the inherited yield.

**Steps**:
1. **Combine primitive calls for variant display**:
   ```python
   def get_recipe_yield_display(recipe_id, session):
       """Get display-ready yield info combining FU name and base yields."""
       from src.services import recipe_service

       # Get this recipe's FinishedUnits (for display_name)
       recipe_fus = recipe_service.get_finished_units(recipe_id, session=session)

       # Get base yields (resolved if variant)
       base_yields = recipe_service.get_base_yield_structure(recipe_id, session=session)

       if not recipe_fus or not base_yields:
           return []

       # Combine: variant display_name + base yield
       result = []
       for fu, y in zip(recipe_fus, base_yields):
           display = {
               "display_name": fu["display_name"],  # Variant's name
               "items_per_batch": y["items_per_batch"],  # Base's yield
               "item_unit": y["item_unit"],  # Base's unit
               "yield_text": f"{y['items_per_batch']} {y['item_unit']} per batch"
                             if y["items_per_batch"] and y["item_unit"]
                             else "Yield not specified"
           }
           result.append(display)

       return result
   ```

2. **Use in production dashboard**:
   ```python
   # In production card or list item
   yields = get_recipe_yield_display(recipe_id, session)
   for y in yields:
       label = f"{y['display_name']}: {y['yield_text']}"
       # Display: "Raspberry Cookie: 24 cookies per batch"
   ```

3. **Handle multiple FinishedUnits**:
   - Some recipes have multiple FUs (e.g., a cake recipe that makes both rounds and cupcakes)
   - Display each with its name and yield

**Files**:
- `src/ui/production_dashboard_tab.py` (modify)
- `src/ui/dashboards/make_dashboard.py` (modify if applicable)
- Create helper function in `src/ui/utils/` if pattern is reused

**Validation**:
- [ ] Variant shows variant's display_name (not base's)
- [ ] Variant shows base's yield values
- [ ] Base recipes work unchanged
- [ ] Multiple FU case handled

---

### Subtask T021 – Test production dashboard with variants

**Purpose**: Verify the dashboard works correctly for base recipes, variants, and multiple FU scenarios.

**Steps**:
1. **Manual testing checklist**:
   - [ ] Base recipe with 1 FU displays correctly
   - [ ] Base recipe with 2 FUs displays correctly
   - [ ] Variant recipe shows variant's display_name
   - [ ] Variant recipe shows base's yield values
   - [ ] Recipe with no FUs shows appropriate message
   - [ ] Batch calculations work for variants

2. **Create test data if needed**:
   - Base recipe "Plain Cookie" with FU (24 cookies/batch)
   - Variant "Raspberry Cookie" with FU (NULL yields)
   - Verify production dashboard shows:
     - Base: "Plain Cookie: 24 cookies per batch"
     - Variant: "Raspberry Cookie: 24 cookies per batch"

3. **Document any issues found**:
   - Screenshot unexpected behavior
   - Note which component/file needs fixing

**Files**:
- No code changes (testing task)
- Document results in PR description

**Validation**:
- [ ] All manual test scenarios pass
- [ ] No visual regressions
- [ ] Yield calculations correct for variants

---

## Definition of Done

- [ ] Production dashboard uses primitives for yield access
- [ ] Variant recipes display correctly (variant name + base yield)
- [ ] No direct FinishedUnit yield field access in updated code
- [ ] All identified display locations updated
- [ ] Manual testing passes for base, variant, and multi-FU cases

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Many display locations | Focus on production dashboard; expand if time permits |
| Performance (multiple service calls) | Calls are lightweight reads; cache if needed |
| Breaking existing displays | Test thoroughly before/after changes |

---

## Reviewer Guidance

When reviewing this work package, verify:

1. **Primitive Usage**: Uses `get_base_yield_structure()` not direct FU access
2. **No Variant Logic**: Code doesn't check `base_recipe_id` - primitives handle this
3. **Display Combination**: Variant shows variant's display_name + base's yield
4. **Session Handling**: Session passed to primitive calls correctly
5. **Edge Cases**: Empty yields, multiple FUs handled
6. **No Regressions**: Base recipe displays unchanged
