---
work_package_id: "WP04"
subtasks:
  - "T026"
  - "T027"
  - "T028"
  - "T029"
title: "UI - Production History"
phase: "Phase 4 - UI History"
lane: "done"
assignee: "gemini"
agent: "claude-reviewer"
shell_pid: "74560"
history:
  - timestamp: "2025-12-21T16:55:08Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - UI - Production History

## Objectives & Success Criteria

- Production history table shows "Loss" column with loss quantity
- Production history table shows "Status" column with production status
- Visual indicators differentiate Complete, Partial Loss, and Total Loss
- Records with no losses show "-" in Loss column
- Status column uses color/styling for quick visual scanning

## Context & Constraints

- **Spec**: `kitty-specs/025-production-loss-tracking/spec.md` - User Story 2
- **Plan**: `kitty-specs/025-production-loss-tracking/plan.md` - Phase 4
- **Existing UI**: `src/ui/production_dashboard_tab.py` (read this first!)
- **Constitution**: `.kittify/memory/constitution.md` - User-Centric Design

**Key Constraints**:
- Maintain table readability with new columns
- Visual indicators must be accessible (not just color)
- Follow existing table styling patterns

**Dependencies**:
- Requires WP02 complete (history query must return loss data)

## Subtasks & Detailed Guidance

### Subtask T026 - Add Loss column to history table
- **Purpose**: Show loss quantity for each production run (FR-013)
- **File**: `src/ui/production_dashboard_tab.py`
- **Steps**:
  1. Locate the production history table/treeview definition
  2. Add "Loss" column after existing yield columns:
     ```python
     # In column definitions
     columns = [..., "loss", ...]
     # In column configuration
     self.tree.heading("loss", text="Loss")
     self.tree.column("loss", width=60, anchor="center")
     ```
  3. When populating rows, include loss_quantity from data:
     ```python
     loss_display = str(run["loss_quantity"]) if run["loss_quantity"] > 0 else "-"
     values = (..., loss_display, ...)
     ```
- **Parallel?**: Yes, with T027
- **Notes**: Center-align for numeric values

### Subtask T027 - Add Status column to history table
- **Purpose**: Show production status for quick identification (FR-013)
- **File**: `src/ui/production_dashboard_tab.py`
- **Steps**:
  1. Add "Status" column after Loss column:
     ```python
     self.tree.heading("status", text="Status")
     self.tree.column("status", width=100, anchor="center")
     ```
  2. Map status values to display labels:
     ```python
     STATUS_DISPLAY = {
         "complete": "Complete",
         "partial_loss": "Partial Loss",
         "total_loss": "Total Loss",
     }
     status_display = STATUS_DISPLAY.get(run["production_status"], "Unknown")
     ```
- **Parallel?**: Yes, with T026
- **Notes**: Use friendly display names, not raw enum values

### Subtask T028 - Implement status visual indicators
- **Purpose**: Quick visual scanning for problem batches (FR-014)
- **File**: `src/ui/production_dashboard_tab.py`
- **Steps**:
  1. Define status-based styling/tags:
     ```python
     # If using Treeview tags
     self.tree.tag_configure("complete", foreground="green")
     self.tree.tag_configure("partial_loss", foreground="orange")
     self.tree.tag_configure("total_loss", foreground="red")
     ```
  2. Apply tag when inserting rows:
     ```python
     status = run["production_status"]
     self.tree.insert("", "end", values=values, tags=(status,))
     ```
  3. Alternative: Use emoji/icon prefix in status text:
     ```python
     STATUS_DISPLAY = {
         "complete": "Complete",
         "partial_loss": "! Partial",
         "total_loss": "!! Total",
     }
     ```
- **Parallel?**: No (depends on column setup)
- **Notes**: Color alone isn't accessible; consider icon/prefix too

### Subtask T029 - Handle "-" display for no-loss records
- **Purpose**: Clear indication that no loss occurred
- **File**: `src/ui/production_dashboard_tab.py`
- **Steps**:
  1. In row population, check for zero/null loss:
     ```python
     loss_qty = run.get("loss_quantity", 0)
     loss_display = str(loss_qty) if loss_qty > 0 else "-"
     ```
  2. Status for complete should show without warning styling:
     ```python
     if run["production_status"] == "complete":
         # Use default styling, no warning color
     ```
  3. Ensure backward compatibility with records missing new fields
- **Parallel?**: No (part of row population logic)
- **Notes**: Handle None/missing values gracefully

## Test Strategy

Manual testing:
1. Record several production runs with varying statuses:
   - Complete (no loss)
   - Partial loss (some units lost)
   - Total loss (all units lost)
2. View production history table
3. Verify:
   - Loss column shows correct values (number or "-")
   - Status column shows correct labels
   - Visual indicators distinguish statuses
   - Table remains readable with new columns

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Table too wide | Use compact column widths |
| Color-only indicators | Add text prefix or icon |
| Missing data in old records | Default to complete/0 if missing |

## Definition of Done Checklist

- [ ] Loss column added to history table
- [ ] Status column added to history table
- [ ] Visual indicators for each status type
- [ ] "-" displayed for records with no loss
- [ ] Complete status uses default/positive styling
- [ ] Partial Loss uses warning styling
- [ ] Total Loss uses error styling
- [ ] Table remains readable and usable
- [ ] Manual testing passes
- [ ] `tasks.md` updated with completion status

## Review Guidance

- Verify column widths don't break table layout
- Check visual indicators are accessible (not just color)
- Test with old records that may lack new fields
- Confirm styling matches app theme

## Activity Log

- 2025-12-21T16:55:08Z - system - lane=planned - Prompt created.
- 2025-12-21T18:17:00Z – gemini – shell_pid=66785 – lane=for_review – T026-T029 complete by Gemini. Loss and Status columns added with visual indicators.
- 2025-12-21T19:11:47Z – claude-reviewer – shell_pid=74560 – lane=done – Code review APPROVED: Loss and Status columns added with accessible visual indicators (text prefix + color).
