---
work_package_id: WP04
title: Enhance MaterialUnit Dialog
lane: "doing"
dependencies: [WP03]
base_branch: 085-fix-material-unit-management-ux-WP03
base_commit: 4e723dcba6e32c83f9e9300bfff6a577715837d0
created_at: '2026-01-30T23:07:02.795967+00:00'
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 2 - Enhancement
assignee: ''
agent: "claude-opus"
shell_pid: "80903"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T22:39:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Enhance MaterialUnit Dialog

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

**IMPORTANT**: This WP depends on WP03. Use the `--base WP03` flag to branch from WP03's completed work (which includes `unit_conversion_service.py`).

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Enhance the MaterialUnitDialog to show a unit dropdown for linear products, allowing users to enter measurements in their preferred units with automatic conversion to centimeters.

**Success Criteria**:
- [ ] Unit dropdown appears for linear products only (base_unit_type == 'linear_cm')
- [ ] Dropdown shows all linear unit options (cm, in, ft, yd, m)
- [ ] Conversion to cm happens automatically on save
- [ ] Placeholder text is helpful and accurate
- [ ] Users can create "8-inch ribbon" by entering "8" and selecting "inches"
- [ ] No dropdown appears for "each" type products

---

## Context & Constraints

**Background**: The current MaterialUnitDialog asks for "Qty per Unit" with a confusing placeholder. Users must manually convert measurements to centimeters. This enhancement adds a unit selector dropdown for linear products.

**Related Documents**:
- Spec: `kitty-specs/085-fix-material-unit-management-ux/spec.md` (FR-003, FR-004, User Story 3)
- Plan: `kitty-specs/085-fix-material-unit-management-ux/plan.md` (Issue 3)

**Dependency**: This WP requires `unit_conversion_service.py` from WP03.

**Key Files**:
- `src/ui/dialogs/material_unit_dialog.py` - Dialog to enhance
- `src/services/unit_conversion_service.py` - Conversion functions (from WP03)
- `src/models/material_product.py` - Has `material_id` FK
- `src/models/material.py` - Has `base_unit_type` field

**Constraints**:
- Only show dropdown for linear products (`base_unit_type == 'linear_cm'`)
- Keep "each" type products unchanged (no dropdown)
- Store values in cm (base unit) regardless of input unit
- Use service layer for conversion (Principle V)

---

## Subtasks & Detailed Guidance

### Subtask T009 – Detect Linear Product in Dialog

**Purpose**: Determine whether the current MaterialProduct's parent Material is linear type, to conditionally show the unit dropdown.

**Steps**:
1. The dialog receives `product_id` as a parameter
2. Query to get the Material's `base_unit_type`:
   ```python
   def _get_material_base_unit_type(self, product_id: int) -> str:
       """Get the base_unit_type for the product's parent material."""
       from src.services.material_catalog_service import get_product

       product = get_product(product_id)
       if product and product.material:
           return product.material.base_unit_type
       return "each"  # Default if not found
   ```
3. Store result in `self.base_unit_type` for use in dialog construction
4. Add check method:
   ```python
   def _is_linear_product(self) -> bool:
       """Check if this is a linear measurement product."""
       return self.base_unit_type == "linear_cm"
   ```

**Files**:
- `src/ui/dialogs/material_unit_dialog.py`

**Notes**:
- Handle case where product or material is None (defensive)
- Call this early in `__init__` before creating form fields
- Check existing service methods - `get_product()` may already exist

---

### Subtask T010 – Add Unit Dropdown for Linear Products

**Purpose**: Add a CTkComboBox showing linear unit options when the product is linear type.

**Steps**:
1. Import the conversion service:
   ```python
   from src.services.unit_conversion_service import get_linear_unit_options, convert_to_cm
   ```

2. Modify `_create_form()` to conditionally show dropdown:
   ```python
   # After quantity entry field creation
   if self._is_linear_product():
       # Add unit dropdown
       ctk.CTkLabel(form_frame, text="Unit:").grid(
           row=row, column=0, sticky="w", padx=10, pady=5
       )

       # Get options from service
       options = get_linear_unit_options()
       option_names = [name for _, name in options]

       # Store code mapping for conversion
       self._unit_code_map = {name: code for code, name in options}

       self.unit_dropdown = ctk.CTkComboBox(
           form_frame,
           values=option_names,
           width=200,
       )
       self.unit_dropdown.set(option_names[0])  # Default to cm
       self.unit_dropdown.grid(row=row, column=1, sticky="w", padx=10, pady=5)
       row += 1
   else:
       self.unit_dropdown = None
       self._unit_code_map = None
   ```

3. Position dropdown next to or below the quantity field
4. Ensure proper grid layout alignment

**Files**:
- `src/ui/dialogs/material_unit_dialog.py`

**Notes**:
- CTkComboBox takes `values` as a list of strings (display names)
- Store mapping to convert display name back to code
- Default to "Centimeters (cm)" as first option

---

### Subtask T011 – Implement Conversion on Save

**Purpose**: Convert user-entered quantity to centimeters before saving to database.

**Steps**:
1. Modify `_on_save()` to handle unit conversion:
   ```python
   def _on_save(self):
       """Validate and save the unit."""
       name = self.name_entry.get().strip()
       description = self.desc_entry.get().strip() or None

       # Validate name
       if not name:
           messagebox.showerror("Validation Error", "Name is required.")
           return

       try:
           if self.unit_id:
               # Update existing unit (no quantity change allowed)
               material_unit_service.update_unit(
                   unit_id=self.unit_id,
                   name=name,
                   description=description,
               )
           else:
               # Create new unit - get quantity
               qty_str = self.qty_entry.get().strip() if self.qty_entry else "1.0"
               try:
                   quantity = float(qty_str)
                   if quantity <= 0:
                       raise ValueError("Must be positive")
               except ValueError:
                   messagebox.showerror(
                       "Validation Error", "Quantity must be a positive number."
                   )
                   return

               # Convert to cm if linear product with dropdown
               if self.unit_dropdown and self._unit_code_map:
                   selected_display = self.unit_dropdown.get()
                   unit_code = self._unit_code_map.get(selected_display, "cm")
                   quantity_per_unit = convert_to_cm(quantity, unit_code)
               else:
                   # "each" type or no dropdown - use value as-is
                   quantity_per_unit = quantity

               if not self.product_id:
                   messagebox.showerror(
                       "Error", "Product must be saved before adding units."
                   )
                   return

               material_unit_service.create_unit(
                   material_product_id=self.product_id,
                   name=name,
                   quantity_per_unit=quantity_per_unit,
                   description=description,
               )

           self.result = True
           self.destroy()

       except ValidationError as e:
           # ... existing error handling
   ```

2. Ensure conversion only happens for new units (edit mode doesn't change quantity)
3. Log or display the converted value for debugging:
   ```python
   print(f"DEBUG: {quantity} {unit_code} -> {quantity_per_unit} cm")
   ```

**Files**:
- `src/ui/dialogs/material_unit_dialog.py`

**Notes**:
- Import `convert_to_cm` at top of file
- Handle case where dropdown exists but user didn't change it
- Ensure "each" type products bypass conversion entirely

---

### Subtask T012 – Update Placeholder Text and Hints

**Purpose**: Make the dialog more user-friendly with accurate placeholder text and optional conversion preview.

**Steps**:
1. Update the quantity field placeholder based on product type:
   ```python
   if self._is_linear_product():
       placeholder = "e.g., 8 (then select unit)"
   else:
       placeholder = "e.g., 1.0"

   self.qty_entry = ctk.CTkEntry(
       form_frame, placeholder_text=placeholder
   )
   ```

2. Remove the confusing old placeholder "e.g., 0.1524 (6 inches in meters)"

3. Optionally add a conversion preview label that updates when values change:
   ```python
   if self._is_linear_product():
       self.preview_label = ctk.CTkLabel(
           form_frame,
           text="",
           text_color="gray",
       )
       self.preview_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=10)

       # Bind to update preview on change
       self.qty_entry.bind("<KeyRelease>", self._update_conversion_preview)
       self.unit_dropdown.configure(command=self._update_conversion_preview)
       row += 1

   def _update_conversion_preview(self, event=None):
       """Update the conversion preview label."""
       if not self.unit_dropdown or not self._unit_code_map:
           return

       try:
           qty = float(self.qty_entry.get().strip())
           selected_display = self.unit_dropdown.get()
           unit_code = self._unit_code_map.get(selected_display, "cm")
           result_cm = convert_to_cm(qty, unit_code)
           self.preview_label.configure(
               text=f"= {result_cm:.2f} cm (stored value)"
           )
       except (ValueError, TypeError):
           self.preview_label.configure(text="")
   ```

4. Test the preview updates live as user types

**Files**:
- `src/ui/dialogs/material_unit_dialog.py`

**Notes**:
- The preview is optional but highly recommended for user confidence
- Keep the preview subtle (gray text, smaller font)
- Handle empty/invalid input gracefully (clear preview)

---

## Test Strategy

**Manual Testing Required**:

1. **Test Linear Product - Add Unit**:
   - Open Edit Product dialog for a linear product (e.g., ribbon)
   - Click "Add Unit" button
   - Verify unit dropdown appears with options: cm, in, ft, yd, m
   - Enter "8" in quantity, select "Inches (in)"
   - Verify preview shows "= 20.32 cm"
   - Enter name "8-inch cut"
   - Save → verify saved to database
   - Query database to confirm `quantity_per_unit = 20.32`

2. **Test Linear Product - Different Units**:
   - Add "1 yard cut" → should save as 91.44 cm
   - Add "1 foot cut" → should save as 30.48 cm
   - Add "100 cm cut" → should save as 100.0 cm

3. **Test "Each" Type Product**:
   - Open Edit Product dialog for an "each" type product
   - Click "Add Unit" button
   - Verify NO unit dropdown appears
   - Enter quantity directly → saved as-is

4. **Test Validation**:
   - Empty quantity → error message
   - Zero quantity → error message
   - Negative quantity → error message (should be caught by convert_to_cm)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Conversion service not available | WP depends on WP03; use `--base WP03` flag |
| UI layout issues with new dropdown | Test dialog size and alignment |
| Preview not updating | Ensure event bindings are correct |
| "each" type accidentally shows dropdown | Check `_is_linear_product()` logic |

---

## Definition of Done Checklist

- [ ] T009: Linear product detection works correctly
- [ ] T010: Unit dropdown appears for linear products only
- [ ] T011: Conversion to cm happens on save
- [ ] T012: Placeholder text is helpful
- [ ] T012: Conversion preview shows live updates (optional)
- [ ] "8-inch ribbon" can be created by entering "8" and selecting "inches"
- [ ] "each" type products have no dropdown
- [ ] All values stored in cm in database
- [ ] No console errors

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Test adding unit with "inches" → verify cm conversion correct
2. Test "each" type product → NO dropdown should appear
3. Verify database stores values in cm
4. Check UI alignment and usability

**Code Review Focus**:
- Correct use of conversion service
- Clean UI layout
- Error handling for invalid input
- No hardcoded conversion factors (use service)

---

## Activity Log

- 2026-01-30T22:39:29Z – system – lane=planned – Prompt created.
- 2026-01-30T23:10:44Z – unknown – shell_pid=79634 – lane=for_review – Implementation complete: Linear product detection, unit dropdown, conversion to cm, preview label
- 2026-01-30T23:10:48Z – claude-opus – shell_pid=80903 – lane=doing – Started review via workflow command
