---
work_package_id: "WP06"
subtasks:
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
  - "T036"
title: "Dashboard & Shopping List"
phase: "Phase 5 - UI Dashboard"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
gemini_candidate: true
history:
  - timestamp: "2025-12-21T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Dashboard & Shopping List

**GEMINI DELEGATION CANDIDATE**: Dashboard (T030-T033) and Shopping List (T034-T036) are separate UI components that can be developed in parallel.

## Objectives & Success Criteria

- Add pending indicator icons to dashboard items with unassigned packaging
- Make indicators clickable (navigate to assignment)
- Add tooltip and filter for pending items
- Update shopping list to group generic packaging by product_name
- Show estimated costs with appropriate labels
- UI operations complete in <200ms

## Context & Constraints

**References**:
- `kitty-specs/026-deferred-packaging-decisions/plan.md` - Phase 5 & 6 details
- `kitty-specs/026-deferred-packaging-decisions/spec.md` - User Stories 3, 4
- Existing dashboard and shopping list UI files

**Constraints**:
- Follow CustomTkinter patterns
- Keep visual indicators subtle but noticeable
- Performance: <200ms response

**Parallel Opportunities**:
- Dashboard (T030-T033) and Shopping List (T034-T036) can proceed in parallel
- **SUITABLE FOR GEMINI DELEGATION** - Different UI components

## Subtasks & Detailed Guidance

### Subtask T030 - Add pending indicator to dashboard

- **Purpose**: Visual cue for items needing attention
- **Steps**:
  1. Locate dashboard/event list view
  2. Query pending requirements for each displayed item
  3. Add warning icon (orange/yellow) next to items with pending packaging
  4. Use lightweight query to avoid performance impact
- **Files**: `src/ui/dashboard.py` or equivalent
- **Parallel?**: Yes - independent of shopping list
- **Notes**: Cache pending status; refresh on relevant changes

### Subtask T031 - Make indicators clickable

- **Purpose**: Quick navigation to assignment workflow
- **Steps**:
  1. Bind click event to pending indicator
  2. On click, navigate to the relevant assignment dialog/screen
  3. Pass composition_id or event_id as context
- **Files**: `src/ui/dashboard.py`
- **Parallel?**: Yes
- **Notes**: Consider opening assignment dialog directly vs navigating to assembly screen

### Subtask T032 - Add tooltip for pending items

- **Purpose**: Explain what action is needed
- **Steps**:
  1. Add tooltip to pending indicator
  2. Text: "Packaging needs selection"
  3. Include count if multiple items pending
- **Files**: `src/ui/dashboard.py`
- **Parallel?**: Yes
- **Notes**: Use CTkToolTip or similar

### Subtask T033 - Add filter for pending items

- **Purpose**: Focus view on items needing attention
- **Steps**:
  1. Add filter toggle/dropdown: "All items" / "Needs attention"
  2. When "Needs attention" selected, show only items with pending packaging
  3. Persist filter preference in session
- **Files**: `src/ui/dashboard.py`
- **Parallel?**: Yes
- **Notes**: Filter applies to current event view

### Subtask T034 - Update shopping list grouping

- **Purpose**: Group generic packaging by product type
- **Steps**:
  1. Locate shopping list generation/display code
  2. For generic compositions (is_generic=True):
     - Group by `product_name` instead of specific product
     - Sum quantities across all matching compositions
  3. For specific compositions: preserve existing behavior
- **Files**: `src/ui/shopping_list.py` or equivalent, `src/services/shopping_list_service.py`
- **Parallel?**: Yes - independent of dashboard
- **Notes**: Uses service layer for grouping logic

### Subtask T035 - Display generic item format

- **Purpose**: Clear representation of generic requirements
- **Steps**:
  1. Format generic items as: "Cellophane Bags 6x10: 50 needed"
  2. Distinguish visually from specific product items
  3. Show as section header with quantity
- **Files**: `src/ui/shopping_list.py` or equivalent
- **Parallel?**: Yes
- **Notes**: Consider indenting specific alternatives below

### Subtask T036 - Show estimated costs in shopping list

- **Purpose**: Display cost estimates for generic items
- **Steps**:
  1. Call `packaging_service.get_estimated_cost()` for generic items
  2. Display with "Estimated" label: "(Estimated: $25.00)"
  3. Use different styling from actual costs
- **Files**: `src/ui/shopping_list.py` or equivalent
- **Parallel?**: Yes
- **Notes**: Consider subtle color difference (e.g., gray vs black)

## Test Strategy

Manual testing checklist:

**Dashboard:**
1. Create event with generic packaging requirement
2. Verify pending indicator appears on dashboard
3. Click indicator - verify navigation works
4. Hover for tooltip - verify text correct
5. Use filter - verify only pending items shown

**Shopping List:**
1. Create shopping list for event with generic packaging
2. Verify generic items grouped by product_name
3. Verify format: "Cellophane Bags 6x10: 50 needed"
4. Verify estimated cost shows with label
5. Assign materials and regenerate - verify actual cost shows

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Indicator overload | Subtle icons; filter reduces noise |
| Performance with many items | Cache pending status; lazy load |
| Confusing cost display | Clear "Estimated" vs actual labeling |

## Definition of Done Checklist

- [ ] Pending indicators show on dashboard
- [ ] Indicators are clickable and navigate correctly
- [ ] Tooltips explain pending status
- [ ] Filter works for pending items
- [ ] Shopping list groups generic packaging correctly
- [ ] Generic items display in correct format
- [ ] Estimated costs shown with appropriate labels
- [ ] Manual testing completed

## Review Guidance

- Test with mix of generic and specific compositions
- Verify indicator visibility without being distracting
- Check shopping list totals are accurate
- Confirm estimated vs actual cost distinction is clear

## Activity Log

- 2025-12-21T12:00:00Z - system - lane=planned - Prompt created.
- 2025-12-21T22:17:21Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-21T22:33:34Z – system – shell_pid= – lane=for_review – Moved to for_review
