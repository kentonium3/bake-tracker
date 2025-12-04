---
work_package_id: "WP06"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Production Tab UI - Status & Costs"
phase: "Phase 3 - UI Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "62373"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Production Tab UI - Status & Costs

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add package status toggle controls (pending/assembled/delivered)
- Display actual vs planned cost comparison at event level
- Add recipe cost breakdown drill-down view
- Add visual progress bars for completion tracking
- Users can update package status within 2 clicks

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/008-production-tracking/spec.md` (User Story 2, 3, 5)
- Service Contract: `kitty-specs/008-production-tracking/contracts/production_service.md`

**Dependencies**:
- WP05: ProductionTab exists with basic structure
- WP03: update_package_status() service function
- WP04: get_recipe_cost_breakdown() service function

---

## Subtasks & Detailed Guidance

### Subtask T024 - Implement Package Status Controls [P]

**Purpose**: Allow users to change package status through UI.

**Steps**:
1. Add package list section to event detail view
2. Show each package with recipient name and current status
3. Add status toggle buttons (Assembled, Delivered)
4. Call update_package_status on click
5. Show feedback for blocked transitions

```python
def _create_package_status_section(self, event_id: int, progress: dict):
    """Create package status controls."""
    section = ctk.CTkFrame(self.detail_panel)
    section.pack(fill="x", padx=10, pady=10)

    header = ctk.CTkLabel(
        section,
        text="Package Status",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    header.pack(pady=5)

    # Get assignments for this event
    try:
        assignments = self._get_event_assignments(event_id)

        for assignment in assignments:
            self._create_package_row(section, assignment, event_id)

    except Exception as e:
        error = ctk.CTkLabel(section, text=f"Error: {e}", text_color="red")
        error.pack()


def _create_package_row(self, parent, assignment: dict, event_id: int):
    """Create a row for one package assignment."""
    row = ctk.CTkFrame(parent)
    row.pack(fill="x", pady=2, padx=5)

    # Recipient and package name
    info = ctk.CTkLabel(
        row,
        text=f"{assignment['recipient_name']} - {assignment['package_name']}",
        width=200
    )
    info.pack(side="left", padx=5)

    # Current status
    status = assignment['status']
    status_label = ctk.CTkLabel(row, text=status.upper(), width=80)

    if status == 'delivered':
        status_label.configure(text_color="green")
    elif status == 'assembled':
        status_label.configure(text_color="blue")
    else:
        status_label.configure(text_color="gray")

    status_label.pack(side="left", padx=5)

    # Action buttons based on current status
    if status == 'pending':
        assemble_btn = ctk.CTkButton(
            row,
            text="Mark Assembled",
            width=120,
            command=lambda: self._update_status(
                assignment['id'], 'assembled', event_id
            )
        )
        assemble_btn.pack(side="right", padx=2)

    elif status == 'assembled':
        deliver_btn = ctk.CTkButton(
            row,
            text="Mark Delivered",
            width=120,
            command=lambda: self._show_delivery_dialog(
                assignment['id'], event_id
            )
        )
        deliver_btn.pack(side="right", padx=2)

    elif status == 'delivered':
        if assignment.get('delivered_to'):
            note = ctk.CTkLabel(
                row,
                text=f"({assignment['delivered_to']})",
                font=ctk.CTkFont(size=10)
            )
            note.pack(side="right", padx=5)


def _update_status(self, assignment_id: int, new_status: str, event_id: int):
    """Update package status via service."""
    from src.models import PackageStatus

    status_map = {
        'pending': PackageStatus.PENDING,
        'assembled': PackageStatus.ASSEMBLED,
        'delivered': PackageStatus.DELIVERED
    }

    try:
        production_service.update_package_status(
            assignment_id=assignment_id,
            new_status=status_map[new_status]
        )

        # Refresh view
        self._load_data()
        self._load_event_detail(event_id)

    except production_service.IncompleteProductionError as e:
        missing = ", ".join(r['recipe_name'] for r in e.missing_recipes)
        self._show_error(f"Cannot assemble: Missing production for {missing}")

    except production_service.InvalidStatusTransitionError as e:
        self._show_error(f"Cannot change from {e.current.value} to {e.target.value}")

    except Exception as e:
        self._show_error(str(e))


def _show_delivery_dialog(self, assignment_id: int, event_id: int):
    """Show dialog to optionally add delivery note."""
    dialog = ctk.CTkInputDialog(
        title="Mark as Delivered",
        text="Optional delivery note (e.g., 'Left with neighbor'):"
    )
    note = dialog.get_input()

    from src.models import PackageStatus
    try:
        production_service.update_package_status(
            assignment_id=assignment_id,
            new_status=PackageStatus.DELIVERED,
            delivered_to=note if note else None
        )
        self._load_data()
        self._load_event_detail(event_id)
    except Exception as e:
        self._show_error(str(e))
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T025 - Implement Cost Comparison Display [P]

**Purpose**: Show actual vs planned costs at event level.

**Steps**:
1. Add cost summary section to event detail
2. Show actual total, planned total, variance
3. Color-code (green: under budget, red: over budget)

```python
def _create_cost_summary(self, progress: dict):
    """Create cost comparison display."""
    section = ctk.CTkFrame(self.detail_panel)
    section.pack(fill="x", padx=10, pady=10)

    header = ctk.CTkLabel(
        section,
        text="Cost Summary",
        font=ctk.CTkFont(size=14, weight="bold")
    )
    header.pack(pady=5)

    costs = progress['costs']
    actual = float(costs['actual_total'])
    planned = float(costs['planned_total'])
    variance = actual - planned

    # Actual cost
    actual_label = ctk.CTkLabel(
        section,
        text=f"Actual Cost: ${actual:.2f}",
        font=ctk.CTkFont(size=16)
    )
    actual_label.pack()

    # Planned cost
    planned_label = ctk.CTkLabel(
        section,
        text=f"Planned Cost: ${planned:.2f}",
        font=ctk.CTkFont(size=14)
    )
    planned_label.pack()

    # Variance
    if variance > 0:
        variance_text = f"Over budget: +${variance:.2f}"
        color = "red"
    elif variance < 0:
        variance_text = f"Under budget: ${variance:.2f}"
        color = "green"
    else:
        variance_text = "On budget"
        color = "gray"

    variance_label = ctk.CTkLabel(
        section,
        text=variance_text,
        text_color=color,
        font=ctk.CTkFont(size=12)
    )
    variance_label.pack()

    # Drill-down button
    breakdown_btn = ctk.CTkButton(
        section,
        text="View Recipe Breakdown",
        command=lambda: self._show_cost_breakdown(progress['event_id'])
    )
    breakdown_btn.pack(pady=10)
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T026 - Implement Recipe Cost Drill-Down [P]

**Purpose**: Show per-recipe cost breakdown with variance.

**Steps**:
1. Create expandable or popup view for recipe costs
2. Show each recipe with actual, planned, variance, variance %
3. Highlight recipes with significant variance

```python
def _show_cost_breakdown(self, event_id: int):
    """Show detailed recipe cost breakdown in a popup."""
    try:
        breakdown = production_service.get_recipe_cost_breakdown(event_id)

        # Create popup window
        popup = ctk.CTkToplevel(self)
        popup.title("Recipe Cost Breakdown")
        popup.geometry("500x400")

        # Header
        header = ctk.CTkLabel(
            popup,
            text="Cost by Recipe",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.pack(pady=10)

        # Scrollable frame for recipes
        scroll = ctk.CTkScrollableFrame(popup)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Table header
        header_frame = ctk.CTkFrame(scroll)
        header_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(header_frame, text="Recipe", width=150, anchor="w").pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="Actual", width=70, anchor="e").pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="Planned", width=70, anchor="e").pack(side="left", padx=2)
        ctk.CTkLabel(header_frame, text="Variance", width=80, anchor="e").pack(side="left", padx=2)

        # Recipe rows
        for recipe in breakdown:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=1)

            actual = float(recipe['actual_cost'])
            planned = float(recipe['planned_cost'])
            variance = float(recipe['variance'])
            variance_pct = recipe['variance_percent']

            ctk.CTkLabel(row, text=recipe['recipe_name'], width=150, anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=f"${actual:.2f}", width=70, anchor="e").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=f"${planned:.2f}", width=70, anchor="e").pack(side="left", padx=2)

            # Variance with color
            if variance > 0:
                var_text = f"+${variance:.2f} ({variance_pct:+.1f}%)"
                color = "red"
            elif variance < 0:
                var_text = f"${variance:.2f} ({variance_pct:+.1f}%)"
                color = "green"
            else:
                var_text = "$0.00 (0%)"
                color = "gray"

            ctk.CTkLabel(row, text=var_text, width=100, anchor="e", text_color=color).pack(side="left", padx=2)

        # Close button
        close_btn = ctk.CTkButton(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=10)

    except Exception as e:
        self._show_error(f"Error loading breakdown: {e}")
```

**Files**: `src/ui/production_tab.py` (ADD)

---

### Subtask T027 - Add Progress Bars [P]

**Purpose**: Visual indicators for completion progress.

**Steps**:
1. Add progress bar for recipe completion (X of Y complete)
2. Add progress bar for package delivery (X of Y delivered)
3. Use CustomTkinter CTkProgressBar

```python
def _create_progress_indicators(self, progress: dict):
    """Create visual progress bars."""
    section = ctk.CTkFrame(self.detail_panel)
    section.pack(fill="x", padx=10, pady=10)

    # Recipe progress
    recipe_frame = ctk.CTkFrame(section)
    recipe_frame.pack(fill="x", pady=5)

    recipes_complete = sum(1 for r in progress['recipes'] if r['is_complete'])
    recipes_total = len(progress['recipes'])
    recipe_pct = recipes_complete / recipes_total if recipes_total > 0 else 0

    ctk.CTkLabel(
        recipe_frame,
        text=f"Recipes: {recipes_complete}/{recipes_total}"
    ).pack(side="left", padx=5)

    recipe_bar = ctk.CTkProgressBar(recipe_frame, width=200)
    recipe_bar.set(recipe_pct)
    recipe_bar.pack(side="left", padx=5)

    # Package progress
    pkg_frame = ctk.CTkFrame(section)
    pkg_frame.pack(fill="x", pady=5)

    pkg = progress['packages']
    delivered = pkg['delivered']
    total = pkg['total']
    pkg_pct = delivered / total if total > 0 else 0

    ctk.CTkLabel(
        pkg_frame,
        text=f"Delivered: {delivered}/{total}"
    ).pack(side="left", padx=5)

    pkg_bar = ctk.CTkProgressBar(pkg_frame, width=200)
    pkg_bar.set(pkg_pct)
    pkg_bar.pack(side="left", padx=5)

    # Assembly progress (assembled + delivered)
    assembled_frame = ctk.CTkFrame(section)
    assembled_frame.pack(fill="x", pady=5)

    assembled_plus_delivered = pkg['assembled'] + pkg['delivered']
    assembled_pct = assembled_plus_delivered / total if total > 0 else 0

    ctk.CTkLabel(
        assembled_frame,
        text=f"Assembled: {assembled_plus_delivered}/{total}"
    ).pack(side="left", padx=5)

    assembled_bar = ctk.CTkProgressBar(assembled_frame, width=200)
    assembled_bar.set(assembled_pct)
    assembled_bar.pack(side="left", padx=5)
```

**Files**: `src/ui/production_tab.py` (ADD)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Status change fails silently | Show clear error messages |
| Users click wrong status button | Use clear button labels, consider confirmation |
| Cost breakdown popup cluttered | Use scrollable frame, limit to essential info |

---

## Definition of Done Checklist

- [ ] Package status can be changed via toggle buttons
- [ ] Invalid transitions show clear error messages
- [ ] Delivery note can be optionally added
- [ ] Cost summary shows actual/planned/variance
- [ ] Recipe breakdown drill-down available
- [ ] Progress bars show visual completion status
- [ ] All changes refresh the display immediately
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify status transitions call service correctly
- Verify error messages are user-friendly
- Check cost calculations display correctly
- Verify progress bars update on data changes

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-04T16:51:07Z – claude – shell_pid=62373 – lane=doing – Started implementation
