---
work_package_id: WP03
title: Create Variant Dialog Polish
lane: "doing"
dependencies: []
base_branch: main
base_commit: 560e62fea4b7ea44de2dd05d0c9a31b2eddd2567
created_at: '2026-01-25T18:19:30.240343+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 1 - UI Polish
assignee: ''
agent: ''
shell_pid: "49512"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-25T18:09:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Create Variant Dialog Polish

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Clean up the Create Variant dialog layout and terminology for improved clarity.

**Success Criteria**:
- [ ] Section header reads "Finished Unit Name(s):" instead of "Variant Yields:"
- [ ] No "Base:" labels appear before finished unit input fields
- [ ] All input fields are left-justified
- [ ] Variant name section has label above field with help text between
- [ ] Existing variant creation functionality unchanged

## Context & Constraints

**Feature**: F067 - Recipe UI Polish - Yield Information and Variant Grouping
**User Story**: US3 - Create Variant Dialog Polish (Priority: P2)
**Spec Reference**: `kitty-specs/067-recipe-ui-polish-yield-variants/spec.md` (FR-007, FR-008, FR-009, FR-010)

**Key Constraints**:
- UI-layer only - no service or model changes
- Follow CustomTkinter best practices for label-above-field pattern
- Preserve existing variant creation logic

**Related Files**:
- `src/ui/forms/variant_creation_dialog.py` - Main file to modify
- `kitty-specs/067-recipe-ui-polish-yield-variants/research.md` - Dialog investigation

**Research Findings** (from research.md):
- Line 143: "Variant Yields:" section header
- Line 213: "Base: {display_name}" label format
- Current layout: 2-column grid with label | entry

## Subtasks & Detailed Guidance

### Subtask T006 – Change Section Header from "Variant Yields:" to "Finished Unit Name(s):"

**Purpose**: "Variant Yields" is confusing terminology. "Finished Unit Name(s)" accurately describes what the user is editing - the display names for the variant's finished units.

**Current State**:
- Line 143 in `_create_finished_units_section()`:
  ```python
  text="Variant Yields:",
  ```

**Steps**:

1. **Locate the section header** in `_create_finished_units_section()` around line 143

2. **Change the text**:
   ```python
   # Before:
   section_label = ctk.CTkLabel(
       ...,
       text="Variant Yields:",
       ...
   )

   # After:
   section_label = ctk.CTkLabel(
       ...,
       text="Finished Unit Name(s):",
       ...
   )
   ```

3. **Verify the label styling** remains consistent (same font, weight, etc.)

**Files**:
- `src/ui/forms/variant_creation_dialog.py` (line ~143)

**Validation**:
- [ ] Section header displays "Finished Unit Name(s):"
- [ ] No occurrences of "Variant Yields" in the dialog

---

### Subtask T007 – Remove "Base:" Label Prefix from FU Rows

**Purpose**: The "Base:" prefix is redundant clutter. Users already understand they're naming variant versions of the base recipe's finished units from the context.

**Current State**:
- Line 213 in `_create_fu_row()`:
  ```python
  text=f"Base: {base_fu['display_name']}",
  ```

**Steps**:

1. **Locate `_create_fu_row()`** method (around line 202-238)

2. **Remove the "Base: " prefix**:
   ```python
   # Before:
   base_label = ctk.CTkLabel(
       self.fu_frame,
       text=f"Base: {base_fu['display_name']}",
       anchor="w",
       width=180,
   )

   # After:
   base_label = ctk.CTkLabel(
       self.fu_frame,
       text=base_fu['display_name'],
       anchor="w",
       width=180,
   )
   ```

3. **Alternatively, consider removing the label entirely** if the entry placeholder is sufficient. Check if users need to see the base name as reference. If keeping:
   - Make it a subtle reference, perhaps in gray text
   - Or use it as a label for the row without "Base:" prefix

4. **Decide on label approach**:
   - Option A: Keep label but remove "Base:" prefix (show just the FU name)
   - Option B: Remove label entirely, rely on placeholder/context

   Spec says "no 'Base:' labels" - this means remove the prefix, not necessarily the entire reference.

**Files**:
- `src/ui/forms/variant_creation_dialog.py` (line ~213)

**Validation**:
- [ ] No "Base:" text appears in the FU section
- [ ] Users can still identify which base FU they're naming variants for

---

### Subtask T008 – Left-Justify Input Fields

**Purpose**: The spec requires input fields to be left-justified for visual consistency.

**Current State**:
- Entry widgets may have centering or inconsistent alignment

**Steps**:

1. **Review current grid configuration** in `_create_fu_row()`:
   ```python
   # Check the entry placement
   entry = ctk.CTkEntry(
       self.fu_frame,
       placeholder_text="Enter variant name...",
   )
   entry.grid(row=idx, column=1, sticky="ew", padx=(5, 0), pady=2)
   ```

2. **Ensure left justification**:
   - `sticky="w"` or `sticky="ew"` (stretches but text aligns left)
   - For the entry content itself, CTkEntry default is left-aligned
   - Check if any explicit `justify` parameter is set

3. **Verify alignment across all FU rows** - multiple rows should line up

4. **Check the variant name entry** in `_create_variant_name_section()` as well:
   - Should also be left-justified

**Files**:
- `src/ui/forms/variant_creation_dialog.py` (FU entries and variant name entry)

**Validation**:
- [ ] All input fields are left-justified
- [ ] Fields align vertically when multiple rows exist

---

### Subtask T009 – Restructure Variant Name Section Layout

**Purpose**: The spec requires the variant name section to have: label above field (left-justified), help text between label and input field.

**Current State** (likely):
- Label and entry may be on the same row (inline)
- Help text position may vary

**Target Layout**:
```
Recipe Variant Name              <-- Label (left-justified, above)
Descriptive help text here       <-- Help text (gray, between label and input)
[____________________]           <-- Entry field (below help text)
```

**Steps**:

1. **Locate `_create_variant_name_section()`** in the dialog class

2. **Restructure the layout** to stack vertically:
   ```python
   def _create_variant_name_section(self, parent, row):
       """Create variant name input with label above and help text between."""
       # Row N: Label
       name_label = ctk.CTkLabel(
           parent,
           text="Recipe Variant Name",
           font=ctk.CTkFont(size=12, weight="bold"),
           anchor="w",
       )
       name_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM)
       row += 1

       # Row N+1: Help text
       help_text = ctk.CTkLabel(
           parent,
           text="Enter a name for this variant (e.g., 'Large', 'Mini', 'Holiday Edition')",
           text_color="gray",
           font=ctk.CTkFont(size=11),
           anchor="w",
       )
       help_text.grid(row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM)
       row += 1

       # Row N+2: Entry field
       self.variant_name_entry = ctk.CTkEntry(
           parent,
           placeholder_text="Variant name...",
           width=300,
       )
       self.variant_name_entry.grid(row=row, column=0, columnspan=2, sticky="w", padx=PADDING_MEDIUM, pady=(2, PADDING_MEDIUM))
       row += 1

       return row
   ```

3. **Verify the help text** is appropriate - it should explain what the variant name is for

4. **Update subsequent row indices** if the restructure changes the total row count

**Files**:
- `src/ui/forms/variant_creation_dialog.py` (modify `_create_variant_name_section()`)

**Validation**:
- [ ] Label "Recipe Variant Name" is above the entry field
- [ ] Help text appears between label and entry
- [ ] Entry field is below help text
- [ ] All elements are left-justified

---

## Test Strategy

**Manual Testing Required**:

1. **Open Create Variant dialog** from a base recipe:
   - Verify section header says "Finished Unit Name(s):"
   - Verify no "Base:" labels appear
   - Verify all input fields are left-aligned
   - Verify variant name section has label above, help text, then input

2. **Test with multiple finished units**:
   - If base recipe has 2-3 FUs, verify all rows display correctly
   - Verify alignment is consistent across rows

3. **Create a variant** successfully:
   - Enter variant name
   - Enter FU display names
   - Click Create
   - Verify variant is created correctly

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Layout restructure breaks dialog sizing | Test with various window sizes |
| Removing labels causes confusion | Keep subtle reference to base FU names |
| Row index miscalculation | Carefully track row increments |

## Definition of Done Checklist

- [ ] T006: Section header changed to "Finished Unit Name(s):"
- [ ] T007: "Base:" prefix removed from FU rows
- [ ] T008: All input fields left-justified
- [ ] T009: Variant name section restructured (label above, help between)
- [ ] Manual testing completed
- [ ] Variant creation still works correctly

## Review Guidance

**Reviewers should verify**:
1. Open Create Variant dialog and inspect all labels/layout
2. Verify no "Variant Yields" or "Base:" text appears
3. Verify input field alignment
4. Test creating a variant to ensure functionality preserved

## Activity Log

- 2026-01-25T18:09:19Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

## Implementation Command

**No dependencies** - start from main:

```bash
spec-kitty implement WP03 --feature 067-recipe-ui-polish-yield-variants
```

After implementation:
```bash
spec-kitty agent tasks move-task WP03 --to for_review --note "Ready for review: dialog terminology and layout polish"
```
