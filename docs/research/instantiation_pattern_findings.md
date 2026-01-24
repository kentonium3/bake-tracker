# Instantiation Pattern Research Findings

**Research Type:** Architecture Analysis  
**Status:** Complete  
**Date Completed:** 2025-01-24  
**Researcher:** Claude (Sonnet 4.5)

---

## Executive Summary

This research investigated how bake-tracker implements the definition-to-instantiation pattern across its catalog services and provides a universal snapshot architecture recommendation for FinishedGoods implementation.

**Key Findings:**
- **Partial Implementation:** Only Recipe has full snapshot support; Inventory and Planning have limited implementations
- **Inconsistent Patterns:** Three different snapshot patterns identified across services
- **Service Ownership:** Recipe demonstrates catalog service ownership; Planning demonstrates planning service ownership
- **No Universal Pattern:** No unified snapshot architecture exists across services
- **Blocking Issue Identified:** FinishedGoods implementation requires architectural decision before proceeding

**Recommendation:** Adopt **Catalog Service Ownership with Mirrored Tables** pattern (Pattern A) for universal snapshot architecture.

---

## Section 1: Current State Assessment

### 1.1 Snapshot Model Inventory

| Model | Purpose | Storage Pattern | Status | Feature |
|-------|---------|----------------|--------|---------|
| **RecipeSnapshot** | Production history | Mirrored table with JSON | ✅ Complete | F037 |
| **InventorySnapshot** | Planning inputs | Denormalized junction | ⚠️ Planning-only | Pre-F037 |
| **ProductionPlanSnapshot** | Cached calculations | JSON blob | ⚠️ Calculations-only | F039 |
| **IngredientSnapshot** | ❌ Not exists | - | ❌ Missing | - |
| **MaterialSnapshot** | ❌ Not exists | - | ❌ Missing | - |
| **FinishedUnitSnapshot** | ❌ Not exists | - | ❌ Missing | - |
| **FinishedGoodSnapshot** | ❌ Not exists | - | ❌ Missing | REQ-FG-037 |

### 1.2 RecipeSnapshot - Complete Implementation (Pattern A)

**File:** `src/models/recipe_snapshot.py`

**Architecture:**
```python
class RecipeSnapshot(BaseModel):
    # Foreign keys
    recipe_id = ForeignKey("recipes.id", ondelete="RESTRICT")
    production_run_id = ForeignKey("production_runs.id", ondelete="CASCADE")
    
    # Scaling
    scale_factor = Float(nullable=False, default=1.0)
    
    # Snapshot data (JSON)
    recipe_data = Text(nullable=False)  # JSON: name, category, yield, etc.
    ingredients_data = Text(nullable=False)  # JSON: list of ingredients
    
    # Metadata
    snapshot_date = DateTime(nullable=False)
    is_backfilled = Boolean(nullable=False, default=False)
```

**Data Captured:**
```python
recipe_data = {
    "name": recipe.name,
    "category": recipe.category,
    "source": recipe.source,
    "yield_quantity": yield_quantity,
    "yield_unit": yield_unit,
    "yield_description": yield_description,
    "estimated_time_minutes": recipe.estimated_time_minutes,
    "notes": recipe.notes,
    "variant_name": recipe.variant_name,
    "is_production_ready": recipe.is_production_ready,
}

ingredients_data = [
    {
        "ingredient_id": ri.ingredient_id,
        "ingredient_name": ri.ingredient.display_name,
        "ingredient_slug": ri.ingredient.slug,
        "quantity": float(ri.quantity),
        "unit": ri.unit,
        "notes": ri.notes,
    }
    for ri in recipe.recipe_ingredients
]
```

**Relationships:**
- **1:1 with ProductionRun** - Each production run has exactly one snapshot
- **RESTRICT on recipe deletion** - Cannot delete recipe with production history
- **CASCADE on production run deletion** - Snapshot deleted with production run

**Service:** `src/services/recipe_snapshot_service.py`

**Key Methods:**
```python
def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session = None
) -> dict
```

**Ownership:** Recipe/Catalog service provides `create_recipe_snapshot()` primitive

**Creation Trigger:** Production service calls during `record_batch_production()`

**File:** `src/services/batch_production_service.py:387`
```python
# Feature 037: Create snapshot FIRST - captures recipe state before production
snapshot = recipe_snapshot_service.create_recipe_snapshot(
    recipe_id=recipe_id,
    scale_factor=scale_factor,
    production_run_id=temp_production_run.id,
    session=session,
)
```

**Usage Pattern:**
- Production service creates ProductionRun first to get ID
- Recipe snapshot service captures complete recipe state
- Production service consumes ingredients from snapshot data (not live recipe)
- ProductionRun stores `recipe_snapshot_id` foreign key

### 1.3 InventorySnapshot - Planning Input (Pattern B)

**File:** `src/models/inventory_snapshot.py`

**Architecture:**
```python
class InventorySnapshot(BaseModel):
    name = String(200, nullable=False)
    snapshot_date = DateTime(nullable=False)
    description = Text(nullable=True)
    
    # Relationship to junction table
    snapshot_ingredients = relationship("SnapshotIngredient", ...)

class SnapshotIngredient(BaseModel):
    snapshot_id = ForeignKey("inventory_snapshots.id", ondelete="CASCADE")
    ingredient_id = ForeignKey("ingredients.id", ondelete="SET NULL")
    quantity = Float(nullable=False, default=0.0)
    
    # Denormalized fields for historical preservation (F035)
    ingredient_name_snapshot = String(200, nullable=True)
    parent_l1_name_snapshot = String(200, nullable=True)
    parent_l0_name_snapshot = String(200, nullable=True)
```

**Purpose:** 
- Captures ingredient inventory quantities at a point in time
- Used for event planning against historical inventory state
- NOT tied to production/assembly instances

**Creation:** Manual user action (not automatic)

**Service:** No dedicated snapshot service (managed via event/planning service)

**Gaps:**
- No Materials inventory snapshots (only ingredients)
- No automated snapshot creation during event planning
- Not referenced by ProductionRun or AssemblyRun
- Snapshot ingredients lack cost data

### 1.4 ProductionPlanSnapshot - Calculation Cache (Pattern C)

**File:** `src/models/production_plan_snapshot.py`

**Architecture:**
```python
class ProductionPlanSnapshot(BaseModel):
    event_id = ForeignKey("events.id", ondelete="CASCADE")
    calculated_at = DateTime(nullable=False)
    
    # Input version tracking (staleness detection)
    requirements_updated_at = DateTime(nullable=False)
    recipes_updated_at = DateTime(nullable=False)
    bundles_updated_at = DateTime(nullable=False)
    
    # Calculation results (JSON blob)
    calculation_results = JSON(nullable=False)
    # Structure: {
    #     "recipe_batches": [...],
    #     "aggregated_ingredients": [...],
    #     "shopping_list": [...]
    # }
    
    # Status tracking
    is_stale = Boolean(default=False, nullable=False)
    stale_reason = String(200, nullable=True)
```

**Purpose:**
- Caches production plan calculations for an event
- Supports staleness detection when inputs change
- NOT an immutable snapshot of definitions

**Creation:** Planning service (`src/services/planning/planning_service.py`)

**Key Difference from RecipeSnapshot:**
- Does NOT capture definition state at planning time
- Does NOT make definitions immutable for the event
- DOES cache calculation results with staleness tracking
- References live definitions (not snapshots) in calculation results

**File:** `src/services/planning/planning_service.py:316`
```python
# Create or update snapshot
snapshot = ProductionPlanSnapshot(
    event_id=event_id,
    calculated_at=now,
    requirements_updated_at=requirements_ts or now,
    recipes_updated_at=recipes_ts or now,
    bundles_updated_at=bundles_ts or now,
    calculation_results=calculation_results,
    is_stale=False,
    stale_reason=None,
)
session.add(snapshot)
```

**Architectural Problem:**
This is NOT true definition/instantiation separation. It's a performance optimization (calculation cache), not an immutable snapshot for production integrity.

### 1.5 Missing Snapshot Support

**Catalog services WITHOUT snapshot implementations:**

1. **Ingredient Service** (`src/services/ingredient_service.py`)
   - No snapshot model
   - No `create_snapshot()` method
   - ProductionConsumption stores ingredient_slug (reference by slug, not snapshot)

2. **Material Service** (`src/services/material_catalog_service.py`)
   - No snapshot model
   - No `create_snapshot()` method
   - AssemblyConsumption would need material snapshots (not implemented)

3. **FinishedUnit Service** (`src/services/finished_unit_service.py`)
   - No snapshot model
   - No `create_snapshot()` method
   - AssemblyFinishedUnitConsumption references live FinishedUnit (not snapshot)

4. **FinishedGood Service** (`src/services/finished_good_service.py`)
   - No snapshot model
   - No `create_snapshot()` method
   - Required for REQ-FG-037 implementation

5. **Product Service** (`src/services/product_service.py`)
   - No snapshot model
   - Products are instance-level (brand/package specifics)
   - Inventory items capture cost_per_unit at purchase (already snapshot-like)

### 1.6 Consumption Records as Pseudo-Snapshots

Some models capture identity information at consumption time:

**ProductionConsumption** (`src/models/production_consumption.py`):
```python
class ProductionConsumption(BaseModel):
    production_run_id = ForeignKey("production_runs.id")
    ingredient_slug = String(200, nullable=False)  # Identity snapshot
    quantity_consumed = Numeric(10, 4, nullable=False)
    unit = String(50, nullable=False)
    total_cost = Numeric(10, 4, nullable=False)  # Cost snapshot
```

**MaterialConsumption** (`src/models/material_consumption.py`):
```python
class MaterialConsumption(BaseModel):
    assembly_run_id = ForeignKey("assembly_runs.id")
    
    # Identity snapshots (REQ-M-016)
    material_id = Integer(nullable=False)
    product_id = Integer(nullable=False)
    display_name_snapshot = String(200, nullable=False)
    
    # Quantity consumed
    quantity_consumed = Numeric(10, 4, nullable=False)
    unit = String(50, nullable=False)
    
    # Cost snapshot (immutable)
    cost_per_unit = Numeric(10, 4, nullable=False)
```

**Pattern:** Consumption records capture snapshot-like data (identity, cost) but NOT full definition state.

---

## Section 2: Architecture Recommendation

### 2.1 Universal Snapshot Pattern

**Recommendation: Pattern A - Catalog Service Ownership with Mirrored Tables**

### 2.2 Pattern Comparison

| Aspect | Pattern A (Mirrored) | Pattern B (JSON Blob) | Pattern C (Hybrid) |
|--------|---------------------|---------------------|-------------------|
| **Storage** | Dedicated table per entity type | Universal snapshot table | Entity table + JSON data |
| **Query Performance** | ✅ Excellent (indexed columns) | ❌ Poor (JSON parsing required) | ⚠️ Mixed |
| **Schema Evolution** | ⚠️ Requires migration | ✅ Flexible | ⚠️ Mixed |
| **Referential Integrity** | ✅ Enforced by FK | ❌ Cannot enforce | ⚠️ Partial |
| **Implementation Complexity** | ⚠️ High (N models) | ✅ Low (1 model) | ⚠️ Medium |
| **Type Safety** | ✅ Full | ❌ Runtime only | ⚠️ Partial |
| **Existing Pattern** | ✅ RecipeSnapshot | ❌ None | ⚠️ ProductionPlanSnapshot |

### 2.3 Why Pattern A (Mirrored Tables)?

**Pros:**
1. **Consistency with existing RecipeSnapshot** - Proven pattern already in use
2. **Query performance** - No JSON parsing for cost calculations or reporting
3. **Type safety** - SQLAlchemy validates structure at model level
4. **Clear relationships** - FK constraints enforce referential integrity
5. **Indexing** - Can index snapshot fields for fast lookups
6. **Auditability** - Explicit schema makes snapshots self-documenting

**Cons:**
1. **Schema coupling** - Snapshot model must track definition model changes
2. **Migration overhead** - Adding definition field requires snapshot migration
3. **Storage efficiency** - More storage than JSON (marginal concern)

**Mitigation for Cons:**
- Use JSON columns for non-critical metadata (like RecipeSnapshot does)
- Reserve structured fields for query-critical data (IDs, costs, quantities)
- Hybrid approach: structured core + JSON metadata

### 2.4 Recommended Architecture

#### 2.4.1 Service Responsibility Assignment

**Catalog Service Ownership:**
- Each catalog service provides `create_snapshot()` primitive
- Catalog service knows definition structure and what to capture
- Planning/Assembly/Production services call catalog primitives
- Catalog service manages snapshot lifecycle (CRUD where applicable)

**Service Method Signatures:**

```python
# Recipe Service
def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session = None
) -> dict

# Ingredient Service (NEW)
def create_ingredient_snapshot(
    ingredient_id: int,
    session: Session = None
) -> dict

# Material Service (NEW)
def create_material_snapshot(
    material_id: int,
    session: Session = None
) -> dict

# FinishedUnit Service (NEW)
def create_finished_unit_snapshot(
    finished_unit_id: int,
    session: Session = None
) -> dict

# FinishedGood Service (NEW)
def create_finished_good_snapshot(
    finished_good_id: int,
    recursive: bool = True,  # Include nested components
    session: Session = None
) -> dict
```

**Orchestration Pattern:**

```python
# Planning service orchestrates snapshot creation
def create_event_plan_snapshots(event_id: int, session: Session):
    event = session.get(Event, event_id)
    
    # Snapshot recipes
    for target in event.production_targets:
        recipe_snapshot_service.create_recipe_snapshot(
            recipe_id=target.recipe_id,
            scale_factor=1.0,
            planning_snapshot_id=planning_snapshot_id,
            session=session
        )
    
    # Snapshot finished goods (with nested components)
    for target in event.assembly_targets:
        finished_good_service.create_finished_good_snapshot(
            finished_good_id=target.finished_good_id,
            recursive=True,  # Captures nested FinishedUnits/Materials
            planning_snapshot_id=planning_snapshot_id,
            session=session
        )
```

#### 2.4.2 Data Model Specification

**General Snapshot Structure:**

```python
class EntitySnapshot(BaseModel):
    """Base pattern for all snapshot models."""
    
    # Source reference
    entity_id = ForeignKey("entities.id", ondelete="RESTRICT")
    
    # Context reference (what triggered snapshot)
    production_run_id = ForeignKey("production_runs.id", ondelete="CASCADE", nullable=True)
    assembly_run_id = ForeignKey("assembly_runs.id", ondelete="CASCADE", nullable=True)
    planning_snapshot_id = ForeignKey("planning_snapshots.id", ondelete="CASCADE", nullable=True)
    
    # Snapshot data (structured + JSON hybrid)
    entity_data = JSON(nullable=False)  # Full state capture
    
    # Metadata
    snapshot_date = DateTime(nullable=False)
    snapshot_type = String(50, nullable=False)  # 'production', 'assembly', 'planning'
```

**FinishedGoodSnapshot (Example):**

```python
class FinishedGoodSnapshot(BaseModel):
    __tablename__ = "finished_good_snapshots"
    
    # Source reference
    finished_good_id = ForeignKey("finished_goods.id", ondelete="RESTRICT")
    
    # Context (what triggered this snapshot)
    assembly_run_id = ForeignKey("assembly_runs.id", ondelete="CASCADE", nullable=True)
    planning_snapshot_id = ForeignKey("planning_snapshots.id", ondelete="CASCADE", nullable=True)
    
    # Snapshot data (JSON for flexibility)
    definition_data = JSON(nullable=False)
    # Structure: {
    #     "slug": "...",
    #     "display_name": "...",
    #     "assembly_type": "...",
    #     "packaging_instructions": "...",
    #     "notes": "...",
    #     "components": [
    #         {
    #             "component_type": "finished_unit|finished_good|material_unit",
    #             "component_slug": "...",
    #             "component_name": "...",  # denormalized
    #             "quantity": 6,
    #             "notes": "...",
    #             "snapshot_id": 123  # FK to nested snapshot if recursive
    #         }
    #     ]
    # }
    
    # Metadata
    snapshot_date = DateTime(nullable=False)
    snapshot_type = String(50, nullable=False)  # 'planning' or 'assembly'
    is_backfilled = Boolean(nullable=False, default=False)
    
    # Relationships
    finished_good = relationship("FinishedGood", back_populates="snapshots")
    assembly_run = relationship("AssemblyRun", back_populates="snapshot")
```

#### 2.4.3 Nested Relationship Handling

**Strategy: Recursive Snapshot Creation**

```python
def create_finished_good_snapshot(
    finished_good_id: int,
    recursive: bool = True,
    session: Session = None
) -> dict:
    """
    Create snapshot of FinishedGood with all components.
    
    If recursive=True, creates snapshots for nested FinishedGoods
    and references them in the component data.
    """
    fg = session.get(FinishedGood, finished_good_id)
    
    components_data = []
    for composition in fg.components:
        component_data = {
            "component_type": composition.component_type,
            "component_quantity": composition.component_quantity,
            "component_notes": composition.component_notes,
            "sort_order": composition.sort_order,
        }
        
        if composition.finished_unit_id:
            # Snapshot FinishedUnit
            fu_snapshot = finished_unit_service.create_finished_unit_snapshot(
                composition.finished_unit_id, session=session
            )
            component_data["finished_unit_snapshot_id"] = fu_snapshot["id"]
            component_data["component_name"] = fu_snapshot["display_name"]
        
        elif composition.finished_good_id and recursive:
            # Recursively snapshot nested FinishedGood
            nested_snapshot = create_finished_good_snapshot(
                composition.finished_good_id, recursive=True, session=session
            )
            component_data["finished_good_snapshot_id"] = nested_snapshot["id"]
            component_data["component_name"] = nested_snapshot["display_name"]
        
        elif composition.material_unit_id:
            # Snapshot MaterialUnit
            mu_snapshot = material_service.create_material_unit_snapshot(
                composition.material_unit_id, session=session
            )
            component_data["material_unit_snapshot_id"] = mu_snapshot["id"]
            component_data["component_name"] = mu_snapshot["name"]
        
        components_data.append(component_data)
    
    # Create snapshot
    snapshot = FinishedGoodSnapshot(
        finished_good_id=finished_good_id,
        definition_data={
            "slug": fg.slug,
            "display_name": fg.display_name,
            "assembly_type": fg.assembly_type.value,
            "packaging_instructions": fg.packaging_instructions,
            "components": components_data,
        },
        snapshot_date=utc_now(),
        snapshot_type="planning",
    )
    session.add(snapshot)
    session.flush()
    
    return {"id": snapshot.id, "finished_good_id": fg.id, ...}
```

**Circular Reference Prevention:**
- Track visited entity IDs during recursive traversal
- Raise error if circular reference detected
- Maximum nesting depth: 10 levels (configurable)

**Performance Consideration:**
- For deep hierarchies, consider iterative approach with deque
- Batch snapshot creation in single transaction
- Use selectinload to avoid N+1 queries

---

## Section 3: Implementation Guidance

### 3.1 Snapshot Creation Flow

**Sequence Diagram (Conceptual):**

```
Event Planning Phase:
User → PlanningService: calculate_plan(event_id)
PlanningService → EventService: get_event(event_id)
PlanningService → RecipeService: create_recipe_snapshot(recipe_id)
RecipeService → Database: INSERT recipe_snapshots
PlanningService → FinishedGoodService: create_finished_good_snapshot(fg_id, recursive=True)
FinishedGoodService → FinishedUnitService: create_finished_unit_snapshot(fu_id)
FinishedGoodService → MaterialService: create_material_unit_snapshot(mu_id)
FinishedGoodService → Database: INSERT finished_good_snapshots
PlanningService → Database: INSERT production_plan_snapshots (references all snapshots)
PlanningService → User: plan_summary

Production Phase:
User → ProductionService: record_batch_production(recipe_id, num_batches)
ProductionService → RecipeService: create_recipe_snapshot(recipe_id)
RecipeService → Database: INSERT recipe_snapshots
ProductionService → InventoryService: consume_fifo(ingredient_slug, qty) [uses snapshot data]
ProductionService → Database: INSERT production_runs, production_consumptions
ProductionService → User: production_summary

Assembly Phase:
User → AssemblyService: record_assembly(finished_good_id, quantity)
AssemblyService → FinishedGoodService: create_finished_good_snapshot(fg_id)
FinishedGoodService → Database: INSERT finished_good_snapshots (with nested components)
AssemblyService → InventoryService: consume_finished_units(snapshot_data)
AssemblyService → MaterialInventoryService: consume_materials(snapshot_data)
AssemblyService → Database: INSERT assembly_runs, assembly_consumptions
AssemblyService → User: assembly_summary
```

### 3.2 Example Implementations

#### 3.2.1 Recipe Snapshot (Existing - Reference)

**File:** `src/services/recipe_snapshot_service.py`

```python
def create_recipe_snapshot(
    recipe_id: int, scale_factor: float, production_run_id: int, session: Session = None
) -> dict:
    """
    Create an immutable snapshot of recipe state at production time.
    
    Args:
        recipe_id: Source recipe ID
        scale_factor: Batch size multiplier (e.g., 2.0 = double batch)
        production_run_id: The production run this snapshot is for (1:1)
        session: Optional SQLAlchemy session for transaction sharing
    
    Returns:
        dict with snapshot data including id
    """
    if session is not None:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)
    
    with session_scope() as session:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)

def _create_recipe_snapshot_impl(
    recipe_id: int, scale_factor: float, production_run_id: int, session: Session
) -> dict:
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise SnapshotCreationError(f"Recipe {recipe_id} not found")
    
    # Eagerly load ingredients
    _ = recipe.recipe_ingredients
    for ri in recipe.recipe_ingredients:
        _ = ri.ingredient
    
    # Build JSON data
    recipe_data = {
        "name": recipe.name,
        "category": recipe.category,
        # ... all relevant fields
    }
    
    ingredients_data = [
        {
            "ingredient_id": ri.ingredient_id,
            "ingredient_slug": ri.ingredient.slug,
            "quantity": float(ri.quantity),
            "unit": ri.unit,
        }
        for ri in recipe.recipe_ingredients
    ]
    
    # Create snapshot
    snapshot = RecipeSnapshot(
        recipe_id=recipe_id,
        production_run_id=production_run_id,
        scale_factor=scale_factor,
        snapshot_date=utc_now(),
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=False,
    )
    
    session.add(snapshot)
    session.flush()
    
    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "recipe_data": recipe_data,
        "ingredients_data": ingredients_data,
    }
```

#### 3.2.2 FinishedGood Snapshot (NEW - Recommendation)

**File:** `src/services/finished_good_service.py` (new methods)

```python
def create_finished_good_snapshot(
    finished_good_id: int,
    recursive: bool = True,
    assembly_run_id: Optional[int] = None,
    planning_snapshot_id: Optional[int] = None,
    session: Session = None
) -> dict:
    """
    Create an immutable snapshot of FinishedGood definition.
    
    Args:
        finished_good_id: Source FinishedGood ID
        recursive: If True, create snapshots for nested components
        assembly_run_id: Optional FK to AssemblyRun (assembly phase)
        planning_snapshot_id: Optional FK to PlanningSnapshot (planning phase)
        session: Optional SQLAlchemy session for transaction sharing
    
    Returns:
        dict with snapshot data including id
    
    Raises:
        FinishedGoodNotFoundError: If finished_good_id not found
        CircularReferenceError: If circular dependency detected
    """
    if session is not None:
        return _create_finished_good_snapshot_impl(
            finished_good_id, recursive, assembly_run_id, planning_snapshot_id, session
        )
    
    with session_scope() as session:
        return _create_finished_good_snapshot_impl(
            finished_good_id, recursive, assembly_run_id, planning_snapshot_id, session
        )

def _create_finished_good_snapshot_impl(
    finished_good_id: int,
    recursive: bool,
    assembly_run_id: Optional[int],
    planning_snapshot_id: Optional[int],
    session: Session,
    visited: Optional[set] = None
) -> dict:
    """Internal implementation with circular reference prevention."""
    
    # Circular reference prevention
    if visited is None:
        visited = set()
    
    if finished_good_id in visited:
        raise CircularReferenceError(
            f"Circular reference detected: FinishedGood {finished_good_id} already in snapshot tree"
        )
    
    visited.add(finished_good_id)
    
    # Load FinishedGood with components
    fg = session.query(FinishedGood).filter_by(id=finished_good_id).first()
    if not fg:
        raise FinishedGoodNotFoundError(f"FinishedGood {finished_good_id} not found")
    
    # Eagerly load components
    _ = fg.components
    
    # Build components data with optional recursive snapshots
    components_data = []
    for composition in fg.components:
        component_data = {
            "component_type": composition.component_type,
            "component_quantity": composition.component_quantity,
            "component_notes": composition.component_notes,
            "sort_order": composition.sort_order,
            "is_generic": composition.is_generic,
        }
        
        if composition.finished_unit_id:
            # FinishedUnit component
            fu_snapshot = finished_unit_service.create_finished_unit_snapshot(
                composition.finished_unit_id, session=session
            )
            component_data["finished_unit_snapshot_id"] = fu_snapshot["id"]
            component_data["component_slug"] = fu_snapshot["slug"]
            component_data["component_name"] = fu_snapshot["display_name"]
        
        elif composition.finished_good_id and recursive:
            # Nested FinishedGood - recursive snapshot
            nested_snapshot = _create_finished_good_snapshot_impl(
                composition.finished_good_id,
                recursive=True,
                assembly_run_id=assembly_run_id,
                planning_snapshot_id=planning_snapshot_id,
                session=session,
                visited=visited.copy()  # Pass copy to avoid pollution
            )
            component_data["finished_good_snapshot_id"] = nested_snapshot["id"]
            component_data["component_slug"] = nested_snapshot["slug"]
            component_data["component_name"] = nested_snapshot["display_name"]
        
        elif composition.material_unit_id:
            # MaterialUnit component
            mu_snapshot = material_service.create_material_unit_snapshot(
                composition.material_unit_id, session=session
            )
            component_data["material_unit_snapshot_id"] = mu_snapshot["id"]
            component_data["component_slug"] = mu_snapshot["slug"]
            component_data["component_name"] = mu_snapshot["name"]
        
        elif composition.material_id:
            # Generic material placeholder
            component_data["material_id"] = composition.material_id
            component_data["component_name"] = f"{composition.material_component.name} (generic)"
        
        components_data.append(component_data)
    
    # Build definition data
    definition_data = {
        "slug": fg.slug,
        "display_name": fg.display_name,
        "assembly_type": fg.assembly_type.value,
        "packaging_instructions": fg.packaging_instructions,
        "notes": fg.notes,
        "components": components_data,
    }
    
    # Determine snapshot type
    if assembly_run_id:
        snapshot_type = "assembly"
    elif planning_snapshot_id:
        snapshot_type = "planning"
    else:
        snapshot_type = "standalone"
    
    # Create snapshot
    snapshot = FinishedGoodSnapshot(
        finished_good_id=finished_good_id,
        assembly_run_id=assembly_run_id,
        planning_snapshot_id=planning_snapshot_id,
        definition_data=definition_data,
        snapshot_date=utc_now(),
        snapshot_type=snapshot_type,
        is_backfilled=False,
    )
    
    session.add(snapshot)
    session.flush()
    
    return {
        "id": snapshot.id,
        "finished_good_id": fg.id,
        "slug": fg.slug,
        "display_name": fg.display_name,
        "components_count": len(components_data),
        "snapshot_type": snapshot_type,
    }
```

#### 3.2.3 FinishedUnit Snapshot (NEW - Recommendation)

**File:** `src/services/finished_unit_service.py` (new methods)

```python
def create_finished_unit_snapshot(
    finished_unit_id: int,
    session: Session = None
) -> dict:
    """
    Create an immutable snapshot of FinishedUnit definition.
    
    Args:
        finished_unit_id: Source FinishedUnit ID
        session: Optional SQLAlchemy session for transaction sharing
    
    Returns:
        dict with snapshot data including id
    
    Raises:
        FinishedUnitNotFoundError: If finished_unit_id not found
    """
    if session is not None:
        return _create_finished_unit_snapshot_impl(finished_unit_id, session)
    
    with session_scope() as session:
        return _create_finished_unit_snapshot_impl(finished_unit_id, session)

def _create_finished_unit_snapshot_impl(
    finished_unit_id: int,
    session: Session
) -> dict:
    """Internal implementation of snapshot creation."""
    
    # Load FinishedUnit with recipe
    fu = session.query(FinishedUnit).filter_by(id=finished_unit_id).first()
    if not fu:
        raise FinishedUnitNotFoundError(f"FinishedUnit {finished_unit_id} not found")
    
    # Eagerly load recipe
    _ = fu.recipe
    
    # Build definition data
    definition_data = {
        "slug": fu.slug,
        "display_name": fu.display_name,
        "description": fu.description,
        "recipe_id": fu.recipe_id,
        "recipe_name": fu.recipe.name if fu.recipe else None,
        "yield_mode": fu.yield_mode.value,
        "items_per_batch": fu.items_per_batch,
        "item_unit": fu.item_unit,
        "batch_percentage": float(fu.batch_percentage) if fu.batch_percentage else None,
        "portion_description": fu.portion_description,
        "category": fu.category,
        "production_notes": fu.production_notes,
        "notes": fu.notes,
    }
    
    # Create snapshot
    snapshot = FinishedUnitSnapshot(
        finished_unit_id=finished_unit_id,
        definition_data=definition_data,
        snapshot_date=utc_now(),
        is_backfilled=False,
    )
    
    session.add(snapshot)
    session.flush()
    
    return {
        "id": snapshot.id,
        "finished_unit_id": fu.id,
        "slug": fu.slug,
        "display_name": fu.display_name,
    }
```

### 3.3 Error Handling and Validation

**Validation Requirements:**

1. **Existence Validation:**
   - Verify source entity exists before snapshot creation
   - Return descriptive error if not found

2. **Circular Reference Detection:**
   - Track visited entities during recursive snapshot creation
   - Raise `CircularReferenceError` if loop detected
   - Maximum nesting depth: 10 levels

3. **Transaction Atomicity:**
   - All snapshots in a hierarchy created in single transaction
   - Rollback if any snapshot creation fails
   - Pass session parameter through all nested calls

4. **Foreign Key Validation:**
   - Ensure production_run_id or assembly_run_id exists (if provided)
   - Use nullable FKs for optional context references

**Error Classes:**

```python
class SnapshotCreationError(Exception):
    """Raised when snapshot creation fails."""
    pass

class CircularReferenceError(SnapshotCreationError):
    """Raised when circular dependency detected in snapshot tree."""
    pass

class MaxDepthExceededError(SnapshotCreationError):
    """Raised when snapshot nesting exceeds maximum depth."""
    pass
```

---

## Section 4: Migration Plan

### 4.1 Services Requiring New Implementations

| Service | Priority | Scope | Risk | Dependencies |
|---------|----------|-------|------|-------------|
| **FinishedGood** | P0 - Blocking | HIGH | HIGH | FinishedUnit, Material |
| **FinishedUnit** | P0 - Blocking | MEDIUM | LOW | Recipe (reference only) |
| **Material** | P1 - Critical | MEDIUM | MEDIUM | MaterialUnit |
| **Ingredient** | P2 - Desirable | LOW | LOW | None (Product already snapshot-like) |

### 4.2 Implementation Order

**Phase 1: FinishedUnit Snapshots (Foundational)**
1. Create `FinishedUnitSnapshot` model
2. Add `create_finished_unit_snapshot()` to finished_unit_service
3. Add `get_finished_unit_snapshot()` retrieval methods
4. Test snapshot creation and data capture

**Phase 2: Material Snapshots (Parallel to FinishedGood)**
1. Create `MaterialUnitSnapshot` model (if MaterialUnit exists)
2. Add `create_material_snapshot()` to material_catalog_service
3. Add `create_material_unit_snapshot()` to material_unit_service
4. Test material snapshot creation

**Phase 3: FinishedGood Snapshots (Core Feature)**
1. Create `FinishedGoodSnapshot` model
2. Implement `create_finished_good_snapshot()` with recursive support
3. Add circular reference detection
4. Integrate with Assembly service
5. Test nested snapshot creation and retrieval

**Phase 4: Planning Integration**
1. Update Planning service to call snapshot primitives
2. Create planning-phase snapshots for all definitions
3. Update AssemblyRun to reference finished_good_snapshot_id
4. Update ProductionRun to reference existing recipe_snapshot_id

**Phase 5: Ingredient Snapshots (Optional Enhancement)**
1. Create `IngredientSnapshot` model
2. Add `create_ingredient_snapshot()` to ingredient_service
3. Update ProductionConsumption to reference ingredient_snapshot_id
4. Backfill existing records (or leave nullable)

### 4.3 Backward Compatibility

**Strategy: Nullable Snapshot FKs with Gradual Migration**

```python
# AssemblyRun model update
class AssemblyRun(BaseModel):
    finished_good_id = ForeignKey("finished_goods.id", ondelete="RESTRICT")
    
    # NEW: Optional snapshot reference (nullable for backward compatibility)
    finished_good_snapshot_id = ForeignKey(
        "finished_good_snapshots.id",
        ondelete="RESTRICT",
        nullable=True,  # Allow existing records without snapshots
    )
```

**Migration Path:**
1. Add nullable `_snapshot_id` columns to production/assembly tables
2. New records REQUIRE snapshots (enforced at service level)
3. Existing records continue working (legacy mode)
4. Backfill tool creates snapshots for historical records (best-effort)
5. After backfill, make snapshot FKs non-nullable (future phase)

### 4.4 Testing Strategy

**Unit Tests:**
- Snapshot model validation (required fields, constraints)
- Service method snapshot creation (happy path)
- Service method error handling (entity not found)
- Circular reference detection
- Maximum depth enforcement

**Integration Tests:**
- End-to-end snapshot creation for complex hierarchies
- Snapshot data accuracy (all fields captured correctly)
- Snapshot immutability (definition changes don't affect snapshots)
- Recursive snapshot creation (nested FinishedGoods)
- Transaction rollback on snapshot creation failure

**Performance Tests:**
- Snapshot creation time for deep hierarchies (10 levels)
- Bulk snapshot creation for event planning (100+ recipes)
- Query performance for snapshot retrieval
- Storage impact for large snapshot datasets

**Test Coverage Target:** >85% for new snapshot services

---

## Section 5: FinishedGoods Integration

### 5.1 How FinishedGoods Should Implement Snapshots

**REQ-FG-037 Implementation:**

```python
# src/models/finished_good_snapshot.py
class FinishedGoodSnapshot(BaseModel):
    __tablename__ = "finished_good_snapshots"
    
    # Source reference
    finished_good_id = Column(
        Integer,
        ForeignKey("finished_goods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    
    # Context references (what triggered snapshot)
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    planning_snapshot_id = Column(
        Integer,
        ForeignKey("production_plan_snapshots.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Snapshot data (JSON for flexibility)
    definition_data = Column(JSON, nullable=False)
    
    # Metadata
    snapshot_date = Column(DateTime, nullable=False, default=utc_now)
    snapshot_type = Column(String(50), nullable=False)  # 'planning', 'assembly'
    is_backfilled = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    finished_good = relationship("FinishedGood", back_populates="snapshots")
    assembly_run = relationship("AssemblyRun", back_populates="snapshot", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_fg_snapshot_fg", "finished_good_id"),
        Index("idx_fg_snapshot_assembly_run", "assembly_run_id"),
        Index("idx_fg_snapshot_planning", "planning_snapshot_id"),
        Index("idx_fg_snapshot_date", "snapshot_date"),
        Index("idx_fg_snapshot_type", "snapshot_type"),
    )
```

### 5.2 Primitives FinishedGoods Service Must Provide

**Catalog Management:**
```python
def get_finished_good(slug: str) -> FinishedGood
def create_finished_good(data: dict, components: list) -> FinishedGood
def update_finished_good(slug: str, changes: dict) -> FinishedGood
def delete_finished_good(slug: str) -> bool
def list_all_finished_goods() -> List[FinishedGood]
```

**Component Management:**
```python
def add_component(fg_slug: str, component_data: dict) -> Composition
def remove_component(fg_slug: str, component_id: int) -> bool
def update_component(fg_slug: str, component_id: int, changes: dict) -> Composition
def list_components(fg_slug: str) -> List[Composition]
```

**Snapshot Management:**
```python
def create_finished_good_snapshot(
    finished_good_id: int,
    recursive: bool = True,
    assembly_run_id: Optional[int] = None,
    planning_snapshot_id: Optional[int] = None,
    session: Session = None
) -> dict

def get_snapshot_by_id(snapshot_id: int, session: Session = None) -> dict
def get_snapshots_by_finished_good(finished_good_id: int, session: Session = None) -> list
def get_snapshot_by_assembly_run(assembly_run_id: int, session: Session = None) -> dict
```

**Validation:**
```python
def validate_components(components: list) -> Tuple[bool, List[str]]
def check_circular_reference(fg_slug: str, component_slug: str) -> bool
def validate_material_selection(material_placeholder_id: int, material_unit_id: int) -> bool
```

### 5.3 Integration Points with Planning/Event/Assembly Services

**Planning Service Integration:**

```python
# src/services/planning/planning_service.py

def create_event_plan(event_id: int, session: Session) -> dict:
    """Create production plan with snapshots for all definitions."""
    
    event = session.get(Event, event_id)
    
    # Create planning snapshot container
    planning_snapshot = PlanningSnapshot(
        event_id=event_id,
        created_at=utc_now(),
    )
    session.add(planning_snapshot)
    session.flush()
    
    # Snapshot all recipes for production targets
    for target in event.production_targets:
        recipe_snapshot = recipe_service.create_recipe_snapshot(
            recipe_id=target.recipe_id,
            scale_factor=1.0,
            planning_snapshot_id=planning_snapshot.id,
            session=session
        )
        # Store snapshot reference in target
        target.recipe_snapshot_id = recipe_snapshot["id"]
    
    # Snapshot all finished goods for assembly targets (recursive)
    for target in event.assembly_targets:
        fg_snapshot = finished_good_service.create_finished_good_snapshot(
            finished_good_id=target.finished_good_id,
            recursive=True,  # Captures nested components
            planning_snapshot_id=planning_snapshot.id,
            session=session
        )
        # Store snapshot reference in target
        target.finished_good_snapshot_id = fg_snapshot["id"]
    
    # Calculate batch requirements using snapshots
    batch_requirements = _calculate_batch_requirements_from_snapshots(
        planning_snapshot.id, session
    )
    
    # Store calculation results
    planning_snapshot.calculation_results = batch_requirements
    
    return {
        "planning_snapshot_id": planning_snapshot.id,
        "recipe_snapshots": len(event.production_targets),
        "finished_good_snapshots": len(event.assembly_targets),
        "batch_requirements": batch_requirements,
    }
```

**Assembly Service Integration:**

```python
# src/services/assembly_service.py

def record_assembly(
    finished_good_id: int,
    quantity_assembled: int,
    event_id: Optional[int] = None,
    session: Session = None
) -> dict:
    """
    Record assembly of FinishedGood with snapshot creation.
    
    Captures immutable snapshot of FinishedGood definition at assembly time.
    """
    
    # Create AssemblyRun (placeholder to get ID)
    assembly_run = AssemblyRun(
        finished_good_id=finished_good_id,
        quantity_assembled=quantity_assembled,
        assembled_at=utc_now(),
        event_id=event_id,
    )
    session.add(assembly_run)
    session.flush()
    
    # Create snapshot (with nested components)
    fg_snapshot = finished_good_service.create_finished_good_snapshot(
        finished_good_id=finished_good_id,
        recursive=True,
        assembly_run_id=assembly_run.id,
        session=session
    )
    
    # Link snapshot to assembly run
    assembly_run.finished_good_snapshot_id = fg_snapshot["id"]
    
    # Consume components using snapshot data (not live definitions)
    snapshot_data = fg_snapshot["definition_data"]
    for component in snapshot_data["components"]:
        if component["component_type"] == "finished_unit":
            # Consume FinishedUnit inventory
            finished_unit_service.consume_inventory(
                finished_unit_id=component["finished_unit_snapshot_id"],
                quantity=component["component_quantity"] * quantity_assembled,
                session=session
            )
        elif component["component_type"] == "material_unit":
            # Consume Material inventory
            material_service.consume_material_unit(
                material_unit_id=component["material_unit_snapshot_id"],
                quantity=component["component_quantity"] * quantity_assembled,
                session=session
            )
    
    # Calculate total cost from component consumption
    assembly_run.total_component_cost = _calculate_assembly_cost_from_snapshot(
        fg_snapshot["id"], quantity_assembled, session
    )
    assembly_run.per_unit_cost = assembly_run.total_component_cost / quantity_assembled
    
    return {
        "assembly_run_id": assembly_run.id,
        "finished_good_snapshot_id": fg_snapshot["id"],
        "quantity_assembled": quantity_assembled,
        "total_cost": str(assembly_run.total_component_cost),
        "per_unit_cost": str(assembly_run.per_unit_cost),
    }
```

### 5.4 Example: Snapshot Creation for Nested FinishedGood

**Scenario:** Holiday Cookie Assortment (FinishedGood) containing 6 Chocolate Chip Cookies (FinishedUnit), 6 Sugar Cookies (FinishedUnit), and 1 Gift Box (MaterialUnit).

**Structure:**
```
FinishedGood: "Holiday Cookie Assortment"
├─ Component: Chocolate Chip Cookie (FinishedUnit) × 6
├─ Component: Sugar Cookie (FinishedUnit) × 6
└─ Component: Gift Box (MaterialUnit) × 1
```

**Snapshot Creation:**

```python
# Planning service calls snapshot creation
fg_snapshot = finished_good_service.create_finished_good_snapshot(
    finished_good_id=123,  # "Holiday Cookie Assortment"
    recursive=True,
    planning_snapshot_id=456,
    session=session
)

# Result:
{
    "id": 789,  # finished_good_snapshot.id
    "finished_good_id": 123,
    "definition_data": {
        "slug": "holiday-cookie-assortment",
        "display_name": "Holiday Cookie Assortment",
        "assembly_type": "gift_box",
        "components": [
            {
                "component_type": "finished_unit",
                "finished_unit_snapshot_id": 111,  # Chocolate Chip snapshot
                "component_slug": "chocolate-chip-cookie",
                "component_name": "Chocolate Chip Cookie",
                "component_quantity": 6,
            },
            {
                "component_type": "finished_unit",
                "finished_unit_snapshot_id": 222,  # Sugar Cookie snapshot
                "component_slug": "sugar-cookie",
                "component_name": "Sugar Cookie",
                "component_quantity": 6,
            },
            {
                "component_type": "material_unit",
                "material_unit_snapshot_id": 333,  # Gift Box snapshot
                "component_slug": "6x6-gift-box",
                "component_name": "6x6 Gift Box",
                "component_quantity": 1,
            }
        ]
    },
    "snapshot_type": "planning"
}
```

**Nested FinishedGood Example:**

```
FinishedGood: "Deluxe Gift Tower"
├─ Component: Holiday Cookie Assortment (FinishedGood) × 2
│   ├─ Chocolate Chip Cookie (FinishedUnit) × 6
│   ├─ Sugar Cookie (FinishedUnit) × 6
│   └─ Gift Box (MaterialUnit) × 1
├─ Component: Brownie Trio (FinishedUnit) × 1
└─ Component: Decorative Ribbon (MaterialUnit) × 1
```

**Recursive Snapshot Creation:**

```python
# Create snapshot for "Deluxe Gift Tower"
tower_snapshot = finished_good_service.create_finished_good_snapshot(
    finished_good_id=456,  # "Deluxe Gift Tower"
    recursive=True,
    planning_snapshot_id=789,
    session=session
)

# Result includes nested snapshots:
{
    "id": 999,
    "finished_good_id": 456,
    "definition_data": {
        "slug": "deluxe-gift-tower",
        "display_name": "Deluxe Gift Tower",
        "components": [
            {
                "component_type": "finished_good",
                "finished_good_snapshot_id": 888,  # Nested FG snapshot
                "component_slug": "holiday-cookie-assortment",
                "component_name": "Holiday Cookie Assortment",
                "component_quantity": 2,
                # Nested snapshot 888 contains full component tree
            },
            {
                "component_type": "finished_unit",
                "finished_unit_snapshot_id": 444,
                "component_slug": "brownie-trio",
                "component_name": "Brownie Trio",
                "component_quantity": 1,
            },
            {
                "component_type": "material_unit",
                "material_unit_snapshot_id": 555,
                "component_slug": "1in-satin-ribbon",
                "component_name": "1 inch Satin Ribbon",
                "component_quantity": 1,
            }
        ]
    }
}
```

---

## Section 6: Conclusion

### 6.1 Summary of Findings

1. **Current State:** Only Recipe has full snapshot support; other catalog services lack snapshot implementations.

2. **Architectural Gaps:** No universal snapshot pattern exists; inconsistent approaches across services.

3. **Service Boundaries:** Recipe demonstrates correct catalog service ownership pattern; Planning demonstrates orchestration without ownership.

4. **Blocking Issue:** FinishedGoods implementation REQUIRES architectural decision on snapshot pattern before proceeding.

### 6.2 Recommended Universal Pattern

**Adopt Catalog Service Ownership with Mirrored Tables (Pattern A):**
- Each catalog service provides `create_snapshot()` primitive
- Snapshots stored in dedicated mirrored tables with JSON for flexibility
- Planning/Production/Assembly services orchestrate snapshot creation
- Recursive snapshot support for nested relationships
- Circular reference detection prevents infinite loops

### 6.3 Implementation Priorities

| Priority | Service | Dependencies | Risk |
|----------|---------|-------------|------|
| **P0** | FinishedUnit | None (Recipe reference only) | LOW |
| **P0** | FinishedGood | FinishedUnit, Material | HIGH |
| **P1** | Material/MaterialUnit | None | MEDIUM |
| **P2** | Ingredient | None | LOW |

### 6.4 Next Steps

1. **Approve Architecture:** Confirm Pattern A (Mirrored Tables + Catalog Ownership) as universal pattern
2. **Create Models:** Implement `FinishedUnitSnapshot` and `FinishedGoodSnapshot` models
3. **Implement Services:** Add snapshot creation methods to finished_unit_service and finished_good_service
4. **Integrate Planning:** Update planning service to create snapshots during event planning
5. **Integrate Assembly:** Update assembly service to reference snapshots during assembly recording
6. **Test Thoroughly:** Unit + integration tests for snapshot creation, retrieval, and immutability
7. **Document:** Update requirements and technical docs with snapshot architecture

### 6.5 Open Questions for User

1. **Backward Compatibility:** Should we backfill snapshots for existing ProductionRuns/AssemblyRuns, or leave them nullable?
2. **Snapshot Retention:** Should snapshots be kept indefinitely, or archived after N years?
3. **Ingredient Snapshots:** Is full ingredient snapshot implementation desired (P2), or can we defer this?
4. **Planning Snapshot Trigger:** Should snapshots be created when event is created, or when planning is finalized?

---

**END OF RESEARCH FINDINGS**

---

## Appendices

### Appendix A: File Reference Index

**Models:**
- `src/models/recipe_snapshot.py` - RecipeSnapshot (complete implementation)
- `src/models/production_plan_snapshot.py` - ProductionPlanSnapshot (calculation cache)
- `src/models/inventory_snapshot.py` - InventorySnapshot (planning input)
- `src/models/production_run.py` - ProductionRun (references recipe_snapshot_id)
- `src/models/assembly_run.py` - AssemblyRun (needs finished_good_snapshot_id)
- `src/models/composition.py` - Composition (FinishedGood components)

**Services:**
- `src/services/recipe_snapshot_service.py` - Recipe snapshot CRUD
- `src/services/batch_production_service.py` - Production with snapshot creation
- `src/services/assembly_service.py` - Assembly (needs snapshot integration)
- `src/services/planning/planning_service.py` - Planning orchestration
- `src/services/finished_good_service.py` - FinishedGood catalog (needs snapshots)
- `src/services/finished_unit_service.py` - FinishedUnit catalog (needs snapshots)
- `src/services/ingredient_service.py` - Ingredient catalog (missing snapshots)
- `src/services/material_catalog_service.py` - Material catalog (missing snapshots)

**Requirements:**
- `docs/requirements/req_finished_goods.md` - FinishedGoods requirements (REQ-FG-037)
- `docs/requirements/req_recipes.md` - Recipe requirements (snapshot section)
- `docs/requirements/req_materials.md` - Materials requirements (identity snapshot)

### Appendix B: Code Examples Index

All code examples in this document are based on actual codebase implementations:
- RecipeSnapshot implementation: Working reference in production
- FinishedGoodSnapshot implementation: Recommended pattern (not yet implemented)
- Snapshot creation flows: Based on existing batch_production_service pattern
- Service integration: Modeled after recipe_snapshot_service + batch_production_service

### Appendix C: Glossary

- **Definition:** Mutable catalog entity (Recipe, Ingredient, FinishedGood)
- **Instantiation:** Immutable snapshot or production record (RecipeSnapshot, AssemblyRun)
- **Snapshot:** Immutable capture of definition state at specific point in time
- **Catalog Service:** Service managing definitions (recipe_service, finished_good_service)
- **Planning Service:** Orchestration service that coordinates snapshot creation
- **Mirrored Table:** Dedicated snapshot table that mirrors definition structure
- **Recursive Snapshot:** Snapshot that includes nested component snapshots
- **Circular Reference:** Invalid nesting where entity contains itself (directly or transitively)
