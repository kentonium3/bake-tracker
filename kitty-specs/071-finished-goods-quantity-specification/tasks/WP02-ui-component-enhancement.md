---
work_package_id: WP02
title: UI Component Enhancement
lane: "doing"
dependencies: [WP01]
base_branch: 071-finished-goods-quantity-specification-WP01
base_commit: 69a9ebc983d54438bb3354bc30afc1bfd78c1397
created_at: '2026-01-27T14:23:49.294458+00:00'
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - UI Layer
assignee: ''
agent: ''
shell_pid: "78233"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-27T12:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – UI Component Enhancement

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Note**: Uses `--base WP01` because this work package depends on WP01 service methods.

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – This section is empty initially.

---

## Objectives & Success Criteria

Extend FGSelectionFrame with quantity input fields and live validation.

**Success Criteria:**
- [ ] Quantity entry field (CTkEntry, width=80) displayed next to each FG checkbox
- [ ] Live validation: empty OK, positive integer OK, invalid → orange text
- [ ] `set_quantities()` method pre-populates fields from loaded data
- [ ] `get_selected()` returns `List[Tuple[int, int]]` (fg_id, quantity)
- [ ] Tab order logical for efficient data entry
- [ ] Component can be tested independently (displays correctly, returns valid data)

## Context & Constraints

### Referenced Documents
- **Constitution**: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)
- **Plan**: `kitty-specs/071-finished-goods-quantity-specification/plan.md`
- **Research**: `kitty-specs/071-finished-goods-quantity-specification/research.md`

### Existing Component Structure

**File**: `src/ui/components/fg_selection_frame.py`

Current structure (from research.md):
```
FGSelectionFrame
├── Header with event name
├── Count label ("X of Y selected")
├── Scrollable frame with CTkCheckBox per FG
│   └── For each FG:
│       └── CTkCheckBox with display_name
└── Save/Cancel buttons
```

**Target structure**:
```
FGSelectionFrame
├── Header with event name
├── Count label ("X of Y selected")
├── Scrollable frame
│   └── For each FG:
│       ├── CTkCheckBox with display_name
│       └── CTkEntry for quantity (width=80)  ← NEW
└── Save/Cancel buttons
```

### Validation Pattern Reference

From `src/ui/dialogs/adjustment_dialog.py:258-306`:
```python
def _update_preview(self, event=None):
    try:
        qty_text = self.qty_entry.get().strip()
        if not qty_text:
            # Empty is valid (FG not selected)
            self.feedback_label.configure(text="", text_color="gray")
            return

        qty = int(qty_text)
        if qty <= 0:
            self.feedback_label.configure(
                text="Must be positive",
                text_color="orange"
            )
            return

        # Valid
        self.feedback_label.configure(text="", text_color="gray")
    except ValueError:
        self.feedback_label.configure(
            text="Must be integer",
            text_color="orange"
        )
```

### Layout Pattern Reference

From `src/ui/forms/package_form.py`:
```python
self.quantity_entry = ctk.CTkEntry(self, width=80, placeholder_text="Qty")
self.quantity_entry.insert(0, str(quantity))
```

---

## Subtasks & Detailed Guidance

### Subtask T005 – Add CTkEntry Quantity Inputs

**Purpose**: Display a quantity input field next to each FG checkbox.

**File**: `src/ui/components/fg_selection_frame.py`

**Steps**:

1. **Add instance variable to track quantity entries**:
   ```python
   def __init__(self, parent, on_save_callback, on_cancel_callback):
       super().__init__(parent)
       self._checkbox_vars: Dict[int, ctk.BooleanVar] = {}
       self._quantity_vars: Dict[int, ctk.StringVar] = {}  # NEW
       self._quantity_entries: Dict[int, ctk.CTkEntry] = {}  # NEW
       # ... rest of init
   ```

2. **Modify `populate_finished_goods()` to add quantity entries**:

   Find the loop that creates checkboxes and add quantity entry after each:
   ```python
   def populate_finished_goods(self, finished_goods: List[FinishedGood], event_name: str) -> None:
       # ... existing header setup ...

       # Clear existing widgets
       for widget in self._scroll_frame.winfo_children():
           widget.destroy()
       self._checkbox_vars.clear()
       self._quantity_vars.clear()  # NEW
       self._quantity_entries.clear()  # NEW

       for i, fg in enumerate(finished_goods):
           # Create row frame for checkbox + entry
           row_frame = ctk.CTkFrame(self._scroll_frame, fg_color="transparent")
           row_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
           row_frame.grid_columnconfigure(0, weight=1)  # Checkbox expands
           row_frame.grid_columnconfigure(1, weight=0)  # Entry fixed width

           # Checkbox (existing logic)
           var = ctk.BooleanVar(value=False)
           self._checkbox_vars[fg.id] = var
           checkbox = ctk.CTkCheckBox(
               row_frame,
               text=fg.display_name,
               variable=var,
               command=self._update_count
           )
           checkbox.grid(row=0, column=0, sticky="w")

           # Quantity entry (NEW)
           qty_var = ctk.StringVar(value="")
           self._quantity_vars[fg.id] = qty_var
           qty_entry = ctk.CTkEntry(
               row_frame,
               width=80,
               textvariable=qty_var,
               placeholder_text="Qty"
           )
           qty_entry.grid(row=0, column=1, padx=(10, 0))
           self._quantity_entries[fg.id] = qty_entry

           # Bind validation (will be implemented in T006)
           qty_var.trace_add("write", lambda *args, fid=fg.id: self._validate_quantity(fid))
   ```

3. **Update grid configuration** for proper tab order:
   ```python
   # Entries should be tabbable in order
   # Tab order follows grid order naturally in Tkinter
   ```

**Files Modified**:
- `src/ui/components/fg_selection_frame.py`

**Validation**:
- Each FG has checkbox AND quantity entry
- Layout is clean (entry to right of checkbox)
- Scroll behavior works with new entries

---

### Subtask T006 – Add Live Validation with Colored Feedback

**Purpose**: Validate quantity input on keystroke with visual feedback.

**File**: `src/ui/components/fg_selection_frame.py`

**Steps**:

1. **Add validation feedback label storage**:
   ```python
   self._feedback_labels: Dict[int, ctk.CTkLabel] = {}
   ```

2. **Add feedback label in row creation** (modify T005 code):
   ```python
   # After qty_entry creation:
   feedback_label = ctk.CTkLabel(
       row_frame,
       text="",
       width=100,
       anchor="w"
   )
   feedback_label.grid(row=0, column=2, padx=(5, 0))
   self._feedback_labels[fg.id] = feedback_label
   ```

3. **Implement `_validate_quantity()` method**:
   ```python
   def _validate_quantity(self, fg_id: int) -> None:
       """Validate quantity input and show feedback."""
       qty_text = self._quantity_vars[fg_id].get().strip()
       feedback_label = self._feedback_labels.get(fg_id)

       if not feedback_label:
           return

       # Empty is valid (FG not selected or quantity not specified)
       if not qty_text:
           feedback_label.configure(text="", text_color=("gray60", "gray40"))
           return

       try:
           qty = int(qty_text)
           if qty <= 0:
               feedback_label.configure(
                   text="Must be > 0",
                   text_color="orange"
               )
           else:
               # Valid - clear feedback
               feedback_label.configure(text="", text_color=("gray60", "gray40"))
       except ValueError:
           feedback_label.configure(
               text="Integer only",
               text_color="orange"
           )
   ```

4. **Handle edge cases**:
   - Leading zeros: `int("007")` → 7 (Python handles this)
   - Decimal values: `int("24.5")` raises ValueError → "Integer only"
   - Pasted text: Same validation applies

**Validation**:
- Empty field: no error
- Positive integer (1, 10, 100): no error
- Zero: orange "Must be > 0"
- Negative (-5): orange "Must be > 0"
- Non-integer (3.5, "abc"): orange "Integer only"

---

### Subtask T007 – Implement Quantity Pre-population

**Purpose**: Pre-populate quantity fields when loading existing event data.

**File**: `src/ui/components/fg_selection_frame.py`

**Steps**:

1. **Modify `set_selected()` or add `set_quantities()` method**:

   Option A: Extend `set_selected()` to accept quantities:
   ```python
   def set_selected_with_quantities(
       self,
       fg_quantities: List[Tuple[int, int]]  # [(fg_id, quantity), ...]
   ) -> None:
       """Pre-populate checkboxes and quantities."""
       # Create lookup for quantities
       qty_lookup = {fg_id: qty for fg_id, qty in fg_quantities}

       for fg_id, checkbox_var in self._checkbox_vars.items():
           if fg_id in qty_lookup:
               # Check the checkbox and set quantity
               checkbox_var.set(True)
               self._quantity_vars[fg_id].set(str(qty_lookup[fg_id]))
           else:
               # Uncheck and clear quantity
               checkbox_var.set(False)
               self._quantity_vars[fg_id].set("")

       self._update_count()
   ```

   Option B: Keep `set_selected()` for IDs only, add separate method:
   ```python
   def set_quantities(self, fg_quantities: Dict[int, int]) -> None:
       """Set quantity values for FGs (call after populate_finished_goods)."""
       for fg_id, quantity in fg_quantities.items():
           if fg_id in self._quantity_vars:
               self._quantity_vars[fg_id].set(str(quantity))
               # Also check the checkbox
               if fg_id in self._checkbox_vars:
                   self._checkbox_vars[fg_id].set(True)
       self._update_count()
   ```

2. **Ensure existing `set_selected()` still works** for backward compatibility if needed.

**Validation**:
- FGs with saved quantities show values in entry fields
- FGs without quantities show empty entry fields
- Checkboxes are checked for FGs with quantities

---

### Subtask T008 – Update get_selected() Return Type

**Purpose**: Return list of (fg_id, quantity) tuples instead of just IDs.

**File**: `src/ui/components/fg_selection_frame.py`

**Steps**:

1. **Update `get_selected()` method**:
   ```python
   def get_selected(self) -> List[Tuple[int, int]]:
       """
       Return selected FGs with their quantities.

       Returns:
           List of (fg_id, quantity) tuples for FGs with valid quantities.
           FGs with empty or invalid quantities are excluded.
       """
       result = []
       for fg_id, checkbox_var in self._checkbox_vars.items():
           # Only include if checkbox is checked
           if not checkbox_var.get():
               continue

           # Get quantity value
           qty_text = self._quantity_vars.get(fg_id, ctk.StringVar()).get().strip()

           # Skip empty quantities
           if not qty_text:
               continue

           # Skip invalid quantities
           try:
               qty = int(qty_text)
               if qty > 0:
                   result.append((fg_id, qty))
           except ValueError:
               continue  # Skip invalid entries

       return result
   ```

2. **Consider adding validation method** to check if all checked FGs have valid quantities:
   ```python
   def has_validation_errors(self) -> bool:
       """Check if any checked FG has invalid quantity."""
       for fg_id, checkbox_var in self._checkbox_vars.items():
           if not checkbox_var.get():
               continue

           qty_text = self._quantity_vars.get(fg_id, ctk.StringVar()).get().strip()
           if not qty_text:
               return True  # Checked but no quantity

           try:
               qty = int(qty_text)
               if qty <= 0:
                   return True
           except ValueError:
               return True

       return False
   ```

3. **Update any existing callers** (planning_tab.py) - this will be done in WP03.

**Validation**:
- Returns empty list when no FGs selected
- Returns (fg_id, quantity) tuples for valid selections
- Excludes FGs with empty quantities
- Excludes FGs with invalid quantities (zero, negative, non-integer)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing checkbox behavior | Test checkbox-only functionality still works |
| Tab order issues | Grid layout handles order; test manually |
| Performance with many FGs | Single-user app, ~50 FGs max - not a concern |
| Layout breaks on resize | Use sticky="ew" and weight for flexible layout |

---

## Definition of Done Checklist

- [ ] Quantity entry (CTkEntry, width=80) next to each FG checkbox
- [ ] Live validation with orange feedback text
- [ ] Empty field is valid (no error)
- [ ] Positive integers are valid
- [ ] Zero/negative/non-integer shows error
- [ ] `set_selected_with_quantities()` or `set_quantities()` pre-populates fields
- [ ] `get_selected()` returns `List[Tuple[int, int]]`
- [ ] Tab order is logical (can tab through all fields)
- [ ] No visual layout issues

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Quantity entry visible and properly aligned?
2. Validation feedback appears on invalid input?
3. Pre-population works correctly?
4. `get_selected()` returns correct format?
5. Existing checkbox behavior preserved?

**Manual Testing Steps**:
1. Open app, go to Planning Tab
2. Select event with available FGs
3. Verify each FG has checkbox + quantity entry
4. Enter various values (valid, invalid) and check feedback
5. Check tab order works logically

---

## Activity Log

- 2026-01-27T12:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
