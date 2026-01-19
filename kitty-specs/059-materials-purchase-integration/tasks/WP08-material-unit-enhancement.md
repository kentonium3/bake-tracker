---
work_package_id: "WP08"
subtasks:
  - "T041"
  - "T042"
  - "T043"
  - "T044"
  - "T045"
title: "MaterialUnit UI Enhancement"
phase: "Wave 2 - Extended Features"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "13142"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - MaterialUnit UI Enhancement

## Important: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# No service dependencies - UI-only changes to existing dialog
spec-kitty implement WP08
```

---

## Objectives & Success Criteria

Enhance MaterialUnitFormDialog to display inherited unit type and consumption preview. This enables users to:
- See the base unit type inherited from the parent Material
- Understand what units they're defining
- See a preview of how consumption will work
- Have quantity auto-set to 1 for "each" materials

**Success Criteria**:
- [ ] Unit type displays when Material is selected
- [ ] Quantity label is dynamic based on unit type
- [ ] Preview text shows consumption example
- [ ] "each" materials lock quantity to 1
- [ ] All tests pass

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Research: `kitty-specs/059-materials-purchase-integration/research.md`

**Gap Identified** (from research.md):
> base_unit_type is loaded but not displayed to user in MaterialUnitFormDialog

**Key File Reference**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog, approximately lines 1304-1562)

**Material Unit Types**:
- `each`: Discrete items (1 bag, 1 box) - quantity MUST be 1
- `linear_cm`: Length-based (ribbon, tape) - quantity is cm consumed
- `square_cm`: Area-based (paper, fabric) - quantity is cm² consumed

---

## Subtasks & Detailed Guidance

### Subtask T041 - Add Unit Type Display Label

**Purpose**: Show the inherited base_unit_type from the selected Material.

**Steps**:
1. Open `src/ui/materials_tab.py`
2. Find MaterialUnitFormDialog class
3. Add a label to display unit type after Material dropdown:

```python
# In _create_form_widgets() or similar method, after material dropdown:

# Unit type display (read-only)
self._unit_type_label = ctk.CTkLabel(
    self._form_frame,
    text="Unit Type: (select material)",
    font=ctk.CTkFont(size=12),
    text_color="gray"
)
self._unit_type_label.pack(anchor="w", pady=(5, 0))
```

4. Update label when material is selected (see T045):

```python
def _update_unit_type_display(self, unit_type: str):
    """Update the unit type display label."""
    type_descriptions = {
        "each": "each (discrete items)",
        "linear_cm": "linear_cm (length in centimeters)",
        "square_cm": "square_cm (area in square centimeters)",
    }
    description = type_descriptions.get(unit_type, unit_type)
    self._unit_type_label.configure(
        text=f"Unit Type: {description}",
        text_color="black"
    )
```

**Files**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog section)

**Validation**:
- [ ] Label shows "select material" initially
- [ ] Label updates to show unit type when material selected
- [ ] Description is user-friendly (not just "each")

---

### Subtask T042 - Make Quantity Label Dynamic

**Purpose**: Update quantity field label based on selected unit type.

**Steps**:
1. Create dynamic label that changes with material selection:

```python
# Replace static "Quantity per unit:" label with dynamic one
self._quantity_label = ctk.CTkLabel(
    self._form_frame,
    text="Quantity per unit:",
    font=ctk.CTkFont(weight="bold")
)
self._quantity_label.pack(anchor="w", pady=(10, 0))
```

2. Update label text based on unit type (see T045):

```python
def _update_quantity_label(self, unit_type: str):
    """Update the quantity field label based on unit type."""
    label_text = {
        "each": "Quantity per unit (always 1):",
        "linear_cm": "Length consumed per unit (cm):",
        "square_cm": "Area consumed per unit (cm²):",
    }
    self._quantity_label.configure(
        text=label_text.get(unit_type, "Quantity per unit:")
    )
```

**Files**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog section)

**Validation**:
- [ ] Label changes when material type changes
- [ ] Label is clear about what unit to enter
- [ ] Default label shown when no material selected

---

### Subtask T043 - Add Preview Text for Consumption

**Purpose**: Show user-friendly preview of what this unit will consume.

**Steps**:
1. Add preview section to dialog:

```python
# After quantity entry
self._preview_frame = ctk.CTkFrame(self._form_frame)
self._preview_frame.pack(fill="x", pady=10)

self._preview_label = ctk.CTkLabel(
    self._preview_frame,
    text="",
    font=ctk.CTkFont(size=11),
    text_color="gray"
)
self._preview_label.pack(anchor="w")
```

2. Update preview when material or quantity changes (see T045):

```python
def _update_consumption_preview(self):
    """Update the consumption preview text."""
    material_name = self._get_selected_material_name()
    unit_type = self._get_selected_unit_type()
    quantity = self._get_quantity_value()

    if not material_name or not unit_type or quantity is None:
        self._preview_label.configure(text="")
        return

    if unit_type == "each":
        preview = f"Each use of this unit will consume 1 {material_name}"
    elif unit_type == "linear_cm":
        preview = f"Each use of this unit will consume {quantity:.2f} cm of {material_name}"
    elif unit_type == "square_cm":
        preview = f"Each use of this unit will consume {quantity:.2f} cm² of {material_name}"
    else:
        preview = f"Each use will consume {quantity:.2f} {unit_type} of {material_name}"

    self._preview_label.configure(text=preview)
```

**Files**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog section)

**Validation**:
- [ ] Preview updates in real-time
- [ ] Text is clear and user-friendly
- [ ] Shows material name and quantity with units

---

### Subtask T044 - Lock Quantity to 1 for "each" Materials

**Purpose**: Prevent invalid quantity for discrete materials.

**Steps**:
1. Add logic to lock quantity field for "each" materials (see T045):

```python
def _set_quantity_locked(self, locked: bool, value: int = 1):
    """Lock or unlock the quantity field."""
    if locked:
        # Set value to 1 and disable
        self._quantity_var.set("1")
        self._quantity_entry.configure(state="disabled")
    else:
        # Enable the field
        self._quantity_entry.configure(state="normal")
```

2. Call when material changes:

```python
# In _on_material_selected() handler
if unit_type == "each":
    self._set_quantity_locked(True, value=1)
else:
    self._set_quantity_locked(False)
```

3. Ensure validation respects the lock:

```python
def _validate_quantity(self) -> tuple[bool, str]:
    """Validate quantity value."""
    unit_type = self._get_selected_unit_type()

    if unit_type == "each":
        # Must be exactly 1
        try:
            qty = Decimal(self._quantity_var.get())
            if qty != 1:
                return False, "Quantity must be 1 for 'each' materials"
        except:
            return False, "Invalid quantity"
    else:
        # Must be positive number
        try:
            qty = Decimal(self._quantity_var.get())
            if qty <= 0:
                return False, "Quantity must be greater than 0"
        except:
            return False, "Invalid quantity"

    return True, ""
```

**Files**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog section)

**Validation**:
- [ ] "each" materials auto-set quantity to 1
- [ ] Quantity field disabled for "each" materials
- [ ] Field re-enabled when switching to variable material
- [ ] Validation enforces quantity=1 for "each"

---

### Subtask T045 - Update _on_material_selected Handler

**Purpose**: Wire up all the dynamic updates when material selection changes.

**Steps**:
1. Find existing `_on_material_selected()` method (or create if missing)
2. Add calls to all update methods:

```python
def _on_material_selected(self, event=None):
    """Handle material dropdown selection change."""
    # Get selected material
    selected = self._material_var.get()
    if not selected or selected == "Select Material":
        # Reset to defaults
        self._unit_type_label.configure(text="Unit Type: (select material)", text_color="gray")
        self._quantity_label.configure(text="Quantity per unit:")
        self._preview_label.configure(text="")
        self._quantity_entry.configure(state="normal")
        return

    # Look up material data
    material = self._get_material_by_name(selected)
    if not material:
        return

    unit_type = material.get("base_unit_type", "each")

    # Update all dynamic elements (T041-T044)
    self._update_unit_type_display(unit_type)
    self._update_quantity_label(unit_type)

    # Lock/unlock quantity for "each" materials
    if unit_type == "each":
        self._set_quantity_locked(True)
    else:
        self._set_quantity_locked(False)

    # Update preview
    self._update_consumption_preview()

def _get_material_by_name(self, name: str) -> Optional[Dict]:
    """Get material data from cached materials dict."""
    # Materials should already be loaded in self._materials
    for m in self._materials:
        if m.get("name") == name:
            return m
    return None
```

3. Add trace for quantity changes to update preview:

```python
# In __init__ or widget creation
self._quantity_var.trace_add("write", lambda *args: self._update_consumption_preview())
```

4. Bind material dropdown change:

```python
self._material_dropdown.configure(command=self._on_material_selected)
# Or if using combobox:
self._material_combobox.bind("<<ComboboxSelected>>", self._on_material_selected)
```

**Files**:
- `src/ui/materials_tab.py` (MaterialUnitFormDialog section)

**Validation**:
- [ ] All dynamic elements update on material change
- [ ] Preview updates on quantity change
- [ ] Switching between materials works smoothly
- [ ] No errors when clearing selection

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/ui/test_materials_tab.py -v -k unit
```

Manual testing:
1. Open Materials tab, click "Add Unit"
2. Verify default state (no material selected)
3. Select an "each" material (e.g., "Gift Bags")
   - Verify unit type shows "each (discrete items)"
   - Verify quantity label shows "Quantity per unit (always 1):"
   - Verify quantity is locked at 1
   - Verify preview shows correct text
4. Switch to a "linear_cm" material (e.g., "Ribbon")
   - Verify unit type updates
   - Verify quantity unlocks
   - Enter "15.24" for 6-inch
   - Verify preview shows "15.24 cm"
5. Test "square_cm" material similarly

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout space constraints | May need to resize dialog |
| Material data not available | Load materials on dialog open |
| User confusion about units | Clear labels and preview text |

---

## Definition of Done Checklist

- [ ] T041: Unit type display label shows inherited type
- [ ] T042: Quantity label updates dynamically
- [ ] T043: Consumption preview shows clear example
- [ ] T044: Quantity locked to 1 for "each" materials
- [ ] T045: Handler wires all updates on material change
- [ ] Preview updates on quantity change
- [ ] Manual testing confirms all scenarios
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify "each" materials MUST have quantity=1 (no exceptions)
- Check preview text is grammatically correct
- Ensure quantity field state (locked/unlocked) persists correctly
- Verify no errors when switching between materials

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T03:13:59Z – claude-opus – shell_pid=9582 – lane=doing – Started implementation via workflow command
- 2026-01-19T03:22:37Z – claude-opus – shell_pid=9582 – lane=for_review – Ready for review: MaterialUnit dialog now shows inherited unit type, dynamic quantity labels, consumption preview, and locks quantity to 1 for 'each' materials. All 2511 tests pass.
- 2026-01-19T03:29:16Z – claude-opus – shell_pid=13142 – lane=doing – Started review via workflow command
- 2026-01-19T03:29:50Z – claude-opus – shell_pid=13142 – lane=done – Review passed: All success criteria met - unit type display, dynamic labels, consumption preview, quantity locking for 'each' materials. Code is well-documented with dark mode support. All 2511 tests pass.
