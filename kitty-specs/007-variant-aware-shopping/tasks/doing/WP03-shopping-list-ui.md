---
work_package_id: "WP03"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Shopping List UI Enhancement"
phase: "Phase 3 - UI Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "36821"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Shopping List UI Enhancement

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend the shopping list table UI to display variant recommendations with cost information, handle multiple variant scenarios, and show total estimated cost.

**Success Criteria**:
- New columns visible: Variant, Package Size, Cost/Unit, Est. Cost
- Preferred variants show "[preferred]" indicator (FR-001)
- Multiple variants display as vertically stacked rows (FR-002)
- "No variant configured" displays for missing variants (FR-003)
- Total estimated cost shown at bottom (FR-007)
- Shopping list tab loads in <2 seconds (SC-005)

## Context & Constraints

**Prerequisites**: WP02 must be complete (shopping list returns variant data).

**Key Files**:
- Modify: `src/ui/event_planning_tab.py`
- Reference: `src/services/event_service.py` (WP02 output)

**Architecture Constraints**:
- UI layer must NOT contain business logic (Constitution Principle I)
- UI only displays data from service layer
- Use CustomTkinter components consistently with existing UI

**Related Documents**:
- [spec.md](../spec.md) - FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, SC-005
- [data-model.md](../data-model.md) - UI Display Mapping table

## Subtasks & Detailed Guidance

### Subtask T008 - Add variant columns to shopping list table

**Purpose**: Extend the existing table with new columns for variant information.

**Steps**:
1. Locate the shopping list table in `event_planning_tab.py`.
   - Look for CTkTable or Treeview widget displaying shopping list data.

2. Add new columns to the table definition:
```python
columns = [
    # Existing columns
    ("Ingredient", 150),
    ("Needed", 80),
    ("On Hand", 80),
    ("To Buy", 80),
    # NEW columns
    ("Variant", 150),        # Brand name or "[preferred]" indicator
    ("Package Size", 120),   # e.g., "25 lb = 90 cups"
    ("Cost/Unit", 80),       # e.g., "$0.18/cup"
    ("Est. Cost", 80),       # e.g., "$18.00"
]
```

3. Update column configuration:
```python
# If using ttk.Treeview:
self.shopping_tree["columns"] = ("ingredient", "needed", "on_hand", "to_buy",
                                  "variant", "package_size", "cost_unit", "est_cost")

for col, width in columns:
    self.shopping_tree.column(col.lower().replace(" ", "_"), width=width, anchor="w")
    self.shopping_tree.heading(col.lower().replace(" ", "_"), text=col)
```

4. Update the data population method:
```python
def populate_shopping_list(self, shopping_data):
    # Clear existing rows
    for item in self.shopping_tree.get_children():
        self.shopping_tree.delete(item)

    for item in shopping_data['items']:
        # Format existing columns
        ingredient = item['ingredient_name']
        needed = f"{item['quantity_needed']:.2f} {item['unit']}"
        on_hand = f"{item['quantity_on_hand']:.2f} {item['unit']}"
        to_buy = f"{item['shortfall']:.2f} {item['unit']}"

        # Format new columns based on variant_status
        variant, package_size, cost_unit, est_cost = self._format_variant_columns(item)

        self.shopping_tree.insert("", "end", values=(
            ingredient, needed, on_hand, to_buy,
            variant, package_size, cost_unit, est_cost
        ))
```

**Files**: `src/ui/event_planning_tab.py`

**Notes**:
- Match existing column styling for consistency
- Consider column width tuning for readability

---

### Subtask T009 - Handle vertically stacked rows for multiple variants

**Purpose**: When `variant_status='multiple'`, display each variant on its own row under the ingredient.

**Steps**:
1. Create helper method to format variant rows:
```python
def _format_variant_columns(self, item):
    """Format variant columns for a single item."""
    status = item.get('variant_status', 'none')

    if status == 'sufficient':
        return ("Sufficient stock", "", "", "")

    if status == 'none':
        return ("No variant configured", "", "", "")

    if status == 'preferred':
        rec = item['variant_recommendation']
        return self._format_single_variant(rec, show_preferred=True)

    # For 'multiple', return None - handled separately
    return None
```

2. Modify populate method to handle multiple variants:
```python
def populate_shopping_list(self, shopping_data):
    for item in shopping_data['items']:
        status = item.get('variant_status', 'none')

        if status == 'multiple':
            # Insert ingredient row (main row)
            ingredient = item['ingredient_name']
            needed = f"{item['quantity_needed']:.2f} {item['unit']}"
            on_hand = f"{item['quantity_on_hand']:.2f} {item['unit']}"
            to_buy = f"{item['shortfall']:.2f} {item['unit']}"

            # First variant row with ingredient info
            first_variant = item['all_variants'][0] if item['all_variants'] else None
            if first_variant:
                v_cols = self._format_single_variant(first_variant, show_preferred=False)
                self.shopping_tree.insert("", "end", values=(
                    ingredient, needed, on_hand, to_buy, *v_cols
                ))

            # Additional variant rows (ingredient columns blank)
            for variant in item['all_variants'][1:]:
                v_cols = self._format_single_variant(variant, show_preferred=False)
                self.shopping_tree.insert("", "end", values=(
                    "", "", "", "", *v_cols  # Blank ingredient columns
                ))
        else:
            # Single row (preferred, none, sufficient)
            # ... existing logic from T008
```

3. Helper for single variant formatting:
```python
def _format_single_variant(self, rec, show_preferred=False):
    """Format columns for a single variant recommendation."""
    if not rec:
        return ("", "", "", "")

    # Brand with [preferred] indicator
    brand = rec.get('brand', '')
    if show_preferred and rec.get('is_preferred'):
        brand = f"{brand} [preferred]"

    # Package size context: "25 lb bag"
    # Could also show: "25 lb = 90 cups" if conversion available
    package_size = rec.get('package_size', '')

    # Cost per recipe unit: "$0.18/cup"
    cost_per_unit = rec.get('cost_per_recipe_unit')
    if cost_per_unit and rec.get('cost_available', True):
        cost_unit = f"${cost_per_unit:.2f}/{rec.get('recipe_unit', 'unit')}"
    else:
        cost_unit = "Cost unknown"

    # Estimated total cost
    total_cost = rec.get('total_cost')
    if total_cost and rec.get('cost_available', True):
        est_cost = f"${total_cost:.2f}"
    else:
        est_cost = "-"

    return (brand, package_size, cost_unit, est_cost)
```

**Files**: `src/ui/event_planning_tab.py`

**Notes**:
- Vertically stacked rows should visually group under the ingredient
- Consider indentation or different background for sub-rows
- Per clarification: one variant per line, no accordion/expand needed

---

### Subtask T010 - Display "[preferred]" indicator

**Purpose**: Clearly mark the recommended variant as preferred.

**Steps**:
1. In `_format_single_variant()`, add "[preferred]" to brand name:
```python
if show_preferred and rec.get('is_preferred'):
    brand = f"{brand} [preferred]"
```

2. Alternative: Use a separate column or icon
   - Could add a checkmark icon in a dedicated column
   - Or use bold/color styling for preferred row

3. Ensure the indicator is visible and doesn't truncate:
   - If brand name is long, consider abbreviation
   - Or show indicator in a tooltip

**Files**: `src/ui/event_planning_tab.py`

**Notes**:
- Keep indicator simple and unobtrusive
- "[preferred]" text matches spec requirement exactly

---

### Subtask T011 - Display "No variant configured" fallback

**Purpose**: Show clear message when ingredient has no variants.

**Steps**:
1. Already implemented in `_format_variant_columns()`:
```python
if status == 'none':
    return ("No variant configured", "", "", "")
```

2. The text should span or be prominent in the Variant column:
   - Other columns (Package Size, Cost/Unit, Est. Cost) show empty or "-"

3. Consider styling:
   - Could use italic or gray text to indicate missing data
   - Should not look like an error (it's informational)

**Files**: `src/ui/event_planning_tab.py`

---

### Subtask T012 - Display total estimated cost at bottom

**Purpose**: Show summary of total shopping expense.

**Steps**:
1. Add a summary section below the table:
```python
def populate_shopping_list(self, shopping_data):
    # ... populate table rows ...

    # Update total cost label
    total = shopping_data.get('total_estimated_cost', Decimal('0.00'))
    self.total_cost_label.configure(text=f"Total Estimated Cost: ${total:.2f}")
```

2. Create the label widget (if not exists):
```python
# In __init__ or setup method
self.total_cost_label = ctk.CTkLabel(
    self.shopping_frame,
    text="Total Estimated Cost: $0.00",
    font=ctk.CTkFont(size=14, weight="bold")
)
self.total_cost_label.pack(side="bottom", pady=10)
```

3. Position appropriately:
   - Below the table
   - Right-aligned to match Est. Cost column
   - Prominent but not overwhelming

4. Handle edge cases:
   - If no items with recommendations, show "$0.00"
   - If some items have "multiple" status (not in total), consider a note

**Files**: `src/ui/event_planning_tab.py`

**Notes**:
- Total only includes 'preferred' items (per data-model.md)
- Consider adding a note: "* Excludes items without a preferred variant selected"

---

## Test Strategy

**Manual Verification** (no automated UI tests required):

1. **Preferred variant display**:
   - Open event with ingredient that has preferred variant
   - Verify: Brand shows with "[preferred]", all columns populated

2. **Multiple variants display**:
   - Open event with ingredient that has multiple variants (none preferred)
   - Verify: Multiple rows appear, first row has ingredient info, subsequent rows have blank ingredient columns

3. **No variant display**:
   - Open event with ingredient that has no variants
   - Verify: "No variant configured" shows in Variant column

4. **Total cost display**:
   - Open event with mixed ingredients
   - Verify: Total shows at bottom, matches sum of preferred items only

5. **Performance (SC-005)**:
   - Load shopping list with 20+ ingredients
   - Verify: Tab loads in <2 seconds

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Table too wide | Use abbreviations, tooltips, or horizontal scroll |
| Multiple variant rows confusing | Clear visual grouping (indent, background) |
| Performance degradation | Lazy loading if needed; profile if >2s |
| Column width inconsistency | Test with various data lengths |

---

## Definition of Done Checklist

- [ ] New columns visible and properly sized
- [ ] Preferred variants show "[preferred]" indicator
- [ ] Multiple variants display as stacked rows
- [ ] "No variant configured" displays correctly
- [ ] Total estimated cost shown at bottom
- [ ] Table loads in <2 seconds (SC-005)
- [ ] Manual verification of all scenarios passes
- [ ] Code passes black formatting
- [ ] Code passes flake8 linting

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Visual inspection of all variant_status cases
2. Verify multiple variant rows don't duplicate ingredient info
3. Verify total excludes 'multiple' status items
4. Test with long brand names and verify no truncation issues
5. Verify performance requirement (SC-005)

---

## Activity Log

- 2025-12-04 - system - lane=planned - Prompt created via /spec-kitty.tasks.
- 2025-12-04T06:59:13Z – claude – shell_pid=36821 – lane=doing – Started implementation of Shopping List UI Enhancement
