# Research: F071 Finished Goods Quantity Specification

**Date**: 2026-01-27
**Feature**: 071-finished-goods-quantity-specification
**Status**: Complete

## Research Questions

| # | Question | Status |
|---|----------|--------|
| 1 | How is PlanningService structured for CRUD operations? | Resolved |
| 2 | What is the EventFinishedGood model schema? | Resolved |
| 3 | How does FGSelectionFrame display finished goods? | Resolved |
| 4 | What numeric input validation patterns exist? | Resolved |

## Findings

### 1. PlanningService CRUD Patterns

**File**: `src/services/planning/planning_service.py`
**Lines**: 217-327

**Decision**: Follow existing session management pattern - accept optional `session` parameter, delegate to `_impl` function.

**Pattern**:
```python
def create_plan(
    event_id: int,
    *,
    force_recreate: bool = False,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    if session is not None:
        return _create_plan_impl(event_id, force_recreate, session)
    with session_scope() as session:
        return _create_plan_impl(event_id, force_recreate, session)
```

**Rationale**: Maintains transactional atomicity and prevents object detachment when service methods call each other.

**Alternatives Considered**:
- Always create new session: Rejected - causes nested session issues documented in CLAUDE.md
- Require session parameter: Rejected - less ergonomic for simple single-operation calls

---

### 2. EventFinishedGood Model Schema

**File**: `src/models/event_finished_good.py`

**Decision**: Use existing model as-is. No schema changes required.

**Schema**:
```python
class EventFinishedGood(BaseModel):
    __tablename__ = "event_finished_goods"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id", ondelete="RESTRICT"))
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id"),
        CheckConstraint("quantity > 0", name="ck_event_fg_quantity_positive"),
    )
```

**Key Finding**: Database already enforces `quantity > 0` via CHECK constraint. UI and service validation provide early feedback but DB is the final authority.

**Rationale**: F068 created this model with quantity field anticipating F071. No changes needed.

**Alternatives Considered**:
- Add min/max constraints: Rejected - user confirmed no limits desired

---

### 3. FGSelectionFrame Display Pattern

**File**: `src/ui/components/fg_selection_frame.py`
**Lines**: 14-195

**Decision**: Extend existing component with quantity inputs alongside checkboxes.

**Current Structure**:
- Header with event name
- Count label ("X of Y selected")
- Scrollable frame with CTkCheckBox per FG
- Save/Cancel buttons

**Extension Point**: In `populate_finished_goods()` loop, add CTkEntry after each checkbox.

**Key Methods to Modify**:
- `populate_finished_goods()` - Add quantity inputs
- `set_selected()` - Also set quantity values
- `get_selected()` - Return fg_id + quantity tuples

**Rationale**: Minimal modification to existing working component. Follows established patterns.

**Alternatives Considered**:
- Create new component: Rejected - duplicates existing logic
- Use dropdown for quantities: Rejected - less efficient for arbitrary integer entry

---

### 4. Numeric Input Validation Patterns

**Files**:
- `src/ui/dialogs/adjustment_dialog.py:258-306`
- `src/ui/forms/package_form.py:36-143`

**Decision**: Use CTkEntry with live validation and colored text feedback.

**Pattern from AdjustmentDialog**:
```python
def _update_preview(self, event=None):
    try:
        qty_text = self.qty_entry.get().strip()
        if not qty_text:
            self.label.configure(text="--", text_color="gray")
            return

        qty = int(qty_text)  # Use int() not Decimal() for integers
        if qty <= 0:
            self.label.configure(text="(enter positive value)", text_color="orange")
            return

        # Valid - show normal
        self.label.configure(text=str(qty), text_color="default")
    except ValueError:
        self.label.configure(text="(invalid input)", text_color="orange")
```

**Pattern from PackageForm (FinishedGoodRow)**:
```python
self.quantity_entry = ctk.CTkEntry(self, width=80, placeholder_text="Qty")
self.quantity_entry.insert(0, str(quantity))
```

**Rationale**: Consistent with existing codebase patterns. Users already familiar with this validation style.

**Alternatives Considered**:
- Modal error dialogs: Rejected - disruptive for quantity entry
- Prevent invalid keystrokes: Rejected - harder to implement in CustomTkinter, paste handling complex
- Validation only on save: Rejected - delayed feedback frustrates users

---

## Event Service Gap Analysis

**File**: `src/services/event_service.py`
**Lines**: 3099-3177

**Current Methods**:
- `get_event_finished_good_ids()` - Returns only IDs, not quantities
- `set_event_finished_goods()` - Creates records without quantities (defaults?)

**Gap**: Current `set_event_finished_goods()` creates EventFinishedGood records but doesn't set quantity values. Need to either:
1. Modify existing method to accept quantities
2. Add new quantity-aware methods

**Decision**: Add new methods to avoid breaking existing callers:
- `get_event_fg_quantities(session, event_id)`
- `set_event_fg_quantities(session, event_id, fg_quantities)`
- `remove_event_fg(session, event_id, fg_id)`

**Rationale**: Existing methods may be called from other places (F070). Adding new methods is safer than modifying signatures.

---

## Summary

All research questions resolved. Implementation can proceed with:

1. **No schema changes** - EventFinishedGood already has quantity with CHECK constraint
2. **Extend FGSelectionFrame** - Add CTkEntry inputs following existing layout patterns
3. **Add event_service methods** - New quantity-aware CRUD methods following session pattern
4. **Use existing validation pattern** - try/except + colored text feedback
