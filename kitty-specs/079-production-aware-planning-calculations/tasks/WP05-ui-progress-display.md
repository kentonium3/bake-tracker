---
work_package_id: WP05
title: UI Progress Display
lane: "doing"
dependencies: [WP01, WP04]
base_branch: 079-production-aware-planning-calculations-WP04
base_commit: 3902ad097d18b29209277e63cc2860b183755479
created_at: '2026-01-28T12:05:08.190146+00:00'
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 3 - Polish
assignee: ''
agent: "claude-lead"
shell_pid: "28507"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T06:03:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – UI Progress Display

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP01 and WP04 - branch from WP04 (which should have WP01 merged)
spec-kitty implement WP05 --base WP04
```

**Note**: If WP02 or WP03 completed first, branch from whichever has WP01 merged.

---

## Objectives & Success Criteria

**Objective**: Update the planning tab UI to display remaining batches, overage indicators, and lock icons for recipes with completed production.

**Success Criteria**:
- [ ] Progress display shows "X of Y (Z remaining)" format
- [ ] Overage indicator "+N" shown when completed > target
- [ ] Lock icon displayed next to recipes with production
- [ ] Amendment controls disabled for locked recipes
- [ ] UI updates correctly for various production states
- [ ] No regression in existing planning tab functionality

---

## Context & Constraints

**Feature**: F079 Production-Aware Planning Calculations
**Spec**: `kitty-specs/079-production-aware-planning-calculations/spec.md` (User Story 6)
**Plan**: `kitty-specs/079-production-aware-planning-calculations/plan.md`

**Dependencies**:
- WP01: Provides `remaining_batches` and `overage_batches` in ProductionProgress DTO
- WP04: Provides `_has_production_for_recipe()` logic (or can reuse similar query)

**Key Constraints**:
- UI uses CustomTkinter (CTk) framework
- Must maintain consistent styling with existing planning tab
- Must be intuitive for non-technical users (constitution principle I)
- Refresh should complete within 2 seconds (success criteria SC-006)

**Existing Code Context**:
- File to modify: `src/ui/planning_tab.py`
- Progress data source: `planning/progress.py` get_production_progress()
- Existing progress display needs enhancement, not replacement

---

## Subtasks & Detailed Guidance

### Subtask T018 – Update Progress Display to Show Remaining

**Purpose**: Enhance progress text to show remaining batches alongside completed/target.

**Steps**:
1. Open `src/ui/planning_tab.py`
2. Locate the method that renders production progress (likely in a refresh or update method)
3. Find where progress text is constructed (e.g., "3 of 5 batches")
4. Update to include remaining:
   ```python
   # Old format
   progress_text = f"{progress.completed_batches} of {progress.target_batches} batches"

   # New format with remaining
   if progress.remaining_batches > 0:
       progress_text = (
           f"{progress.completed_batches} of {progress.target_batches} "
           f"({progress.remaining_batches} remaining)"
       )
   else:
       progress_text = (
           f"{progress.completed_batches} of {progress.target_batches} "
           "(complete)"
       )
   ```
5. Ensure the ProductionProgress DTO is being used (has remaining_batches field)

**Files**: `src/ui/planning_tab.py`

**Notes**:
- Keep format readable: "3 of 5 (2 remaining)" or "5 of 5 (complete)"
- Consider using a shorter format if space is constrained

**Parallel?**: Yes - can work on this while T019 works on overage

---

### Subtask T019 – Add Overage Indicator

**Purpose**: Show visual indicator when production exceeds target.

**Steps**:
1. In the same progress rendering code, add overage handling:
   ```python
   # Check for overage
   if progress.overage_batches > 0:
       progress_text = (
           f"{progress.completed_batches} of {progress.target_batches} "
           f"(+{progress.overage_batches} overage)"
       )
       # Optionally style differently
       overage_style = True
   else:
       overage_style = False
   ```
2. Apply visual styling for overage (optional - depends on existing patterns):
   ```python
   if overage_style:
       # Use a different color or add a warning indicator
       label.configure(text_color="orange")  # Example CTk styling
   ```
3. Test with scenarios where completed > target

**Files**: `src/ui/planning_tab.py`

**Notes**:
- Overage isn't necessarily bad (user may have produced extra intentionally)
- Use neutral or informational styling (orange/amber), not error (red)

**Parallel?**: Yes - independent from T018

---

### Subtask T020 – Add Lock Icon for Recipes with Production

**Purpose**: Visual indicator that a recipe has production and cannot be amended.

**Steps**:
1. Determine where recipe rows are rendered in the planning tab
2. Add production check (similar to WP04's logic):
   ```python
   def _has_production_for_recipe(self, event_id: int, recipe_id: int) -> bool:
       """Check if recipe has production records."""
       with session_scope() as session:
           from src.models import ProductionRun
           count = session.query(ProductionRun).filter(
               ProductionRun.event_id == event_id,
               ProductionRun.recipe_id == recipe_id,
           ).count()
           return count > 0
   ```
3. Add lock indicator in the recipe row:
   ```python
   # When rendering recipe row
   has_production = self._has_production_for_recipe(event_id, recipe_id)

   if has_production:
       # Add lock icon or indicator
       lock_label = ctk.CTkLabel(
           row_frame,
           text="🔒",  # Or use an image
           width=20,
       )
       lock_label.pack(side="left", padx=2)
   ```
4. Consider tooltip explaining the lock:
   ```python
   # If CTk supports tooltips, add explanation
   # "Production recorded - cannot modify batch decision"
   ```

**Files**: `src/ui/planning_tab.py`

**Notes**:
- Lock icon should be subtle but noticeable
- Emoji "🔒" works but image may be more professional
- Check existing icon patterns in the UI

---

### Subtask T021 – Disable Amendment Controls for Locked Recipes

**Purpose**: Prevent users from attempting to modify locked recipes via UI.

**Steps**:
1. Locate the batch modification controls (buttons, entry fields)
2. Disable them when recipe has production:
   ```python
   def _update_batch_controls(self, recipe_id: int):
       """Update batch modification controls based on production status."""
       has_production = self._has_production_for_recipe(
           self.current_event_id, recipe_id
       )

       if has_production:
           # Disable modification controls
           self.batch_modify_button.configure(state="disabled")
           self.batch_entry.configure(state="disabled")
           # Optional: show explanation
           self.batch_status_label.configure(
               text="Locked - has production"
           )
       else:
           # Enable controls
           self.batch_modify_button.configure(state="normal")
           self.batch_entry.configure(state="normal")
           self.batch_status_label.configure(text="")
   ```
3. Ensure this check runs when:
   - Planning tab is refreshed
   - Recipe selection changes
   - After production is recorded
4. Consider disabling DROP_FG button for FGs with production similarly

**Files**: `src/ui/planning_tab.py`

**Notes**:
- Disabled controls should be visually obvious (grayed out)
- User should understand WHY controls are disabled (lock icon + text helps)
- Service layer validation (WP04) is the safety net; UI is convenience

---

## Test Strategy

**Manual Testing Required** (UI changes):

1. **Remaining Display Test**:
   - Create event with 5 target batches
   - Record 0, 3, 5, 7 batches progressively
   - Verify display: "0 of 5 (5 remaining)", "3 of 5 (2 remaining)", "5 of 5 (complete)", "7 of 5 (+2 overage)"

2. **Lock Icon Test**:
   - Create event with recipe
   - Before production: no lock icon, controls enabled
   - After recording production: lock icon appears, controls disabled

3. **Refresh Test**:
   - Record production in another window/session
   - Refresh planning tab
   - Verify UI updates within 2 seconds

**Commands**:
```bash
# Run the app and manually test
python src/main.py
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Layout breaks with longer text | Medium | Medium | Test with various data; use flexible layouts |
| Performance with production checks | Medium | Low | Cache results per refresh; don't query per render |
| Inconsistent styling | Low | Low | Follow existing patterns in planning_tab.py |

---

## Definition of Done Checklist

- [ ] Progress shows "X of Y (Z remaining)" format
- [ ] Overage shows "+N overage" when completed > target
- [ ] Lock icon appears for recipes with production
- [ ] Batch modification controls disabled for locked recipes
- [ ] UI updates on refresh
- [ ] No regressions in existing functionality
- [ ] Visual styling is consistent with existing UI

---

## Review Guidance

**Key Checkpoints**:
1. Verify progress text is readable and fits in layout
2. Verify lock icon is visible and intuitive
3. Verify disabled controls are obviously disabled
4. Verify refresh performance (< 2 seconds)
5. Test edge cases: 0 batches, many batches, long recipe names

**User Testing**:
- Have a non-technical user verify the UI is intuitive
- "What does the lock mean?" - should be obvious

---

## Activity Log

- 2026-01-28T06:03:15Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-28T12:31:43Z – unknown – shell_pid=22519 – lane=for_review – Ready for review: Production progress display with remaining/overage, lock icons, disabled controls for locked recipes
- 2026-01-28T12:42:16Z – claude-lead – shell_pid=28507 – lane=doing – Started review via workflow command
