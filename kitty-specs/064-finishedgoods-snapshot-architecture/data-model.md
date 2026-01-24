# Data Model: FinishedGoods Snapshot Architecture

**Feature**: 064-finishedgoods-snapshot-architecture
**Date**: 2025-01-24

## Entity Diagram

```
┌─────────────────────┐     ┌─────────────────────────┐
│      Event          │     │    PlanningSnapshot     │
│─────────────────────│     │─────────────────────────│
│ id                  │◄────┤ event_id (nullable)     │
│ name                │     │ created_at              │
│ ...                 │     │ notes                   │
└─────────────────────┘     └───────────┬─────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        ▼                               ▼                               ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ FinishedUnitSnapshot  │   │FinishedGoodSnapshot   │   │ MaterialUnitSnapshot  │
│───────────────────────│   │───────────────────────│   │───────────────────────│
│ id                    │   │ id                    │   │ id                    │
│ finished_unit_id (FK) │   │ finished_good_id (FK) │   │ material_unit_id (FK) │
│ planning_snapshot_id  │   │ planning_snapshot_id  │   │ planning_snapshot_id  │
│ assembly_run_id       │   │ assembly_run_id       │   │ assembly_run_id       │
│ snapshot_date         │   │ snapshot_date         │   │ snapshot_date         │
│ definition_data (JSON)│   │ definition_data (JSON)│   │ definition_data (JSON)│
│ is_backfilled         │   │ is_backfilled         │   │ is_backfilled         │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
        ▲                           ▲ │                         ▲
        │                           │ │                         │
        │    ┌──────────────────────┘ │                         │
        │    │  (components JSON      │                         │
        │    │   references these     │                         │
        │    │   snapshot IDs)        │                         │
        │    │                        │                         │
        │    └────────────────────────┼─────────────────────────┘
        │                             │
        │                             │ (recursive for nested
        │                             │  FinishedGood components)
        │                             ▼
        │                    ┌───────────────────┐
        │                    │  (self-reference) │
        │                    └───────────────────┘

Source Catalog Entities (read-only references):
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  FinishedUnit   │   │  FinishedGood   │   │  MaterialUnit   │
│─────────────────│   │─────────────────│   │─────────────────│
│ id              │   │ id              │   │ id              │
│ slug            │   │ slug            │   │ slug            │
│ display_name    │   │ display_name    │   │ name            │
│ ...             │   │ components[]    │   │ ...             │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## New Models

### PlanningSnapshot

Container record linking an event to all snapshots created during plan finalization.

```python
class PlanningSnapshot(BaseModel):
    __tablename__ = "planning_snapshots"

    # Optional event linkage
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Metadata
    created_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="planning_snapshots")
    finished_unit_snapshots = relationship("FinishedUnitSnapshot", back_populates="planning_snapshot")
    finished_good_snapshots = relationship("FinishedGoodSnapshot", back_populates="planning_snapshot")
    material_unit_snapshots = relationship("MaterialUnitSnapshot", back_populates="planning_snapshot")

    # Indexes
    __table_args__ = (
        Index("idx_planning_snapshot_event", "event_id"),
        Index("idx_planning_snapshot_created", "created_at"),
    )
```

### FinishedUnitSnapshot

Immutable capture of a FinishedUnit definition at planning/assembly time.

```python
class FinishedUnitSnapshot(BaseModel):
    __tablename__ = "finished_unit_snapshots"

    # Source reference (RESTRICT: can't delete catalog item with snapshots)
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Context linkage (exactly one should be set)
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Denormalized definition data (JSON)
    definition_data = Column(Text, nullable=False)

    # Relationships
    finished_unit = relationship("FinishedUnit")
    planning_snapshot = relationship("PlanningSnapshot", back_populates="finished_unit_snapshots")

    # Indexes
    __table_args__ = (
        Index("idx_fu_snapshot_unit", "finished_unit_id"),
        Index("idx_fu_snapshot_planning", "planning_snapshot_id"),
        Index("idx_fu_snapshot_assembly", "assembly_run_id"),
        Index("idx_fu_snapshot_date", "snapshot_date"),
    )
```

**definition_data JSON schema**:
```json
{
    "slug": "chocolate-chip-cookie",
    "display_name": "Chocolate Chip Cookie",
    "description": "Classic chocolate chip cookie",
    "recipe_id": 123,
    "recipe_name": "Chocolate Chip Cookie Recipe",
    "recipe_category": "Cookies",
    "yield_mode": "discrete_count",
    "items_per_batch": 32,
    "item_unit": "cookie",
    "batch_percentage": null,
    "portion_description": null,
    "category": "Cookies",
    "production_notes": "Cool on wire rack",
    "notes": "Best served warm"
}
```

### MaterialUnitSnapshot

Immutable capture of a MaterialUnit definition at planning/assembly time.

```python
class MaterialUnitSnapshot(BaseModel):
    __tablename__ = "material_unit_snapshots"

    # Source reference
    material_unit_id = Column(
        Integer,
        ForeignKey("material_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Context linkage
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Denormalized definition data (JSON)
    definition_data = Column(Text, nullable=False)

    # Relationships
    material_unit = relationship("MaterialUnit")
    planning_snapshot = relationship("PlanningSnapshot", back_populates="material_unit_snapshots")

    # Indexes
    __table_args__ = (
        Index("idx_mu_snapshot_unit", "material_unit_id"),
        Index("idx_mu_snapshot_planning", "planning_snapshot_id"),
        Index("idx_mu_snapshot_assembly", "assembly_run_id"),
        Index("idx_mu_snapshot_date", "snapshot_date"),
    )
```

**definition_data JSON schema**:
```json
{
    "slug": "6-inch-red-ribbon",
    "name": "6-inch Red Ribbon",
    "description": "Red satin ribbon cut to 6 inches",
    "material_id": 45,
    "material_name": "Red Satin Ribbon",
    "material_category": "Ribbons",
    "quantity_per_unit": 6.0
}
```

### FinishedGoodSnapshot

Immutable capture of a FinishedGood definition including component structure.

```python
class FinishedGoodSnapshot(BaseModel):
    __tablename__ = "finished_good_snapshots"

    # Source reference
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Context linkage
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("planning_snapshots.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    is_backfilled = Column(Boolean, nullable=False, default=False)

    # Denormalized definition data (JSON) - includes components
    definition_data = Column(Text, nullable=False)

    # Relationships
    finished_good = relationship("FinishedGood")
    planning_snapshot = relationship("PlanningSnapshot", back_populates="finished_good_snapshots")

    # Indexes
    __table_args__ = (
        Index("idx_fg_snapshot_good", "finished_good_id"),
        Index("idx_fg_snapshot_planning", "planning_snapshot_id"),
        Index("idx_fg_snapshot_assembly", "assembly_run_id"),
        Index("idx_fg_snapshot_date", "snapshot_date"),
    )
```

**definition_data JSON schema**:
```json
{
    "slug": "holiday-cookie-box",
    "display_name": "Holiday Cookie Box",
    "description": "Assorted holiday cookies in decorative box",
    "assembly_type": "gift_box",
    "packaging_instructions": "Layer cookies with parchment paper",
    "notes": "Include recipe card",
    "components": [
        {
            "component_type": "finished_unit",
            "snapshot_id": 101,
            "original_id": 45,
            "component_slug": "chocolate-chip-cookie",
            "component_name": "Chocolate Chip Cookie",
            "component_quantity": 6,
            "component_notes": "Place in bottom layer",
            "sort_order": 1,
            "is_generic": false
        },
        {
            "component_type": "finished_unit",
            "snapshot_id": 102,
            "original_id": 46,
            "component_slug": "sugar-cookie",
            "component_name": "Sugar Cookie",
            "component_quantity": 6,
            "component_notes": null,
            "sort_order": 2,
            "is_generic": false
        },
        {
            "component_type": "material_unit",
            "snapshot_id": 201,
            "original_id": 78,
            "component_slug": "6-inch-red-ribbon",
            "component_name": "6-inch Red Ribbon",
            "component_quantity": 1,
            "component_notes": null,
            "sort_order": 3,
            "is_generic": false
        },
        {
            "component_type": "finished_good",
            "snapshot_id": 301,
            "original_id": 12,
            "component_slug": "cookie-sampler",
            "component_name": "Cookie Sampler",
            "component_quantity": 1,
            "component_notes": "Nested sub-assembly",
            "sort_order": 4,
            "is_generic": false
        },
        {
            "component_type": "material",
            "snapshot_id": null,
            "original_id": 89,
            "component_slug": null,
            "component_name": "Gift Box (selection pending)",
            "component_quantity": 1,
            "component_notes": "Choose at assembly time",
            "sort_order": 5,
            "is_generic": true
        }
    ]
}
```

## Service Layer Additions

### FinishedUnitService (addition)

```python
def create_finished_unit_snapshot(
    finished_unit_id: int,
    planning_snapshot_id: int = None,
    assembly_run_id: int = None,
    session: Session = None
) -> dict:
    """
    Create immutable snapshot of FinishedUnit definition.

    Args:
        finished_unit_id: Source FinishedUnit ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing

    Returns:
        dict with snapshot id and definition_data

    Raises:
        SnapshotCreationError: If FinishedUnit not found or creation fails
    """
```

### MaterialUnitService (addition)

```python
def create_material_unit_snapshot(
    material_unit_id: int,
    planning_snapshot_id: int = None,
    assembly_run_id: int = None,
    session: Session = None
) -> dict:
    """
    Create immutable snapshot of MaterialUnit definition.

    Args:
        material_unit_id: Source MaterialUnit ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing

    Returns:
        dict with snapshot id and definition_data

    Raises:
        SnapshotCreationError: If MaterialUnit not found or creation fails
    """
```

### FinishedGoodService (addition)

```python
def create_finished_good_snapshot(
    finished_good_id: int,
    planning_snapshot_id: int = None,
    assembly_run_id: int = None,
    session: Session = None,
    _visited_ids: set[int] = None,
    _depth: int = 0
) -> dict:
    """
    Create immutable snapshot of FinishedGood definition with components.

    Recursively creates snapshots for all FinishedUnit, MaterialUnit,
    and nested FinishedGood components.

    Args:
        finished_good_id: Source FinishedGood ID
        planning_snapshot_id: Optional planning context
        assembly_run_id: Optional assembly context
        session: Optional session for transaction sharing
        _visited_ids: Internal - tracked IDs for circular reference detection
        _depth: Internal - current recursion depth

    Returns:
        dict with snapshot id and definition_data (including component snapshot IDs)

    Raises:
        SnapshotCreationError: If FinishedGood not found or creation fails
        CircularReferenceError: If circular reference detected in hierarchy
        MaxDepthExceededError: If nesting depth exceeds 10 levels
    """
```

### PlanningSnapshotService (new)

```python
def create_planning_snapshot(
    event_id: int = None,
    notes: str = None,
    session: Session = None
) -> dict:
    """
    Create empty PlanningSnapshot container.

    Args:
        event_id: Optional event to link
        notes: Optional notes
        session: Optional session

    Returns:
        dict with planning_snapshot id and created_at
    """

def get_planning_snapshot(
    planning_snapshot_id: int,
    session: Session = None
) -> dict:
    """Get planning snapshot with all linked snapshots."""

def delete_planning_snapshot(
    planning_snapshot_id: int,
    session: Session = None
) -> bool:
    """Delete planning snapshot (cascades to all linked snapshots)."""
```

## Validation Rules

1. **Exactly one context FK**: Each snapshot must have either `planning_snapshot_id` OR `assembly_run_id` set, not both, not neither (enforced at service layer, not DB constraint since both are nullable for flexibility during creation)

2. **Circular reference prevention**: `create_finished_good_snapshot()` tracks visited FinishedGood IDs and raises `CircularReferenceError` if same ID encountered twice in hierarchy

3. **Max depth enforcement**: Recursion depth capped at 10 levels; `MaxDepthExceededError` raised if exceeded

4. **Source entity protection**: `ondelete="RESTRICT"` prevents deletion of catalog items that have snapshots

5. **JSON validity**: `definition_data` must be valid JSON (enforced at service layer via `json.dumps()`)

## State Transitions

Snapshots are immutable - no state transitions after creation.

```
[FinishedUnit/Good/MaterialUnit] --snapshot--> [Snapshot] --immutable--
                                                   │
                                                   └── Deleted only via:
                                                       - CASCADE from PlanningSnapshot
                                                       - CASCADE from AssemblyRun
```
