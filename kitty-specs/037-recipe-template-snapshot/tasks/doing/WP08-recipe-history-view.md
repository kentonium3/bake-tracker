---
work_package_id: "WP08"
subtasks:
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
title: "Recipe History View"
phase: "Phase 3 - Production Readiness & History"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP08 - Recipe History View

## Objectives & Success Criteria

Display snapshot history for a recipe with restore capability.

**Success Criteria**:
- View list of snapshots for a recipe
- Display snapshot date, scale factor, is_backfilled badge
- View snapshot details (ingredient list as captured)
- Restore as new recipe from snapshot

## Context & Constraints

**Key References**:
- `src/services/recipe_snapshot_service.py` - get_recipe_snapshots()
- `kitty-specs/037-recipe-template-snapshot/spec.md` - User Story 6

**User Story 6 Acceptance**:
- "Given a recipe with multiple production snapshots, When I view its history, Then I see a chronological list of snapshots with dates."
- "Given a snapshot in history, When I click 'View Details', Then I see the full ingredient list as captured at that time."
- "Given a snapshot in history, When I click 'Restore as New Recipe', Then a new recipe template is created with the snapshot's data."

## Subtasks & Detailed Guidance

### Subtask T034 - Create recipe_history_view.py Dialog

**Purpose**: Modal dialog showing snapshot history for a recipe.

**File**: `src/ui/views/recipe_history_view.py`

**Implementation**:
```python
"""
Recipe History View - Display production snapshots for a recipe.

Shows chronological list of snapshots with ability to view details
and restore as new recipe.
"""

import customtkinter as ctk
from datetime import datetime

from src.services import recipe_snapshot_service, recipe_service


class RecipeHistoryView(ctk.CTkToplevel):
    """Dialog showing snapshot history for a recipe."""

    def __init__(self, parent, recipe_id: int, recipe_name: str):
        super().__init__(parent)

        self.recipe_id = recipe_id
        self.recipe_name = recipe_name
        self.selected_snapshot = None

        self.title(f"History: {recipe_name}")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_snapshots()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create dialog widgets."""
        # Header
        header = ctk.CTkLabel(
            self,
            text=f"Production History: {self.recipe_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        header.pack(pady=10)

        # Main content frame
        content = ctk.CTkFrame(self)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Snapshot list (left side)
        list_frame = ctk.CTkFrame(content)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        list_label = ctk.CTkLabel(list_frame, text="Snapshots (newest first)")
        list_label.pack(anchor="w", pady=5)

        self.snapshot_listbox = ctk.CTkScrollableFrame(list_frame, height=300)
        self.snapshot_listbox.pack(fill="both", expand=True)

        # Details panel (right side)
        details_frame = ctk.CTkFrame(content)
        details_frame.pack(side="right", fill="both", expand=True)

        details_label = ctk.CTkLabel(details_frame, text="Snapshot Details")
        details_label.pack(anchor="w", pady=5)

        self.details_text = ctk.CTkTextbox(details_frame, height=300, state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)

        self.restore_btn = ctk.CTkButton(
            button_frame,
            text="Restore as New Recipe",
            command=self._on_restore,
            state="disabled"
        )
        self.restore_btn.pack(side="left")

        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy
        )
        close_btn.pack(side="right")

    def _load_snapshots(self):
        """Load and display snapshots."""
        snapshots = recipe_snapshot_service.get_recipe_snapshots(self.recipe_id)

        if not snapshots:
            no_data = ctk.CTkLabel(
                self.snapshot_listbox,
                text="No production history yet.",
                text_color="gray"
            )
            no_data.pack(pady=20)
            return

        for snapshot in snapshots:
            self._create_snapshot_row(snapshot)

    def _create_snapshot_row(self, snapshot: dict):
        """Create a row for a snapshot."""
        row = ctk.CTkFrame(self.snapshot_listbox)
        row.pack(fill="x", pady=2)

        # Format date
        date_str = snapshot.get("snapshot_date", "")
        try:
            dt = datetime.fromisoformat(date_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_display = date_str

        # Build label text
        label_text = f"{date_display}"
        if snapshot.get("scale_factor", 1.0) != 1.0:
            label_text += f" (Scale: {snapshot['scale_factor']}x)"
        if snapshot.get("is_backfilled"):
            label_text += " (approximated)"

        label = ctk.CTkLabel(row, text=label_text, anchor="w")
        label.pack(side="left", fill="x", expand=True, padx=5)

        # View button
        view_btn = ctk.CTkButton(
            row,
            text="View",
            width=60,
            command=lambda s=snapshot: self._on_view_snapshot(s)
        )
        view_btn.pack(side="right", padx=2)

    def _on_view_snapshot(self, snapshot: dict):
        """Display snapshot details."""
        self.selected_snapshot = snapshot
        self.restore_btn.configure(state="normal")

        # Build details text
        recipe_data = snapshot.get("recipe_data", {})
        ingredients = snapshot.get("ingredients_data", [])

        details = []
        details.append(f"Snapshot Date: {snapshot.get('snapshot_date', 'N/A')}")
        details.append(f"Scale Factor: {snapshot.get('scale_factor', 1.0)}x")
        if snapshot.get("is_backfilled"):
            details.append("** Data approximated from current recipe **")
        details.append("")
        details.append(f"Recipe: {recipe_data.get('name', 'N/A')}")
        details.append(f"Category: {recipe_data.get('category', 'N/A')}")
        details.append(f"Yield: {recipe_data.get('yield_quantity', 0)} {recipe_data.get('yield_unit', '')}")
        details.append("")
        details.append("Ingredients (as captured):")

        for ing in ingredients:
            details.append(f"  - {ing.get('quantity', 0)} {ing.get('unit', '')} {ing.get('ingredient_name', 'Unknown')}")

        # Update display
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", "\n".join(details))
        self.details_text.configure(state="disabled")

    def _on_restore(self):
        """Restore selected snapshot as new recipe."""
        if not self.selected_snapshot:
            return

        # Confirm
        from src.ui.utils.dialogs import show_confirmation
        if not show_confirmation(
            self,
            "Restore Snapshot",
            "Create a new recipe from this snapshot?\n\nThis will create a copy, not modify the original."
        ):
            return

        try:
            result = recipe_snapshot_service.create_recipe_from_snapshot(
                self.selected_snapshot["id"]
            )

            from src.ui.utils.dialogs import show_info
            show_info(
                self,
                "Recipe Created",
                f"New recipe created: {result['name']}"
            )
            self.destroy()

        except Exception as e:
            from src.ui.utils.dialogs import show_error
            show_error(self, f"Failed to restore: {e}")
```

---

### Subtask T035 - Display Snapshot List with Badges

**Purpose**: Show "(approximated)" badge for backfilled snapshots.

**Already Covered**: The `_create_snapshot_row()` method in T034 adds "(approximated)" suffix when `is_backfilled=True`.

---

### Subtask T036 - Add View Details Functionality

**Purpose**: Show snapshot ingredient data.

**Already Covered**: The `_on_view_snapshot()` method in T034 displays full snapshot details.

---

### Subtask T037 - Add Restore as New Recipe

**Purpose**: Create new recipe from historical snapshot.

**UI Already Covered**: Button and handler in T034.

**Needs**: Service function (T038).

---

### Subtask T038 - Add create_recipe_from_snapshot()

**Purpose**: Service function to create recipe from snapshot data.

**File**: `src/services/recipe_snapshot_service.py`

**Implementation**:
```python
def create_recipe_from_snapshot(snapshot_id: int, session=None) -> dict:
    """
    Create a new recipe from historical snapshot data.

    Args:
        snapshot_id: Snapshot to restore from
        session: Optional session

    Returns:
        Created recipe dict
    """
    if session is not None:
        return _create_recipe_from_snapshot_impl(snapshot_id, session)

    with session_scope() as session:
        return _create_recipe_from_snapshot_impl(snapshot_id, session)


def _create_recipe_from_snapshot_impl(snapshot_id: int, session) -> dict:
    from src.models import Recipe, RecipeIngredient, RecipeSnapshot

    # Get snapshot
    snapshot = session.query(RecipeSnapshot).filter_by(id=snapshot_id).first()
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    recipe_data = snapshot.get_recipe_data()
    ingredients_data = snapshot.get_ingredients_data()

    # Create new recipe with restored data
    new_name = f"{recipe_data.get('name', 'Restored')} (restored {datetime.now().strftime('%Y-%m-%d')})"

    recipe = Recipe(
        name=new_name,
        category=recipe_data.get("category", "Uncategorized"),
        source=recipe_data.get("source"),
        yield_quantity=recipe_data.get("yield_quantity", 1),
        yield_unit=recipe_data.get("yield_unit", "each"),
        yield_description=recipe_data.get("yield_description"),
        estimated_time_minutes=recipe_data.get("estimated_time_minutes"),
        notes=f"Restored from snapshot {snapshot_id}. Original notes: {recipe_data.get('notes', '')}",
        is_production_ready=False,  # Restored recipes start experimental
    )

    session.add(recipe)
    session.flush()

    # Restore ingredients
    for ing in ingredients_data:
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.get("ingredient_id"),
            quantity=ing.get("quantity", 0),
            unit=ing.get("unit", ""),
            notes=ing.get("notes"),
        )
        session.add(ri)

    session.commit()

    return {
        "id": recipe.id,
        "name": recipe.name,
        "category": recipe.category,
    }
```

## Test Strategy

- Manual testing: View history, click snapshots, verify details
- Restore test: Restore from snapshot, verify new recipe created
- Badge test: Verify "(approximated)" shows for backfilled

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Many snapshots slow | Pagination (defer to future) |
| Ingredient deleted | Handle gracefully in restore |

## Definition of Done Checklist

- [ ] RecipeHistoryView dialog created
- [ ] Snapshot list displayed (newest first)
- [ ] "(approximated)" badge for backfilled snapshots
- [ ] View Details shows ingredients
- [ ] Restore as New Recipe creates recipe
- [ ] create_recipe_from_snapshot() service function

## Review Guidance

- Verify date formatting is user-friendly
- Check restore handles deleted ingredients
- Confirm dialog is accessible from recipe details

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
- 2026-01-04T19:09:43Z – system – shell_pid= – lane=doing – Moved to doing
