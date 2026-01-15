---
work_package_id: "WP07"
subtasks:
  - "T044"
  - "T045"
  - "T046"
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
title: "Reparent Operations"
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

# Work Package Prompt: WP07 – Reparent Operations

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

**Goal**: Implement reparent (move) functionality to move items between parents in the hierarchy.

**Success Criteria**:
- Reparent dialog shows valid target parents (excluding current parent and descendants)
- Cycle detection prevents invalid moves
- Name uniqueness validated in new location
- Tree refreshes with item in new position after move
- Hierarchy path displays correctly after move

**User Story Reference**: User Story 6 (spec.md) - "Reparent Ingredient or Material"

## Context & Constraints

**Constitution Principles**:
- V. Layered Architecture: UI calls services; services handle validation
- IV. Test-Driven Development: Service methods tested (>70% coverage)

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - User Story 6
- `kitty-specs/052-ingredient-material-hierarchy-admin/research.md` - RQ6 on cycle detection

**Existing Code**:
- `src/ui/hierarchy_admin_window.py` (from WP04) - Has button placeholder
- `src/services/ingredient_hierarchy_service.py` - To extend
- `src/services/material_hierarchy_service.py` - To extend
- `src/services/hierarchy_admin_service.py` (from WP03) - `validate_no_cycle()` method
- `src/models/ingredient.py` - Has `get_descendants()` method

**Dependencies**: WP04 must be complete (needs admin UI shell).

**Parallelization**: Can run in parallel with WP05 (Add) and WP06 (Rename).

## Subtasks & Detailed Guidance

### Subtask T044 – Add reparent_ingredient() to ingredient_hierarchy_service.py

- **Purpose**: Service method to move ingredient to new parent.
- **Files**: Extend `src/services/ingredient_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T045, T046 (materials)

**Implementation**:
```python
def reparent_ingredient(
    self,
    ingredient_id: int,
    new_parent_id: int,
    session: Optional[Session] = None
) -> Ingredient:
    """
    Move ingredient to new parent.

    Valid moves:
    - L2 can move to any L1
    - L1 can move to any L0

    Args:
        ingredient_id: ID of ingredient to move
        new_parent_id: ID of new parent ingredient

    Returns:
        Updated Ingredient object

    Raises:
        ValueError: If invalid move (wrong levels, cycle, duplicate name)
    """
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    def _impl(sess: Session) -> Ingredient:
        # Find ingredient
        ingredient = sess.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()

        if not ingredient:
            raise ValueError(f"Ingredient {ingredient_id} not found")

        # Find new parent
        new_parent = sess.query(Ingredient).filter(
            Ingredient.id == new_parent_id
        ).first()

        if not new_parent:
            raise ValueError(f"New parent ingredient {new_parent_id} not found")

        # Validate level compatibility
        if ingredient.hierarchy_level == 2:
            # L2 must move to L1
            if new_parent.hierarchy_level != 1:
                raise ValueError("L2 ingredients can only move to L1 parents")
        elif ingredient.hierarchy_level == 1:
            # L1 must move to L0
            if new_parent.hierarchy_level != 0:
                raise ValueError("L1 ingredients can only move to L0 parents")
        else:
            # L0 cannot be moved
            raise ValueError("L0 (root) ingredients cannot be reparented")

        # Check if already under this parent
        if ingredient.parent_ingredient_id == new_parent_id:
            raise ValueError("Item is already under this parent")

        # Validate no cycle (for L1 moving to L0, check descendants)
        if ingredient.hierarchy_level == 1:
            descendants = ingredient.get_descendants()
            if not hierarchy_admin_service.validate_no_cycle(descendants, new_parent):
                raise ValueError("Cannot move: would create circular reference")

        # Validate unique name in new location
        siblings = sess.query(Ingredient).filter(
            Ingredient.parent_ingredient_id == new_parent_id
        ).all()

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, ingredient.display_name, exclude_id=ingredient_id
        ):
            raise ValueError(f"An ingredient named '{ingredient.display_name}' already exists under the new parent")

        # Perform move
        ingredient.parent_ingredient_id = new_parent_id

        sess.flush()
        return ingredient

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T045 – Add reparent_material() to material_hierarchy_service.py

- **Purpose**: Service method to move material to new subcategory.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T044, T046

**Implementation**:
```python
def reparent_material(
    self,
    material_id: int,
    new_subcategory_id: int,
    session: Optional[Session] = None
) -> Material:
    """
    Move material to new subcategory.

    Args:
        material_id: ID of material to move
        new_subcategory_id: ID of new subcategory

    Returns:
        Updated Material object

    Raises:
        ValueError: If material/subcategory not found or duplicate name
    """
    from src.models.material_subcategory import MaterialSubcategory
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    def _impl(sess: Session) -> Material:
        # Find material
        material = sess.query(Material).filter(
            Material.id == material_id
        ).first()

        if not material:
            raise ValueError(f"Material {material_id} not found")

        # Find new subcategory
        new_subcategory = sess.query(MaterialSubcategory).filter(
            MaterialSubcategory.id == new_subcategory_id
        ).first()

        if not new_subcategory:
            raise ValueError(f"Subcategory {new_subcategory_id} not found")

        # Check if already under this subcategory
        if material.subcategory_id == new_subcategory_id:
            raise ValueError("Material is already under this subcategory")

        # Validate unique name in new location
        siblings = sess.query(Material).filter(
            Material.subcategory_id == new_subcategory_id
        ).all()

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, material.name, exclude_id=material_id
        ):
            raise ValueError(f"A material named '{material.name}' already exists in the new subcategory")

        # Perform move
        material.subcategory_id = new_subcategory_id

        sess.flush()
        return material

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T046 – Add reparent_subcategory() to material_hierarchy_service.py

- **Purpose**: Service method to move subcategory to new category.
- **Files**: Extend `src/services/material_hierarchy_service.py`
- **Parallel?**: Yes - can develop parallel with T044, T045

**Implementation**:
```python
def reparent_subcategory(
    self,
    subcategory_id: int,
    new_category_id: int,
    session: Optional[Session] = None
):
    """
    Move subcategory to new category.

    Args:
        subcategory_id: ID of subcategory to move
        new_category_id: ID of new category

    Returns:
        Updated MaterialSubcategory object

    Raises:
        ValueError: If subcategory/category not found or duplicate name
    """
    from src.models.material_category import MaterialCategory
    from src.models.material_subcategory import MaterialSubcategory
    from src.services.hierarchy_admin_service import hierarchy_admin_service

    def _impl(sess: Session):
        # Find subcategory
        subcategory = sess.query(MaterialSubcategory).filter(
            MaterialSubcategory.id == subcategory_id
        ).first()

        if not subcategory:
            raise ValueError(f"Subcategory {subcategory_id} not found")

        # Find new category
        new_category = sess.query(MaterialCategory).filter(
            MaterialCategory.id == new_category_id
        ).first()

        if not new_category:
            raise ValueError(f"Category {new_category_id} not found")

        # Check if already under this category
        if subcategory.category_id == new_category_id:
            raise ValueError("Subcategory is already under this category")

        # Validate unique name in new location
        siblings = sess.query(MaterialSubcategory).filter(
            MaterialSubcategory.category_id == new_category_id
        ).all()

        if not hierarchy_admin_service.validate_unique_sibling_name(
            siblings, subcategory.name, exclude_id=subcategory_id
        ):
            raise ValueError(f"A subcategory named '{subcategory.name}' already exists in the new category")

        # Perform move
        subcategory.category_id = new_category_id

        sess.flush()
        return subcategory

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        result = _impl(sess)
        sess.commit()
        return result
```

### Subtask T047 – Create reparent dialog in hierarchy_admin_window.py

- **Purpose**: Modal dialog for moving items.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T044-T046

**Implementation**:
```python
class ReparentDialog(ctk.CTkToplevel):
    """Dialog for moving an item to a new parent."""

    def __init__(
        self,
        parent,
        item_name: str,
        current_parent_name: str,
        valid_parents: list,
        on_save: Callable
    ):
        super().__init__(parent)

        self.on_save = on_save
        self.result = None

        # Window setup
        self.title("Move Item")
        self.geometry("450x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Build form
        self._create_form(item_name, current_parent_name, valid_parents)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_form(self, item_name: str, current_parent_name: str, valid_parents: list):
        """Create the reparent form."""
        # Item being moved
        item_frame = ctk.CTkFrame(self)
        item_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(item_frame, text="Moving:").pack(anchor="w")
        ctk.CTkLabel(
            item_frame,
            text=item_name,
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w")

        # Current parent
        current_frame = ctk.CTkFrame(self)
        current_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(current_frame, text="Current Parent:").pack(anchor="w")
        ctk.CTkLabel(current_frame, text=current_parent_name).pack(anchor="w")

        # New parent selection
        new_frame = ctk.CTkFrame(self)
        new_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(new_frame, text="Move to:").pack(anchor="w")

        self.parent_var = ctk.StringVar()
        self.parent_dropdown = ctk.CTkComboBox(
            new_frame,
            values=[p["display"] for p in valid_parents],
            variable=self.parent_var,
            state="readonly",
            width=350
        )
        self.parent_dropdown.pack(fill="x", pady=5)

        # Store mapping
        self._parent_map = {p["display"]: p["id"] for p in valid_parents}

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
            text="Move",
            command=self._on_save
        ).pack(side="right", padx=5)

    def _on_save(self):
        """Handle save button click."""
        parent_display = self.parent_var.get()

        if not parent_display:
            self.error_label.configure(text="Please select a new parent")
            return

        new_parent_id = self._parent_map.get(parent_display)
        if not new_parent_id:
            self.error_label.configure(text="Invalid selection")
            return

        self.result = new_parent_id

        try:
            self.on_save(new_parent_id)
            self.destroy()
        except ValueError as e:
            self.error_label.configure(text=str(e))
```

### Subtask T048 – Implement new parent dropdown (filtered to valid targets)

- **Purpose**: Show only valid parent options (excluding current and descendants).
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - part of T047

**Implementation**:
```python
# Add to HierarchyAdminWindow class:

def _get_valid_reparent_targets(self, node: dict) -> list:
    """Get valid parent targets for reparent operation."""
    if self.entity_type == "ingredient":
        return self._get_valid_ingredient_parents(node)
    else:
        return self._get_valid_material_parents(node)

def _get_valid_ingredient_parents(self, node: dict) -> list:
    """Get valid parent targets for ingredient reparent."""
    ingredient = node.get("ingredient")
    if not ingredient:
        return []

    level = node.get("level", 0)
    tree = self.hierarchy_service.get_hierarchy_tree()

    # Get descendants to exclude
    descendants_ids = set()
    if hasattr(ingredient, "get_descendants"):
        descendants_ids = {d.id for d in ingredient.get_descendants()}

    options = []

    if level == 2:
        # L2 can move to any L1 (except current parent)
        for l0 in tree:
            for l1 in l0.get("children", []):
                if l1["id"] == ingredient.parent_ingredient_id:
                    continue  # Skip current parent
                options.append({
                    "id": l1["id"],
                    "display": f"{l0['name']} > {l1['name']}"
                })

    elif level == 1:
        # L1 can move to any L0 (except current parent)
        for l0 in tree:
            if l0["id"] == ingredient.parent_ingredient_id:
                continue  # Skip current parent
            if l0["id"] in descendants_ids:
                continue  # Skip descendants (cycle prevention)
            options.append({
                "id": l0["id"],
                "display": l0["name"]
            })

    return options

def _get_valid_material_parents(self, node: dict) -> list:
    """Get valid parent targets for material reparent."""
    item_type = node.get("type")
    tree = self.hierarchy_service.get_hierarchy_tree()

    options = []

    if item_type == "material":
        # Material can move to any subcategory (except current)
        material = node.get("material")
        current_subcat_id = material.subcategory_id if material else None

        for cat in tree:
            for subcat in cat.get("children", []):
                if subcat["id"] == current_subcat_id:
                    continue
                options.append({
                    "id": subcat["id"],
                    "display": f"{cat['name']} > {subcat['name']}"
                })

    elif item_type == "subcategory":
        # Subcategory can move to any category (except current)
        subcategory = node.get("subcategory")
        current_cat_id = subcategory.category_id if subcategory else None

        for cat in tree:
            if cat["id"] == current_cat_id:
                continue
            options.append({
                "id": cat["id"],
                "display": cat["name"]
            })

    # Categories cannot be reparented (no parent)

    return options
```

### Subtask T049 – Implement cycle detection validation

- **Purpose**: Prevent moves that would create circular references.
- **Files**: Already implemented in T044 (uses `validate_no_cycle`)
- **Parallel?**: N/A - integrated into service method

*For ingredients:*
- `reparent_ingredient()` calls `ingredient.get_descendants()`
- Then calls `hierarchy_admin_service.validate_no_cycle(descendants, new_parent)`
- Raises error if cycle would be created

*For materials:*
- Fixed 3-level structure (Category → Subcategory → Material) prevents cycles by design
- No cycle detection needed

### Subtask T050 – Refresh tree after reparent (item moves in tree)

- **Purpose**: Update tree to show item in new location.
- **Files**: Extend `src/ui/hierarchy_admin_window.py`
- **Parallel?**: No - depends on T047

**Implementation**:
```python
# Update _on_reparent_click in HierarchyAdminWindow:

def _on_reparent_click(self):
    """Handle reparent button click - open reparent dialog."""
    if not self.selected_item:
        return

    node = self.selected_item

    # Check if item can be reparented
    if self.entity_type == "ingredient":
        level = node.get("level", 0)
        if level == 0:
            from tkinter import messagebox
            messagebox.showwarning("Cannot Move", "Root categories (L0) cannot be moved.")
            return
    else:
        item_type = node.get("type")
        if item_type == "category":
            from tkinter import messagebox
            messagebox.showwarning("Cannot Move", "Top-level categories cannot be moved.")
            return

    valid_parents = self._get_valid_reparent_targets(node)

    if not valid_parents:
        from tkinter import messagebox
        messagebox.showinfo("No Valid Targets", "No valid parent locations available for this item.")
        return

    # Get current parent name
    if self.entity_type == "ingredient":
        ing = node.get("ingredient")
        current_parent_name = ing.parent.display_name if ing and ing.parent else "None"
    else:
        item_type = node.get("type")
        if item_type == "material":
            mat = node.get("material")
            current_parent_name = mat.subcategory.name if mat and mat.subcategory else "None"
        elif item_type == "subcategory":
            subcat = node.get("subcategory")
            current_parent_name = subcat.category.name if subcat and subcat.category else "None"
        else:
            current_parent_name = "None"

    def on_save(new_parent_id: int):
        """Callback when dialog saves."""
        try:
            if self.entity_type == "ingredient":
                self.hierarchy_service.reparent_ingredient(
                    ingredient_id=node["id"],
                    new_parent_id=new_parent_id
                )
            else:
                item_type = node.get("type")
                if item_type == "material":
                    self.hierarchy_service.reparent_material(
                        material_id=node["id"],
                        new_subcategory_id=new_parent_id
                    )
                elif item_type == "subcategory":
                    self.hierarchy_service.reparent_subcategory(
                        subcategory_id=node["id"],
                        new_category_id=new_parent_id
                    )

            # Refresh tree
            self._load_tree()

            # Clear selection (tree was rebuilt)
            self._clear_detail_panel()

            # Show success
            from tkinter import messagebox
            messagebox.showinfo("Success", "Item moved successfully!")

        except ValueError as e:
            raise  # Re-raise for dialog to display

    ReparentDialog(
        self,
        item_name=node.get("name", "Unknown"),
        current_parent_name=current_parent_name,
        valid_parents=valid_parents,
        on_save=on_save
    )

# Enable the reparent button in _create_action_buttons:
self.reparent_btn = ctk.CTkButton(
    self.actions_frame,
    text="Move to...",
    command=self._on_reparent_click,
    state="normal"  # Now enabled
)
```

### Subtask T051 – Add tests for reparent operations including cycle detection

- **Purpose**: Test service methods for reparent functionality.
- **Files**: Extend test files
- **Parallel?**: No - depends on T044-T046

**Test Cases for Ingredients** (`test_ingredient_hierarchy_service.py`):
```python
def test_reparent_l2_to_different_l1(session, l1_ingredient, l2_ingredient, another_l1):
    """Test moving L2 ingredient to different L1 parent."""
    original_parent = l2_ingredient.parent_ingredient_id

    result = ingredient_hierarchy_service.reparent_ingredient(
        ingredient_id=l2_ingredient.id,
        new_parent_id=another_l1.id,
        session=session
    )

    assert result.parent_ingredient_id == another_l1.id
    assert result.parent_ingredient_id != original_parent

def test_reparent_l1_to_different_l0(session, l0_ingredient, l1_ingredient, another_l0):
    """Test moving L1 ingredient to different L0 parent."""
    result = ingredient_hierarchy_service.reparent_ingredient(
        ingredient_id=l1_ingredient.id,
        new_parent_id=another_l0.id,
        session=session
    )

    assert result.parent_ingredient_id == another_l0.id

def test_reparent_l0_fails(session, l0_ingredient, another_l0):
    """Test that L0 cannot be reparented."""
    with pytest.raises(ValueError, match="L0.*cannot be reparented"):
        ingredient_hierarchy_service.reparent_ingredient(
            ingredient_id=l0_ingredient.id,
            new_parent_id=another_l0.id,
            session=session
        )

def test_reparent_to_wrong_level_fails(session, l0_ingredient, l2_ingredient):
    """Test that L2 cannot move to L0."""
    with pytest.raises(ValueError, match="L2 ingredients can only move to L1"):
        ingredient_hierarchy_service.reparent_ingredient(
            ingredient_id=l2_ingredient.id,
            new_parent_id=l0_ingredient.id,
            session=session
        )

def test_reparent_to_same_parent_fails(session, l1_ingredient, l2_ingredient):
    """Test that moving to same parent fails."""
    with pytest.raises(ValueError, match="already under this parent"):
        ingredient_hierarchy_service.reparent_ingredient(
            ingredient_id=l2_ingredient.id,
            new_parent_id=l1_ingredient.id,  # Already the parent
            session=session
        )

def test_reparent_duplicate_name_fails(session, l1_ingredient, l2_ingredient, another_l1):
    """Test that duplicate name in new location fails."""
    # Create ingredient with same name under target parent
    duplicate = Ingredient(
        display_name=l2_ingredient.display_name,
        slug=f"dup-{l2_ingredient.slug}",
        parent_ingredient_id=another_l1.id,
        hierarchy_level=2
    )
    session.add(duplicate)
    session.flush()

    with pytest.raises(ValueError, match="already exists"):
        ingredient_hierarchy_service.reparent_ingredient(
            ingredient_id=l2_ingredient.id,
            new_parent_id=another_l1.id,
            session=session
        )

def test_reparent_last_l2_leaves_l1_empty(session, l1_ingredient, l2_ingredient, another_l1):
    """Test that reparenting the only L2 under an L1 leaves L1 empty (valid operation)."""
    # Verify l1 has only one child
    children = session.query(Ingredient).filter(
        Ingredient.parent_ingredient_id == l1_ingredient.id
    ).all()
    assert len(children) == 1

    # Reparent to another L1
    result = ingredient_hierarchy_service.reparent_ingredient(
        ingredient_id=l2_ingredient.id,
        new_parent_id=another_l1.id,
        session=session
    )

    # Original L1 should now have no children (empty but valid)
    children_after = session.query(Ingredient).filter(
        Ingredient.parent_ingredient_id == l1_ingredient.id
    ).all()
    assert len(children_after) == 0
```

**Test Cases for Materials** (`test_material_hierarchy_service.py`):
```python
def test_reparent_material_success(session, material, another_subcategory):
    """Test moving material to different subcategory."""
    result = material_hierarchy_service.reparent_material(
        material_id=material.id,
        new_subcategory_id=another_subcategory.id,
        session=session
    )

    assert result.subcategory_id == another_subcategory.id

def test_reparent_subcategory_success(session, subcategory, another_category):
    """Test moving subcategory to different category."""
    result = material_hierarchy_service.reparent_subcategory(
        subcategory_id=subcategory.id,
        new_category_id=another_category.id,
        session=session
    )

    assert result.category_id == another_category.id

def test_reparent_material_to_same_subcategory_fails(session, material):
    """Test that moving to same subcategory fails."""
    with pytest.raises(ValueError, match="already under"):
        material_hierarchy_service.reparent_material(
            material_id=material.id,
            new_subcategory_id=material.subcategory_id,
            session=session
        )
```

## Test Strategy

**Required Tests** (per constitution >70% coverage):
- Unit tests for `reparent_ingredient()` - all branches
- Unit tests for `reparent_material()` - all branches
- Unit tests for `reparent_subcategory()` - all branches
- Run: `./run-tests.sh -k "reparent" -v`

**Manual Testing**:
1. Select L2 ingredient, click Move, select different L1
2. Select material, click Move, select different subcategory
3. Try invalid moves - verify error messages
4. Verify tree shows item in new location

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cycle creation (ingredients) | Use `validate_no_cycle()` with `get_descendants()` |
| Name conflict in new location | Validate uniqueness before move |
| UI confusion about valid targets | Filter dropdown to show only valid options |

## Definition of Done Checklist

- [ ] `reparent_ingredient()` method handles L2→L1 and L1→L0 moves
- [ ] `reparent_material()` method works correctly
- [ ] `reparent_subcategory()` method works correctly
- [ ] Cycle detection prevents invalid ingredient moves
- [ ] Name validation prevents duplicates in new location
- [ ] Dialog shows only valid target parents
- [ ] Tree refreshes with item in new position
- [ ] Unit tests pass with >70% coverage

## Review Guidance

**Key checkpoints for reviewer**:
1. Move L2 ingredient to different L1 - verify tree updates
2. Move L1 ingredient to different L0 - verify tree updates
3. Try to move L0 - verify error
4. Move material to different subcategory - verify tree updates
5. Move subcategory to different category - verify tree updates
6. Try duplicate name scenario - verify error
7. Run service tests: `./run-tests.sh -k "reparent" -v`

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T04:03:18Z – claude – lane=doing – Moved to doing
- 2026-01-15T04:28:44Z – claude – lane=for_review – Reparent operations complete with 21 tests
- 2026-01-15T05:36:46Z – claude – lane=done – Review approved: Reparent operations with level validation and 21 tests
