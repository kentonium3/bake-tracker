---
work_package_id: "WP06"
subtasks:
  - "T036"
  - "T037"
  - "T038"
  - "T039"
  - "T040"
  - "T041"
  - "T042"
  - "T043"
title: "Rename Operations"
phase: "Phase 4 - Operations"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T15:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Rename Operations

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **Mark as acknowledged**: When you understand feedback and begin addressing it.
- **Report progress**: Update Activity Log as you address each item.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Goal**: Implement rename functionality for any hierarchy item (L0/L1/L2 ingredients, categories/subcategories/materials).

**Success Criteria**:
- Rename dialog shows current name pre-populated
- Name validation prevents duplicates among siblings
- Slug regenerated after rename
- Tree and detail panel refresh after rename
- Renamed item shows new name in Products and Recipes automatically (FK propagation)

**User Story Reference**: User Story 5 (spec.md) - "Rename Ingredient or Material"

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; services handle validation
- IV. Test-Driven Development: Service methods tested (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Story 5
- `kitty-specs/052-ingredient-material-hierarchy-admin/research.md` - RQ5 on rename propagation

**Existing Code**:
- `src/ui/hierarchy_admin_window.py` (from WP04) - Has button placeholder
- `src/services/ingredient_hierarchy_service.py` - To extend
- `src/services/material_hierarchy_service.py` - To extend
- `src/services/hierarchy_admin_service.py` (from WP03) - Validation utilities

**Dependencies**: WP04 must be complete (needs admin UI shell).

**Parallelization**: Can run in parallel with WP05 (Add) and WP07 (Reparent).

## Subtasks & Detailed Guidance

### Subtask T036 – Add rename_ingredient() to ingredient_hierarchy_service.py

- **Purpose**: Service method to rename any level ingredient.
- **Files**: Extend `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T037 (materials)

**Implementation**:
```python
def rename_ingredient(
    self,
    ingredient_id: int,
    new_name: str,
    session: Optional[Session] = None
) -> Ingredient:
    """
    Rename an ingredient (any level).

    Args:
        ingredient_id: ID of ingredient to rename
        new_name: New display name

    Returns:
        Updated Ingredient object

    Raises:
        ValueError: If ingredient not found, name empty, or name not unique among siblings
    """
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    def _impl(sess: Session) -> Ingredient:
        # Find ingredient
        ingredient = sess.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()

        if not ingredient:
            raise ValueError(f"Ingredient {ingredient_id} not found")

        new_name_stripped = new_name.strip()
        if not new_name_stripped:
            raise ValueError("Name cannot be empty")

        # Get siblings for uniqueness check
        if ingredient.parent_ingredient_id:
            siblings = sess.query(Ingredient).filter(
                Ingredient.parent_ingredient_id == ingredient.parent_ingredient_id
            ).all()
        else:
            # Root level - siblings are other roots
            siblings = sess.query(Ingredient).filter(
                Ingredient.parent_ingredient_id == None,
                Ingredient.hierarchy_level == ingredient.hierarchy_level
            ).all()

        # Validate unique name (excluding self)
        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, new_name_stripped, exclude_id=ingredient_id
        ):
            raise ValueError(f"An ingredient named '{new_name_stripped}' already exists at this level")

        # Update name
        ingredient.display_name = new_name_stripped

        # Regenerate slug
        new_slug = hierarchy_admin_service.generate_slug(new_name_stripped)

        # Check slug uniqueness globally (excluding self)
        existing_slug = sess.query(Ingredient).filter(
            Ingredient.slug == new_slug,
            Ingredient.id != ingredient_id
        ).first()

        if existing_slug:
            # Append level or parent info for uniqueness
            if ingredient.parent:
                new_slug = f"{ingredient.parent.slug}-{new_slug}"
            else:
                new_slug = f"l{ingredient.hierarchy_level}-{new_slug}"

        ingredient.slug = new_slug

        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T037 – Add rename_item() to material_hierarchy_service.py

- **Purpose**: Service method to rename category, subcategory, or material.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T036 (ingredients)

**Implementation**:
```python
def rename_item(
    self,
    item_type: str,
    item_id: int,
    new_name: str,
    session: Optional[Session] = None
):
    """
    Rename a category, subcategory, or material.

    Args:
        item_type: "category", "subcategory", or "material"
        item_id: ID of item to rename
        new_name: New name

    Returns:
        Updated entity object

    Raises:
        ValueError: If item not found, invalid type, name empty, or name not unique
    """
    from src.models.material_category import MaterialCategory
    from src.models.material_subcategory import MaterialSubcategory
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    VALID_TYPES = ("category", "subcategory", "material")

    def _impl(sess: Session):
        if item_type not in VALID_TYPES:
            raise ValueError(f"Invalid item type '{item_type}'. Must be one of: {VALID_TYPES}")

        new_name_stripped = new_name.strip()
        if not new_name_stripped:
            raise ValueError("Name cannot be empty")

        # Get entity and siblings based on type
        if item_type == "category":
            entity = sess.query(MaterialCategory).filter(
                MaterialCategory.id == item_id
            ).first()
            if not entity:
                raise ValueError(f"Category {item_id} not found")
            # Categories are unique globally
            siblings = sess.query(MaterialCategory).all()

        elif item_type == "subcategory":
            entity = sess.query(MaterialSubcategory).filter(
                MaterialSubcategory.id == item_id
            ).first()
            if not entity:
                raise ValueError(f"Subcategory {item_id} not found")
            # Subcategories unique within category
            siblings = sess.query(MaterialSubcategory).filter(
                MaterialSubcategory.category_id == entity.category_id
            ).all()

        else:  # material
            entity = sess.query(Material).filter(
                Material.id == item_id
            ).first()
            if not entity:
                raise ValueError(f"Material {item_id} not found")
            # Materials unique within subcategory
            siblings = sess.query(Material).filter(
                Material.subcategory_id == entity.subcategory_id
            ).all()

        # Validate unique name (excluding self)
        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, new_name_stripped, exclude_id=item_id
        ):
            raise ValueError(f"A {item_type} named '{new_name_stripped}' already exists at this level")

        # Update name
        entity.name = new_name_stripped

        # Regenerate slug
        new_slug = hierarchy_admin_service.generate_slug(new_name_stripped)

        # Check slug uniqueness based on type
        if item_type == "category":
            existing = sess.query(MaterialCategory).filter(
                MaterialCategory.slug == new_slug,
                MaterialCategory.id != item_id
            ).first()
        elif item_type == "subcategory":
            existing = sess.query(MaterialSubcategory).filter(
                MaterialSubcategory.slug == new_slug,
                MaterialSubcategory.id != item_id
            ).first()
        else:
            existing = sess.query(Material).filter(
                Material.slug == new_slug,
                Material.id != item_id
            ).first()

        if existing:
            # Add prefix for uniqueness
            new_slug = f"{item_type[0]}-{new_slug}"

        entity.slug = new_slug

        sess.flush()
        return entity

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T038 – Create rename dialog in hierarchy_admin_window.py

- **Purpose**: Modal dialog for renaming items.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T036, T037

**Implementation**:
```python
class RenameDialog(ctk.CTkToplevel):
    """Dialog for renaming an item."""

    def __init__(
        self,
        parent,
        current_name: str,
        entity_type: str,
        on_save: Callable
    ):
        super().__init__(parent)

        self.on_save = on_save
        self.result = None

        # Window setup
        self.title(f"Rename {entity_type.title()}")
        self.geometry("400x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Build form
        self._create_form(current_name)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_form(self, current_name: str):
        """Create the rename form."""
        # Current name (read-only)
        current_frame = ctk.CTkFrame(self)
        current_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(current_frame, text="Current Name:").pack(anchor="w")
        ctk.CTkLabel(
            current_frame,
            text=current_name,
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w")

        # New name input
        name_frame = ctk.CTkFrame(self)
        name_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(name_frame, text="New Name:").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(name_frame, width=300)
        self.name_entry.pack(fill="x", pady=5)
        self.name_entry.insert(0, current_name)  # Pre-populate
        self.name_entry.select_range(0, "end")  # Select all for easy editing
        self.name_entry.focus()

        # Error label
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack(pady=5)

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            fg_color="gray"
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Rename",
            command=self._on_save
        ).pack(side="right", padx=5)

    def _on_save(self):
        """Handle save button click."""
        new_name = self.name_entry.get().strip()

        if not new_name:
            self.error_label.configure(text="Name cannot be empty")
            return

        self.result = new_name

        try:
            self.on_save(new_name)
            self.destroy()
        except ValueError as e:
            self.error_label.configure(text=str(e))
```

### Subtask T039 – Pre-populate current name in dialog

- **Purpose**: Show existing name for easy editing.
- **Files**: Already implemented in T038
- **Parallel?**: N/A - integrated into T038

*The `RenameDialog._create_form()` method:*
1. Displays current name as read-only label
2. Pre-populates entry with current name: `self.name_entry.insert(0, current_name)`
3. Selects all text for easy replacement: `self.name_entry.select_range(0, "end")`

### Subtask T040 – Implement name validation (unique among siblings)

- **Purpose**: Prevent duplicate names.
- **Files**: Already implemented in T036, T037
- **Parallel?**: N/A - integrated into service methods

*Validation uses `hierarchy_admin_service.validate_unique_sibling_name()` with `exclude_id` parameter to allow keeping the same name.*

### Subtask T041 – Regenerate slug on rename

- **Purpose**: Keep slug consistent with name.
- **Files**: Already implemented in T036, T037
- **Parallel?**: N/A - integrated into service methods

*Both `rename_ingredient()` and `rename_item()` call `hierarchy_admin_service.generate_slug()` and handle global slug uniqueness.*

### Subtask T042 – Refresh tree and detail panel after rename

- **Purpose**: Update UI to show new name.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T038

**Implementation**:
```python
# Update _on_rename_click in HierarchyAdminWindow:

def _on_rename_click(self):
    """Handle rename button click - open rename dialog."""
    if not self.selected_item:
        return

    node = self.selected_item
    current_name = node.get("name", "")

    def on_save(new_name: str):
        """Callback when dialog saves."""
        try:
            if self.entity_type == "ingredient":
                self.hierarchy_service.rename_ingredient(
                    ingredient_id=node["id"],
                    new_name=new_name
                )
            else:
                # Determine item type for materials
                item_type = node.get("type", "material")
                self.hierarchy_service.rename_item(
                    item_type=item_type,
                    item_id=node["id"],
                    new_name=new_name
                )

            # Refresh tree
            self._load_tree()

            # Clear selection (tree was rebuilt)
            self._clear_detail_panel()

            # Show success
            from tkinter import messagebox
            messagebox.showinfo("Success", "Item renamed successfully!")

        except ValueError as e:
            raise  # Re-raise for dialog to display

    RenameDialog(self, current_name, self.entity_type, on_save)

# Enable the rename button in _create_action_buttons:
self.rename_btn = ctk.CTkButton(
    self.actions_frame,
    text="Rename...",
    command=self._on_rename_click,
    state="normal"  # Now enabled
)
```

### Subtask T043 – Add tests for rename operations

- **Purpose**: Test service methods for rename functionality.
- **Files**: Extend test files
- **Parallel?**: No - depends on T036, T037

**Test Cases for Ingredients** (`test_ingredient_hierarchy_service.py`):
```python
def test_rename_ingredient_success(session, l2_ingredient):
    """Test renaming an ingredient."""
    result = ingredient_hierarchy_service.rename_ingredient(
        ingredient_id=l2_ingredient.id,
        new_name="Renamed Ingredient",
        session=session
    )
    assert result.display_name == "Renamed Ingredient"
    assert "renamed-ingredient" in result.slug

def test_rename_ingredient_same_name(session, l2_ingredient):
    """Test keeping the same name (should succeed)."""
    original_name = l2_ingredient.display_name
    result = ingredient_hierarchy_service.rename_ingredient(
        ingredient_id=l2_ingredient.id,
        new_name=original_name,
        session=session
    )
    assert result.display_name == original_name

def test_rename_ingredient_duplicate_sibling(session, l1_ingredient, l2_ingredient):
    """Test error when renaming to existing sibling name."""
    # Create another L2 under same parent
    other_l2 = Ingredient(
        display_name="Other Ingredient",
        slug="other-ingredient",
        parent_ingredient_id=l1_ingredient.id,
        hierarchy_level=2
    )
    session.add(other_l2)
    session.flush()

    with pytest.raises(ValueError, match="already exists"):
        ingredient_hierarchy_service.rename_ingredient(
            ingredient_id=l2_ingredient.id,
            new_name="Other Ingredient",
            session=session
        )

def test_rename_ingredient_empty_name(session, l2_ingredient):
    """Test error for empty name."""
    with pytest.raises(ValueError, match="cannot be empty"):
        ingredient_hierarchy_service.rename_ingredient(
            ingredient_id=l2_ingredient.id,
            new_name="   ",
            session=session
        )

def test_rename_ingredient_not_found(session):
    """Test error when ingredient doesn't exist."""
    with pytest.raises(ValueError, match="not found"):
        ingredient_hierarchy_service.rename_ingredient(
            ingredient_id=99999,
            new_name="Test",
            session=session
        )

def test_rename_ingredient_trims_whitespace(session, l2_ingredient):
    """Test that leading/trailing whitespace is trimmed on rename."""
    result = ingredient_hierarchy_service.rename_ingredient(
        ingredient_id=l2_ingredient.id,
        new_name="  Renamed Item  ",
        session=session
    )
    assert result.display_name == "Renamed Item"  # trimmed
```

**Test Cases for Materials** (`test_material_hierarchy_service.py`):
```python
def test_rename_material_success(session, material):
    """Test renaming a material."""
    result = material_hierarchy_service.rename_item(
        item_type="material",
        item_id=material.id,
        new_name="Renamed Material",
        session=session
    )
    assert result.name == "Renamed Material"

def test_rename_subcategory_success(session, subcategory):
    """Test renaming a subcategory."""
    result = material_hierarchy_service.rename_item(
        item_type="subcategory",
        item_id=subcategory.id,
        new_name="Renamed Subcategory",
        session=session
    )
    assert result.name == "Renamed Subcategory"

def test_rename_category_success(session, category):
    """Test renaming a category."""
    result = material_hierarchy_service.rename_item(
        item_type="category",
        item_id=category.id,
        new_name="Renamed Category",
        session=session
    )
    assert result.name == "Renamed Category"

def test_rename_invalid_type(session, material):
    """Test error for invalid item type."""
    with pytest.raises(ValueError, match="Invalid item type"):
        material_hierarchy_service.rename_item(
            item_type="invalid",
            item_id=material.id,
            new_name="Test",
            session=session
        )
```

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for `rename_ingredient()` - all branches
- Unit tests for `rename_item()` - all types and branches
- Run: `./run-tests.sh -k "rename" -v`

**Manual Testing**:
1. Select item, click Rename
2. Verify current name pre-populated
3. Change name, save
4. Verify tree shows new name
5. Verify Products/Recipes show new name (FK propagation)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slug collision on rename | Append prefix if collision |
| Case-only rename fails | `validate_unique_sibling_name` uses lowercase compare |
| FK propagation not visible | Test by opening Products/Recipes after rename |

## Definition of Done Checklist

- [ ] `rename_ingredient()` method works correctly for all levels
- [ ] `rename_item()` method works for category/subcategory/material
- [ ] Rename dialog shows current name pre-populated
- [ ] Name validation prevents duplicates
- [ ] Slug regenerated correctly
- [ ] Tree and detail panel refresh after rename
- [ ] Unit tests pass with >70% coverage
- [ ] Products/Recipes show renamed items automatically

## Review Guidance

**Key checkpoints for reviewer**:
1. Select ingredient at each level (L0, L1, L2) and rename
2. Select category, subcategory, material and rename
3. Try duplicate name - verify error shown
4. Verify tree shows new name after rename
5. Open Products/Recipes tab - verify renamed item shows correctly
6. Run service tests: `./run-tests.sh -k "rename" -v`

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:58:25Z – claude – lane=doing – Moved to doing
- 2026-01-15T04:02:54Z – claude – lane=for_review – All subtasks complete, 19 rename tests passing
- 2026-01-15T05:36:42Z – claude – lane=done – Review approved: Rename operations with sibling uniqueness validation
