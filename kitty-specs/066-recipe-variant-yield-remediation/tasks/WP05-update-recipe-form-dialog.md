---
work_package_id: WP05
title: Update RecipeFormDialog
lane: "doing"
dependencies: [WP01]
base_branch: 066-recipe-variant-yield-remediation-WP01
base_commit: 0f8146edc950f76b75603199edc4f1f08a1fe498
created_at: '2026-01-25T04:09:05.231512+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - UI Polish
assignee: ''
agent: "claude-opus"
shell_pid: "30283"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-25T03:23:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Update RecipeFormDialog

## Objectives & Success Criteria

**Goal**: Add variant detection and variant-specific behavior to RecipeFormDialog so users understand what can and cannot be edited for variants.

**Success Criteria**:
- [ ] Variants show "Base Recipe: [name]" banner at top
- [ ] Yield structure fields (items_per_batch, item_unit, yield_mode) are read-only for variants
- [ ] display_name field remains editable for variants
- [ ] Explanatory text about inheritance is displayed for variants
- [ ] Base recipes continue to have fully editable yield fields

**Implementation Command**:
```bash
# Step 1: Create worktree based on WP01 branch
spec-kitty implement WP05 --base WP01

# Step 2: Change to worktree directory
cd .worktrees/066-recipe-variant-yield-remediation-WP05
```

**Note**: The `--base WP01` flag creates the worktree from WP01's branch, not from main. This is required because WP01 changes are not yet merged to main.

## Context & Constraints

**Background**:
RecipeFormDialog currently has no variant detection. All recipes are treated identically, meaning variant recipes can appear to have editable yield fields (even though changes would be confusing or inconsistent with the inheritance model).

**User Story (from spec.md)**:
> As a recipe manager, when I edit a variant recipe, I can see that yield structure is inherited from the base recipe (read-only) but I can customize the display name.

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md` (User Story 3)
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`

**File to Update**: `src/ui/forms/recipe_form.py`

## Subtasks & Detailed Guidance

### Subtask T011 – Add Variant Detection in `__init__`

**Purpose**: Detect whether the recipe being edited is a variant and set up instance variables for conditional UI.

**Location**: `RecipeFormDialog.__init__()` method (around lines 500-530)

**Steps**:
1. After `self.recipe = recipe`, add variant detection
2. Store `is_variant` flag and optionally fetch base recipe name

**Code to Add** (after `self.recipe = recipe`):
```python
# Variant detection for conditional UI (F066)
self.is_variant = False
self.base_recipe_name = None
if self.recipe and self.recipe.base_recipe_id:
    self.is_variant = True
    # Fetch base recipe name for display
    try:
        with session_scope() as session:
            base_recipe = session.get(Recipe, self.recipe.base_recipe_id)
            if base_recipe:
                self.base_recipe_name = base_recipe.name
    except Exception:
        self.base_recipe_name = f"Recipe #{self.recipe.base_recipe_id}"
```

**Files**: `src/ui/forms/recipe_form.py` (in `__init__`)

**Notes**: May need to add import for `session_scope` if not present.

---

### Subtask T012 – Add Base Recipe Banner for Variants

**Purpose**: Display "Base Recipe: [name]" at the top of the form for variants.

**Location**: In `_create_form_fields()` method, at the very beginning (before "Basic Information" section)

**Steps**:
1. Check `self.is_variant`
2. If variant, add a banner frame at the top

**Code to Add** (at start of `_create_form_fields()`, before row 0):
```python
def _create_form_fields(self, parent):
    """Create all form input fields."""
    row = 0

    # F066: Variant banner if editing a variant recipe
    if self.is_variant:
        variant_banner = ctk.CTkFrame(parent, fg_color=("lightblue", "darkblue"))
        variant_banner.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=PADDING_MEDIUM,
            pady=(0, PADDING_MEDIUM),
        )

        banner_text = f"Base Recipe: {self.base_recipe_name or 'Unknown'}"
        banner_label = ctk.CTkLabel(
            variant_banner,
            text=banner_text,
            font=ctk.CTkFont(weight="bold"),
        )
        banner_label.pack(padx=PADDING_MEDIUM, pady=5)

        row += 1

    # Basic Information section (existing code continues...)
```

**Files**: `src/ui/forms/recipe_form.py` (in `_create_form_fields()`)

---

### Subtask T013 – Make Yield Structure Fields Read-Only for Variants

**Purpose**: Prevent editing of items_per_batch, item_unit, and yield_mode for variant recipes.

**Location**: In the yield type row creation logic (likely in `YieldTypeRow` class or similar)

**Steps**:
1. Find where yield type fields are created (items_per_batch entry, item_unit entry, yield_mode combo)
2. Pass `is_variant` flag or check it directly
3. Set fields to disabled/read-only state for variants

**Approach**: Look for where `YieldTypeRow` is instantiated or where yield fields are created. Add conditional disable.

**Code Pattern**:
```python
# When creating yield fields, check is_variant
if self.is_variant:
    # Make structural fields read-only
    items_per_batch_entry.configure(state="disabled")
    item_unit_entry.configure(state="disabled")
    yield_mode_combo.configure(state="disabled")
```

**Alternative**: If `YieldTypeRow` is a separate class, add a `readonly` parameter:
```python
yield_row = YieldTypeRow(
    parent,
    ...,
    readonly=self.is_variant,  # New parameter
)
```

**Files**: `src/ui/forms/recipe_form.py` (yield type creation)

---

### Subtask T014 – Keep display_name Field Editable for Variants

**Purpose**: Allow users to customize the display name of variant yields even though structure is inherited.

**Location**: Same area as T013 (yield field creation)

**Steps**:
1. Ensure display_name field is NOT disabled for variants
2. Only structural fields (items_per_batch, item_unit, yield_mode) should be read-only

**Code Pattern**:
```python
# Display name remains editable even for variants
display_name_entry.configure(state="normal")  # Always editable

# Structural fields are read-only for variants
if self.is_variant:
    items_per_batch_entry.configure(state="disabled")
    item_unit_entry.configure(state="disabled")
    yield_mode_combo.configure(state="disabled")
```

**Files**: `src/ui/forms/recipe_form.py`

---

### Subtask T015 – Add Explanatory Text About Inheritance

**Purpose**: Explain to users that yield structure is inherited from the base recipe.

**Location**: In the Yield Information section, after the banner or section header

**Steps**:
1. Add conditional explanatory text for variants
2. Use subtle styling (gray, smaller font)

**Code to Add** (in the yield section, after the section header):
```python
if self.is_variant:
    inheritance_note = ctk.CTkLabel(
        parent,
        text="Yield structure inherited from base recipe. Only display names can be edited.",
        text_color="gray",
        font=ctk.CTkFont(size=11),
    )
    inheritance_note.grid(
        row=row,
        column=0,
        columnspan=2,
        sticky="w",
        padx=PADDING_MEDIUM,
        pady=(0, 5),
    )
    row += 1
```

**Files**: `src/ui/forms/recipe_form.py` (in yield section)

## Test Strategy

**Manual Testing Required**:

**Test Case 1: Edit Base Recipe**
1. Open RecipeFormDialog for a base recipe (one without base_recipe_id)
2. Verify NO variant banner is shown
3. Verify all yield fields are fully editable
4. Save changes successfully

**Test Case 2: Edit Variant Recipe**
1. Create a variant of a base recipe first
2. Open RecipeFormDialog for the variant
3. Verify "Base Recipe: [name]" banner is shown
4. Verify inheritance explanatory text is shown
5. Verify items_per_batch, item_unit, yield_mode are disabled/read-only
6. Verify display_name IS editable
7. Edit display_name and save successfully

**Test Case 3: Create New Recipe**
1. Open RecipeFormDialog for new recipe (recipe=None)
2. Verify NO variant banner (new recipes are not variants)
3. Verify all fields are editable

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| YieldTypeRow structure complex | Study existing code carefully before modifying |
| Grid row numbering disruption | Carefully track row increments |
| Session scope in __init__ | Use try/except to handle failures gracefully |

## Definition of Done Checklist

- [ ] T011: Variant detection added in __init__
- [ ] T012: Base recipe banner shows for variants
- [ ] T013: Yield structure fields are read-only for variants
- [ ] T014: display_name remains editable for variants
- [ ] T015: Inheritance explanatory text added for variants
- [ ] Base recipes still fully editable
- [ ] New recipe creation still works
- [ ] Changes committed with clear message

## Review Guidance

- Test with both base and variant recipes
- Verify banner shows correct base recipe name
- Verify read-only fields cannot be edited
- Verify display_name can still be edited and saved
- Verify no regressions for base recipe editing
- Check that explanatory text is helpful and clear

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
- 2026-01-25T04:13:23Z – unknown – shell_pid=29155 – lane=for_review – Ready for review: Implemented variant detection, banner, read-only yield fields, and inheritance explanatory text in RecipeFormDialog. Syntax validated.
- 2026-01-25T04:13:34Z – claude-opus – shell_pid=30283 – lane=doing – Started review via workflow command
