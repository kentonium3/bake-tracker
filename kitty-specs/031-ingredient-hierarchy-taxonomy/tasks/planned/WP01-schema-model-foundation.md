---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
title: "Schema & Model Foundation"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-30T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Schema & Model Foundation

## Objectives & Success Criteria

**Goal**: Add hierarchy fields to the Ingredient model to support three-tier self-referential taxonomy.

**Success Criteria**:
- Ingredient model has `parent_ingredient_id` FK column (nullable, self-referential)
- Ingredient model has `hierarchy_level` column (integer, CHECK constraint 0/1/2, default=2)
- Self-referential relationship exists (children/parent backref)
- Database indexes created for tree traversal performance
- Existing `category` field retained but marked deprecated
- Database successfully recreated with new schema
- All existing ingredient data preserved (export → recreate → import)

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md` - Principle VI (Schema Change Strategy)
- Plan: `kitty-specs/031-ingredient-hierarchy-taxonomy/plan.md`
- Data Model: `kitty-specs/031-ingredient-hierarchy-taxonomy/data-model.md`
- Research: `kitty-specs/031-ingredient-hierarchy-taxonomy/research.md` - Decision D1

**Constraints**:
- Follow SQLAlchemy 2.x patterns
- Use session_scope pattern per CLAUDE.md
- Default all existing ingredients to hierarchy_level=2 (leaves)
- Retain `category` field for rollback safety (do not remove)

## Subtasks & Detailed Guidance

### Subtask T001 – Add parent_ingredient_id FK column
- **Purpose**: Enable self-referential parent-child relationship for hierarchy.
- **Steps**:
  1. Open `src/models/ingredient.py`
  2. Add column: `parent_ingredient_id = Column(Integer, ForeignKey('ingredients.id'), nullable=True)`
  3. Place after existing `slug` field for logical grouping
- **Files**: `src/models/ingredient.py`
- **Parallel?**: No (foundation change)
- **Notes**: Nullable to support root ingredients (level 0) which have no parent

### Subtask T002 – Add hierarchy_level column
- **Purpose**: Track position in hierarchy (0=root, 1=mid, 2=leaf).
- **Steps**:
  1. Add column: `hierarchy_level = Column(Integer, nullable=False, default=2)`
  2. Add CHECK constraint in __table_args__ or via Column constraint: `CheckConstraint('hierarchy_level IN (0, 1, 2)')`
  3. Default=2 ensures existing ingredients become leaves
- **Files**: `src/models/ingredient.py`
- **Parallel?**: No
- **Notes**: CHECK constraint provides database-level validation as defense-in-depth

### Subtask T003 – Add self-referential relationship
- **Purpose**: Enable SQLAlchemy navigation of parent/children.
- **Steps**:
  1. Add relationship with backref:
     ```python
     children = relationship(
         "Ingredient",
         backref=backref('parent', remote_side=[id]),
         lazy='dynamic'
     )
     ```
  2. Place after column definitions
- **Files**: `src/models/ingredient.py`
- **Parallel?**: No
- **Notes**: `lazy='dynamic'` allows filtering children without loading all; `remote_side` is required for self-referential

### Subtask T004 – Add database indexes
- **Purpose**: Optimize tree traversal queries.
- **Steps**:
  1. Add index on parent_ingredient_id: `Index('idx_ingredient_parent', 'parent_ingredient_id')`
  2. Add index on hierarchy_level: `Index('idx_ingredient_hierarchy_level', 'hierarchy_level')`
  3. Add to `__table_args__` tuple
- **Files**: `src/models/ingredient.py`
- **Parallel?**: No
- **Notes**: These indexes are critical for get_children() and get_root_ingredients() performance

### Subtask T005 – Update to_dict() for hierarchy fields
- **Purpose**: Include new fields in dictionary serialization.
- **Steps**:
  1. Find `to_dict()` method in Ingredient model
  2. Add to returned dict:
     - `'parent_ingredient_id': self.parent_ingredient_id`
     - `'hierarchy_level': self.hierarchy_level`
  3. Optionally add computed `'is_leaf': self.hierarchy_level == 2`
- **Files**: `src/models/ingredient.py`
- **Parallel?**: No
- **Notes**: Services return dicts, so this is required for hierarchy data to flow through

### Subtask T006 – Export/recreate database per Constitution VI
- **Purpose**: Apply schema changes via export → delete → recreate → import cycle.
- **Steps**:
  1. Export all data using existing export functionality: `python -m src.cli.export` or via UI
  2. Backup the export file
  3. Delete database file: `rm bake_tracker.db` (or dev/test database)
  4. Run application to recreate database with new schema
  5. Import data from backup
  6. Verify record counts match pre-export
- **Files**: Database file, export JSON
- **Parallel?**: No
- **Notes**: This is the constitution-compliant schema change strategy for desktop phase

## Test Strategy

- **Model Tests**:
  - Verify Ingredient can be created with hierarchy fields
  - Verify parent/children relationship navigates correctly
  - Verify default hierarchy_level=2 for new ingredients
  - Verify CHECK constraint rejects invalid levels (3, -1, etc.)

- **Commands**:
  ```bash
  pytest src/tests/models/test_ingredient.py -v
  ```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Export ALL data before schema change; verify counts after import |
| Import fails with new fields | Update import service to handle new nullable fields gracefully |
| Existing tests fail | Run full test suite after model changes; fix failures |

## Definition of Done Checklist

- [ ] T001: parent_ingredient_id column added
- [ ] T002: hierarchy_level column with CHECK constraint added
- [ ] T003: Self-referential relationship defined
- [ ] T004: Indexes created
- [ ] T005: to_dict() returns hierarchy fields
- [ ] T006: Database recreated with new schema; data preserved
- [ ] All existing tests pass
- [ ] Model can create ingredients at all three hierarchy levels

## Review Guidance

- Verify SQLAlchemy relationship uses correct `remote_side` syntax
- Verify CHECK constraint syntax is SQLite-compatible
- Verify export/import cycle preserved all records (count check)
- Verify `category` field is retained (not removed)

## Activity Log

- 2025-12-30T12:00:00Z – system – lane=planned – Prompt created.
