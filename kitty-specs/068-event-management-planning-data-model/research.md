# Research: Event Management & Planning Data Model

**Feature**: 068-event-management-planning-data-model
**Date**: 2026-01-26
**Status**: Complete

## Research Questions

### RQ1: What existing Event infrastructure exists?

**Finding**: Comprehensive Event model and service already implemented.

**Evidence**:
- `src/models/event.py` (503 lines): Event, EventRecipientPackage, EventProductionTarget, EventAssemblyTarget models
- `src/services/event_service.py` (1900+ lines): Full CRUD, shopping list generation, event cloning

**Key observations**:
- Event model has: `name`, `event_date`, `year`, `notes`, `output_mode`, timestamps
- Event model LACKS: `expected_attendees`, `plan_state` (needed for F068)
- EventService follows session management pattern (session passed to methods)
- Relationships to ProductionRun, AssemblyRun, PlanningSnapshot already exist

**Decision**: Extend existing Event model rather than create new one.

---

### RQ2: What is the existing PlanningSnapshot structure?

**Finding**: PlanningSnapshot exists but with different purpose than F068 spec.

**Evidence** (`src/models/planning_snapshot.py`):
```python
class PlanningSnapshot(BaseModel):
    __tablename__ = "planning_snapshots"
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)
    # Relationships to FinishedUnitSnapshot, MaterialUnitSnapshot, FinishedGoodSnapshot
```

**Gap**: F068 spec requires `snapshot_type` (ORIGINAL/CURRENT) and `snapshot_data` (JSON) fields for Phase 3 plan comparison.

**Decision**: Add `snapshot_type` field to existing PlanningSnapshot model. `snapshot_data` JSON field can be added but may remain unused until Phase 3.

---

### RQ3: What SQLAlchemy model patterns should new models follow?

**Finding**: Established patterns in existing models.

**Pattern from `src/models/recipe.py`**:
```python
class Recipe(BaseModel):
    __tablename__ = "recipes"

    # Columns with types, nullable, index
    name = Column(String(200), nullable=False, index=True)

    # Foreign keys with ondelete behavior
    base_recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)

    # Relationships with back_populates, cascade, lazy
    recipe_ingredients = relationship("RecipeIngredient", back_populates="recipe",
                                       cascade="all, delete-orphan", lazy="joined")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_recipe_name", "name"),
        CheckConstraint("base_recipe_id IS NULL OR base_recipe_id != id", name="ck_recipe_no_self_variant"),
    )
```

**Pattern from junction tables** (`EventProductionTarget`):
```python
class EventProductionTarget(BaseModel):
    __tablename__ = "event_production_targets"

    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_batches = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe_target"),
        CheckConstraint("target_batches > 0", name="ck_target_batches_positive"),
    )
```

**Decision**: Follow these exact patterns for new planning models.

---

### RQ4: What UI patterns exist for CRUD operations?

**Finding**: Established dialog and tab patterns.

**Tab pattern** (from `src/ui/recipes_tab.py`):
- Inherits from `ctk.CTkFrame`
- Contains list view (DataTable widget or CTkScrollableFrame)
- Action buttons (Create, Edit, Delete)
- Status bar for feedback
- Refresh method for list updates

**Dialog pattern** (from `src/ui/forms/recipe_form.py`):
- Inherits from `ctk.CTkToplevel`
- Form fields with validation
- Save/Cancel buttons
- Calls service layer on save
- Returns result via callback

**Decision**: Follow existing patterns for Planning tab and event dialogs.

---

### RQ5: What enums exist and how are they defined?

**Finding**: Enums defined inline in model files.

**Pattern from `src/models/event.py`**:
```python
class FulfillmentStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    DELIVERED = "delivered"

class OutputMode(str, Enum):
    BULK_COUNT = "bulk_count"
    BUNDLED = "bundled"
```

**Decision**: Define `PlanState` enum in `event.py`:
```python
class PlanState(str, Enum):
    DRAFT = "draft"
    LOCKED = "locked"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
```

---

### RQ6: How does import/export handle new tables?

**Finding**: Import/export service uses explicit table lists.

**Evidence** (from `src/services/import_export_service.py`):
- Tables listed explicitly in export/import order
- Foreign key dependencies determine order
- New tables need to be added to both export and import sequences

**Decision**: Add new planning tables to import/export service in correct dependency order:
1. events (already exists)
2. event_recipes (after events, recipes)
3. event_finished_goods (after events, finished_goods)
4. batch_decisions (after events, recipes, recipe_yield_options)
5. plan_amendments (after events)

---

## Research Summary

| Topic | Status | Decision |
|-------|--------|----------|
| Existing Event infrastructure | Researched | Extend, don't replace |
| PlanningSnapshot structure | Researched | Add snapshot_type field |
| SQLAlchemy patterns | Researched | Follow existing patterns exactly |
| UI patterns | Researched | Follow existing tab/dialog patterns |
| Enum patterns | Researched | Define PlanState in event.py |
| Import/Export handling | Researched | Add tables in dependency order |

## Risks Identified

1. **Import/Export complexity**: New tables add to import/export sequence; must maintain referential integrity
   - *Mitigation*: Follow export/reset/import cycle per Constitution

2. **EventService size**: Already 1900+ lines; adding methods increases complexity
   - *Mitigation*: Group planning methods in clearly marked section; consider extraction in future if needed

3. **Migration coordination**: Multiple model files change simultaneously
   - *Mitigation*: WP01 handles all model changes as single unit before service work begins
