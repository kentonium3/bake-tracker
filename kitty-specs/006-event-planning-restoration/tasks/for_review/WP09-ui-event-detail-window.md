---
work_package_id: "WP09"
subtasks:
  - "T060"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
title: "UI - EventDetailWindow"
phase: "Phase 3 - UI Layer"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "9077"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-03"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP09 - UI - EventDetailWindow

## Objectives & Success Criteria

- Create EventDetailWindow with 4 tabs: Assignments, Recipe Needs, Shopping List, Summary
- Enable full gift planning workflow

**Success Criteria**:
- All 4 tabs display correct data (FR-023 through FR-027)
- Assignments tab allows CRUD (FR-024)
- Recipe Needs shows aggregated batch counts (FR-025)
- Shopping List shows shortfall with pantry data (FR-026)
- Summary shows totals and cost breakdown (FR-027)
- All tabs load in <2 seconds for 50 assignments (SC-004)

## Context & Constraints

**Priority**: P1 - This is critical for the core gift planning workflow (User Story 5).

**Key Documents**:
- `kitty-specs/006-event-planning-restoration/spec.md` - User Stories 5-8
- `kitty-specs/006-event-planning-restoration/contracts/event_service.md` - Service interface
- `kitty-specs/006-event-planning-restoration/quickstart.md` - Usage examples

**Dependencies**: Requires WP04 complete (EventService with all aggregation methods).

## Subtasks & Detailed Guidance

### Subtask T060 - Create EventDetailWindow base frame with tab container

**Purpose**: Window shell with tab navigation.

**Steps**:
1. Create `src/ui/event_detail_window.py`
2. Create EventDetailWindow class (CTkToplevel)
3. Initialize with event_id parameter
4. Add tab container (CTkTabview) with 4 tabs:
   - Assignments
   - Recipe Needs
   - Shopping List
   - Summary
5. Load event data on init

**Files**: `src/ui/event_detail_window.py`

**Example structure**:
```python
class EventDetailWindow(ctk.CTkToplevel):
    def __init__(self, parent, event_id: int):
        super().__init__(parent)
        self.event_id = event_id
        self.event = EventService.get_event_by_id(event_id)
        self.title(f"Event: {self.event.name}")
        self.setup_tabs()

    def setup_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True)

        self.tab_assignments = self.tabview.add("Assignments")
        self.tab_recipe_needs = self.tabview.add("Recipe Needs")
        self.tab_shopping_list = self.tabview.add("Shopping List")
        self.tab_summary = self.tabview.add("Summary")

        # Initialize each tab content
        self.setup_assignments_tab()
        self.setup_recipe_needs_tab()
        self.setup_shopping_list_tab()
        self.setup_summary_tab()
```

### Subtask T061 - Implement Assignments tab (FR-024)

**Purpose**: CRUD for recipient-package assignments.

**Steps**:
1. Create assignments list showing: Recipient, Package, Quantity, Cost
2. Add "Add Assignment" button
3. Implement add dialog with:
   - Recipient dropdown (from RecipientService.get_all_recipients())
   - Package dropdown (from PackageService.get_all_packages())
   - Quantity spinbox
   - Notes field
4. Implement edit/delete on selection
5. Refresh totals on any change
6. Service calls:
   - EventService.assign_package_to_recipient()
   - EventService.update_assignment()
   - EventService.remove_assignment()

**Files**: `src/ui/event_detail_window.py`
**User Story Reference**: User Story 5

### Subtask T062 - Implement Recipe Needs tab (FR-025)

**Purpose**: Display aggregated batch counts per recipe.

**Steps**:
1. Create table/list showing:
   - Recipe Name
   - Total Units Needed
   - Items Per Batch
   - Batches Needed (rounded up)
2. Load data via EventService.get_recipe_needs()
3. Show empty state if no assignments: "No assignments yet"
4. Add refresh button for recalculation

**Files**: `src/ui/event_detail_window.py`
**User Story Reference**: User Story 6

**Example layout**:
```
| Recipe Name          | Units Needed | Per Batch | Batches |
|---------------------|--------------|-----------|---------|
| Chocolate Chip       | 48           | 24        | 2       |
| Brownies            | 36           | 12        | 3       |
```

### Subtask T063 - Implement Shopping List tab (FR-026)

**Purpose**: Display ingredients with on-hand and shortfall.

**Steps**:
1. Create table showing:
   - Ingredient Name
   - Unit
   - Quantity Needed
   - On Hand
   - Shortfall (highlighted if > 0)
2. Load data via EventService.get_shopping_list()
3. Integrate with PantryService for on-hand quantities (FR-029)
4. Highlight shortfall rows (red background or bold text)
5. Show empty state if no assignments

**Files**: `src/ui/event_detail_window.py`
**User Story Reference**: User Story 7

**Example layout**:
```
| Ingredient  | Unit   | Needed | On Hand | Shortfall |
|-------------|--------|--------|---------|-----------|
| Flour       | cups   | 10.5   | 5.0     | 5.5 *     |
| Sugar       | cups   | 8.0    | 10.0    | 0         |
| Butter      | lbs    | 3.0    | 1.5     | 1.5 *     |
```

### Subtask T064 - Implement Summary tab (FR-027)

**Purpose**: Display event totals and cost breakdown.

**Steps**:
1. Display summary metrics:
   - Total Event Cost (formatted as currency)
   - Recipient Count
   - Package Count (sum of quantities)
   - Assignment Count
2. Display cost by recipient table:
   - Recipient Name
   - Total Cost for that recipient
3. Load data via EventService.get_event_summary()
4. Show empty state with zero totals if no assignments

**Files**: `src/ui/event_detail_window.py`
**User Story Reference**: User Story 8

### Subtask T065 - Performance optimization (<2s load time)

**Purpose**: Ensure SC-004 compliance.

**Steps**:
1. Profile each tab loading time
2. Optimize slow queries:
   - Use eager loading for relationships
   - Batch database queries where possible
3. Consider lazy loading tabs (only load when selected)
4. If still slow, use background threading with loading indicator:
   ```python
   def load_tab_in_background(self, tab_name, load_func):
       self.show_loading(tab_name)
       thread = Thread(target=self._load_and_update, args=(tab_name, load_func))
       thread.start()
   ```
5. Test with 50 assignments

**Files**: `src/ui/event_detail_window.py`

### Subtask T066 - Handle empty states for events with no assignments

**Purpose**: User-friendly empty state messages.

**Steps**:
1. For each tab, check if no data:
   - Assignments: "No packages assigned. Click 'Add Assignment' to start."
   - Recipe Needs: "No assignments yet. Add assignments to see recipe needs."
   - Shopping List: "No assignments yet. Add assignments to see shopping list."
   - Summary: Show zero totals with message "Add assignments to see event summary."
2. Use consistent styling for empty state messages

**Files**: `src/ui/event_detail_window.py`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex UI with 4 tabs | Break into separate frame classes |
| Performance with 50+ assignments | Lazy load tabs, use threading |
| PantryService integration | Verify service exists, mock if needed |

## Definition of Done Checklist

- [ ] EventDetailWindow opens from Events tab
- [ ] Assignments tab: CRUD works (FR-024)
- [ ] Recipe Needs tab: Batch counts correct (FR-025)
- [ ] Shopping List tab: Shortfall calculated (FR-026)
- [ ] Summary tab: Totals correct (FR-027)
- [ ] All tabs load in <2s with 50 assignments (SC-004)
- [ ] Empty states display correctly
- [ ] User Stories 5-8 acceptance scenarios pass
- [ ] `tasks.md` updated with status change

## Review Guidance

- Verify cost calculations match manual verification (SC-002)
- Test recipe needs aggregation across multiple packages
- Check shopping list shortfall accuracy (SC-003)
- Performance test with 50 assignments

## Activity Log

- 2025-12-03 - system - lane=planned - Prompt created.
- 2025-12-04T02:52:58Z – claude – shell_pid=9077 – lane=for_review – Completed: EventDetailWindow verified - imports work, exception fixed
