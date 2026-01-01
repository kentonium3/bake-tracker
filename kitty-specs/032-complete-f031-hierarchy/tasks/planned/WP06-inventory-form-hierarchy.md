---
work_package_id: "WP06"
subtasks:
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Inventory Form Hierarchy Display"
phase: "Phase 3 - Inventory Tab"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-31T23:59:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Inventory Form Hierarchy Display

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Display read-only hierarchy information in inventory add/edit forms.

**Success Criteria**:
- Add inventory dialog shows hierarchy labels (L0, L1, L2)
- Edit inventory dialog shows hierarchy labels (L0, L1, L2)
- Labels are read-only (informational only)
- Hierarchy populated from product -> ingredient relationship
- Missing levels display as dash

**User Story**: US5 - View Inventory with Hierarchy Information

---

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/032-complete-f031-hierarchy/spec.md` (FR-019, FR-020)
- Plan: `kitty-specs/032-complete-f031-hierarchy/plan.md`

**Key Service Functions**:
```python
# Get product to find ingredient
product = product_service.get_product(product_id)
ingredient_id = product.ingredient_id

# Get hierarchy info
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
ingredient = ingredient_service.get_ingredient(ingredient_id)
```

**Files to Modify**:
- `src/ui/inventory_tab.py` (if inline dialog)
- `src/ui/forms/inventory_form.py` or similar (if separate file)

**Dependencies**: WP05 (Inventory grid) for consistency

---

## Subtasks & Detailed Guidance

### Subtask T032 - Add Hierarchy Labels to Add Dialog

**Purpose**: Show hierarchy information when adding new inventory item.

**Steps**:
1. Find the add inventory dialog
2. Add three read-only labels: "Category (L0):", "Subcategory (L1):", "Ingredient (L2):"
3. Position labels near product selection for context
4. Labels initially show "--" until product is selected
5. On product selection change, update labels

**Implementation**:
```python
# In dialog setup
self.l0_label = ctk.CTkLabel(form_frame, text="Category (L0):")
self.l0_value = ctk.CTkLabel(form_frame, text="--")

self.l1_label = ctk.CTkLabel(form_frame, text="Subcategory (L1):")
self.l1_value = ctk.CTkLabel(form_frame, text="--")

self.l2_label = ctk.CTkLabel(form_frame, text="Ingredient (L2):")
self.l2_value = ctk.CTkLabel(form_frame, text="--")

# On product selection change
def _on_product_change(self, product_name: str):
    product = self.products_map.get(product_name)
    if product and product.get("ingredient_id"):
        self._update_hierarchy_labels(product.get("ingredient_id"))
    else:
        self._clear_hierarchy_labels()

def _update_hierarchy_labels(self, ingredient_id: int):
    ingredient = ingredient_service.get_ingredient(ingredient_id)
    ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)

    # L2 is the ingredient itself
    l2_name = ingredient.get("display_name", "--") if ingredient else "--"

    # L1 and L0 from ancestors
    if len(ancestors) >= 2:
        l0_name = ancestors[1].get("display_name", "--")
        l1_name = ancestors[0].get("display_name", "--")
    elif len(ancestors) == 1:
        l0_name = ancestors[0].get("display_name", "--")
        l1_name = "--"
    else:
        l0_name = "--"
        l1_name = "--"

    self.l0_value.configure(text=l0_name)
    self.l1_value.configure(text=l1_name)
    self.l2_value.configure(text=l2_name)
```

**Files**: `src/ui/inventory_tab.py` or `src/ui/forms/inventory_form.py`

---

### Subtask T033 - Add Hierarchy Labels to Edit Dialog

**Purpose**: Show hierarchy information when editing inventory item.

**Steps**:
1. Find the edit inventory dialog
2. Add same three read-only labels as T032
3. Pre-populate labels based on item's product -> ingredient

**Notes**: May be same dialog as add (just with different init). If so, ensure labels populate correctly on edit mode.

**Files**: `src/ui/inventory_tab.py` or `src/ui/forms/inventory_form.py`

**Parallel?**: Yes, can proceed alongside T032 if separate dialogs.

---

### Subtask T034 - Populate Hierarchy from Product Relationship

**Purpose**: Get hierarchy data through product -> ingredient chain.

**Steps**:
1. When loading inventory item for edit, get product_id
2. Look up product to get ingredient_id
3. Use `get_ancestors()` and ingredient service to get hierarchy
4. Update labels with hierarchy names

**Implementation**:
```python
def _load_item_for_edit(self, inventory_item_id: int):
    item = inventory_service.get_inventory_item(inventory_item_id)
    product = product_service.get_product(item.product_id)

    if product and product.get("ingredient_id"):
        self._update_hierarchy_labels(product.get("ingredient_id"))

    # ... load other fields ...
```

**Files**: `src/ui/inventory_tab.py` or `src/ui/forms/inventory_form.py`

---

### Subtask T035 - Handle Incomplete Hierarchy

**Purpose**: Gracefully display dash for missing hierarchy levels.

**Steps**:
1. Handle null product
2. Handle null ingredient_id
3. Handle ingredients with incomplete hierarchy (L0 or L1 with no parents)
4. Display "--" for any missing level

**Notes**: Already handled in T032 implementation. This subtask is verification.

---

## Test Strategy

**Manual Testing**:
1. Open add inventory dialog, verify hierarchy labels show "--" initially
2. Select a product, verify hierarchy labels update correctly
3. Open edit inventory dialog for existing item, verify labels pre-populated
4. Test with product that has L2 ingredient - all three labels should show values
5. Test with product where ingredient has no L1 (if any) - L1 should show "--"
6. Verify labels are read-only (not editable)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Form layout space | Use compact label layout or collapsible section |
| Null chain (missing product/ingredient) | Handle each null case with "--" |
| Product without ingredient | Should not happen per schema, but handle gracefully |

---

## Definition of Done Checklist

- [ ] Add dialog shows hierarchy labels
- [ ] Edit dialog shows hierarchy labels
- [ ] Labels populate from product -> ingredient chain
- [ ] Missing levels display as "--"
- [ ] Labels are read-only
- [ ] Labels position near product selection

---

## Review Guidance

**Key Checkpoints**:
1. Labels update on product selection change
2. Edit mode pre-populates correctly
3. Null handling is robust
4. Labels clearly marked as informational

---

## Activity Log

- 2025-12-31T23:59:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
