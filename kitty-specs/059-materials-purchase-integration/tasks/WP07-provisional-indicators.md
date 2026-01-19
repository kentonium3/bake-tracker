---
work_package_id: "WP07"
subtasks:
  - "T037"
  - "T038"
  - "T039"
  - "T040"
title: "Provisional Product UI Indicators"
phase: "Wave 2 - Extended Features"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "13641"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-18T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Provisional Product UI Indicators

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
# Depends on WP01 (check_provisional_completeness method)
spec-kitty implement WP07
```

---

## Objectives & Success Criteria

Add provisional product indicators to MaterialProductsTab and enrichment workflow. This enables users to:
- Easily identify products that need additional information
- See visual badges/indicators for provisional products
- Complete product information through editing
- Have is_provisional auto-clear when all fields are complete

**Success Criteria**:
- [ ] Provisional products show visual indicator in table
- [ ] Indicator is prominent (color/icon, not subtle)
- [ ] Edit dialog shows which fields are missing
- [ ] Saving complete product clears is_provisional
- [ ] All tests pass

---

## Context & Constraints

**Feature**: F059 - Materials Purchase Integration & Workflows
**Reference Documents**:
- Spec: `kitty-specs/059-materials-purchase-integration/spec.md`
- Plan: `kitty-specs/059-materials-purchase-integration/plan.md`
- Data Model: `kitty-specs/059-materials-purchase-integration/data-model.md`

**Completeness Criteria** (from spec clarification):
Product is complete when ALL present:
- name
- brand
- slug
- package_quantity
- package_unit
- material_id

**Pattern Reference**: Follow existing indicator patterns (e.g., hidden products styling)

**Key Files**:
- `src/ui/materials_tab.py` (modify - MaterialProductsTab)
- `src/services/material_catalog_service.py` (consume - check_provisional_completeness)

---

## Subtasks & Detailed Guidance

### Subtask T037 - Add Provisional Indicator to Table

**Purpose**: Add a column or badge showing provisional status.

**Steps**:
1. Open `src/ui/materials_tab.py`
2. Find MaterialProductsTab class and its table/treeview setup
3. Add "Status" column to show provisional indicator:

```python
# In column configuration
columns = {
    # ... existing columns ...
    "status": {"width": 100, "anchor": "center", "text": "Status"},
}
```

4. Populate status column based on is_provisional:

```python
def _get_product_status(self, product: Dict) -> str:
    """Get status text for product."""
    if product.get("is_provisional", False):
        return "⚠ Needs Info"  # Or use different indicator
    elif product.get("is_hidden", False):
        return "Hidden"
    return "Complete"
```

5. Apply visual styling for provisional status:

```python
# When inserting row, apply tag for provisional
if product.get("is_provisional", False):
    self._tree.item(item_id, tags=("provisional",))

# Configure tag styling
self._tree.tag_configure("provisional", foreground="orange")
```

**Files**:
- `src/ui/materials_tab.py` (MaterialProductsTab section)

**Validation**:
- [ ] Status column visible in table
- [ ] Provisional products show "Needs Info" or similar
- [ ] Color/styling makes provisional rows stand out

---

### Subtask T038 - Show "Needs Enrichment" Badge

**Purpose**: Make provisional indicator prominent and actionable.

**Steps**:
1. Create a more prominent indicator (option A - row highlighting):

```python
# Configure tag with background color
self._tree.tag_configure(
    "provisional",
    foreground="black",
    background="#FFE4B5"  # Moccasin/light orange
)
```

2. Or use icon column (option B - if preferred):

```python
# Add icon column
columns = {
    "icon": {"width": 30, "anchor": "center", "text": ""},
    # ... other columns ...
}

# Set icon value
icon = "⚠" if product.get("is_provisional") else ""
values = (icon, product["name"], ...)
```

3. Add tooltip or additional context (if supported):

```python
def _on_row_hover(self, event):
    """Show tooltip for provisional products."""
    item = self._tree.identify_row(event.y)
    if item:
        product = self._get_product_for_item(item)
        if product and product.get("is_provisional"):
            # Show tooltip: "Missing: brand, slug"
            pass
```

**Files**:
- `src/ui/materials_tab.py` (MaterialProductsTab section)

**Validation**:
- [ ] Indicator is immediately visible
- [ ] Not confusable with other states (hidden, error)
- [ ] Color-blind friendly (use icon + color, not color alone)

---

### Subtask T039 - Update Edit Dialog for Completeness Tracking

**Purpose**: Show which fields are missing during editing.

**Steps**:
1. Find or create the product edit dialog
2. Add completeness indicator that updates as user fills fields:

```python
def _update_completeness_indicator(self):
    """Update the completeness status display."""
    from src.services.material_catalog_service import check_provisional_completeness

    # Build current values from form
    current_values = {
        "name": self._name_var.get().strip(),
        "brand": self._brand_var.get().strip(),
        "slug": self._slug_var.get().strip(),
        "package_quantity": self._package_qty_var.get(),
        "package_unit": self._package_unit_var.get().strip(),
        "material_id": self._material_id,
    }

    # Check what's missing
    missing = []
    if not current_values["name"]:
        missing.append("name")
    if not current_values["brand"]:
        missing.append("brand")
    if not current_values["slug"]:
        missing.append("slug")
    # ... etc for other fields

    if missing:
        self._completeness_label.configure(
            text=f"Missing: {', '.join(missing)}",
            text_color="orange"
        )
    else:
        self._completeness_label.configure(
            text="✓ Product complete",
            text_color="green"
        )
```

3. Add trace handlers to update on field changes:

```python
self._name_var.trace_add("write", lambda *args: self._update_completeness_indicator())
self._brand_var.trace_add("write", lambda *args: self._update_completeness_indicator())
# ... etc
```

4. Add visual indicator for required fields:

```python
# Label required fields
ctk.CTkLabel(
    frame,
    text="Brand *",  # Asterisk for required
    font=ctk.CTkFont(weight="bold")
)
```

**Files**:
- `src/ui/materials_tab.py` (product edit dialog)
- Or `src/ui/dialogs/material_product_dialog.py` if separate file

**Validation**:
- [ ] Missing fields listed in real-time
- [ ] Required fields marked with asterisk
- [ ] Complete status shown when all fields filled

---

### Subtask T040 - Auto-clear is_provisional on Save

**Purpose**: Automatically promote product when complete.

**Steps**:
1. The service layer (WP01) handles this automatically via update_product()
2. Verify the edit dialog calls update_product() correctly:

```python
def _on_save(self):
    """Handle save button click."""
    from src.services.material_catalog_service import update_product

    try:
        # Gather all field values
        updates = {
            "name": self._name_var.get().strip(),
            "brand": self._brand_var.get().strip(),
            "slug": self._slug_var.get().strip(),
            "package_quantity": Decimal(self._package_qty_var.get()),
            "package_unit": self._package_unit_var.get().strip(),
            # ... other fields
        }

        # Update product (service auto-clears is_provisional if complete)
        result = update_product(self._product_id, **updates)

        # Show feedback if status changed
        was_provisional = self._original_product.get("is_provisional", False)
        is_provisional = result.get("is_provisional", False)

        if was_provisional and not is_provisional:
            # Product was promoted from provisional
            self._show_message("Product completed! No longer provisional.")

        self._on_save_callback(result)
        self.destroy()

    except Exception as e:
        self._show_error(str(e))
```

3. Refresh the table after save to show updated status:

```python
# In the callback passed to dialog
def on_product_saved(result):
    self._refresh_products_table()
```

**Files**:
- `src/ui/materials_tab.py` (product edit dialog save handler)

**Validation**:
- [ ] Saving complete product clears is_provisional
- [ ] Table row updates to show "Complete" status
- [ ] User gets feedback that product was promoted

---

## Test Strategy

Run tests with:
```bash
./run-tests.sh src/tests/ui/test_materials_tab.py -v
```

Manual testing:
1. Create a provisional product via CLI (WP06)
2. Open Materials tab, verify indicator shows
3. Edit the product, verify missing fields listed
4. Fill in all required fields
5. Save and verify is_provisional cleared
6. Verify table updates to show "Complete"

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Indicator too subtle | Use both color AND icon/text |
| User confusion about requirements | Clear labeling of required fields |
| Save without all fields | Allow save but keep provisional (by design) |

---

## Definition of Done Checklist

- [ ] T037: Status column added to products table
- [ ] T038: Prominent visual indicator for provisional
- [ ] T039: Edit dialog shows missing fields in real-time
- [ ] T040: is_provisional auto-clears on save when complete
- [ ] Indicator visible and accessible (color + text/icon)
- [ ] Manual testing confirms workflow
- [ ] tasks.md updated with status change

---

## Review Guidance

- Verify indicator is visible at a glance (not subtle)
- Check accessibility (not color-only indicator)
- Ensure required fields match completeness criteria from spec
- Verify table refreshes after save

---

## Activity Log

- 2026-01-18T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-19T02:57:34Z – claude-opus – shell_pid=5334 – lane=doing – Started implementation via workflow command
- 2026-01-19T03:10:11Z – claude-opus – shell_pid=5334 – lane=for_review – Ready for review: Added provisional product UI indicators - status column with visual badge, completeness tracking in edit dialog, auto-clear is_provisional on save when complete. All 2511 tests pass.
- 2026-01-19T03:31:33Z – claude-opus – shell_pid=13641 – lane=doing – Started review via workflow command
- 2026-01-19T03:43:13Z – claude-opus – shell_pid=13641 – lane=done – Review passed: All success criteria met - status column with visual badge (icon + color), completeness tracking in edit dialog with real-time updates, brand field added, auto-clear is_provisional on save. Accessibility addressed with icon+text not just color. All 2511 tests pass.
