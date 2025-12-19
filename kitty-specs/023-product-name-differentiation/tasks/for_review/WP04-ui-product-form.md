---
work_package_id: "WP04"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "UI Layer - ProductFormDialog Updates"
phase: "Phase 3 - UI Changes"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "29660"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-19T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - UI Layer - ProductFormDialog Updates

## Review Feedback

> **Populated by `/spec-kitty.review`** - Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

**Objective**: Add Product Name field to the Add/Edit Product form dialog in the UI.

**Success Criteria**:
- [ ] "Product Name" field appears after Brand field in form
- [ ] Field is optional (no asterisk, can be left blank)
- [ ] Existing product_name value loads when editing
- [ ] Entered value is included in save result
- [ ] 200-character limit enforced
- [ ] Help text explains when to use the field

## Context & Constraints

**Spec Reference**: `kitty-specs/023-product-name-differentiation/spec.md` - FR-004, FR-005
**Research Reference**: `kitty-specs/023-product-name-differentiation/research.md` - Section 5

**Key File**: `src/ui/ingredients_tab.py`
- ProductFormDialog class: line ~1448
- _create_form() method: line ~1499
- _populate_form() method: line ~1637
- _save() method: (find in class)

**Key Constraints**:
- CustomTkinter widgets (CTkEntry, CTkLabel)
- Follow existing form patterns exactly
- Constitution I: UI must be intuitive for non-technical users
- Window geometry is 550x550 - should accommodate new field

**Dependencies**: WP02 must be complete (service must accept product_name parameter)

## Subtasks & Detailed Guidance

### Subtask T010 - Add Product Name Entry Field

**Purpose**: Create the UI field for entering product variant names.

**Steps**:
1. Open `src/ui/ingredients_tab.py`
2. Locate `ProductFormDialog._create_form()` method (line ~1499)
3. Find the Brand field section (lines ~1519-1525):

```python
# Brand (required)
ctk.CTkLabel(form_frame, text="Brand*:").grid(
    row=row, column=0, sticky="w", padx=10, pady=5
)
self.brand_entry = ctk.CTkEntry(form_frame, placeholder_text="e.g., King Arthur")
self.brand_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
row += 1
```

4. Add Product Name field immediately after Brand (before Purchase Quantity):

```python
# Product Name (optional - for variants like "70% Cacao")
ctk.CTkLabel(form_frame, text="Product Name:").grid(
    row=row, column=0, sticky="w", padx=10, pady=5
)
self.product_name_entry = ctk.CTkEntry(
    form_frame,
    placeholder_text="e.g., 70% Cacao, Extra Virgin"
)
self.product_name_entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
row += 1
```

**Files**: `src/ui/ingredients_tab.py`
**Parallel?**: No (other subtasks depend on this)

**Notes**:
- No asterisk on label (optional field)
- Placeholder shows common examples
- Uses same entry pattern as brand

### Subtask T011 - Update _populate_form() Method

**Purpose**: Load existing product_name when editing a product.

**Steps**:
1. Locate `_populate_form()` method (line ~1637)
2. Find where brand is populated:

```python
self.brand_entry.insert(0, self.product.get("brand", ""))
```

3. Add product_name population after brand:

```python
self.brand_entry.insert(0, self.product.get("brand", ""))
self.product_name_entry.insert(0, self.product.get("product_name", "") or "")
```

**Files**: `src/ui/ingredients_tab.py`
**Parallel?**: No (depends on T010)

**Notes**:
- Use `or ""` to handle None values (None would cause insert error)
- product_name may be None from database, convert to empty string for display

### Subtask T012 - Update _save() Method

**Purpose**: Include product_name in the result dictionary when saving.

**Steps**:
1. Locate the `_save()` method in ProductFormDialog
2. Find where result dict is built (likely near form validation):

```python
self.result = {
    "brand": brand_value,
    "package_unit": package_unit_value,
    # ... other fields
}
```

3. Add product_name to result:

```python
# Get product_name value (empty string if blank)
product_name_value = self.product_name_entry.get().strip()

self.result = {
    "brand": brand_value,
    "product_name": product_name_value if product_name_value else None,  # NEW
    "package_unit": package_unit_value,
    # ... other fields
}
```

**Files**: `src/ui/ingredients_tab.py`
**Parallel?**: No (depends on T010)

**Notes**:
- Strip whitespace from input
- Convert empty string to None for consistency
- Position after brand in dict (readability)

### Subtask T013 - Add Validation and Help Text

**Purpose**: Enforce 200-character limit and explain field purpose.

**Steps**:
1. In `_save()`, add length validation:

```python
product_name_value = self.product_name_entry.get().strip()
if len(product_name_value) > 200:
    messagebox.showerror(
        "Validation Error",
        "Product Name must be 200 characters or less."
    )
    return
```

2. Locate the help text label (around line 1596-1605):

```python
help_label = ctk.CTkLabel(
    form_frame,
    text="* Required fields\n\n"
    "Package size is calculated from quantity + unit.\n"
    "Example: 25 lb → '25 lb bag'\n"
    "Preferred products are used by default in shopping lists.",
    text_color="gray",
    justify="left",
)
```

3. Update to include product_name explanation:

```python
help_label = ctk.CTkLabel(
    form_frame,
    text="* Required fields\n\n"
    "Product Name: Use for variants like flavors or formulations\n"
    "(e.g., '70% Cacao', 'Extra Virgin', 'Unsweetened').\n\n"
    "Package size is calculated from quantity + unit.\n"
    "Preferred products are used by default in shopping lists.",
    text_color="gray",
    justify="left",
)
```

**Files**: `src/ui/ingredients_tab.py`
**Parallel?**: No (depends on T010)

**Notes**:
- 200-char limit matches database column size
- Help text should be concise and practical
- Examples help non-technical users understand purpose

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Form too tall for window | Low | Current window is 550x550, has room |
| User confusion about field | Medium | Clear placeholder and help text |
| Validation error UX | Low | Use standard messagebox pattern |

## Definition of Done Checklist

- [ ] T010: Product Name field visible in form after Brand
- [ ] T011: Existing product_name loads correctly when editing
- [ ] T012: Entered product_name included in save result
- [ ] T013: 200-char validation works; help text updated
- [ ] Field label shows no asterisk (optional)
- [ ] Manual test: Add product with product_name, edit to change it

## Review Guidance

**Reviewers should verify**:
1. Field position is between Brand and Purchase Quantity
2. Label is "Product Name:" (no asterisk)
3. Placeholder text is helpful
4. None handling correct in _populate_form
5. Empty string converted to None in _save
6. Help text mentions product_name use case

## Activity Log

- 2025-12-19T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-19T16:51:12Z – claude – shell_pid=29391 – lane=doing – Started implementation
- 2025-12-19T16:52:21Z – claude – shell_pid=29660 – lane=for_review – UI updates complete - ready for review
