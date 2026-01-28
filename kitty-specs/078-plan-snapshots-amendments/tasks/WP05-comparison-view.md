---
work_package_id: WP05
title: Comparison View & Integration
lane: "doing"
dependencies: [WP02, WP03, WP04]
base_branch: 078-plan-snapshots-amendments-WP04
base_commit: 0474335093934e3aef6864ac6b3f0ec45d45f65b
created_at: '2026-01-28T04:04:47.586373+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - Polish
assignee: ''
agent: "gemini"
shell_pid: "86660"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-28T03:25:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Comparison View & Integration

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
spec-kitty implement WP05 --base WP04
```

Depends on WP02 (snapshot), WP03 (amendments), WP04 (UI).

**Note**: This is the final integration work package. All prior WPs must be complete.

---

## Objectives & Success Criteria

**Objective**: Implement plan comparison view showing original (snapshot) vs current (amended) plan with highlighted differences.

**Success Criteria**:
- [ ] Comparison dataclasses defined for structured diff
- [ ] `get_plan_comparison()` returns accurate diff between snapshot and current
- [ ] Comparison view panel displays original vs current
- [ ] Dropped FGs highlighted (red)
- [ ] Added FGs highlighted (green)
- [ ] Modified batches highlighted (yellow)
- [ ] Integration test passes full workflow
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`

---

## Context & Constraints

**Feature**: F078 Plan Snapshots & Amendments
**Spec**: `kitty-specs/078-plan-snapshots-amendments/spec.md` (US-4: Compare Original vs Current)
**Plan**: `kitty-specs/078-plan-snapshots-amendments/plan.md` (D5)

**Key Constraints**:
- Compare snapshot JSON against current EventFinishedGood/BatchDecision records
- Visual indicators: green (added), red (dropped), yellow (modified)
- Comparison panel should be collapsible to avoid UI clutter
- Lazy load comparison (don't compute on every refresh)

**Comparison Dataclasses** (from plan.md):
```python
@dataclass
class FGComparisonItem:
    fg_id: int
    fg_name: str
    original_quantity: Optional[int]  # None if added
    current_quantity: Optional[int]   # None if dropped
    status: str  # "unchanged", "added", "dropped", "modified"

@dataclass
class BatchComparisonItem:
    recipe_id: int
    recipe_name: str
    original_batches: Optional[int]
    current_batches: Optional[int]
    status: str  # "unchanged", "added", "dropped", "modified"

@dataclass
class PlanComparison:
    has_snapshot: bool
    finished_goods: List[FGComparisonItem]
    batch_decisions: List[BatchComparisonItem]
    total_changes: int
```

---

## Subtasks & Detailed Guidance

### Subtask T021 – Create comparison dataclasses

**Purpose**: Define structured types for comparison results.

**Steps**:
1. Open `src/services/plan_snapshot_service.py`
2. Add dataclass imports
3. Define FGComparisonItem, BatchComparisonItem, PlanComparison dataclasses
4. Place near top of file after imports

**File**: `src/services/plan_snapshot_service.py` (MODIFY, ~40 lines added)

**Implementation**:
```python
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FGComparisonItem:
    """Comparison item for a finished good."""
    fg_id: int
    fg_name: str
    original_quantity: Optional[int]  # None if added via amendment
    current_quantity: Optional[int]   # None if dropped via amendment
    status: str  # "unchanged", "added", "dropped"

    @property
    def is_changed(self) -> bool:
        return self.status != "unchanged"


@dataclass
class BatchComparisonItem:
    """Comparison item for a batch decision."""
    recipe_id: int
    recipe_name: str
    original_batches: Optional[int]  # None if recipe added
    current_batches: Optional[int]   # None if recipe removed
    status: str  # "unchanged", "modified", "added", "dropped"

    @property
    def is_changed(self) -> bool:
        return self.status != "unchanged"


@dataclass
class PlanComparison:
    """Complete plan comparison result."""
    has_snapshot: bool
    finished_goods: List[FGComparisonItem]
    batch_decisions: List[BatchComparisonItem]

    @property
    def total_changes(self) -> int:
        fg_changes = sum(1 for fg in self.finished_goods if fg.is_changed)
        batch_changes = sum(1 for bd in self.batch_decisions if bd.is_changed)
        return fg_changes + batch_changes

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0
```

**Validation**:
- Dataclasses can be instantiated
- Properties work correctly

---

### Subtask T022 – Implement get_plan_comparison()

**Purpose**: Compare snapshot against current plan state.

**Steps**:
1. Add `get_plan_comparison(event_id, session=None)` to plan_snapshot_service.py
2. Get snapshot (return empty comparison if none)
3. Parse snapshot JSON for original FGs and batch decisions
4. Query current EventFinishedGood and BatchDecision records
5. Compare and categorize: unchanged, added, dropped, modified
6. Return PlanComparison with all items

**File**: `src/services/plan_snapshot_service.py` (MODIFY, ~80 lines added)

**Implementation**:
```python
def _get_plan_comparison_impl(event_id: int, session: Session) -> PlanComparison:
    """Internal implementation of get_plan_comparison."""
    # Get snapshot
    snapshot = session.query(PlanSnapshot).filter(
        PlanSnapshot.event_id == event_id
    ).first()

    if snapshot is None:
        return PlanComparison(
            has_snapshot=False,
            finished_goods=[],
            batch_decisions=[],
        )

    snapshot_data = snapshot.snapshot_data

    # Parse original FGs from snapshot
    original_fgs = {
        fg["fg_id"]: fg
        for fg in snapshot_data.get("finished_goods", [])
    }

    # Get current FGs
    current_event_fgs = session.query(EventFinishedGood).filter(
        EventFinishedGood.event_id == event_id
    ).all()
    current_fgs = {
        efg.finished_good_id: {
            "fg_id": efg.finished_good_id,
            "fg_name": efg.finished_good.display_name if efg.finished_good else "Unknown",
            "quantity": efg.quantity,
        }
        for efg in current_event_fgs
    }

    # Compare FGs
    fg_comparison = []
    all_fg_ids = set(original_fgs.keys()) | set(current_fgs.keys())

    for fg_id in all_fg_ids:
        original = original_fgs.get(fg_id)
        current = current_fgs.get(fg_id)

        if original and current:
            # Present in both - unchanged (quantity changes tracked via batch)
            status = "unchanged"
            if original.get("quantity") != current.get("quantity"):
                status = "modified"  # Note: This shouldn't happen via standard amendments
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=original.get("fg_name", "Unknown"),
                original_quantity=original.get("quantity"),
                current_quantity=current.get("quantity"),
                status=status,
            ))
        elif original and not current:
            # Dropped
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=original.get("fg_name", "Unknown"),
                original_quantity=original.get("quantity"),
                current_quantity=None,
                status="dropped",
            ))
        elif current and not original:
            # Added
            fg_comparison.append(FGComparisonItem(
                fg_id=fg_id,
                fg_name=current.get("fg_name", "Unknown"),
                original_quantity=None,
                current_quantity=current.get("quantity"),
                status="added",
            ))

    # Parse original batch decisions from snapshot
    original_batches = {
        bd["recipe_id"]: bd
        for bd in snapshot_data.get("batch_decisions", [])
    }

    # Get current batch decisions
    current_batch_decisions = session.query(BatchDecision).filter(
        BatchDecision.event_id == event_id
    ).all()
    current_batches = {
        bd.recipe_id: {
            "recipe_id": bd.recipe_id,
            "recipe_name": bd.recipe.name if bd.recipe else "Unknown",
            "batches": bd.batches,
        }
        for bd in current_batch_decisions
    }

    # Compare batches
    batch_comparison = []
    all_recipe_ids = set(original_batches.keys()) | set(current_batches.keys())

    for recipe_id in all_recipe_ids:
        original = original_batches.get(recipe_id)
        current = current_batches.get(recipe_id)

        if original and current:
            orig_count = original.get("batches")
            curr_count = current.get("batches")
            status = "unchanged" if orig_count == curr_count else "modified"
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=original.get("recipe_name", "Unknown"),
                original_batches=orig_count,
                current_batches=curr_count,
                status=status,
            ))
        elif original and not current:
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=original.get("recipe_name", "Unknown"),
                original_batches=original.get("batches"),
                current_batches=None,
                status="dropped",
            ))
        elif current and not original:
            batch_comparison.append(BatchComparisonItem(
                recipe_id=recipe_id,
                recipe_name=current.get("recipe_name", "Unknown"),
                original_batches=None,
                current_batches=current.get("batches"),
                status="added",
            ))

    return PlanComparison(
        has_snapshot=True,
        finished_goods=fg_comparison,
        batch_decisions=batch_comparison,
    )


def get_plan_comparison(event_id: int, session: Session = None) -> PlanComparison:
    """Compare original plan (snapshot) with current plan state.

    Returns structured comparison showing what changed since
    production started.

    Args:
        event_id: Event ID to compare
        session: Optional session for transaction sharing

    Returns:
        PlanComparison with original vs current differences
    """
    if session is not None:
        return _get_plan_comparison_impl(event_id, session)

    with session_scope() as session:
        return _get_plan_comparison_impl(event_id, session)
```

**Validation**:
- Handles event with no snapshot
- Correctly identifies dropped, added, modified items
- Returns empty lists for events with no plan data

---

### Subtask T023 – Add comparison view panel to planning_tab.py

**Purpose**: Display comparison view in the UI.

**Steps**:
1. Add comparison frame to planning_tab.py (near amendment controls)
2. Add "Show Comparison" button to toggle visibility
3. Implement `_refresh_comparison_view()` method
4. Call `get_plan_comparison()` and display results
5. Show panel only when snapshot exists

**File**: `src/ui/planning_tab.py` (MODIFY, ~60 lines added)

**Implementation**:
```python
# In _create_widgets, after amendment history:

# Comparison view frame
self.comparison_frame = ctk.CTkFrame(self.amendment_frame)
# Don't pack initially - shown on demand

self.show_comparison_btn = ctk.CTkButton(
    self.amendment_header,
    text="Show Comparison",
    command=self._toggle_comparison_view,
    width=120
)
self.show_comparison_btn.pack(side="right", padx=5)

self.comparison_visible = False


def _toggle_comparison_view(self):
    """Toggle comparison view visibility."""
    if self.comparison_visible:
        self.comparison_frame.pack_forget()
        self.show_comparison_btn.configure(text="Show Comparison")
        self.comparison_visible = False
    else:
        self._refresh_comparison_view()
        self.comparison_frame.pack(fill="x", padx=5, pady=5)
        self.show_comparison_btn.configure(text="Hide Comparison")
        self.comparison_visible = True


def _refresh_comparison_view(self):
    """Refresh the comparison view with current data."""
    # Clear existing
    for widget in self.comparison_frame.winfo_children():
        widget.destroy()

    if not self.selected_event:
        return

    from src.services import plan_snapshot_service
    comparison = plan_snapshot_service.get_plan_comparison(self.selected_event.id)

    if not comparison.has_snapshot:
        ctk.CTkLabel(
            self.comparison_frame,
            text="No snapshot available (production not started)",
            text_color="gray"
        ).pack(pady=10)
        return

    # Header
    header_text = f"Plan Comparison ({comparison.total_changes} changes)"
    ctk.CTkLabel(
        self.comparison_frame,
        text=header_text,
        font=ctk.CTkFont(size=12, weight="bold")
    ).pack(anchor="w", padx=5, pady=5)

    # FG comparison section
    if comparison.finished_goods:
        self._render_fg_comparison(comparison.finished_goods)

    # Batch comparison section
    if comparison.batch_decisions:
        self._render_batch_comparison(comparison.batch_decisions)

    if not comparison.has_changes:
        ctk.CTkLabel(
            self.comparison_frame,
            text="No changes from original plan.",
            text_color="gray"
        ).pack(pady=5)
```

**Validation**:
- Panel toggles correctly
- Shows "No snapshot" when appropriate
- Displays comparison data

---

### Subtask T024 – Implement FG diff highlighting

**Purpose**: Display FG comparison with visual indicators.

**Steps**:
1. Add `_render_fg_comparison()` method to planning_tab.py
2. Display each FG with status indicator
3. Color coding: green (added), red (dropped), gray (unchanged)
4. Show original and current quantities

**File**: `src/ui/planning_tab.py` (MODIFY, ~40 lines added)

**Implementation**:
```python
def _render_fg_comparison(self, fg_items: list):
    """Render finished goods comparison section."""
    section = ctk.CTkFrame(self.comparison_frame)
    section.pack(fill="x", padx=5, pady=5)

    ctk.CTkLabel(
        section,
        text="Finished Goods",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    for item in fg_items:
        row = ctk.CTkFrame(section)
        row.pack(fill="x", pady=1)

        # Status indicator and color
        if item.status == "dropped":
            indicator = "[-]"
            color = "#ff6b6b"  # Red
            text = f"{item.fg_name}: was {item.original_quantity}"
        elif item.status == "added":
            indicator = "[+]"
            color = "#51cf66"  # Green
            text = f"{item.fg_name}: now {item.current_quantity}"
        elif item.status == "modified":
            indicator = "[~]"
            color = "#fcc419"  # Yellow
            text = f"{item.fg_name}: {item.original_quantity} → {item.current_quantity}"
        else:
            indicator = "[ ]"
            color = "gray"
            text = f"{item.fg_name}: {item.current_quantity}"

        ctk.CTkLabel(
            row,
            text=f"{indicator} {text}",
            text_color=color
        ).pack(anchor="w", padx=10)
```

**Validation**:
- Dropped FGs shown in red with original quantity
- Added FGs shown in green with new quantity
- Unchanged FGs shown in gray

---

### Subtask T025 – Implement batch diff highlighting

**Purpose**: Display batch decision comparison with visual indicators.

**Steps**:
1. Add `_render_batch_comparison()` method to planning_tab.py
2. Display each recipe with batch count changes
3. Color coding: yellow (modified), gray (unchanged)
4. Show original → current batch counts

**File**: `src/ui/planning_tab.py` (MODIFY, ~40 lines added)

**Implementation**:
```python
def _render_batch_comparison(self, batch_items: list):
    """Render batch decisions comparison section."""
    section = ctk.CTkFrame(self.comparison_frame)
    section.pack(fill="x", padx=5, pady=5)

    ctk.CTkLabel(
        section,
        text="Batch Decisions",
        font=ctk.CTkFont(weight="bold")
    ).pack(anchor="w")

    for item in batch_items:
        row = ctk.CTkFrame(section)
        row.pack(fill="x", pady=1)

        if item.status == "modified":
            indicator = "[~]"
            color = "#fcc419"  # Yellow
            text = f"{item.recipe_name}: {item.original_batches} → {item.current_batches} batches"
        elif item.status == "dropped":
            indicator = "[-]"
            color = "#ff6b6b"  # Red
            text = f"{item.recipe_name}: was {item.original_batches} batches"
        elif item.status == "added":
            indicator = "[+]"
            color = "#51cf66"  # Green
            text = f"{item.recipe_name}: now {item.current_batches} batches"
        else:
            indicator = "[ ]"
            color = "gray"
            text = f"{item.recipe_name}: {item.current_batches} batches"

        ctk.CTkLabel(
            row,
            text=f"{indicator} {text}",
            text_color=color
        ).pack(anchor="w", padx=10)
```

**Validation**:
- Modified batches shown in yellow with before/after
- Unchanged batches shown in gray

---

### Subtask T026 – Integration test of full workflow

**Purpose**: Verify complete workflow: lock → start production → amend → compare.

**Steps**:
1. Add integration test to test file
2. Test complete workflow:
   - Create event with FGs and batch decisions
   - Lock plan
   - Start production (creates snapshot)
   - Create amendments (drop, add, modify)
   - Get comparison
   - Verify all changes detected

**File**: `src/tests/test_plan_snapshot_service.py` (MODIFY, ~80 lines added)

**Test**:
```python
class TestFullWorkflowIntegration:
    """Integration test for complete F078 workflow."""

    def test_full_workflow_lock_produce_amend_compare(self):
        """Test complete workflow from lock to comparison."""
        from src.services import plan_state_service, plan_amendment_service

        with session_scope() as session:
            # Setup: Create event with plan data
            event = Event(
                name="Full Workflow Test",
                event_date=datetime(2026, 12, 25).date(),
                year=2026,
                plan_state=PlanState.DRAFT,
            )
            session.add(event)
            session.flush()

            # Add FG to plan (need real FG)
            fg = session.query(FinishedGood).first()
            if not fg:
                pytest.skip("No FinishedGood in database")

            event_fg = EventFinishedGood(
                event_id=event.id,
                finished_good_id=fg.id,
                quantity=10,
            )
            session.add(event_fg)

            # Add batch decision (need real recipe)
            recipe = session.query(Recipe).first()
            if recipe:
                batch = BatchDecision(
                    event_id=event.id,
                    recipe_id=recipe.id,
                    batches=5,
                    yield_per_batch=24,
                )
                session.add(batch)

            session.flush()
            event_id = event.id
            fg_id = fg.id

            # Step 1: Lock plan
            plan_state_service.lock_plan(event_id, session)
            assert event.plan_state == PlanState.LOCKED

            # Step 2: Start production (creates snapshot)
            plan_state_service.start_production(event_id, session)
            assert event.plan_state == PlanState.IN_PRODUCTION

            # Verify snapshot created
            snapshot = plan_snapshot_service.get_plan_snapshot(event_id, session)
            assert snapshot is not None
            assert len(snapshot.snapshot_data["finished_goods"]) == 1

            # Step 3: Create amendment (drop the FG)
            plan_amendment_service.drop_finished_good(
                event_id, fg_id, "Changed mind", session
            )

            # Step 4: Get comparison
            comparison = plan_snapshot_service.get_plan_comparison(event_id, session)

            # Verify comparison shows the drop
            assert comparison.has_snapshot
            assert comparison.has_changes

            dropped_fgs = [fg for fg in comparison.finished_goods if fg.status == "dropped"]
            assert len(dropped_fgs) == 1
            assert dropped_fgs[0].fg_id == fg_id
            assert dropped_fgs[0].original_quantity == 10
            assert dropped_fgs[0].current_quantity is None
```

**Validation**:
- Test passes: `./run-tests.sh src/tests/test_plan_snapshot_service.py::TestFullWorkflowIntegration -v`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Snapshot JSON schema changes | Include snapshot_version for compatibility |
| Performance with large plans | Lazy load comparison; don't compute on every refresh |
| Session issues in comparison | Query all data within same session |
| UI layout issues | Use scrollable frame; limit items displayed |

---

## Definition of Done Checklist

- [ ] Comparison dataclasses defined (FGComparisonItem, BatchComparisonItem, PlanComparison)
- [ ] `get_plan_comparison()` correctly identifies all change types
- [ ] Comparison view panel exists in planning_tab.py
- [ ] FG changes highlighted with correct colors
- [ ] Batch changes highlighted with correct colors
- [ ] Toggle button shows/hides comparison view
- [ ] Integration test passes complete workflow
- [ ] All tests pass: `./run-tests.sh src/tests/test_plan_snapshot_service.py -v`

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Verify dataclasses have correct fields and properties
2. Test get_plan_comparison with various scenarios:
   - Event with no snapshot
   - Event with snapshot, no changes
   - Event with dropped FG
   - Event with added FG
   - Event with modified batch
3. Verify UI colors are correct
4. Run integration test
5. Manual test: lock → start → amend → view comparison

---

## Activity Log

- 2026-01-28T03:25:47Z – system – lane=planned – Prompt created.
- 2026-01-28T04:09:36Z – unknown – shell_pid=81572 – lane=for_review – Comparison view complete with diff highlighting, color coding, and 15 passing tests
- 2026-01-28T05:17:25Z – gemini – shell_pid=86660 – lane=doing – Started review via workflow command
