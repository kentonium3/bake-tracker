---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Schema & Model"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "98384"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Schema & Model

## Objectives & Success Criteria

- Create `RecipeComponent` model class in `src/models/recipe.py`
- Add all database constraints (positive quantity, no self-reference, unique combination)
- Add indexes for query performance
- Add bidirectional relationships to Recipe model
- Export model from `src/models/__init__.py`
- Verify schema auto-creates correctly

**Definition of Done**: RecipeComponent can be instantiated, saved to database, and all constraints enforce correctly.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/data-model.md` - Entity design and constraints
- `kitty-specs/012-nested-recipes/research.md` - Pattern decisions
- `src/models/recipe.py` - Existing RecipeIngredient pattern to follow
- `src/models/composition.py` - Constraint pattern reference

**Architecture Constraints**:
- Follow existing RecipeIngredient junction table pattern
- Use SQLAlchemy 2.x syntax
- CASCADE on parent recipe delete, RESTRICT on component recipe delete
- Float type for quantity (supports 0.5, 1.0, 2.0 batch multipliers)

## Subtasks & Detailed Guidance

### Subtask T001 – Create RecipeComponent class

**Purpose**: Define the junction table model linking parent recipe to child recipe.

**Steps**:
1. Open `src/models/recipe.py`
2. Add new class `RecipeComponent(BaseModel)` after the `RecipeIngredient` class
3. Define `__tablename__ = "recipe_components"`
4. Add columns:
   - `recipe_id`: Integer FK to recipes.id, nullable=False
   - `component_recipe_id`: Integer FK to recipes.id, nullable=False
   - `quantity`: Float, nullable=False, default=1.0
   - `notes`: String(500), nullable=True
   - `sort_order`: Integer, nullable=False, default=0

**Files**: `src/models/recipe.py`

**Reference Code Pattern** (from RecipeIngredient):
```python
class RecipeComponent(BaseModel):
    """Junction table linking parent recipes to child (component) recipes."""

    __tablename__ = "recipe_components"

    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    component_recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    notes = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
```

---

### Subtask T002 – Add database constraints

**Purpose**: Enforce data integrity at database level.

**Steps**:
1. Add CheckConstraint for `quantity > 0`
2. Add CheckConstraint for `recipe_id != component_recipe_id` (no self-reference)
3. Add UniqueConstraint for `(recipe_id, component_recipe_id)` (no duplicate components)

**Files**: `src/models/recipe.py`

**Code**:
```python
__table_args__ = (
    CheckConstraint("quantity > 0", name="ck_recipe_component_quantity_positive"),
    CheckConstraint("recipe_id != component_recipe_id", name="ck_recipe_component_no_self_reference"),
    UniqueConstraint("recipe_id", "component_recipe_id", name="uq_recipe_component_recipe_component"),
    # Indexes added in T003
)
```

---

### Subtask T003 – Add indexes

**Purpose**: Optimize query performance for common lookups.

**Steps**:
1. Add index on `recipe_id` (lookup components of a recipe)
2. Add index on `component_recipe_id` (lookup recipes using a component)
3. Add composite index on `(recipe_id, sort_order)` (ordered retrieval)

**Files**: `src/models/recipe.py`

**Code** (add to `__table_args__`):
```python
__table_args__ = (
    # Constraints from T002...
    Index("idx_recipe_component_recipe", "recipe_id"),
    Index("idx_recipe_component_component", "component_recipe_id"),
    Index("idx_recipe_component_sort", "recipe_id", "sort_order"),
)
```

---

### Subtask T004 – Add recipe_components relationship to Recipe

**Purpose**: Enable Recipe to access its sub-recipes (children).

**Steps**:
1. In `Recipe` class, add `recipe_components` relationship
2. Use `foreign_keys` parameter to specify which FK to use
3. Add `cascade="all, delete-orphan"` for cleanup on recipe deletion

**Files**: `src/models/recipe.py`

**Code**:
```python
# In Recipe class, after existing relationships
recipe_components = relationship(
    "RecipeComponent",
    foreign_keys="RecipeComponent.recipe_id",
    back_populates="recipe",
    cascade="all, delete-orphan",
    lazy="joined",
)
```

---

### Subtask T005 – Add used_in_recipes relationship to Recipe

**Purpose**: Enable Recipe to see which recipes use it as a component (parents).

**Steps**:
1. In `Recipe` class, add `used_in_recipes` relationship
2. Use `foreign_keys` parameter pointing to `component_recipe_id`
3. No cascade (component side doesn't own the relationship)

**Files**: `src/models/recipe.py`

**Code**:
```python
# In Recipe class
used_in_recipes = relationship(
    "RecipeComponent",
    foreign_keys="RecipeComponent.component_recipe_id",
    back_populates="component_recipe",
    lazy="select",  # Only load when accessed
)
```

Also add relationships on RecipeComponent side:
```python
# In RecipeComponent class
recipe = relationship("Recipe", foreign_keys=[recipe_id], back_populates="recipe_components", lazy="joined")
component_recipe = relationship("Recipe", foreign_keys=[component_recipe_id], back_populates="used_in_recipes", lazy="joined")
```

---

### Subtask T006 – Export RecipeComponent from __init__.py

**Purpose**: Make model available for import throughout codebase.

**Steps**:
1. Open `src/models/__init__.py`
2. Add `RecipeComponent` to import from recipe module
3. Add to `__all__` list

**Files**: `src/models/__init__.py`

**Code**:
```python
from .recipe import Recipe, RecipeIngredient, RecipeComponent

__all__ = [
    # ... existing exports ...
    "RecipeComponent",
]
```

---

### Subtask T007 – Verify schema auto-creates correctly

**Purpose**: Confirm model definition creates valid database schema.

**Steps**:
1. Run the application briefly or execute a test that triggers schema creation
2. Verify `recipe_components` table exists with correct columns
3. Verify constraints are in place (try inserting invalid data)
4. Check indexes exist

**Verification Commands**:
```bash
# Run a simple test or the app
python -m pytest src/tests -v -k "test_" --maxfail=1

# Or check schema directly with sqlite3
sqlite3 data/baking.db ".schema recipe_components"
```

**Expected Schema**:
```sql
CREATE TABLE recipe_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    component_recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT,
    quantity REAL NOT NULL DEFAULT 1.0,
    notes VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT ck_recipe_component_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_recipe_component_no_self_reference CHECK (recipe_id != component_recipe_id),
    CONSTRAINT uq_recipe_component_recipe_component UNIQUE (recipe_id, component_recipe_id)
);
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import with Recipe | Define RecipeComponent in same file after Recipe |
| Constraint name conflicts | Use unique `ck_recipe_component_` prefix |
| Schema migration issues | This is new table, no migration needed |

## Definition of Done Checklist

- [ ] RecipeComponent class defined with all columns
- [ ] All three constraints in place
- [ ] All three indexes created
- [ ] Recipe.recipe_components relationship works
- [ ] Recipe.used_in_recipes relationship works
- [ ] RecipeComponent exported from __init__.py
- [ ] Schema creates without errors
- [ ] Existing tests still pass

## Review Guidance

- Verify FK ondelete behaviors: CASCADE for recipe_id, RESTRICT for component_recipe_id
- Check relationship lazy loading strategies are appropriate
- Confirm constraint names are unique and descriptive
- Test constraint enforcement by attempting invalid inserts

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-09T13:20:03Z – claude – shell_pid=87946 – lane=doing – Started implementation
- 2025-12-09T13:24:23Z – claude – shell_pid=88670 – lane=for_review – Completed implementation - all tests pass
- 2025-12-09T17:46:47Z – claude-reviewer – shell_pid=98384 – lane=done – Code review: APPROVED - All criteria met
