---
work_package_id: "WP05"
subtasks:
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Scale Factor UI"
phase: "Phase 2 - Scaling & Variants"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 - Scale Factor UI

## Objectives & Success Criteria

Add scale_factor input to production dialog with calculated yield display.

**Success Criteria**:
- User can enter scale_factor (default 1.0)
- Expected yield updates: base_yield x scale_factor x num_batches
- Ingredient requirements shown with scaling applied
- Validation: scale_factor > 0 (0.5 valid for half batches)
- Scale factor passed to record_batch_production()

## Context & Constraints

**Key References**:
- `src/ui/forms/record_production_dialog.py` - Modify this file
- `kitty-specs/037-recipe-template-snapshot/spec.md` - User Story 3 acceptance criteria
- `kitty-specs/037-recipe-template-snapshot/research.md` - UI patterns

**Existing Pattern**:
- Dialog has batch_count entry
- Updates expected_yield on batch change
- Shows ingredient availability

**User Story 3 Acceptance**:
- "Given a recipe yielding 36 cookies with 2 cups flour, When I produce 2 batches at 2x scale, Then expected yield is 144 cookies (36 x 2 x 2) and flour needed is 8 cups (2 x 2 x 2)."

## Subtasks & Detailed Guidance

### Subtask T018 - Add scale_factor Entry to Dialog

**Purpose**: Allow user to specify batch size multiplier.

**File**: `src/ui/forms/record_production_dialog.py`

**Steps**:
1. Add scale_factor entry field after batch_count
2. Set default value to "1.0"
3. Add label explaining "Scale Factor (batch size multiplier)"
4. Bind to _on_scale_changed() for live updates

**Code to Add**:
```python
# After batch_count entry (around existing batch UI):

# Scale Factor
scale_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
scale_frame.grid(row=next_row, column=0, columnspan=2, sticky="ew", pady=5)

scale_label = ctk.CTkLabel(
    scale_frame,
    text="Scale Factor:",
    width=120
)
scale_label.pack(side="left")

self.scale_factor_var = ctk.StringVar(value="1.0")
self.scale_factor_entry = ctk.CTkEntry(
    scale_frame,
    textvariable=self.scale_factor_var,
    width=80
)
self.scale_factor_entry.pack(side="left", padx=5)

scale_hint = ctk.CTkLabel(
    scale_frame,
    text="(1.0 = normal, 2.0 = double batch, 0.5 = half batch)",
    text_color="gray"
)
scale_hint.pack(side="left", padx=5)

# Bind to update handler
self.scale_factor_var.trace_add("write", self._on_scale_changed)
```

---

### Subtask T019 - Update Expected Yield Calculation Display

**Purpose**: Show calculated yield with scaling formula.

**Steps**:
1. Modify _on_batch_changed() or create _update_calculations()
2. Calculate: expected = base_yield x scale_factor x num_batches
3. Display formula for clarity: "Expected: 144 cookies (36 x 2.0 x 2)"

**Code**:
```python
def _update_calculations(self):
    """Update expected yield and ingredient requirements with scaling."""
    try:
        num_batches = int(self.batch_count_var.get() or "1")
        scale_factor = float(self.scale_factor_var.get() or "1.0")
    except ValueError:
        return

    if num_batches <= 0 or scale_factor <= 0:
        return

    # Get base yield from finished unit or recipe
    base_yield = self.finished_unit.items_per_batch  # or recipe yield

    # Calculate expected yield
    expected_yield = int(base_yield * scale_factor * num_batches)

    # Update display with formula
    formula = f"{base_yield} x {scale_factor} x {num_batches}"
    self.expected_yield_label.configure(
        text=f"Expected: {expected_yield} {self.yield_unit} ({formula})"
    )

    # Update ingredient requirements
    self._update_ingredient_requirements(scale_factor, num_batches)


def _on_scale_changed(self, *args):
    """Handle scale factor changes."""
    self._update_calculations()


def _on_batch_changed(self, *args):
    """Handle batch count changes."""
    self._update_calculations()
```

---

### Subtask T020 - Show Ingredient Requirements Scaled

**Purpose**: Display scaled ingredient needs for production planning.

**Steps**:
1. Get aggregated ingredients for recipe
2. Apply scale_factor x num_batches to each quantity
3. Display in availability section or new requirements section

**Code**:
```python
def _update_ingredient_requirements(self, scale_factor: float, num_batches: int):
    """Update ingredient requirements display with scaling."""
    multiplier = scale_factor * num_batches

    # Get base ingredients
    ingredients = recipe_service.get_aggregated_ingredients(
        self.recipe_id,
        multiplier=1.0  # Base quantities
    )

    # Build requirements display
    requirements = []
    for ing in ingredients:
        base_qty = ing["total_quantity"]
        scaled_qty = base_qty * multiplier
        requirements.append(
            f"  {ing['ingredient_name']}: {scaled_qty:.2f} {ing['unit']}"
        )

    # Update display (add to existing availability or new section)
    self.requirements_text.configure(
        text="Ingredients Needed:\n" + "\n".join(requirements)
    )
```

---

### Subtask T021 - Validate scale_factor > 0

**Purpose**: Prevent invalid scale factors.

**Steps**:
1. In _on_ok() or validation method
2. Check scale_factor is numeric and > 0
3. Show error if invalid

**Code**:
```python
def _validate_inputs(self) -> bool:
    """Validate all inputs before production."""
    # Existing validations...

    # Validate scale_factor
    try:
        scale_factor = float(self.scale_factor_var.get())
        if scale_factor <= 0:
            show_error(self, "Scale factor must be greater than 0")
            return False
    except ValueError:
        show_error(self, "Scale factor must be a number")
        return False

    return True


def _on_ok(self):
    """Handle OK button - validate and record production."""
    if not self._validate_inputs():
        return

    scale_factor = float(self.scale_factor_var.get())

    # Pass to service
    result = batch_production_service.record_batch_production(
        recipe_id=self.recipe_id,
        finished_unit_id=self.finished_unit_id,
        num_batches=int(self.batch_count_var.get()),
        actual_yield=int(self.actual_yield_var.get()),
        scale_factor=scale_factor,  # NEW PARAMETER
        # ... other params
    )
```

## Test Strategy

- Manual testing: Enter various scale factors (0.5, 1.0, 2.0)
- Verify calculations match formula
- Test edge cases: 0, negative, non-numeric
- Run existing production dialog tests to ensure no regressions

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI clutter | Clear labeling with hint text |
| User confusion | Show formula in display |
| Invalid input | Validation with clear error messages |

## Definition of Done Checklist

- [ ] Scale factor entry added to dialog
- [ ] Default value is 1.0
- [ ] Expected yield calculation includes scale factor
- [ ] Ingredient requirements shown scaled
- [ ] Validation prevents invalid values (<=0)
- [ ] scale_factor passed to record_batch_production()

## Review Guidance

- Verify formula display is clear
- Check 0.5 (half batch) works correctly
- Confirm validation error messages are helpful

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
