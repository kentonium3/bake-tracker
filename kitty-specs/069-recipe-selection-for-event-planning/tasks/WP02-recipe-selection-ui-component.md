---
work_package_id: WP02
title: Recipe Selection UI Component
lane: "doing"
dependencies: [WP01]
base_branch: 069-recipe-selection-for-event-planning-WP01
base_commit: 1bc0971b0175cde1d2bdc47e5bb8abaece08886c
created_at: '2026-01-26T23:23:33.160562+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - UI Component
assignee: ''
agent: "claude-opus-4-5"
shell_pid: "15784"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-26T22:57:43Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Recipe Selection UI Component

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

This WP depends on WP01. Branch from WP01:

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

**Goal**: Create a reusable `RecipeSelectionFrame` widget that displays a scrollable list of recipes with checkboxes, visual distinction between base and variant recipes, and real-time selection count.

**Success Criteria**:
- Frame renders with scrollable list of recipe checkboxes
- Base recipes display normally; variants show indentation and "(variant: X)" label
- Selection count updates immediately on checkbox change (FR-007)
- `get_selected_ids()` returns currently selected recipe IDs
- `set_selected(recipe_ids)` pre-checks specified recipes
- Save and Cancel buttons trigger callbacks

**Acceptance from spec.md**:
- FR-001: System MUST display all recipes in a single flat list
- FR-002: System MUST visually distinguish base recipes from variant recipes
- FR-003: System MUST provide a checkbox for each recipe enabling explicit selection
- FR-006: System MUST display selection count in format "X of Y recipes selected"
- FR-007: System MUST update selection count immediately when checkboxes change
- FR-011: System MUST support scrolling for recipe lists exceeding viewport height

## Context & Constraints

**Reference Documents**:
- `kitty-specs/069-recipe-selection-for-event-planning/research.md` - UI patterns (RQ-006, RQ-007)
- `kitty-specs/069-recipe-selection-for-event-planning/plan.md` - AD-003 visual distinction strategy
- `src/ui/forms/recipe_form.py` line 714 - Existing CTkCheckBox pattern

**Key Constraints**:
- Use CustomTkinter (CTk) widgets only
- Follow existing UI patterns in `src/ui/`
- Must handle up to 100 recipes with acceptable performance (SC-002: <2s load)
- Selection count must update within 100ms (SC-003)

**UI Framework Reference**:
```python
# From research.md RQ-007
self.var = ctk.BooleanVar(value=False)
self.checkbox = ctk.CTkCheckBox(
    parent,
    text="Label",
    variable=self.var,
    command=self._on_change,  # Optional callback
)
```

---

## Subtasks & Detailed Guidance

### Subtask T005 – Create `RecipeSelectionFrame` Class

**Purpose**: Create the container widget class with scrollable recipe list area.

**Steps**:
1. Create new file `src/ui/components/recipe_selection_frame.py`
2. Implement the base class structure:

```python
"""Recipe selection frame for event planning."""
from typing import Callable, Dict, List, Optional
import customtkinter as ctk

from src.models.recipe import Recipe


class RecipeSelectionFrame(ctk.CTkFrame):
    """
    A frame for selecting recipes for an event.

    Displays a scrollable list of recipes with checkboxes,
    visual distinction between base and variant recipes,
    and real-time selection count.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_save: Optional[Callable[[List[int]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize the recipe selection frame.

        Args:
            parent: Parent widget
            on_save: Callback when Save is clicked, receives list of selected recipe IDs
            on_cancel: Callback when Cancel is clicked
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(parent, **kwargs)

        self._on_save = on_save
        self._on_cancel = on_cancel
        self._recipes: List[Recipe] = []
        self._recipe_vars: Dict[int, ctk.BooleanVar] = {}
        self._event_name: str = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the frame layout."""
        # Header label
        self._header_label = ctk.CTkLabel(
            self,
            text="Recipe Selection",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self._header_label.pack(pady=(10, 5), padx=10, anchor="w")

        # Selection count label
        self._count_label = ctk.CTkLabel(
            self,
            text="0 of 0 recipes selected",
            font=ctk.CTkFont(size=12),
        )
        self._count_label.pack(pady=(0, 10), padx=10, anchor="w")

        # Scrollable frame for checkboxes
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            height=300,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Button frame
        self._button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._button_frame.pack(fill="x", padx=10, pady=10)

        self._cancel_button = ctk.CTkButton(
            self._button_frame,
            text="Cancel",
            width=100,
            command=self._handle_cancel,
        )
        self._cancel_button.pack(side="right", padx=(5, 0))

        self._save_button = ctk.CTkButton(
            self._button_frame,
            text="Save",
            width=100,
            command=self._handle_save,
        )
        self._save_button.pack(side="right")
```

3. Ensure the file has proper module docstring and imports

**Files**:
- `src/ui/components/recipe_selection_frame.py` (create)

**Notes**:
- Use `CTkScrollableFrame` for the checkbox list container
- Store recipes and BooleanVars as instance attributes for later access
- Button order: Save then Cancel (right-aligned)

---

### Subtask T006 – Implement Checkbox List Population

**Purpose**: Populate the scrollable frame with checkboxes from recipe data.

**Steps**:
1. Add method to populate recipes:

```python
def populate_recipes(self, recipes: List[Recipe], event_name: str = "") -> None:
    """
    Populate the frame with recipe checkboxes.

    Args:
        recipes: List of Recipe objects to display
        event_name: Optional event name to display in header
    """
    # Clear existing checkboxes
    for widget in self._scroll_frame.winfo_children():
        widget.destroy()
    self._recipe_vars.clear()

    # Update header
    self._event_name = event_name
    if event_name:
        self._header_label.configure(text=f"Recipe Selection for {event_name}")
    else:
        self._header_label.configure(text="Recipe Selection")

    # Store recipes
    self._recipes = recipes

    # Handle empty list
    if not recipes:
        empty_label = ctk.CTkLabel(
            self._scroll_frame,
            text="No recipes available",
            font=ctk.CTkFont(size=12, slant="italic"),
        )
        empty_label.pack(pady=20)
        self._update_count()
        return

    # Create checkbox for each recipe
    for recipe in recipes:
        display_name = self._get_display_name(recipe)

        var = ctk.BooleanVar(value=False)
        self._recipe_vars[recipe.id] = var

        checkbox = ctk.CTkCheckBox(
            self._scroll_frame,
            text=display_name,
            variable=var,
            command=self._update_count,
        )
        checkbox.pack(anchor="w", pady=2, padx=5)

    self._update_count()
```

2. Add helper method for checkbox command:

```python
def _update_count(self) -> None:
    """Update the selection count label."""
    selected = sum(1 for var in self._recipe_vars.values() if var.get())
    total = len(self._recipe_vars)
    self._count_label.configure(text=f"{selected} of {total} recipes selected")
```

**Files**:
- `src/ui/components/recipe_selection_frame.py` (modify)

**Notes**:
- Clear existing widgets before repopulating (prevents duplicates on refresh)
- Handle empty recipe list with "No recipes available" message
- Each checkbox triggers `_update_count` via command callback

---

### Subtask T007 – Implement Visual Distinction for Base vs Variant

**Purpose**: Visually distinguish variant recipes from base recipes using indentation and labels.

**Steps**:
1. Add the display name helper method:

```python
def _get_display_name(self, recipe: Recipe) -> str:
    """
    Get display name for a recipe with visual distinction.

    Base recipes display as: "Recipe Name"
    Variants display as: "    Recipe Name (variant: Variant Label)"

    Args:
        recipe: Recipe object

    Returns:
        Formatted display name string
    """
    if recipe.base_recipe_id is not None:
        # This is a variant recipe
        variant_label = recipe.variant_name or "variant"
        return f"    {recipe.name} (variant: {variant_label})"
    else:
        # This is a base recipe
        return recipe.name
```

**Files**:
- `src/ui/components/recipe_selection_frame.py` (modify)

**Visual Example**:
```
☑ Chocolate Chip Cookies
    ☑ Chocolate Chip Cookies (variant: Raspberry)
    ☐ Chocolate Chip Cookies (variant: Strawberry)
☐ Sugar Cookies
```

**Notes**:
- 4-space indent creates visual hierarchy
- Fallback to "variant" if `variant_name` is empty
- Consistent with plan.md AD-003 decision

---

### Subtask T008 – Implement Selection Count Display

**Purpose**: Show real-time "X of Y recipes selected" count that updates immediately.

**Steps**:
1. The `_update_count` method was added in T006
2. Verify it's called:
   - On initial population (`populate_recipes`)
   - On every checkbox change (via `command` callback)
   - After `set_selected` is called

3. Verify count label is visible even when scrolling (it's outside the scroll frame)

**Performance Requirement** (SC-003):
- Count must update within 100ms of checkbox interaction
- Using BooleanVar with command callback ensures synchronous update

**Files**:
- `src/ui/components/recipe_selection_frame.py` (verify)

---

### Subtask T009 – Implement `get_selected_ids` and `set_selected` Methods

**Purpose**: Provide programmatic access to selection state for loading and saving.

**Steps**:
1. Add getter method:

```python
def get_selected_ids(self) -> List[int]:
    """
    Get IDs of all currently selected recipes.

    Returns:
        List of recipe IDs that are checked
    """
    return [
        recipe_id
        for recipe_id, var in self._recipe_vars.items()
        if var.get()
    ]
```

2. Add setter method:

```python
def set_selected(self, recipe_ids: List[int]) -> None:
    """
    Set which recipes are selected (checked).

    Args:
        recipe_ids: List of recipe IDs to check (others will be unchecked)
    """
    selected_set = set(recipe_ids)
    for recipe_id, var in self._recipe_vars.items():
        var.set(recipe_id in selected_set)
    self._update_count()
```

**Files**:
- `src/ui/components/recipe_selection_frame.py` (modify)

**Notes**:
- `set_selected` replaces current selection (uncheck all, then check specified)
- Handles unknown IDs gracefully (ignores them)
- Updates count after setting

---

### Subtask T010 – Add Save and Cancel Buttons with Callback Hooks

**Purpose**: Allow parent widget to handle save and cancel actions.

**Steps**:
1. Add button handlers (buttons already created in T005):

```python
def _handle_save(self) -> None:
    """Handle Save button click."""
    if self._on_save:
        selected_ids = self.get_selected_ids()
        self._on_save(selected_ids)

def _handle_cancel(self) -> None:
    """Handle Cancel button click."""
    if self._on_cancel:
        self._on_cancel()
```

2. Verify buttons are wired to handlers in `_setup_ui` (done in T005)

**Files**:
- `src/ui/components/recipe_selection_frame.py` (modify)

**Notes**:
- Save passes selected IDs to callback (parent handles persistence)
- Cancel callback has no arguments (parent decides what to do)
- Callbacks are optional - if None, button click does nothing

---

## Complete File Structure

After all subtasks, `src/ui/components/recipe_selection_frame.py` should contain:

```python
"""Recipe selection frame for event planning."""
from typing import Callable, Dict, List, Optional
import customtkinter as ctk

from src.models.recipe import Recipe


class RecipeSelectionFrame(ctk.CTkFrame):
    """A frame for selecting recipes for an event."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_save: Optional[Callable[[List[int]], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._recipes: List[Recipe] = []
        self._recipe_vars: Dict[int, ctk.BooleanVar] = {}
        self._event_name: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the frame layout."""
        # ... (from T005)

    def populate_recipes(self, recipes: List[Recipe], event_name: str = "") -> None:
        """Populate the frame with recipe checkboxes."""
        # ... (from T006)

    def _get_display_name(self, recipe: Recipe) -> str:
        """Get display name with visual distinction."""
        # ... (from T007)

    def _update_count(self) -> None:
        """Update the selection count label."""
        # ... (from T006)

    def get_selected_ids(self) -> List[int]:
        """Get IDs of selected recipes."""
        # ... (from T009)

    def set_selected(self, recipe_ids: List[int]) -> None:
        """Set which recipes are selected."""
        # ... (from T009)

    def _handle_save(self) -> None:
        """Handle Save button click."""
        # ... (from T010)

    def _handle_cancel(self) -> None:
        """Handle Cancel button click."""
        # ... (from T010)
```

---

## Test Strategy

**Manual Testing** (UI components):
1. Create a test script or use the app to verify:
   - Frame renders correctly
   - Checkboxes appear for all recipes
   - Variants show indentation and labels
   - Count updates on click
   - Save/Cancel callbacks fire

**Optional Unit Tests** (if time permits):
- Test `_get_display_name` for base vs variant
- Test `get_selected_ids` / `set_selected` logic

**Commands**:
```bash
# Run app to manually test
python src/main.py
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with 100+ recipes | CTkScrollableFrame handles virtualization; test with large list |
| Checkbox state not syncing | Use BooleanVar consistently; avoid manual state tracking |
| Import issues | Ensure Recipe model import doesn't cause circular dependencies |

---

## Definition of Done Checklist

- [ ] `RecipeSelectionFrame` class created and functional
- [ ] Checkbox list populates from recipe data
- [ ] Visual distinction works (indent + variant label)
- [ ] Selection count updates in real-time
- [ ] `get_selected_ids()` returns correct IDs
- [ ] `set_selected()` pre-checks specified recipes
- [ ] Save and Cancel buttons trigger callbacks
- [ ] No linting or type errors
- [ ] Edge case: empty recipe list shows message

---

## Review Guidance

**Key checkpoints for reviewer**:
1. Verify visual distinction matches plan.md AD-003
2. Verify count format matches FR-006: "X of Y recipes selected"
3. Test with empty recipe list - should show "No recipes available"
4. Test with mix of base and variant recipes
5. Verify callbacks work (Save passes IDs, Cancel has no args)

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-26T22:57:43Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane:
```bash
spec-kitty agent tasks move-task WP02 --to <lane> --note "message"
```

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-26T23:28:42Z – unknown – shell_pid=14673 – lane=for_review – Ready for review: RecipeSelectionFrame component with 13 passing tests
- 2026-01-26T23:31:07Z – claude-opus-4-5 – shell_pid=15784 – lane=doing – Started review via workflow command
