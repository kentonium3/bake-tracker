---
work_package_id: "WP05"
subtasks:
  - "T029"
  - "T030"
  - "T031"
  - "T032"
  - "T033"
  - "T034"
  - "T035"
title: "Add Operations"
phase: "Phase 4 - Operations"
lane: "doing"
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

# Work Package Prompt: WP05 – Add Operations

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

**Goal**: Implement add functionality for new L2 ingredients and materials via the admin UI.

**Success Criteria**:
- Add dialog allows creating new L2 ingredient under selected L1 parent
- Add dialog allows creating new material under selected subcategory
- Name validation prevents duplicates among siblings
- Slug auto-generated from name
- Tree refreshes after successful add
- New item appears in Ingredients/Materials tab and dropdowns

**User Story Reference**: User Story 4 (spec.md) - "Add New L2 Ingredient"

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; services handle validation
- IV. Test-Driven Development: Service methods tested (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Story 4
- `kitty-specs/052-ingredient-material-hierarchy-admin/data-model.md` - Service interfaces

**Existing Code**:
- `src/ui/hierarchy_admin_window.py` (from WP04) - Has button placeholder
- `src/services/ingredient_hierarchy_service.py` - To extend
- `src/services/material_hierarchy_service.py` - To extend
- `src/services/hierarchy_admin_service.py` (from WP03) - Validation utilities

**Dependencies**: WP04 must be complete (needs admin UI shell).

**Parallelization**: Can run in parallel with WP06 (Rename) and WP07 (Reparent).

## Subtasks & Detailed Guidance

### Subtask T029 – Add add_leaf_ingredient() to ingredient_hierarchy_service.py

- **Purpose**: Service method to create new L2 ingredient.
- **Files**: Extend `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T030 (materials)

**Implementation**:
```python
def add_leaf_ingredient(
    self,
    parent_id: int,
    name: str,
    session: Optional[Session] = None
) -> Ingredient:
    """
    Create new L2 (leaf) ingredient under L1 parent.

    Args:
        parent_id: ID of L1 parent ingredient
        name: Display name for new ingredient

    Returns:
        Created Ingredient object

    Raises:
        ValueError: If parent not found, parent not L1, or name not unique
    """
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    def _impl(sess: Session) -> Ingredient:
        # Validate parent exists and is L1
        parent = sess.query(Ingredient).filter(
            Ingredient.id == parent_id
        ).first()

        if not parent:
            raise ValueError(f"Parent ingredient {parent_id} not found")

        if parent.hierarchy_level != 1:
            raise ValueError(f"Parent must be L1 (level 1), got level {parent.hierarchy_level}")

        # Get siblings for uniqueness check
        siblings = sess.query(Ingredient).filter(
            Ingredient.parent_ingredient_id == parent_id
        ).all()

        # Validate unique name
        if not hierarchy_admin_service.validate_unique_sibling_name(siblings, name):
            raise ValueError(f"An ingredient named '{name}' already exists under this parent")

        # Generate slug
        slug = hierarchy_admin_service.generate_slug(name)

        # Check slug uniqueness globally
        existing_slug = sess.query(Ingredient).filter(
            Ingredient.slug == slug
        ).first()
        if existing_slug:
            # Append parent slug for uniqueness
            slug = f"{parent.slug}-{slug}"

        # Create ingredient
        ingredient = Ingredient(
            display_name=name.strip(),
            slug=slug,
            parent_ingredient_id=parent_id,
            hierarchy_level=2
        )

        sess.add(ingredient)
        sess.flush()  # Get ID

        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T030 – Add add_material() to material_hierarchy_service.py

- **Purpose**: Service method to create new material.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T029 (ingredients)

**Implementation**:
```python
def add_material(
    self,
    subcategory_id: int,
    name: str,
    base_unit_type: str = "each",
    session: Optional[Session] = None
) -> Material:
    """
    Create new material under subcategory.

    Args:
        subcategory_id: ID of parent subcategory
        name: Display name for new material
        base_unit_type: Unit type ('each', 'linear_inches', 'square_inches')

    Returns:
        Created Material object

    Raises:
        ValueError: If subcategory not found, invalid unit type, or name not unique
    """
    from src.models.material_subcategory import MaterialSubcategory
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    VALID_UNIT_TYPES = ("each", "linear_inches", "square_inches")

    def _impl(sess: Session) -> Material:
        # Validate unit type
        if base_unit_type not in VALID_UNIT_TYPES:
            raise ValueError(f"Invalid unit type '{base_unit_type}'. Must be one of: {VALID_UNIT_TYPES}")

        # Validate subcategory exists
        subcategory = sess.query(MaterialSubcategory).filter(
            MaterialSubcategory.id == subcategory_id
        ).first()

        if not subcategory:
            raise ValueError(f"Subcategory {subcategory_id} not found")

        # Get siblings for uniqueness check
        siblings = sess.query(Material).filter(
            Material.subcategory_id == subcategory_id
        ).all()

        # Validate unique name
        if not hierarchy_admin_service.validate_unique_sibling_name(siblings, name):
            raise ValueError(f"A material named '{name}' already exists in this subcategory")

        # Generate slug
        slug = hierarchy_admin_service.generate_slug(name)

        # Check slug uniqueness globally
        existing_slug = sess.query(Material).filter(
            Material.slug == slug
        ).first()
        if existing_slug:
            # Append subcategory slug for uniqueness
            slug = f"{subcategory.slug}-{slug}"

        # Create material
        material = Material(
            name=name.strip(),
            slug=slug,
            subcategory_id=subcategory_id,
            base_unit_type=base_unit_type
        )

        sess.add(material)
        sess.flush()  # Get ID

        return material

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T031 – Create add dialog in hierarchy_admin_window.py

- **Purpose**: Modal dialog for adding new items.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T029, T030

**Implementation**:
```python
class AddItemDialog(ctk.CTkToplevel):
    """Dialog for adding new ingredient or material."""

    def __init__(
        self,
        parent,
        entity_type: str,
        parent_options: list,
        on_save: Callable
    ):
        super().__init__(parent)

        self.entity_type = entity_type
        self.on_save = on_save
        self.result = None

        # Window setup
        self.title(f"Add New {entity_type.title()}")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Build form
        self._create_form(parent_options)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_form(self, parent_options):
        """Create the add form."""
        # Parent selection
        parent_frame = ctk.CTkFrame(self)
        parent_frame.pack(fill="x", padx=20, pady=10)

        if self.entity_type == "ingredient":
            label_text = "Parent (L1):"
        else:
            label_text = "Subcategory:"

        ctk.CTkLabel(parent_frame, text=label_text).pack(anchor="w")

        self.parent_var = ctk.StringVar()
        self.parent_dropdown = ctk.CTkComboBox(
            parent_frame,
            values=[p["display"] for p in parent_options],
            variable=self.parent_var,
            state="readonly",
            width=300
        )
        self.parent_dropdown.pack(fill="x", pady=5)

        # Store mapping for lookup
        self._parent_map = {p["display"]: p["id"] for p in parent_options}

        # Name input
        name_frame = ctk.CTkFrame(self)
        name_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(name_frame, text="Name:").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(name_frame, width=300)
        self.name_entry.pack(fill="x", pady=5)
        self.name_entry.focus()

        # Unit type (materials only)
        if self.entity_type == "material":
            unit_frame = ctk.CTkFrame(self)
            unit_frame.pack(fill="x", padx=20, pady=10)

            ctk.CTkLabel(unit_frame, text="Unit Type:").pack(anchor="w")
            self.unit_var = ctk.StringVar(value="each")
            self.unit_dropdown = ctk.CTkComboBox(
                unit_frame,
                values=["each", "linear_inches", "square_inches"],
                variable=self.unit_var,
                state="readonly",
                width=300
            )
            self.unit_dropdown.pack(fill="x", pady=5)

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
            text="Add",
            command=self._on_save
        ).pack(side="right", padx=5)

    def _on_save(self):
        """Handle save button click."""
        # Validate
        parent_display = self.parent_var.get()
        if not parent_display:
            self.error_label.configure(text="Please select a parent")
            return

        name = self.name_entry.get().strip()
        if not name:
            self.error_label.configure(text="Name is required")
            return

        parent_id = self._parent_map.get(parent_display)
        if not parent_id:
            self.error_label.configure(text="Invalid parent selection")
            return

        # Build result
        self.result = {
            "parent_id": parent_id,
            "name": name
        }

        if self.entity_type == "material":
            self.result["base_unit_type"] = self.unit_var.get()

        # Call save callback
        try:
            self.on_save(self.result)
            self.destroy()
        except ValueError as e:
            self.error_label.configure(text=str(e))
```

### Subtask T032 – Implement parent selection (L1 for ingredients, subcategory for materials)

- **Purpose**: Populate parent dropdown with valid options.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - part of T031

**Implementation**:
```python
# Add to HierarchyAdminWindow class:

def _get_parent_options(self) -> list:
    """Get valid parent options for add operation."""
    if self.entity_type == "ingredient":
        # Get all L1 ingredients
        tree = self.hierarchy_service.get_hierarchy_tree()
        options = []
        for l0 in tree:
            for l1 in l0.get("children", []):
                options.append({
                    "id": l1["id"],
                    "display": f"{l0['name']} > {l1['name']}"
                })
        return options
    else:
        # Get all subcategories
        tree = self.hierarchy_service.get_hierarchy_tree()
        options = []
        for cat in tree:
            for subcat in cat.get("children", []):
                options.append({
                    "id": subcat["id"],
                    "display": f"{cat['name']} > {subcat['name']}"
                })
        return options
```

### Subtask T033 – Implement name validation (unique among siblings, non-empty)

- **Purpose**: Prevent duplicate names and empty names.
- **Files**: Already implemented in T029, T030, T031
- **Parallel?**: N/A - integrated into service methods

*Validation is handled at two levels:*
1. UI level: Empty name check in `_on_save()`
2. Service level: `validate_unique_sibling_name()` called in `add_leaf_ingredient()` and `add_material()`

### Subtask T034 – Refresh tree after successful add

- **Purpose**: Update tree view to show new item.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T031

**Implementation**:
```python
# Update _on_add_click in HierarchyAdminWindow:

def _on_add_click(self):
    """Handle add button click - open add dialog."""
    parent_options = self._get_parent_options()

    if not parent_options:
        # Show error - no valid parents
        from tkinter import messagebox
        messagebox.showerror(
            "Cannot Add",
            f"No valid parent {'L1 ingredients' if self.entity_type == 'ingredient' else 'subcategories'} available."
        )
        return

    def on_save(data):
        """Callback when dialog saves."""
        try:
            if self.entity_type == "ingredient":
                self.hierarchy_service.add_leaf_ingredient(
                    parent_id=data["parent_id"],
                    name=data["name"]
                )
            else:
                self.hierarchy_service.add_material(
                    subcategory_id=data["parent_id"],
                    name=data["name"],
                    base_unit_type=data.get("base_unit_type", "each")
                )

            # Refresh tree
            self._load_tree()

            # Show success
            from tkinter import messagebox
            messagebox.showinfo("Success", f"{self.entity_type.title()} added successfully!")

        except ValueError as e:
            raise  # Re-raise for dialog to display

    AddItemDialog(self, self.entity_type, parent_options, on_save)

# Enable the add button in _create_action_buttons:
self.add_btn = ctk.CTkButton(
    self.actions_frame,
    text="Add New...",
    command=self._on_add_click,
    state="normal"  # Now enabled
)
```

### Subtask T035 – Add tests for add operations

- **Purpose**: Test service methods for add functionality.
- **Files**: Extend test files from WP01/WP02
- **Parallel?**: No - depends on T029, T030

**Test Cases for Ingredients** (`test_ingredient_hierarchy_service.py`):
```python
def test_add_leaf_ingredient_success(session, l1_ingredient):
    """Test adding L2 ingredient under L1 parent."""
    result = ingredient_hierarchy_service.add_leaf_ingredient(
        parent_id=l1_ingredient.id,
        name="New Leaf Ingredient",
        session=session
    )
    assert result.id is not None
    assert result.display_name == "New Leaf Ingredient"
    assert result.hierarchy_level == 2
    assert result.parent_ingredient_id == l1_ingredient.id

def test_add_leaf_ingredient_invalid_parent(session, l0_ingredient):
    """Test error when parent is not L1."""
    with pytest.raises(ValueError, match="Parent must be L1"):
        ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=l0_ingredient.id,
            name="Test",
            session=session
        )

def test_add_leaf_ingredient_duplicate_name(session, l1_ingredient, l2_ingredient):
    """Test error when name already exists under parent."""
    with pytest.raises(ValueError, match="already exists"):
        ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=l1_ingredient.id,
            name=l2_ingredient.display_name,
            session=session
        )

def test_add_leaf_ingredient_parent_not_found(session):
    """Test error when parent doesn't exist."""
    with pytest.raises(ValueError, match="not found"):
        ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=99999,
            name="Test",
            session=session
        )

def test_add_ingredient_empty_name_rejected(session, l1_ingredient):
    """Test that empty/whitespace-only names are rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        ingredient_hierarchy_service.add_leaf_ingredient(
            parent_id=l1_ingredient.id,
            name="   ",  # whitespace only
            session=session
        )

def test_add_ingredient_trims_whitespace(session, l1_ingredient):
    """Test that leading/trailing whitespace is trimmed."""
    result = ingredient_hierarchy_service.add_leaf_ingredient(
        parent_id=l1_ingredient.id,
        name="  New Ingredient  ",
        session=session
    )
    assert result.display_name == "New Ingredient"  # trimmed
```

**Test Cases for Materials** (`test_material_hierarchy_service.py`):
```python
def test_add_material_success(session, subcategory):
    """Test adding material under subcategory."""
    result = material_hierarchy_service.add_material(
        subcategory_id=subcategory.id,
        name="New Material",
        base_unit_type="each",
        session=session
    )
    assert result.id is not None
    assert result.name == "New Material"
    assert result.subcategory_id == subcategory.id

def test_add_material_invalid_unit_type(session, subcategory):
    """Test error for invalid unit type."""
    with pytest.raises(ValueError, match="Invalid unit type"):
        material_hierarchy_service.add_material(
            subcategory_id=subcategory.id,
            name="Test",
            base_unit_type="invalid",
            session=session
        )

def test_add_material_duplicate_name(session, subcategory, material):
    """Test error when name already exists in subcategory."""
    with pytest.raises(ValueError, match="already exists"):
        material_hierarchy_service.add_material(
            subcategory_id=subcategory.id,
            name=material.name,
            session=session
        )
```

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for `add_leaf_ingredient()` - all branches
- Unit tests for `add_material()` - all branches
- Run: `./run-tests.sh -k "add_" -v`

**Manual Testing**:
1. Open Hierarchy Admin, click Add
2. Select parent, enter name, save
3. Verify tree refreshes with new item
4. Verify new item appears in main tab

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slug collision | Append parent slug if global collision |
| Dialog focus issues | Use transient + grab_set |
| Validation bypass | Service validates regardless of UI |

## Definition of Done Checklist

- [ ] `add_leaf_ingredient()` method works correctly
- [ ] `add_material()` method works correctly
- [ ] Add dialog displays with parent selection
- [ ] Name validation prevents duplicates
- [ ] Slug auto-generated correctly
- [ ] Tree refreshes after add
- [ ] Unit tests pass with >70% coverage
- [ ] New items appear in main tabs and dropdowns

## Review Guidance

**Key checkpoints for reviewer**:
1. Click Add in Ingredients admin - add new L2
2. Click Add in Materials admin - add new material
3. Try duplicate name - verify error shown
4. Verify new item in tree after add
5. Check new item appears in Ingredients/Materials tab
6. Run service tests: `./run-tests.sh -k "add_" -v`

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T03:51:54Z – claude – lane=doing – Moved to doing
