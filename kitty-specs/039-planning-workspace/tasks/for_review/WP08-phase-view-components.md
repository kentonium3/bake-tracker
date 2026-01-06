---
work_package_id: "WP08"
subtasks:
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
title: "Phase View Components"
phase: "Phase 3 - UI"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "70991"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T03:09:20Z"
    lane: "planned"
    agent: "claude"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Phase View Components

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create four phase view components: Calculate, Shop, Produce, Assemble
- Each view displays phase-specific data from PlanningService
- Implement user interactions for each phase

**Success Metrics (from spec):**
- US1: Calculate phase shows batch counts and waste
- US2: Shop phase shows Need/Have/Buy columns
- US4: Produce phase shows progress bars per recipe
- US5: Assemble phase shows checklist with partial assembly support

---

## Context & Constraints

### Reference Documents
- **Quickstart**: `kitty-specs/039-planning-workspace/quickstart.md` - UI guidelines
- **Spec**: `kitty-specs/039-planning-workspace/spec.md` - User stories and acceptance criteria
- **Contract**: `kitty-specs/039-planning-workspace/contracts/planning_service.py` - DTOs

### Key Constraints
- Uses CustomTkinter components
- All views are CTkFrame that can be swapped by container
- Views call PlanningService for data - no direct model access
- Parallelizable (all four views can be developed concurrently)

### Architectural Notes
- Located in `src/ui/planning/` module
- Each view is self-contained frame
- Use consistent color/style patterns across views

---

## Subtasks & Detailed Guidance

### Subtask T049 - Create calculate_view.py [P]

- **Purpose**: Calculate phase UI (User Story 1)
- **Steps**:
  1. Create `src/ui/planning/calculate_view.py`
  2. Define CalculateView class:
     ```python
     class CalculateView(ctk.CTkFrame):
         def __init__(self, parent, event_id: int, on_calculated: Callable = None, **kwargs):
             super().__init__(parent, **kwargs)
             self.event_id = event_id
             self.on_calculated = on_calculated
             self._setup_ui()
     ```
  3. UI elements:
     - "Calculate Plan" button (prominent)
     - Results table (recipe, units needed, batches, yield, waste)
     - Waste percentage display with color coding
  4. On calculate:
     - Call `planning_service.calculate_plan(event_id)`
     - Display results in table
     - Call `on_calculated` callback
- **Files**: `src/ui/planning/calculate_view.py`
- **Parallel?**: Yes - can develop alongside other views

### Subtask T050 - Create shop_view.py [P]

- **Purpose**: Shopping phase UI (User Story 2)
- **Steps**:
  1. Create `src/ui/planning/shop_view.py`
  2. Define ShopView class:
     ```python
     class ShopView(ctk.CTkFrame):
         def __init__(self, parent, event_id: int, **kwargs):
             super().__init__(parent, **kwargs)
             self.event_id = event_id
             self._setup_ui()
             self._load_shopping_list()
     ```
  3. UI elements:
     - Shopping list table: Ingredient | Need | Have | Buy
     - Color coding: green for sufficient, red for needs purchase
     - "Mark Shopping Complete" button
  4. Data: call `planning_service.get_shopping_list(event_id)`
- **Files**: `src/ui/planning/shop_view.py`
- **Parallel?**: Yes

### Subtask T051 - Create produce_view.py [P]

- **Purpose**: Production phase UI (User Story 4)
- **Steps**:
  1. Create `src/ui/planning/produce_view.py`
  2. Define ProduceView class:
     ```python
     class ProduceView(ctk.CTkFrame):
         def __init__(self, parent, event_id: int, **kwargs):
             super().__init__(parent, **kwargs)
             self.event_id = event_id
             self._setup_ui()
             self._load_progress()
     ```
  3. UI elements:
     - Recipe list with progress bars
     - "X/Y batches (Z%)" label per recipe
     - Overall production progress at top
     - Link to production recording (if available)
  4. Data: call `planning_service.get_production_progress(event_id)`
- **Files**: `src/ui/planning/produce_view.py`
- **Parallel?**: Yes

### Subtask T052 - Create assemble_view.py [P]

- **Purpose**: Assembly phase UI (User Story 5)
- **Steps**:
  1. Create `src/ui/planning/assemble_view.py`
  2. Define AssembleView class:
     ```python
     class AssembleView(ctk.CTkFrame):
         def __init__(self, parent, event_id: int, **kwargs):
             super().__init__(parent, **kwargs)
             self.event_id = event_id
             self._setup_ui()
             self._load_checklist()
     ```
  3. UI elements:
     - Assembly checklist with checkboxes
     - "X of Y available to assemble" per bundle
     - Disabled items for incomplete production
     - Feasibility status indicators
  4. Data: call `planning_service.get_assembly_checklist(event_id)`
- **Files**: `src/ui/planning/assemble_view.py`
- **Parallel?**: Yes

### Subtask T053 - Implement calculate button and results table [P]

- **Purpose**: Complete calculate_view functionality
- **Steps**:
  1. Add calculate button handler:
     ```python
     def _on_calculate_click(self):
         try:
             result = planning_service.calculate_plan(self.event_id)
             self._display_results(result)
             if self.on_calculated:
                 self.on_calculated()
         except PlanningError as e:
             self._show_error(str(e))
     ```
  2. Implement results table:
     - Use CTkScrollableFrame for long lists
     - Columns: Recipe | Units Needed | Batches | Total Yield | Waste
     - Sortable by column (optional)
  3. Waste color coding:
     - Green: <5%
     - Yellow: 5-15%
     - Orange: >15%
- **Files**: `src/ui/planning/calculate_view.py`
- **Parallel?**: Yes

### Subtask T054 - Implement shopping list table styling [P]

- **Purpose**: Style shopping list with sufficient/needs-purchase
- **Steps**:
  1. Implement table rows:
     ```python
     def _add_shopping_row(self, item: ShoppingListItem):
         row = CTkFrame(self.table_frame)
         # Ingredient name
         CTkLabel(row, text=item.ingredient_name)
         # Need column
         CTkLabel(row, text=f"{item.needed} {item.unit}")
         # Have column
         CTkLabel(row, text=f"{item.in_stock} {item.unit}")
         # Buy column with color
         buy_color = "green" if item.is_sufficient else "red"
         CTkLabel(row, text=f"{item.to_buy} {item.unit}", text_color=buy_color)
     ```
  2. Add "Mark Shopping Complete" button:
     ```python
     def _on_mark_complete(self):
         planning_service.mark_shopping_complete(self.event_id)
         self._show_success("Shopping marked complete")
     ```
  3. Filter toggle: "Show all" / "Show items to buy only"
- **Files**: `src/ui/planning/shop_view.py`
- **Parallel?**: Yes

### Subtask T055 - Implement progress bars per recipe [P]

- **Purpose**: Visual progress for production
- **Steps**:
  1. Implement progress row:
     ```python
     def _add_progress_row(self, progress: ProductionProgress):
         row = CTkFrame(self.progress_frame)
         # Recipe name
         CTkLabel(row, text=progress.recipe_name)
         # Progress bar
         bar = CTkProgressBar(row)
         bar.set(progress.progress_percent / 100)
         # Progress text
         CTkLabel(row, text=f"{progress.completed_batches}/{progress.target_batches} ({progress.progress_percent:.0f}%)")
         # Checkmark if complete
         if progress.is_complete:
             CTkLabel(row, text="✓", text_color="green")
     ```
  2. Add overall progress at top:
     ```python
     overall = planning_service.get_overall_progress(self.event_id)
     CTkLabel(self, text=f"Overall: {overall['production_percent']:.0f}% production complete")
     ```
- **Files**: `src/ui/planning/produce_view.py`
- **Parallel?**: Yes

### Subtask T056 - Implement assembly checklist UI [P]

- **Purpose**: Checklist with partial assembly support (FR-036)
- **Steps**:
  1. Implement checklist item:
     ```python
     def _add_checklist_item(self, item: dict):
         row = CTkFrame(self.checklist_frame)
         # Checkbox (enabled if available > 0)
         checkbox = CTkCheckBox(row, text=item['finished_good_name'])
         checkbox.configure(state="normal" if item['available'] > 0 else "disabled")
         # Available count
         CTkLabel(row, text=f"{item['available']} of {item['target']} available")
         # If disabled, show reason
         if item['available'] == 0:
             CTkLabel(row, text="Awaiting production", text_color="gray")
     ```
  2. Handle checkbox change:
     ```python
     def _on_checkbox_change(self, item_id: int, quantity: int):
         planning_service.record_assembly_confirmation(
             self.event_id, item_id, quantity
         )
         self._refresh_checklist()
     ```
  3. Support partial assembly: "Assemble X" input for partial counts
- **Files**: `src/ui/planning/assemble_view.py`
- **Parallel?**: Yes

### Subtask T057 - Implement feasibility indicators [P]

- **Purpose**: Visual feasibility status (FR-024-026)
- **Steps**:
  1. Add feasibility section to assemble_view:
     ```python
     def _show_feasibility(self):
         results = planning_service.check_assembly_feasibility(self.event_id)
         for result in results:
             row = CTkFrame(self.feasibility_frame)
             # Bundle name
             CTkLabel(row, text=result.finished_good_name)
             # Status indicator
             status_color = {
                 FeasibilityStatus.CAN_ASSEMBLE: "green",
                 FeasibilityStatus.PARTIAL: "yellow",
                 FeasibilityStatus.AWAITING_PRODUCTION: "orange",
                 FeasibilityStatus.CANNOT_ASSEMBLE: "red",
             }.get(result.status)
             CTkLabel(row, text=f"● {result.status.value}", text_color=status_color)
             # Can assemble count
             CTkLabel(row, text=f"Can assemble: {result.can_assemble}/{result.target_quantity}")
     ```
  2. Show missing components on click/expand
- **Files**: `src/ui/planning/assemble_view.py`
- **Parallel?**: Yes

---

## Test Strategy

**Manual Testing Required:**
- Calculate view: click calculate, verify table populates
- Shop view: verify Need/Have/Buy columns, mark complete
- Produce view: verify progress bars update
- Assemble view: verify checklist enables/disables correctly, partial assembly works

**Run app with:**
```bash
python src/main.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Inconsistent styling | Define shared color constants |
| Large data sets | Use scrollable frames |
| Slow refresh | Cache data, refresh on demand |

---

## Definition of Done Checklist

- [ ] calculate_view.py created with calculate button and results table
- [ ] shop_view.py created with Need/Have/Buy table and complete button
- [ ] produce_view.py created with progress bars per recipe
- [ ] assemble_view.py created with checklist and feasibility indicators
- [ ] Color coding consistent across views
- [ ] Disabled states work correctly
- [ ] Partial assembly supported
- [ ] Manual testing passes for all views
- [ ] `tasks.md` updated with status change

---

## Review Guidance

- Verify acceptance criteria from user stories
- Check color coding is consistent
- Test with realistic data (10+ recipes)
- Validate disabled states for incomplete prerequisites

---

## Activity Log

- 2026-01-06T03:09:20Z - claude - lane=planned - Prompt created.
- 2026-01-06T14:20:51Z – claude – shell_pid=69364 – lane=doing – Started implementation - Phase View Components (Calculate, Shop, Produce, Assemble)
- 2026-01-06T15:18:42Z – claude – shell_pid=70991 – lane=for_review – Implementation complete - All four phase views (Calculate, Shop, Produce, Assemble) with full functionality
