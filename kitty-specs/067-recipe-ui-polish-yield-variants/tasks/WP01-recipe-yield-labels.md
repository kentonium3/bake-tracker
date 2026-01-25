---
work_package_id: WP01
title: Edit Recipe Yield Section Polish
lane: "done"
dependencies: []
base_branch: main
base_commit: fb81dfdc215cc23237d5441a4b7c843294ee85d8
created_at: '2026-01-25T18:16:27.307870+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - UI Polish
assignee: ''
agent: "claude-opus"
shell_pid: "51754"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-01-25T18:09:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Edit Recipe Yield Section Polish

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Improve clarity of the Edit Recipe dialog's Yield Information section by adding column labels and updating help text.

**Success Criteria**:
- [ ] Column labels "Finished Unit Name", "Unit", "Qty/Batch" are visible above yield input fields
- [ ] Help text reads "Each row defines a Finished Unit and quantity per batch for this recipe."
- [ ] Vertical spacing in yield section matches other dialog sections (no excessive whitespace)
- [ ] Existing yield editing functionality unchanged
- [ ] Variant recipes still show readonly fields with inheritance note

## Context & Constraints

**Feature**: F067 - Recipe UI Polish - Yield Information and Variant Grouping
**User Story**: US1 - Edit Recipe Dialog Clarity (Priority: P1)
**Spec Reference**: `kitty-specs/067-recipe-ui-polish-yield-variants/spec.md` (FR-001, FR-002, FR-003)

**Key Constraints**:
- UI-layer only - no service or model changes
- Follow existing CustomTkinter patterns in the codebase
- Preserve F066 variant handling (readonly structure fields, inheritance note)

**Related Files**:
- `src/ui/forms/recipe_form.py` - Main file to modify
- `.kittify/memory/constitution.md` - Architecture principles
- `kitty-specs/067-recipe-ui-polish-yield-variants/plan.md` - Implementation plan

## Subtasks & Detailed Guidance

### Subtask T001 – Add Column Labels Above Yield Inputs

**Purpose**: Users currently cannot tell what each yield input field represents without hovering or guessing. Adding column labels makes the purpose of each field immediately clear.

**Current State** (from research.md):
- Yield section at lines 730-798 in `recipe_form.py`
- `YieldTypeRow` widget has 4 columns: Name (200px) | Unit (100px) | Qty (80px) | Remove button
- No labels above the columns currently

**Steps**:

1. **Locate the yield section** in `_create_yield_section()` method (starts around line 730)

2. **Add a labels row** before `self.yield_types_frame` is created. Insert a new CTkFrame with three labels:

   ```python
   # Column labels for yield inputs
   labels_frame = ctk.CTkFrame(parent, fg_color="transparent")
   labels_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=PADDING_MEDIUM)
   row += 1

   # Configure columns to match YieldTypeRow proportions
   labels_frame.columnconfigure(0, weight=3)  # Name column (wider)
   labels_frame.columnconfigure(1, weight=1)  # Unit column
   labels_frame.columnconfigure(2, weight=1)  # Qty column
   labels_frame.columnconfigure(3, weight=0)  # Spacer for remove button area

   name_label = ctk.CTkLabel(labels_frame, text="Finished Unit Name", font=ctk.CTkFont(size=11))
   name_label.grid(row=0, column=0, sticky="w", padx=(0, 5))

   unit_label = ctk.CTkLabel(labels_frame, text="Unit", font=ctk.CTkFont(size=11))
   unit_label.grid(row=0, column=1, sticky="w", padx=(0, 5))

   qty_label = ctk.CTkLabel(labels_frame, text="Qty/Batch", font=ctk.CTkFont(size=11))
   qty_label.grid(row=0, column=2, sticky="w", padx=(0, 5))
   ```

3. **Verify alignment** with actual `YieldTypeRow` columns. The `YieldTypeRow` class (line 391-499) uses:
   - `self.name_entry` with `width=200`
   - `self.unit_entry` with `width=100`
   - `self.quantity_entry` with `width=80`
   - `self.remove_button` (hidden for variants)

4. **Test with multiple rows** to ensure labels stay aligned as rows are added/removed.

**Files**:
- `src/ui/forms/recipe_form.py` (modify `_create_yield_section()`)

**Validation**:
- [ ] Labels visible above yield input columns
- [ ] Labels align with input fields below
- [ ] Labels remain aligned with 1, 2, and 3+ yield rows

---

### Subtask T002 – Update Help Text to Spec Wording

**Purpose**: The current help text uses inconsistent terminology. The spec requires consistent "Finished Unit" terminology.

**Current State**:
- Line 748-761: Help text says "Yield Types* - Each row defines a finished product from this recipe (Description, Unit, Qty/batch):"

**Steps**:

1. **Locate the help text** in `_create_yield_section()` around line 748

2. **Update the text** to match spec requirement:
   ```python
   yield_types_info = ctk.CTkLabel(
       parent,
       text="Each row defines a Finished Unit and quantity per batch for this recipe.",
       text_color="gray",
       font=ctk.CTkFont(size=11),
   )
   ```

3. **Remove the "Yield Types*" prefix** - the section header "Yield Information" already establishes context

4. **Keep the label styling** consistent with other help text in the form

**Files**:
- `src/ui/forms/recipe_form.py` (modify help text label)

**Validation**:
- [ ] Help text matches exact wording from spec
- [ ] No "Yield Types*" prefix
- [ ] Text color and font match other help text in dialog

---

### Subtask T003 – Reduce Vertical Spacing After Section Title

**Purpose**: The spec requires spacing in the Yield Information section to match other sections (Basic Information, Recipe Ingredients).

**Current State**:
- May have excessive padding/margin after "Yield Information" header

**Steps**:

1. **Compare spacing** with other sections in the dialog:
   - Look at "Basic Information" section spacing
   - Look at "Recipe Ingredients" section spacing

2. **Locate the yield section header** (around line 731-743):
   ```python
   yield_label = ctk.CTkLabel(
       parent,
       text="Yield Information",
       font=ctk.CTkFont(size=14, weight="bold"),
   )
   yield_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(PADDING_LARGE, PADDING_SMALL))
   ```

3. **Adjust the `pady` values** to match other section headers. Typical pattern is:
   - `pady=(PADDING_LARGE, PADDING_SMALL)` for section headers
   - `pady=PADDING_SMALL` for content below

4. **Check the gap** between the help text and the column labels (if labels are above the yield frame, ensure no double-padding)

**Files**:
- `src/ui/forms/recipe_form.py` (adjust padding values)

**Validation**:
- [ ] Vertical spacing matches "Basic Information" section
- [ ] No excessive whitespace after section title
- [ ] Help text, column labels, and yield rows flow naturally

---

## Test Strategy

**Manual Testing Required**:

1. **Open Edit Recipe dialog** for an existing base recipe:
   - Verify column labels are visible and aligned
   - Verify help text is updated
   - Verify spacing is consistent

2. **Open Edit Recipe dialog** for an existing variant recipe:
   - Verify column labels still appear
   - Verify variant inheritance note still shows
   - Verify readonly fields still function correctly

3. **Create a new recipe** and add multiple yield types:
   - Verify labels stay aligned as rows are added
   - Verify remove button area doesn't shift labels

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Column labels misaligned with inputs | Use same width/weight values as YieldTypeRow |
| Variant mode broken | Test variant editing after changes |
| Grid layout conflicts | Use consistent row numbering with `row += 1` pattern |

## Definition of Done Checklist

- [ ] T001: Column labels added and aligned
- [ ] T002: Help text updated to spec wording
- [ ] T003: Spacing matches other sections
- [ ] Manual testing completed for base and variant recipes
- [ ] No regressions in yield editing functionality

## Review Guidance

**Reviewers should verify**:
1. Open Edit Recipe dialog and visually inspect column labels
2. Confirm help text exact wording matches spec
3. Compare spacing with other dialog sections
4. Test both base recipe and variant recipe editing

## Activity Log

- 2026-01-25T18:09:19Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---
- 2026-01-25T18:18:06Z – claude-opus – shell_pid=47605 – lane=for_review – Implemented column labels, updated help text, adjusted spacing
- 2026-01-25T18:27:33Z – claude-opus – shell_pid=51754 – lane=doing – Started review via workflow command
- 2026-01-25T18:28:06Z – claude-opus – shell_pid=51754 – lane=done – Review passed: T001 column labels correctly implemented, T002 help text matches spec, T003 spacing appropriate
- 2026-01-25T18:36:03Z – claude-opus – shell_pid=51754 – lane=done – lane=done – Review passed: T001 column labels correctly implemented, T002 help text matches spec, T003 spacing appropriate

## Implementation Command

**No dependencies** - start from main:

```bash
spec-kitty implement WP01 --feature 067-recipe-ui-polish-yield-variants
```

After implementation:
```bash
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review: column labels, help text, spacing"
```
