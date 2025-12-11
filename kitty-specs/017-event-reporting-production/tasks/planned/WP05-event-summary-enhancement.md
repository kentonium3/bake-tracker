---
work_package_id: "WP05"
subtasks:
  - "T020"
  - "T021"
  - "T022"
  - "T023"
title: "Event Summary Enhancement"
phase: "Phase 5 - Event Summary Enhancement"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-11T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Event Summary Enhancement

## Objectives & Success Criteria

**Objective**: Add planned vs actual reporting to Event Detail summary (User Stories 4 & 5).

**Success Criteria**:
- Planned vs actual production displayed (batches) (FR-011)
- Planned vs actual assembly displayed (quantity) (FR-012)
- Package fulfillment status counts shown (FR-013)
- Cost variance displayed (estimated vs actual) (FR-014)
- Cost totals match sum of consumption record costs (SC-004)

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`
- Data Model: `kitty-specs/017-event-reporting-production/data-model.md`

**Architectural Constraints**:
- Use existing service methods where possible
- New `get_event_cost_analysis()` from WP01 for cost data
- Keep UI layout consistent with existing EventDetailWindow style

**Existing Service Methods**:
- `get_production_progress(event_id)` - production targets vs actual
- `get_assembly_progress(event_id)` - assembly targets vs actual
- `get_event_overall_progress(event_id)` - package status counts
- `get_event_cost_analysis(event_id)` - cost breakdown (from WP01)

**Dependencies**:
- WP01 must be complete (`get_event_cost_analysis()` service method)

## Subtasks & Detailed Guidance

### Subtask T020 - Add planned vs actual production section

**Purpose**: Show recipes: planned batches vs actual batches produced.

**Steps**:
1. Open `src/ui/event_detail_window.py`
2. Find or create Summary tab (may already exist or need to be added to EventDetailWindow)
3. Add production summary section:
   ```python
   def _create_summary_production_section(self, parent):
       """Create production planned vs actual section."""
       prod_frame = ctk.CTkFrame(parent)
       prod_frame.pack(fill="x", padx=10, pady=5)

       ctk.CTkLabel(
           prod_frame,
           text="Production Summary",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", padx=5, pady=5)

       # Get progress data
       progress = event_service.get_production_progress(self.event.id)

       if not progress:
           ctk.CTkLabel(
               prod_frame,
               text="No production targets set",
               text_color="gray"
           ).pack(pady=10)
           return

       # Create table header
       header = ctk.CTkFrame(prod_frame)
       header.pack(fill="x", padx=5)

       for col, width in [("Recipe", 150), ("Target", 80), ("Actual", 80), ("%", 60)]:
           ctk.CTkLabel(
               header,
               text=col,
               width=width,
               font=ctk.CTkFont(weight="bold")
           ).pack(side="left")

       # Data rows
       for item in progress:
           row = ctk.CTkFrame(prod_frame)
           row.pack(fill="x", padx=5)

           pct = item["progress_pct"]
           pct_text = f"{pct:.0f}%"

           ctk.CTkLabel(row, text=item["recipe_name"], width=150, anchor="w").pack(side="left")
           ctk.CTkLabel(row, text=str(item["target_batches"]), width=80).pack(side="left")
           ctk.CTkLabel(row, text=str(item["produced_batches"]), width=80).pack(side="left")
           ctk.CTkLabel(
               row,
               text=pct_text,
               width=60,
               text_color="green" if pct >= 100 else None
           ).pack(side="left")
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: Yes (with T021, T022, T023 after section structure created)

---

### Subtask T021 - Add planned vs actual assembly section

**Purpose**: Show finished goods: planned quantity vs actual assembled.

**Steps**:
1. Add assembly summary section (similar to production):
   ```python
   def _create_summary_assembly_section(self, parent):
       """Create assembly planned vs actual section."""
       asm_frame = ctk.CTkFrame(parent)
       asm_frame.pack(fill="x", padx=10, pady=5)

       ctk.CTkLabel(
           asm_frame,
           text="Assembly Summary",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", padx=5, pady=5)

       progress = event_service.get_assembly_progress(self.event.id)

       if not progress:
           ctk.CTkLabel(
               asm_frame,
               text="No assembly targets set",
               text_color="gray"
           ).pack(pady=10)
           return

       # Create table header
       header = ctk.CTkFrame(asm_frame)
       header.pack(fill="x", padx=5)

       for col, width in [("Finished Good", 150), ("Target", 80), ("Actual", 80), ("%", 60)]:
           ctk.CTkLabel(
               header,
               text=col,
               width=width,
               font=ctk.CTkFont(weight="bold")
           ).pack(side="left")

       # Data rows
       for item in progress:
           row = ctk.CTkFrame(asm_frame)
           row.pack(fill="x", padx=5)

           pct = item["progress_pct"]
           pct_text = f"{pct:.0f}%"

           ctk.CTkLabel(row, text=item["finished_good_name"], width=150, anchor="w").pack(side="left")
           ctk.CTkLabel(row, text=str(item["target_quantity"]), width=80).pack(side="left")
           ctk.CTkLabel(row, text=str(item["assembled_quantity"]), width=80).pack(side="left")
           ctk.CTkLabel(
               row,
               text=pct_text,
               width=60,
               text_color="green" if pct >= 100 else None
           ).pack(side="left")
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: Yes (with T020, T022, T023)

---

### Subtask T022 - Add package fulfillment status counts

**Purpose**: Show count of packages by status (pending/ready/delivered).

**Steps**:
1. Add fulfillment status section:
   ```python
   def _create_summary_fulfillment_section(self, parent):
       """Create package fulfillment status section."""
       status_frame = ctk.CTkFrame(parent)
       status_frame.pack(fill="x", padx=10, pady=5)

       ctk.CTkLabel(
           status_frame,
           text="Package Fulfillment",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", padx=5, pady=5)

       # Get overall progress which includes package counts
       progress = event_service.get_event_overall_progress(self.event.id)

       # Create status row
       counts_frame = ctk.CTkFrame(status_frame)
       counts_frame.pack(fill="x", padx=5, pady=5)

       # Pending
       ctk.CTkLabel(
           counts_frame,
           text=f"Pending: {progress['packages_pending']}",
           fg_color="#FFE4B5",  # Light orange
           corner_radius=5,
           padx=10,
           pady=5
       ).pack(side="left", padx=5)

       # Ready
       ctk.CTkLabel(
           counts_frame,
           text=f"Ready: {progress['packages_ready']}",
           fg_color="#90EE90",  # Light green
           corner_radius=5,
           padx=10,
           pady=5
       ).pack(side="left", padx=5)

       # Delivered
       ctk.CTkLabel(
           counts_frame,
           text=f"Delivered: {progress['packages_delivered']}",
           fg_color="#87CEEB",  # Light blue
           corner_radius=5,
           padx=10,
           pady=5
       ).pack(side="left", padx=5)

       # Total
       ctk.CTkLabel(
           counts_frame,
           text=f"Total: {progress['packages_total']}"
       ).pack(side="left", padx=10)
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: Yes (with T020, T021, T023)

---

### Subtask T023 - Add cost variance display

**Purpose**: Show estimated vs actual cost with variance.

**Steps**:
1. Add cost variance section:
   ```python
   def _create_summary_cost_section(self, parent):
       """Create cost variance section."""
       cost_frame = ctk.CTkFrame(parent)
       cost_frame.pack(fill="x", padx=10, pady=5)

       ctk.CTkLabel(
           cost_frame,
           text="Cost Analysis",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(anchor="w", padx=5, pady=5)

       # Get cost analysis data
       try:
           costs = event_service.get_event_cost_analysis(self.event.id)
       except Exception as e:
           ctk.CTkLabel(
               cost_frame,
               text=f"Could not load cost data: {e}",
               text_color="red"
           ).pack(pady=10)
           return

       # Cost display frame
       display_frame = ctk.CTkFrame(cost_frame)
       display_frame.pack(fill="x", padx=5, pady=5)

       # Estimated cost
       ctk.CTkLabel(
           display_frame,
           text=f"Estimated: ${costs['estimated_cost']:.2f}",
           font=ctk.CTkFont(size=12)
       ).pack(side="left", padx=10)

       # Actual cost
       ctk.CTkLabel(
           display_frame,
           text=f"Actual: ${costs['grand_total']:.2f}",
           font=ctk.CTkFont(size=12)
       ).pack(side="left", padx=10)

       # Variance (positive = under budget, negative = over budget)
       variance = costs['variance']
       variance_sign = "+" if variance >= 0 else ""
       variance_color = "green" if variance >= 0 else "red"

       ctk.CTkLabel(
           display_frame,
           text=f"Variance: {variance_sign}${variance:.2f}",
           font=ctk.CTkFont(size=12, weight="bold"),
           text_color=variance_color
       ).pack(side="left", padx=10)

       # Breakdown section
       if costs['production_costs'] or costs['assembly_costs']:
           self._create_cost_breakdown(cost_frame, costs)

   def _create_cost_breakdown(self, parent, costs):
       """Create detailed cost breakdown."""
       breakdown_frame = ctk.CTkFrame(parent)
       breakdown_frame.pack(fill="x", padx=5, pady=5)

       # Production costs
       if costs['production_costs']:
           ctk.CTkLabel(
               breakdown_frame,
               text="Production Costs by Recipe:",
               font=ctk.CTkFont(size=11, weight="bold")
           ).pack(anchor="w")

           for item in costs['production_costs']:
               text = f"  {item['recipe_name']}: ${item['total_cost']:.2f} ({item['run_count']} runs)"
               ctk.CTkLabel(breakdown_frame, text=text).pack(anchor="w")

       # Assembly costs
       if costs['assembly_costs']:
           ctk.CTkLabel(
               breakdown_frame,
               text="Assembly Costs by Finished Good:",
               font=ctk.CTkFont(size=11, weight="bold")
           ).pack(anchor="w", pady=(5, 0))

           for item in costs['assembly_costs']:
               text = f"  {item['finished_good_name']}: ${item['total_cost']:.2f} ({item['run_count']} runs)"
               ctk.CTkLabel(breakdown_frame, text=text).pack(anchor="w")
   ```

**Files**: `src/ui/event_detail_window.py`
**Parallel?**: Yes (with T020, T021, T022)

---

## Test Strategy

**Manual Testing**:
1. Open Event Detail for event with production/assembly targets
2. Navigate to Summary tab (or section)
3. Verify production table shows target vs actual batches
4. Verify assembly table shows target vs actual quantity
5. Verify fulfillment counts match package status
6. Verify cost variance is correctly calculated
7. Test with event that has no targets (should show "No targets" messages)
8. Test with event that has targets but no production (0% progress, $0 actual)

**Cost Verification**:
1. Manually sum ProductionRun.total_cost for event
2. Compare with displayed "Actual" cost
3. Should match exactly (SC-004)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No Summary tab exists | May need to add tab to EventDetailWindow |
| Layout crowded | Use scrollable frame if needed |
| Cost data unavailable | Show error message, not crash |
| Color contrast issues | Test with light/dark themes |

## Definition of Done Checklist

- [ ] T020: Production planned vs actual section working
- [ ] T021: Assembly planned vs actual section working
- [ ] T022: Fulfillment status counts displayed
- [ ] T023: Cost variance displayed with breakdown
- [ ] Costs match manual calculation
- [ ] "No data" cases handled gracefully
- [ ] Manual testing confirms accuracy
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Tables show correct target vs actual numbers
2. Percentages calculated correctly (actual/target * 100)
3. Cost variance is positive when under budget
4. Color coding is intuitive (green = good)
5. Breakdown totals sum to grand total

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
