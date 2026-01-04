---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Models Layer"
phase: "Phase 1 - Core Snapshot System"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "67067"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-04T21:45:00Z"
    lane: "doing"
    agent: "claude"
    shell_pid: "67067"
    action: "Started implementation"
---

# Work Package Prompt: WP01 - Models Layer

## Objectives & Success Criteria

Create the foundational database models for the Recipe Template & Snapshot system:

1. **RecipeSnapshot model** - Immutable capture of recipe state at production time
2. **Recipe model updates** - Add variant relationship and production readiness fields
3. **ProductionRun model updates** - Add FK to snapshot instead of recipe

**Success Criteria**:
- All models import without errors
- CHECK constraints prevent invalid data (self-referential variants blocked)
- Unit tests pass for new model functionality
- JSON serialization/deserialization works for snapshot data

## Context & Constraints

**Architecture**: Layered (Models -> Services -> UI). Models define schema only.

**Key References**:
- `kitty-specs/037-recipe-template-snapshot/data-model.md` - Entity definitions
- `kitty-specs/037-recipe-template-snapshot/spec.md` - FR-001 to FR-013
- `.kittify/memory/constitution.md` - Principle V (Layered Architecture)
- `CLAUDE.md` - Session management patterns

**Constraints**:
- SQLite with WAL mode (no native JSON type - use Text)
- SQLAlchemy 2.x patterns
- ON DELETE RESTRICT for recipe_id in RecipeSnapshot
- ON DELETE SET NULL for base_recipe_id in Recipe

## Subtasks & Detailed Guidance

### Subtask T001 - Create RecipeSnapshot Model [PARALLEL]

**Purpose**: Immutable record capturing recipe state at production time for historical accuracy.

**File**: `src/models/recipe_snapshot.py`

**Steps**:
1. Create new file with imports from sqlalchemy and .base
2. Define RecipeSnapshot class extending BaseModel
3. Add fields:
   - `recipe_id` - Integer FK to recipes.id, ON DELETE RESTRICT, nullable=False
   - `production_run_id` - Integer FK to production_runs.id, UNIQUE, nullable=False
   - `scale_factor` - Float, default=1.0, nullable=False
   - `snapshot_date` - DateTime, default=utc_now, nullable=False
   - `recipe_data` - Text (JSON string), nullable=False
   - `ingredients_data` - Text (JSON string), nullable=False
   - `is_backfilled` - Boolean, default=False, nullable=False
4. Add relationships:
   - `recipe` - relationship to Recipe
   - `production_run` - relationship to ProductionRun (1:1)
5. Add indexes on recipe_id, snapshot_date
6. Add `to_dict()` method with JSON parsing
7. Add `get_recipe_data()` and `get_ingredients_data()` helper methods

**Example Structure**:
```python
from sqlalchemy import Column, Integer, Float, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import BaseModel
from src.utils.datetime_utils import utc_now
import json

class RecipeSnapshot(BaseModel):
    __tablename__ = "recipe_snapshots"

    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    production_run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=False, unique=True)
    scale_factor = Column(Float, nullable=False, default=1.0)
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    recipe_data = Column(Text, nullable=False)  # JSON string
    ingredients_data = Column(Text, nullable=False)  # JSON string
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="snapshots")
    production_run = relationship("ProductionRun", back_populates="snapshot", uselist=False)

    __table_args__ = (
        Index("idx_snapshot_recipe", "recipe_id"),
        Index("idx_snapshot_date", "snapshot_date"),
    )

    def get_recipe_data(self) -> dict:
        return json.loads(self.recipe_data) if self.recipe_data else {}

    def get_ingredients_data(self) -> list:
        return json.loads(self.ingredients_data) if self.ingredients_data else []
```

---

### Subtask T002 - Add Variant and Readiness Fields to Recipe [PARALLEL]

**Purpose**: Enable recipe variants and production readiness filtering.

**File**: `src/models/recipe.py`

**Steps**:
1. Add new columns after existing fields:
   - `base_recipe_id` - Integer FK to recipes.id (self-ref), nullable=True, ON DELETE SET NULL
   - `variant_name` - String(100), nullable=True
   - `is_production_ready` - Boolean, default=False, nullable=False
2. Add CHECK constraint: `base_recipe_id != id`
3. Add relationships:
   - `base_recipe` - relationship to self (many-to-one)
   - `variants` - relationship to self (one-to-many)
   - `snapshots` - relationship to RecipeSnapshot (one-to-many)
4. Add index on is_production_ready

**Code to Add**:
```python
# After existing columns, add:
base_recipe_id = Column(
    Integer,
    ForeignKey("recipes.id", ondelete="SET NULL"),
    nullable=True,
    index=True
)
variant_name = Column(String(100), nullable=True)
is_production_ready = Column(Boolean, nullable=False, default=False, index=True)

# Add to relationships section:
base_recipe = relationship(
    "Recipe",
    remote_side="Recipe.id",
    foreign_keys=[base_recipe_id],
    backref="variants"
)
snapshots = relationship("RecipeSnapshot", back_populates="recipe")

# Add to __table_args__:
CheckConstraint("base_recipe_id IS NULL OR base_recipe_id != id", name="ck_recipe_no_self_variant"),
```

---

### Subtask T003 - Add Snapshot FK to ProductionRun [PARALLEL]

**Purpose**: Link production runs to snapshots instead of directly to recipes.

**File**: `src/models/production_run.py`

**Steps**:
1. Add new column (nullable initially for migration):
   - `recipe_snapshot_id` - Integer FK to recipe_snapshots.id, nullable=True
2. Add relationship to RecipeSnapshot (1:1)
3. Add index on recipe_snapshot_id
4. Keep existing recipe_id for now (will be deprecated after migration)

**Code to Add**:
```python
# Add after recipe_id:
recipe_snapshot_id = Column(
    Integer,
    ForeignKey("recipe_snapshots.id", ondelete="RESTRICT"),
    nullable=True,  # Nullable for migration; will be required after backfill
    index=True
)

# Add relationship:
snapshot = relationship("RecipeSnapshot", back_populates="production_run", uselist=False)
```

---

### Subtask T004 - Export RecipeSnapshot in __init__.py

**Purpose**: Make RecipeSnapshot available for import from models package.

**File**: `src/models/__init__.py`

**Steps**:
1. Add import: `from .recipe_snapshot import RecipeSnapshot`
2. Add to `__all__` list if present

---

### Subtask T005 - Create Unit Tests [PARALLEL]

**Purpose**: Verify model creation, constraints, and JSON handling.

**File**: `src/tests/models/test_recipe_snapshot_model.py`

**Tests to Write**:
1. `test_create_recipe_snapshot` - Basic creation with valid data
2. `test_snapshot_json_serialization` - Verify get_recipe_data() and get_ingredients_data()
3. `test_snapshot_immutability_pattern` - No update methods exist
4. `test_recipe_self_reference_blocked` - CHECK constraint prevents base_recipe_id = id
5. `test_recipe_variant_relationship` - Variant links to base correctly
6. `test_recipe_production_ready_default` - New recipes default to False
7. `test_snapshot_recipe_delete_blocked` - ON DELETE RESTRICT works

**Example Test**:
```python
def test_create_recipe_snapshot(test_session):
    recipe = Recipe(name="Test", category="Cookies", yield_quantity=36, yield_unit="cookies")
    test_session.add(recipe)
    test_session.flush()

    # Create production run first (snapshot needs it)
    # ... setup code ...

    snapshot = RecipeSnapshot(
        recipe_id=recipe.id,
        production_run_id=production_run.id,
        scale_factor=1.0,
        recipe_data='{"name": "Test", "yield_quantity": 36}',
        ingredients_data='[{"name": "Flour", "quantity": 2, "unit": "cups"}]'
    )
    test_session.add(snapshot)
    test_session.commit()

    assert snapshot.id is not None
    assert snapshot.get_recipe_data()["name"] == "Test"
    assert len(snapshot.get_ingredients_data()) == 1
```

## Test Strategy

- Run: `pytest src/tests/models/test_recipe_snapshot_model.py -v`
- All tests must pass before WP02 can start
- Coverage: Model creation, relationships, constraints, JSON helpers

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Self-referential FK complexity | Explicit CHECK constraint + test coverage |
| JSON in SQLite (no native type) | Use Text column with json.dumps/loads helpers |
| Circular import with ProductionRun | Use string references in relationships |

## Definition of Done Checklist

- [ ] RecipeSnapshot model created with all fields
- [ ] Recipe model updated with variant/readiness fields
- [ ] ProductionRun model updated with snapshot FK
- [ ] All models export from __init__.py
- [ ] Unit tests pass (all 7 test cases)
- [ ] No circular import errors

## Review Guidance

- Verify CHECK constraint syntax is SQLite-compatible
- Confirm ON DELETE behaviors match spec (RESTRICT for snapshot, SET NULL for variant)
- Check JSON helper methods handle None/empty cases

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
- 2026-01-04T21:45:00Z - claude - shell_pid=67067 - lane=doing - Started implementation
- 2026-01-04T22:00:00Z - claude - shell_pid=67067 - lane=doing - Completed T001: Created RecipeSnapshot model with JSON helpers
- 2026-01-04T22:00:00Z - claude - shell_pid=67067 - lane=doing - Completed T002: Added base_recipe_id, variant_name, is_production_ready to Recipe
- 2026-01-04T22:00:00Z - claude - shell_pid=67067 - lane=doing - Completed T003: Added recipe_snapshot_id FK to ProductionRun
- 2026-01-04T22:00:00Z - claude - shell_pid=67067 - lane=doing - Completed T004: Exported RecipeSnapshot in __init__.py
- 2026-01-04T22:00:00Z - claude - shell_pid=67067 - lane=doing - Completed T005: Created 15 unit tests (all passing)
- 2026-01-04T18:55:32Z – claude – shell_pid=67067 – lane=for_review – Ready for review - all 15 tests passing
