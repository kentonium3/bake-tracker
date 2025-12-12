---
work_package_id: "WP06"
subtasks:
  - "T024"
  - "T025"
  - "T026"
title: "Recipient History"
phase: "Phase 6 - Recipient History"
lane: "done"
assignee: ""
agent: "system"
shell_pid: ""
review_status: "approved without changes"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-11T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Recipient History

## Objectives & Success Criteria

**Objective**: Add package history to recipient detail view (User Story 6).

**Success Criteria**:
- Recipient detail shows package history across all events (FR-019)
- History displays: event name, package name, quantity, fulfillment status (FR-020)
- History sorted by event date descending (FR-021)
- "No package history" message when recipient has no assignments

## Context & Constraints

**Reference Documents**:
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`

**Architectural Constraints**:
- Use enhanced `get_recipient_history()` from WP01 (includes fulfillment_status)
- Keep UI consistent with existing RecipientsTab patterns
- History is read-only display (no editing)

**Dependencies**:
- WP01 must be complete (enhanced `get_recipient_history()`)

## Subtasks & Detailed Guidance

### Subtask T024 - Add history section to recipient detail view

**Purpose**: Create UI section to display recipient's package history.

**Steps**:
1. Open `src/ui/recipients_tab.py`
2. Find where recipient detail is displayed (may be in a dialog or detail pane)
3. Add history section frame:
   ```python
   def _create_recipient_history_section(self, parent, recipient_id: int):
       """Create package history section for recipient."""
       history_frame = ctk.CTkFrame(parent)
       history_frame.pack(fill="both", expand=True, padx=10, pady=5)

       # Header
       header_frame = ctk.CTkFrame(history_frame)
       header_frame.pack(fill="x", padx=5, pady=5)

       ctk.CTkLabel(
           header_frame,
           text="Package History",
           font=ctk.CTkFont(size=14, weight="bold")
       ).pack(side="left")

       # Scrollable content
       self.history_scroll = ctk.CTkScrollableFrame(
           history_frame,
           height=200
       )
       self.history_scroll.pack(fill="both", expand=True, padx=5, pady=5)

       # Load and display history
       self._load_recipient_history(recipient_id)

       return history_frame
   ```

4. If recipients_tab uses a dialog for detail view, add to dialog:
   ```python
   class RecipientDetailDialog(ctk.CTkToplevel):
       def __init__(self, parent, recipient):
           super().__init__(parent)
           self.recipient = recipient
           # ... existing fields ...

           # Add history section
           self._create_recipient_history_section(self, recipient.id)
   ```

**Files**: `src/ui/recipients_tab.py`
**Parallel?**: No (must complete before T025)
**Notes**: Explore existing code structure to find best integration point.

---

### Subtask T025 - Display events, packages, quantities, fulfillment status

**Purpose**: Populate history table with data from service.

**Steps**:
1. Add method to load and display history:
   ```python
   def _load_recipient_history(self, recipient_id: int):
       """Load and display recipient's package history."""
       from src.services import event_service

       try:
           history = event_service.get_recipient_history(recipient_id)
       except Exception as e:
           ctk.CTkLabel(
               self.history_scroll,
               text=f"Error loading history: {e}",
               text_color="red"
           ).pack(pady=10)
           return

       if not history:
           ctk.CTkLabel(
               self.history_scroll,
               text="No package history",
               text_color="gray"
           ).pack(pady=20)
           return

       # Create table header
       header = ctk.CTkFrame(self.history_scroll)
       header.pack(fill="x", pady=(0, 5))

       columns = [
           ("Event", 120),
           ("Date", 80),
           ("Package", 120),
           ("Qty", 40),
           ("Status", 80)
       ]

       for col_name, width in columns:
           ctk.CTkLabel(
               header,
               text=col_name,
               width=width,
               font=ctk.CTkFont(weight="bold"),
               anchor="w"
           ).pack(side="left", padx=2)

       # Data rows
       for record in history:
           self._create_history_row(record)

   def _create_history_row(self, record: dict):
       """Create a single history row."""
       row = ctk.CTkFrame(self.history_scroll)
       row.pack(fill="x", pady=1)

       # Event name
       event_name = record["event"].name if record["event"] else "Unknown"
       ctk.CTkLabel(row, text=event_name, width=120, anchor="w").pack(side="left", padx=2)

       # Event date
       event_date = ""
       if record["event"] and record["event"].event_date:
           event_date = record["event"].event_date.strftime("%Y-%m-%d")
       ctk.CTkLabel(row, text=event_date, width=80, anchor="w").pack(side="left", padx=2)

       # Package name
       package_name = record["package"].name if record["package"] else "Unknown"
       ctk.CTkLabel(row, text=package_name, width=120, anchor="w").pack(side="left", padx=2)

       # Quantity
       ctk.CTkLabel(row, text=str(record["quantity"]), width=40, anchor="w").pack(side="left", padx=2)

       # Status with color coding
       status = record.get("fulfillment_status", "pending") or "pending"
       status_colors = {
           "pending": ("#FFE4B5", "black"),    # Orange background
           "ready": ("#90EE90", "black"),      # Green background
           "delivered": ("#87CEEB", "black")   # Blue background
       }
       bg_color, text_color = status_colors.get(status, (None, None))

       status_label = ctk.CTkLabel(
           row,
           text=status.capitalize(),
           width=80,
           anchor="w"
       )
       if bg_color:
           status_label.configure(fg_color=bg_color, text_color=text_color, corner_radius=3)
       status_label.pack(side="left", padx=2)
   ```

**Files**: `src/ui/recipients_tab.py`
**Parallel?**: No (builds on T024)

---

### Subtask T026 - Sort history by event date descending

**Purpose**: Most recent events appear first for easier viewing.

**Steps**:
1. The service method `get_recipient_history()` already returns data sorted by `Event.event_date.desc()` (see event_service.py line 1469)

2. Verify sorting is preserved in display - no additional work needed if using the service method correctly

3. If history appears unsorted, add explicit sort in UI:
   ```python
   # In _load_recipient_history():
   history = event_service.get_recipient_history(recipient_id)

   # Sort by event date descending (should already be sorted by service)
   history.sort(
       key=lambda r: r["event"].event_date if r["event"] else date.min,
       reverse=True
   )
   ```

**Files**: `src/ui/recipients_tab.py`
**Parallel?**: No (verification step)
**Notes**: Service already handles sorting - just verify it works.

---

## Test Strategy

**Manual Testing**:
1. Create/find recipient with packages in multiple events
2. Open Recipients tab
3. Select recipient to view detail
4. Verify history section appears
5. Verify columns: Event, Date, Package, Qty, Status
6. Verify sorted by date (most recent first)
7. Verify status badges have correct colors
8. Test with recipient that has no packages (should show "No package history")

**Test Data Setup**:
```sql
-- Find a recipient with packages
SELECT r.name, e.name as event, p.name as package, erp.quantity, erp.fulfillment_status
FROM recipients r
JOIN event_recipient_packages erp ON erp.recipient_id = r.id
JOIN events e ON e.id = erp.event_id
JOIN packages p ON p.id = erp.package_id
ORDER BY r.name, e.event_date DESC;
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No detail view exists | May need to create dialog or detail pane |
| Long history doesn't fit | Use CTkScrollableFrame |
| Event/package deleted | Show "Unknown" rather than crash |
| Status color not visible | Test with both light/dark themes |

## Definition of Done Checklist

- [ ] T024: History section added to recipient detail view
- [ ] T025: History table displays all columns correctly
- [ ] T026: History sorted by date descending (most recent first)
- [ ] "No package history" shown for recipients without assignments
- [ ] Status colors are correct and visible
- [ ] Manual testing confirms accuracy
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. History section is visible in recipient detail
2. All columns display correctly (Event, Date, Package, Qty, Status)
3. Sorting is correct (most recent event first)
4. Status colors match: pending=orange, ready=green, delivered=blue
5. Handles missing data gracefully (no crashes)

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-12T04:00:51Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-12T04:04:32Z – system – shell_pid= – lane=for_review – Moved to for_review
- 2025-12-12T04:12:25Z – system – shell_pid= – lane=done – Code review approved: Recipient history dialog with status badges and summary
