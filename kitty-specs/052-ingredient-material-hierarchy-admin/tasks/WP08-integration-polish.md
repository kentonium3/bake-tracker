---
work_package_id: "WP08"
subtasks:
  - "T052"
  - "T053"
  - "T054"
  - "T055"
  - "T056"
  - "T057"
title: "Integration & Polish"
phase: "Phase 5 - Polish"
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

# Work Package Prompt: WP08 – Integration & Polish

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

**Goal**: Integrate admin UI into application menu, verify all acceptance criteria, and perform final polish.

**Success Criteria**:
- Hierarchy Admin accessible from Catalog menu
- All acceptance criteria (SC-001 through SC-008) verified
- Historical recipe snapshots unchanged after admin operations
- Code clean and well-documented

**User Story Reference**: All User Stories (spec.md) - Final integration and verification

## Context & Constraints

**Constitution Principles**:
- II. User-Centric Design: UI must be intuitive
- V. Layered Architecture: Menu integration follows existing patterns

**Related Documents**:
- `kitty-specs/052-ingredient-material-hierarchy-admin/spec.md` - Acceptance criteria SC-001-SC-008
- `src/ui/main_window.py` - Menu structure to extend

**Existing Code**:
- `src/ui/main_window.py` - Main application window with menu
- `src/ui/hierarchy_admin_window.py` (from WP04-WP07) - Admin window to integrate
- `src/models/recipe_snapshot.py` - Historical data to verify unchanged

**Dependencies**: WP05, WP06, WP07 must be complete (all operations functional).

## Subtasks & Detailed Guidance

### Subtask T052 – Add "Hierarchy Admin" menu option in Catalog mode

- **Purpose**: Add menu entry point for admin UI.
- **Files**: Modify `src/ui/main_window.py` or relevant menu file
- **Parallel?**: No - foundation for T053, T054

**Implementation**:

First, locate where menus are defined in main_window.py. Then add:

```python
# Option 1: Add to existing Catalog menu
def _create_catalog_menu(self):
    """Create or extend Catalog menu."""
    catalog_menu = tk.Menu(self.menubar, tearoff=0)

    # ... existing menu items ...

    catalog_menu.add_separator()
    catalog_menu.add_command(
        label="Ingredient Hierarchy...",
        command=self._open_ingredient_admin
    )
    catalog_menu.add_command(
        label="Material Hierarchy...",
        command=self._open_material_admin
    )

    self.menubar.add_cascade(label="Catalog", menu=catalog_menu)

# Option 2: Add as submenu
def _create_admin_submenu(self, parent_menu):
    """Create Hierarchy Admin submenu."""
    admin_menu = tk.Menu(parent_menu, tearoff=0)
    admin_menu.add_command(
        label="Ingredients...",
        command=self._open_ingredient_admin
    )
    admin_menu.add_command(
        label="Materials...",
        command=self._open_material_admin
    )
    parent_menu.add_cascade(label="Hierarchy Admin", menu=admin_menu)
```

**Notes**:
- Follow existing menu patterns in the application
- Use ellipsis (...) convention for items that open dialogs
- Consider keyboard shortcuts if appropriate

### Subtask T053 – Wire menu to open Hierarchy Admin window for Ingredients

- **Purpose**: Implement menu callback for ingredients admin.
- **Files**: Modify `src/ui/main_window.py`
- **Parallel?**: No - depends on T052

**Implementation**:
```python
def _open_ingredient_admin(self):
    """Open Ingredient Hierarchy Admin window."""
    from src.ui.hierarchy_admin_window import HierarchyAdminWindow

    # Prevent multiple windows
    if hasattr(self, "_ingredient_admin_window") and self._ingredient_admin_window.winfo_exists():
        self._ingredient_admin_window.focus()
        self._ingredient_admin_window.lift()
        return

    def on_close():
        """Handle admin window close."""
        self._ingredient_admin_window = None
        # Optionally refresh main UI
        self._refresh_ingredients_tab()

    self._ingredient_admin_window = HierarchyAdminWindow(
        self,
        entity_type="ingredient",
        on_close=on_close
    )

def _refresh_ingredients_tab(self):
    """Refresh ingredients tab after admin changes."""
    # Find and refresh the ingredients tab if it exists
    if hasattr(self, "ingredients_tab"):
        self.ingredients_tab.refresh()
```

### Subtask T054 – Wire menu to open Hierarchy Admin window for Materials

- **Purpose**: Implement menu callback for materials admin.
- **Files**: Modify `src/ui/main_window.py`
- **Parallel?**: Yes - can develop parallel with T053

**Implementation**:
```python
def _open_material_admin(self):
    """Open Material Hierarchy Admin window."""
    from src.ui.hierarchy_admin_window import HierarchyAdminWindow

    # Prevent multiple windows
    if hasattr(self, "_material_admin_window") and self._material_admin_window.winfo_exists():
        self._material_admin_window.focus()
        self._material_admin_window.lift()
        return

    def on_close():
        """Handle admin window close."""
        self._material_admin_window = None
        # Optionally refresh main UI
        self._refresh_materials_tab()

    self._material_admin_window = HierarchyAdminWindow(
        self,
        entity_type="material",
        on_close=on_close
    )

def _refresh_materials_tab(self):
    """Refresh materials tab after admin changes."""
    # Find and refresh the materials tab if it exists
    if hasattr(self, "materials_tab"):
        self.materials_tab.refresh()
```

### Subtask T055 – Verify all acceptance criteria from spec (SC-001 through SC-008)

- **Purpose**: Systematic verification of all acceptance criteria.
- **Files**: No code changes - verification checklist
- **Parallel?**: Yes - can run parallel with T056, T057

**Verification Checklist**:

| Criterion | Description | How to Verify |
|-----------|-------------|---------------|
| SC-001 | Only L2 ingredients in Ingredients tab | Open Ingredients tab, confirm no L0/L1 items visible |
| SC-002 | Only materials in Materials tab | Open Materials tab, confirm no category/subcategory items |
| SC-003 | Hierarchy columns show parent context | Check L0, L1 columns in Ingredients; Category, Subcategory in Materials |
| SC-004 | Admin window shows tree structure | Open Hierarchy Admin, verify expandable tree |
| SC-005 | Add new L2 ingredient | Use Add, verify appears in tab and dropdowns |
| SC-006 | Rename propagates to Products/Recipes | Rename item, verify FK propagation (no manual updates needed) |
| SC-007 | Reparent moves item in hierarchy | Move item, verify new path displays correctly |
| SC-008 | Historical snapshots unchanged | Check RecipeSnapshot table after operations |

**Test Steps**:

1. **SC-001 Verification**:
   ```
   1. Launch application
   2. Navigate to Ingredients tab
   3. Verify each row is an L2 (leaf) ingredient
   4. Verify L0 and L1 columns show parent names
   ```

2. **SC-002 Verification**:
   ```
   1. Navigate to Materials tab
   2. Verify each row is a material (not category/subcategory)
   3. Verify Category and Subcategory columns show parent names
   ```

3. **SC-003 Verification**:
   ```
   1. Check Ingredients tab has columns: Category, Subcategory, Ingredient
   2. Check Materials tab has columns: Category, Subcategory, Material
   ```

4. **SC-004 Verification**:
   ```
   1. Open Catalog > Ingredient Hierarchy
   2. Verify tree shows L0 > L1 > L2 structure
   3. Expand/collapse nodes
   4. Open Catalog > Material Hierarchy
   5. Verify tree shows Category > Subcategory > Material structure
   ```

5. **SC-005 Verification**:
   ```
   1. Open Ingredient Hierarchy Admin
   2. Click Add New
   3. Select L1 parent, enter name, save
   4. Verify new item appears in tree
   5. Close admin, verify new item in Ingredients tab
   6. Check any ingredient dropdown (e.g., Recipe editor)
   ```

6. **SC-006 Verification**:
   ```
   1. Note a product that uses an ingredient (check Products tab)
   2. Rename the ingredient in Hierarchy Admin
   3. Check Products tab - verify new name shows automatically
   4. Check any recipe using the ingredient - verify new name
   ```

7. **SC-007 Verification**:
   ```
   1. Open Ingredient Hierarchy Admin
   2. Select an L2 ingredient
   3. Click Move to, select different L1 parent
   4. Verify item moves in tree
   5. Check detail panel shows new path
   6. Verify Ingredients tab shows new parent columns
   ```

8. **SC-008 Verification**:
   ```
   1. Create a recipe with known ingredients
   2. Save/produce the recipe (creates snapshot)
   3. Rename or reparent an ingredient
   4. Check historical recipe snapshot (via export or direct DB query)
   5. Verify snapshot still shows original ingredient names
   ```

### Subtask T056 – Verify historical recipe snapshots unchanged after operations

- **Purpose**: Ensure admin operations don't alter historical data.
- **Files**: No code changes - verification only
- **Parallel?**: Yes - can run parallel with T055, T057

**Background**: RecipeSnapshot stores denormalized ingredient names at the time of production. These should be immutable regardless of subsequent rename/reparent operations.

**Verification Steps**:

1. **Setup**:
   ```sql
   -- Check existing snapshots (via DB browser or export)
   SELECT * FROM recipe_snapshots LIMIT 5;
   -- Note specific ingredient names in snapshot_data
   ```

2. **Perform Admin Operations**:
   - Rename an ingredient that appears in a snapshot
   - Reparent an ingredient that appears in a snapshot

3. **Verify Unchanged**:
   ```sql
   -- Check same snapshots
   SELECT * FROM recipe_snapshots WHERE id IN (...);
   -- Verify snapshot_data contains original names (not renamed values)
   ```

4. **Why This Works**:
   - RecipeSnapshot stores JSON blob with names at snapshot time
   - Admin operations update Ingredient.display_name (live data)
   - Snapshots are immutable - never updated after creation
   - FK design ensures live displays show current names, historical displays show snapshot names

### Subtask T057 – Final code cleanup and docstrings

- **Purpose**: Polish code for maintainability.
- **Files**: All new files from WP01-WP07
- **Parallel?**: Yes - can run parallel with T055, T056

**Checklist**:

1. **Service Files**:
   - [ ] `src/services/ingredient_hierarchy_service.py` - docstrings complete
   - [ ] `src/services/material_hierarchy_service.py` - docstrings complete
   - [ ] `src/services/hierarchy_admin_service.py` - docstrings complete

2. **UI Files**:
   - [ ] `src/ui/hierarchy_admin_window.py` - docstrings complete
   - [ ] `src/ui/ingredients_tab.py` (modified) - changes documented
   - [ ] `src/ui/materials_tab.py` (modified) - changes documented

3. **Code Quality**:
   - [ ] Remove any debug print statements
   - [ ] Remove commented-out code
   - [ ] Consistent import ordering (stdlib, third-party, local)
   - [ ] Type hints on public methods
   - [ ] No unused imports

4. **Documentation**:
   - [ ] Each public method has docstring with Args, Returns, Raises
   - [ ] Complex logic has inline comments
   - [ ] Session management pattern followed consistently

**Docstring Template**:
```python
def method_name(self, arg1: Type, arg2: Type, session: Optional[Session] = None) -> ReturnType:
    """
    Brief description of what the method does.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        session: Optional SQLAlchemy session (pass for transactional atomicity)

    Returns:
        Description of return value

    Raises:
        ValueError: When invalid input provided
    """
```

## Test Strategy

**Verification Testing** (T055):
- Systematic walkthrough of all acceptance criteria
- Document results for each criterion

**Data Integrity Testing** (T056):
- Before/after comparison of RecipeSnapshot data
- Verify immutability of historical records

**Code Review** (T057):
- Run linters: `flake8 src/services/` and `flake8 src/ui/hierarchy_admin_window.py`
- Check type hints: `mypy src/services/`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Menu location not intuitive | Follow existing app menu patterns |
| Snapshot corruption | Verify before merge; snapshots are read-only by design |
| Missing docstrings | Systematic file-by-file review |

## Definition of Done Checklist

- [ ] Hierarchy Admin accessible from Catalog menu
- [ ] Ingredients admin opens via menu
- [ ] Materials admin opens via menu
- [ ] SC-001 verified (L2 only in Ingredients tab)
- [ ] SC-002 verified (materials only in Materials tab)
- [ ] SC-003 verified (hierarchy columns present)
- [ ] SC-004 verified (tree view in admin)
- [ ] SC-005 verified (add operation)
- [ ] SC-006 verified (rename propagation)
- [ ] SC-007 verified (reparent operation)
- [ ] SC-008 verified (historical snapshots unchanged)
- [ ] All new code has docstrings
- [ ] No debug code or commented-out code
- [ ] Linters pass

## Review Guidance

**Key checkpoints for reviewer**:
1. Access Hierarchy Admin from menu - verify menu works
2. Walk through all acceptance criteria systematically
3. Check historical snapshot data integrity
4. Review code for documentation completeness
5. Run full test suite: `./run-tests.sh -v`
6. Verify linters pass: `flake8 src/`

## Activity Log

- 2026-01-14T15:00:00Z – system – lane=planned – Prompt created.
- 2026-01-15T04:11:42Z – claude – lane=doing – Starting menu integration and final polish
- 2026-01-15T04:28:55Z – claude – lane=for_review – Menu integration and lint cleanup complete
- 2026-01-15T05:36:51Z – claude – lane=done – Review approved: Menu integration and aggregated usage counts fix
