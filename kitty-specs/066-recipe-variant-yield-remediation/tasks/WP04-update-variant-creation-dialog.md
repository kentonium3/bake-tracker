---
work_package_id: "WP04"
subtasks:
  - "T008"
  - "T009"
  - "T010"
title: "Update VariantCreationDialog"
phase: "Phase 3 - UI Polish"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-25T03:23:15Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Update VariantCreationDialog

## Objectives & Success Criteria

**Goal**: Update VariantCreationDialog with consistent "yield" terminology and base yield reference display.

**Success Criteria**:
- [ ] Header says "Variant Yields:" instead of "Yield Type Names:"
- [ ] Base recipe yields are displayed as read-only reference (items_per_batch, item_unit)
- [ ] Clear explanatory text about yield inheritance is present
- [ ] Existing variant creation functionality continues to work

**Implementation Command**:
```bash
spec-kitty implement WP04 --base WP01
```

## Context & Constraints

**Background**:
The VariantCreationDialog currently uses "Yield Type Names:" as its header, which is close but not quite aligned with the "yield" terminology standard. Additionally, it doesn't show the base recipe's yield values (items_per_batch, item_unit) as a reference, making it unclear what the variant will inherit.

**User Story (from spec.md)**:
> As a recipe manager, when I create a variant of an existing recipe, I can see the base recipe's yield structure as a reference so that I understand what yields the variant will inherit.

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md` (User Story 2)
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`

**File to Update**: `src/ui/forms/variant_creation_dialog.py`

## Subtasks & Detailed Guidance

### Subtask T008 – Update Header to "Variant Yields:"

**Purpose**: Use consistent "yield" terminology.

**Current Code** (line ~130):
```python
header_label = ctk.CTkLabel(
    fu_container,
    text="Yield Type Names:",
    font=ctk.CTkFont(weight="bold"),
)
```

**Updated Code**:
```python
header_label = ctk.CTkLabel(
    fu_container,
    text="Variant Yields:",
    font=ctk.CTkFont(weight="bold"),
)
```

**Files**: `src/ui/forms/variant_creation_dialog.py` (line ~130)

**Parallel**: Yes - simple text change

---

### Subtask T009 – Add Base Yield Reference Display Section

**Purpose**: Show base recipe yield values so users understand what the variant inherits.

**Location**: In `_create_finished_units_section()` method, BEFORE the editable fields

**Steps**:
1. Add a read-only reference section showing base recipe yields
2. Display items_per_batch and item_unit from base_finished_units
3. Use a visually distinct style (e.g., gray text, no editing controls)

**Implementation Approach**:

Add a new method and call it before the editable section:

```python
def _create_base_yield_reference(self, container):
    """Display base recipe yields as read-only reference."""
    if not self.base_finished_units:
        return

    # Reference header
    ref_header = ctk.CTkLabel(
        container,
        text="Base Recipe Yields (Reference):",
        font=ctk.CTkFont(weight="bold"),
        text_color="gray",
    )
    ref_header.grid(row=0, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(PADDING_MEDIUM, 5))

    # Show each base yield
    ref_frame = ctk.CTkFrame(container, fg_color=("gray90", "gray20"))
    ref_frame.grid(row=1, column=0, sticky="ew", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))

    for idx, fu in enumerate(self.base_finished_units):
        items = fu.get('items_per_batch', 'N/A')
        unit = fu.get('item_unit', 'unit')
        yield_text = f"{fu['display_name']}: {items} {unit}s per batch"

        yield_label = ctk.CTkLabel(
            ref_frame,
            text=yield_text,
            text_color="gray",
            anchor="w",
        )
        yield_label.pack(anchor="w", padx=PADDING_MEDIUM, pady=2)
```

**Modify `_create_finished_units_section()`**:
- Adjust row numbers to accommodate the reference section
- Call `_create_base_yield_reference()` first
- Move editable section down

**Files**: `src/ui/forms/variant_creation_dialog.py`

---

### Subtask T010 – Add Inheritance Explanatory Text

**Purpose**: Make it clear that variants inherit yield structure from the base recipe.

**Location**: Below the base yield reference section, above the editable fields

**Steps**:
1. Add explanatory text explaining inheritance
2. Use subtle styling (gray, smaller font)

**Code to Add** (in `_create_finished_units_section()`):
```python
# Inheritance explanation
explanation = ctk.CTkLabel(
    container,
    text="Variant inherits yield structure from base recipe.\nYou can customize the display names below.",
    text_color="gray",
    font=ctk.CTkFont(size=11),
    justify="left",
)
explanation.grid(row=2, column=0, sticky="w", padx=PADDING_MEDIUM, pady=(0, PADDING_MEDIUM))
```

**Files**: `src/ui/forms/variant_creation_dialog.py`

## Test Strategy

**Manual Testing Required**:
1. Open variant creation dialog for a recipe with FinishedUnits
2. Verify "Variant Yields:" header is displayed
3. Verify base recipe yields are shown as reference
4. Verify explanatory text is present
5. Verify variant can still be created successfully
6. Test with recipe that has multiple FinishedUnits
7. Test with recipe that has no FinishedUnits (edge case)

**No Automated UI Tests** - This is UI polish work.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout disruption | Test with various window sizes |
| Missing data display | Handle None/empty values gracefully |
| Grid row numbering | Carefully adjust row indices |

## Definition of Done Checklist

- [ ] T008: Header updated to "Variant Yields:"
- [ ] T009: Base yield reference section added and displays correctly
- [ ] T010: Inheritance explanatory text added
- [ ] Dialog layout is clean and readable
- [ ] Variant creation still works correctly
- [ ] Tested with multiple FinishedUnits
- [ ] Tested with no FinishedUnits
- [ ] Changes committed with clear message

## Review Guidance

- Verify terminology is consistent ("yield" not "finished unit")
- Verify base yield reference shows items_per_batch and item_unit
- Verify explanatory text is clear and helpful
- Verify layout looks professional
- Test the full variant creation flow

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
