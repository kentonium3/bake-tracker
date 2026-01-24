# F065: InventorySnapshot Extension

**Version**: 1.0  
**Priority**: MEDIUM (P1 - Data Completeness)  
**Type**: Service Extension  
**Status**: Draft  
**Created**: 2025-01-24

---

## Executive Summary

Current gaps in InventorySnapshot implementation:
- ❌ No material inventory snapshots (only ingredients)
- ❌ Manual snapshot creation (no automation during event planning)
- ❌ Not referenced by ProductionRun or AssemblyRun instances
- ❌ Ingredient snapshots lack cost data
- ❌ Limited planning utility (cannot capture complete inventory state)

This spec extends InventorySnapshot to capture both ingredient AND material inventory at planning time, automates snapshot creation during event planning, and links snapshots to production/assembly instances for complete historical preservation.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
InventorySnapshot
├─ ✅ Captures ingredient inventory quantities
├─ ❌ Does NOT capture material inventory
├─ ❌ Does NOT capture cost data
├─ ❌ Manual creation only (user action required)
└─ ❌ Not linked to ProductionRun/AssemblyRun

SnapshotIngredient
├─ ✅ ingredient_id, quantity
├─ ✅ Denormalized name fields (ingredient_name_snapshot, parent_l1/l0_name_snapshot)
├─ ❌ No cost_per_unit field
└─ ❌ No unit field

Event Planning Workflow
├─ ✅ Calculate ingredient requirements
├─ ❌ No automatic inventory snapshot
├─ ❌ No material inventory capture
└─ ❌ Planning based on current inventory (not snapshot)

Production/Assembly Workflow
├─ ✅ ProductionRun references RecipeSnapshot
├─ ❌ No InventorySnapshot reference
├─ ❌ No MaterialInventorySnapshot
└─ ❌ Cannot reconstruct historical inventory state
```

**Target State (COMPLETE):**
```
InventorySnapshot
├─ ✅ Captures ingredient inventory quantities AND costs
├─ ✅ Captures material inventory quantities AND costs
├─ ✅ Auto-created during event planning
├─ ✅ Linked to ProductionPlanSnapshot
└─ ✅ Optionally linked to ProductionRun/AssemblyRun

SnapshotIngredient (Extended)
├─ ✅ ingredient_id, quantity, unit
├─ ✅ Denormalized name fields
├─ ✅ cost_per_unit captured at snapshot time
└─ ✅ Complete ingredient inventory state

SnapshotMaterial (NEW)
├─ ✅ material_id, product_id, quantity, unit
├─ ✅ Denormalized name fields
├─ ✅ cost_per_unit captured at snapshot time
└─ ✅ Complete material inventory state

Event Planning Workflow
├─ ✅ Calculate ingredient/material requirements
├─ ✅ Automatically create InventorySnapshot
├─ ✅ Capture current inventory state (ingredients + materials)
├─ ✅ Link snapshot to ProductionPlanSnapshot
└─ ✅ Planning based on immutable inventory snapshot

Production/Assembly Workflow
├─ ✅ ProductionRun references inventory_snapshot_id
├─ ✅ AssemblyRun references inventory_snapshot_id
└─ ✅ Historical inventory state preserved
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **InventorySnapshot Model (Current)**
   - Find `/src/models/inventory_snapshot.py`
   - Study SnapshotIngredient structure
   - Note denormalized name fields pattern
   - Understand current snapshot creation

2. **Inventory Service (Current)**
   - Find `/src/services/inventory_service.py`
   - Study ingredient inventory tracking
   - Note FIFO consumption logic
   - Understand current inventory queries

3. **Material Inventory (If Exists)**
   - Find `/src/services/material_inventory_service.py` (or equivalent)
   - Study material inventory tracking
   - Note product/material relationship
   - Understand material consumption

4. **Planning Service (Orchestration Context)**
   - Find `/src/services/planning/planning_service.py`
   - Study event planning workflow
   - Note where inventory snapshot should be created
   - Understand requirement calculation

5. **RecipeSnapshot Pattern (Reference)**
   - Find `/src/models/recipe_snapshot.py`
   - Study snapshot metadata (snapshot_date, is_backfilled)
   - Note FK relationships and cascade behavior
   - Understand immutability pattern

6. **ProductionRun/AssemblyRun Models**
   - Find `/src/models/production_run.py`
   - Find `/src/models/assembly_run.py`
   - Study FK relationships
   - Note where inventory_snapshot_id FK should be added

7. **Instantiation Pattern Research**
   - Find `/docs/research/instantiation_pattern_findings.md`
   - Study Section 1.3 (InventorySnapshot gaps)
   - Review Pattern A recommendations
   - Note planning snapshot integration

8. **Constitution Principles**
   - Find `/.kittify/memory/constitution.md`
   - Study Principle II: Definition vs Instantiation
   - Understand snapshot immutability requirements

---

## Requirements Reference

This specification addresses gaps identified in:
- **instantiation_pattern_findings.md** Section 1.3: InventorySnapshot incomplete implementation
- **Pattern A Architecture**: Universal snapshot pattern

---

## Functional Requirements

### FR-1: Extend SnapshotIngredient with Cost and Unit

**What it must do:**
- Add cost_per_unit field to SnapshotIngredient
- Add unit field to SnapshotIngredient
- Capture current inventory cost at snapshot time
- Cost data enables historical cost analysis
- Unit enables proper quantity interpretation

**Pattern reference:** Study MaterialConsumption which captures cost_per_unit

**Model update:**
```python
class SnapshotIngredient(BaseModel):
    snapshot_id = ForeignKey("inventory_snapshots.id", ondelete="CASCADE")
    ingredient_id = ForeignKey("ingredients.id", ondelete="SET NULL", nullable=True)
    
    # Quantity and unit
    quantity = Float(nullable=False, default=0.0)
    unit = String(50, nullable=False)  # NEW: e.g., "g", "ml", "oz"
    
    # Cost snapshot (NEW)
    cost_per_unit = Numeric(10, 4, nullable=True)  # Cost per unit at snapshot time
    
    # Denormalized name fields (existing)
    ingredient_name_snapshot = String(200, nullable=True)
    parent_l1_name_snapshot = String(200, nullable=True)
    parent_l0_name_snapshot = String(200, nullable=True)
```

**Success criteria:**
- [ ] cost_per_unit field added to SnapshotIngredient
- [ ] unit field added to SnapshotIngredient
- [ ] Migration successful
- [ ] Cost captured from current inventory at snapshot time

---

### FR-2: Create SnapshotMaterial Model

**What it must do:**
- Create new SnapshotMaterial model for material inventory snapshots
- Mirror SnapshotIngredient pattern
- Capture material_id, product_id, quantity, unit, cost_per_unit
- Denormalized name fields for historical preservation
- Foreign key to InventorySnapshot (one snapshot, many material records)

**Pattern reference:** Copy SnapshotIngredient pattern exactly, apply to materials

**New model:**
```python
class SnapshotMaterial(BaseModel):
    __tablename__ = "snapshot_materials"
    
    snapshot_id = ForeignKey("inventory_snapshots.id", ondelete="CASCADE")
    material_id = ForeignKey("materials.id", ondelete="SET NULL", nullable=True)
    product_id = ForeignKey("products.id", ondelete="SET NULL", nullable=True)
    
    # Quantity and unit
    quantity = Float(nullable=False, default=0.0)
    unit = String(50, nullable=False)
    
    # Cost snapshot
    cost_per_unit = Numeric(10, 4, nullable=True)
    
    # Denormalized name fields for historical preservation
    material_name_snapshot = String(200, nullable=True)
    product_name_snapshot = String(200, nullable=True)
    category_snapshot = String(100, nullable=True)
```

**Relationship:**
```python
class InventorySnapshot(BaseModel):
    # Existing
    snapshot_ingredients = relationship("SnapshotIngredient", ...)
    
    # NEW
    snapshot_materials = relationship(
        "SnapshotMaterial",
        back_populates="inventory_snapshot",
        cascade="all, delete-orphan"
    )
```

**Success criteria:**
- [ ] SnapshotMaterial model created
- [ ] Relationship added to InventorySnapshot
- [ ] Migration successful
- [ ] Pattern matches SnapshotIngredient exactly

---

### FR-3: Automated Inventory Snapshot Creation

**What it must do:**
- Planning service automatically creates InventorySnapshot during event planning
- Capture current ingredient inventory (all ingredients with quantity > 0)
- Capture current material inventory (all materials with quantity > 0)
- Capture cost_per_unit from current inventory records
- Create inventory snapshot BEFORE calculations (snapshot represents available inventory)
- Link inventory snapshot to ProductionPlanSnapshot via FK

**Pattern reference:** Study how planning creates RecipeSnapshot (F064), apply to inventory

**Planning workflow:**
```python
def create_event_plan(event_id, session):
    event = session.get(Event, event_id)
    
    # Create ProductionPlanSnapshot container (F064)
    planning_snapshot = ProductionPlanSnapshot(
        event_id=event_id,
        created_at=utc_now()
    )
    session.add(planning_snapshot)
    session.flush()
    
    # NEW: Create InventorySnapshot automatically
    inventory_snapshot = inventory_service.create_inventory_snapshot(
        name=f"Planning Snapshot for {event.name}",
        description=f"Auto-created for event planning on {utc_now().date()}",
        planning_snapshot_id=planning_snapshot.id,
        session=session
    )
    
    # Link inventory snapshot to planning snapshot
    planning_snapshot.inventory_snapshot_id = inventory_snapshot["id"]
    
    # Create RecipeSnapshots (F064)
    for target in event.production_targets:
        # ... recipe snapshot creation
    
    # Calculate requirements using inventory snapshot
    calculations = calculate_requirements_from_snapshots(
        planning_snapshot.id, session
    )
    
    return {...}
```

**Success criteria:**
- [ ] Planning service creates InventorySnapshot automatically
- [ ] Ingredient inventory captured completely
- [ ] Material inventory captured completely
- [ ] Costs captured from current inventory
- [ ] Snapshot linked to ProductionPlanSnapshot

---

### FR-4: Inventory Service Create Snapshot Primitive

**What it must do:**
- Add create_inventory_snapshot() primitive to inventory_service
- Capture all ingredient inventory with quantity > 0
- Capture all material inventory with quantity > 0
- Include cost_per_unit from InventoryItem/MaterialInventory records
- Follow Pattern A: catalog service owns snapshot creation
- Accept session parameter for transaction consistency

**Pattern reference:** Study recipe_snapshot_service.create_recipe_snapshot(), apply to inventory

**Service method:**
```python
def create_inventory_snapshot(
    name: str,
    description: str = None,
    planning_snapshot_id: int = None,
    session: Session = None
) -> dict:
    """
    Create immutable snapshot of current inventory state.
    
    Captures:
    - All ingredients with quantity > 0
    - All materials with quantity > 0
    - Cost per unit from current inventory records
    - Denormalized name fields for historical preservation
    """
    if session is not None:
        return _create_inventory_snapshot_impl(
            name, description, planning_snapshot_id, session
        )
    
    with session_scope() as session:
        return _create_inventory_snapshot_impl(
            name, description, planning_snapshot_id, session
        )

def _create_inventory_snapshot_impl(
    name: str,
    description: str,
    planning_snapshot_id: int,
    session: Session
) -> dict:
    # Create snapshot container
    snapshot = InventorySnapshot(
        name=name,
        snapshot_date=utc_now(),
        description=description,
        planning_snapshot_id=planning_snapshot_id
    )
    session.add(snapshot)
    session.flush()
    
    # Capture ingredient inventory
    ingredient_items = session.query(InventoryItem).filter(
        InventoryItem.quantity > 0
    ).all()
    
    for item in ingredient_items:
        snapshot_ingredient = SnapshotIngredient(
            snapshot_id=snapshot.id,
            ingredient_id=item.ingredient_id,
            quantity=item.quantity,
            unit=item.unit,
            cost_per_unit=item.cost_per_unit,
            ingredient_name_snapshot=item.ingredient.display_name,
            parent_l1_name_snapshot=item.ingredient.parent_l1.name if item.ingredient.parent_l1 else None,
            parent_l0_name_snapshot=item.ingredient.parent_l0.name if item.ingredient.parent_l0 else None
        )
        session.add(snapshot_ingredient)
    
    # Capture material inventory (if material inventory exists)
    material_items = session.query(MaterialInventoryItem).filter(
        MaterialInventoryItem.quantity > 0
    ).all()
    
    for item in material_items:
        snapshot_material = SnapshotMaterial(
            snapshot_id=snapshot.id,
            material_id=item.material_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit=item.unit,
            cost_per_unit=item.cost_per_unit,
            material_name_snapshot=item.material.name,
            product_name_snapshot=item.product.name if item.product else None,
            category_snapshot=item.material.category
        )
        session.add(snapshot_material)
    
    session.flush()
    
    return {
        "id": snapshot.id,
        "name": snapshot.name,
        "ingredient_count": len(ingredient_items),
        "material_count": len(material_items),
        "snapshot_date": snapshot.snapshot_date
    }
```

**Success criteria:**
- [ ] create_inventory_snapshot() method exists in inventory_service
- [ ] Captures all ingredients with quantity > 0
- [ ] Captures all materials with quantity > 0
- [ ] Includes cost_per_unit from inventory
- [ ] Session parameter pattern followed
- [ ] Returns snapshot dict with id and counts

---

### FR-5: Link InventorySnapshot to ProductionPlanSnapshot

**What it must do:**
- Add inventory_snapshot_id FK to ProductionPlanSnapshot model
- FK references inventory_snapshots table
- FK nullable=True (optional - backward compatibility)
- Planning service populates inventory_snapshot_id during planning
- Planning calculations can reference snapshot instead of live inventory

**Pattern reference:** Study how ProductionPlanSnapshot references definition snapshots

**Model update:**
```python
class ProductionPlanSnapshot(BaseModel):
    event_id = ForeignKey("events.id", ondelete="CASCADE")
    created_at = DateTime(nullable=False)
    
    # NEW: Inventory snapshot reference
    inventory_snapshot_id = ForeignKey(
        "inventory_snapshots.id",
        ondelete="SET NULL",
        nullable=True
    )
```

**Success criteria:**
- [ ] inventory_snapshot_id FK added to ProductionPlanSnapshot
- [ ] FK properly indexed
- [ ] Migration successful
- [ ] Planning service populates FK during snapshot creation

---

### FR-6: Link InventorySnapshot to Production/Assembly Instances

**What it must do:**
- Add inventory_snapshot_id FK to ProductionRun model
- Add inventory_snapshot_id FK to AssemblyRun model
- FKs nullable=True (backward compatibility)
- Production/Assembly services can optionally reference planning inventory snapshot
- Enables reconstruction of inventory state at production/assembly time

**Pattern reference:** Study how ProductionRun references RecipeSnapshot

**Model updates:**
```python
class ProductionRun(BaseModel):
    recipe_snapshot_id = ForeignKey("recipe_snapshots.id")  # Existing
    
    # NEW: Optional inventory snapshot reference
    inventory_snapshot_id = ForeignKey(
        "inventory_snapshots.id",
        ondelete="SET NULL",
        nullable=True
    )

class AssemblyRun(BaseModel):
    finished_good_snapshot_id = ForeignKey("finished_good_snapshots.id")  # F066
    
    # NEW: Optional inventory snapshot reference
    inventory_snapshot_id = ForeignKey(
        "inventory_snapshots.id",
        ondelete="SET NULL",
        nullable=True
    )
```

**Success criteria:**
- [ ] inventory_snapshot_id FK added to ProductionRun
- [ ] inventory_snapshot_id FK added to AssemblyRun
- [ ] FKs properly indexed
- [ ] Migration successful
- [ ] Backward compatibility maintained (nullable)

---

### FR-7: Extend InventorySnapshot Model for Planning Link

**What it must do:**
- Add planning_snapshot_id FK to InventorySnapshot model
- FK references production_plan_snapshots table
- FK nullable=True (manual snapshots have no planning link)
- Enables bidirectional relationship between planning and inventory snapshots

**Pattern reference:** Study RecipeSnapshot linkage to ProductionPlanSnapshot (F064)

**Model update:**
```python
class InventorySnapshot(BaseModel):
    name = String(200, nullable=False)
    snapshot_date = DateTime(nullable=False)
    description = Text(nullable=True)
    
    # NEW: Planning snapshot linkage
    planning_snapshot_id = ForeignKey(
        "production_plan_snapshots.id",
        ondelete="CASCADE",
        nullable=True  # Manual snapshots have no planning link
    )
    
    # Relationships
    snapshot_ingredients = relationship("SnapshotIngredient", ...)
    snapshot_materials = relationship("SnapshotMaterial", ...)  # NEW
```

**Success criteria:**
- [ ] planning_snapshot_id FK added to InventorySnapshot
- [ ] FK properly indexed
- [ ] Migration successful
- [ ] Bidirectional planning/inventory relationship

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Material model creation (assumed to exist or handled separately)
- ❌ MaterialInventory service implementation (assumed to exist)
- ❌ UI for viewing inventory snapshots
- ❌ Inventory snapshot comparison or diff functionality
- ❌ Automatic re-snapshot if inventory changes between planning and production
- ❌ Inventory snapshot deletion or archival workflows

---

## Success Criteria

**Complete when:**

### Data Models
- [ ] SnapshotIngredient extended with cost_per_unit and unit fields
- [ ] SnapshotMaterial model created (mirrors SnapshotIngredient)
- [ ] InventorySnapshot.planning_snapshot_id FK added
- [ ] ProductionPlanSnapshot.inventory_snapshot_id FK added
- [ ] ProductionRun.inventory_snapshot_id FK added
- [ ] AssemblyRun.inventory_snapshot_id FK added
- [ ] All migrations successful

### Service Layer
- [ ] inventory_service.create_inventory_snapshot() primitive exists
- [ ] Captures all ingredients with quantity > 0 and costs
- [ ] Captures all materials with quantity > 0 and costs
- [ ] Session parameter pattern followed
- [ ] Returns snapshot dict with counts

### Planning Integration
- [ ] Planning service auto-creates InventorySnapshot
- [ ] Inventory snapshot linked to ProductionPlanSnapshot
- [ ] Single transaction for all snapshot creation
- [ ] Planning calculations can use snapshot data

### Production/Assembly Integration
- [ ] Production/Assembly can optionally reference inventory snapshot
- [ ] inventory_snapshot_id populated when running from planned event
- [ ] Backward compatibility maintained (nullable FKs)

### Quality
- [ ] Unit tests for inventory snapshot creation
- [ ] Integration test for planning snapshot orchestration
- [ ] Test material inventory capture (if materials exist)
- [ ] Test cost capture from inventory
- [ ] Pattern consistency with RecipeSnapshot verified

---

## Architecture Principles

### Pattern A: Catalog Service Ownership

**Inventory service owns snapshot creation:**
- inventory_service provides create_inventory_snapshot()
- Planning service orchestrates (calls primitive)
- Production/Assembly services optionally reference snapshots
- Clear service boundary: inventory owns inventory data

### Snapshot Immutability

**InventorySnapshot captures state:**
- Immutable record of inventory at snapshot time
- Includes costs for historical analysis
- Both ingredient and material inventory captured
- Complete inventory state preservation

### Planning Snapshot Orchestration

**Planning service coordinates:**
- Creates ProductionPlanSnapshot container
- Creates RecipeSnapshots (F064)
- Creates InventorySnapshot (F065)
- Creates FinishedGoodSnapshots (F066)
- All snapshots in single transaction

---

## Constitutional Compliance

✅ **Principle II: Definition vs Instantiation Separation**
- Inventory is transactional data (already instances)
- InventorySnapshot captures state at planning/production time
- Historical inventory preserved even if current inventory changes

✅ **Principle V: Service Boundaries**
- inventory_service owns inventory snapshot creation
- Planning service orchestrates (doesn't own inventory logic)
- Clear separation of concerns

✅ **Principle VIII: Session Management**
- All snapshot creation in single transaction
- Session passed through orchestration
- Atomic snapshot creation

---

## Risk Considerations

**Risk: Material inventory model may not exist**
- SnapshotMaterial depends on material inventory
- Mitigation: Planning phase checks if material inventory exists, conditional implementation
- Feature gracefully handles missing material inventory (ingredients only)

**Risk: Large inventory creates large snapshots**
- Hundreds of ingredients/materials in snapshot
- Mitigation: Only capture quantity > 0, acceptable size for typical bakery inventory
- Performance testing with realistic inventory size

**Risk: Backward compatibility for old snapshots**
- Existing InventorySnapshots lack cost_per_unit and materials
- Mitigation: Nullable fields, old snapshots work but missing data
- No backfill attempted (acceptable data loss)

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study InventorySnapshot current implementation
- Study SnapshotIngredient structure (copy for SnapshotMaterial)
- Study inventory_service for current inventory queries
- Study material inventory (if exists) for material queries
- Study planning service for orchestration pattern

**Key Patterns to Copy:**
- SnapshotIngredient → SnapshotMaterial (exact mirror)
- RecipeSnapshot creation → Inventory snapshot creation
- Planning orchestration (F064) → Add inventory snapshot step

**Focus Areas:**
- Material inventory conditional handling (may not exist)
- Cost capture from current inventory records
- Session management in snapshot creation
- Transaction boundaries for planning orchestration

**Migration Strategy:**
1. Add cost_per_unit and unit to SnapshotIngredient
2. Create SnapshotMaterial model
3. Add planning_snapshot_id to InventorySnapshot
4. Add inventory_snapshot_id to ProductionPlanSnapshot
5. Add inventory_snapshot_id to ProductionRun/AssemblyRun
6. Implement create_inventory_snapshot() primitive
7. Update planning service to auto-create inventory snapshot

**Testing Strategy:**
- Unit test inventory snapshot creation (ingredients only)
- Unit test inventory snapshot creation (with materials)
- Test cost capture accuracy
- Integration test planning orchestration
- Test backward compatibility (old snapshots still work)

---

**END OF SPECIFICATION**
