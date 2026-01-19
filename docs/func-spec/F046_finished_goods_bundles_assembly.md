# Finished Goods, Bundles & Assembly Tracking - Feature Specification

**Feature ID**: F046
**Feature Name**: Finished Goods, Bundles & Assembly Tracking
**Priority**: P1 - FOUNDATIONAL (blocks F047, F048, event planning completion)
**Status**: Design Specification
**Created**: 2026-01-09
**Dependencies**: F045 (Cost Architecture Refactor ✅)
**Blocks**: F047 (Shopping Lists), F048 (Assembly Workflows), Complete Event Planning
**Constitutional References**: Principle I (User-Centric Design), Principle III (Data Integrity), Principle V (Layered Architecture)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, UI mockups, and implementation patterns. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification

**The requirements are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

**Problem**: From 2026-01-07 user testing + architectural analysis:
- **"Finished Goods button goes nowhere"** - Cannot define gift boxes, bundles, packages
- Missing assembly tracking workflow (cannot record when gift boxes are assembled)
- AssemblyRun lacks cost snapshots (violates definition/instantiation pattern)
- No component consumption tracking (which FinishedUnits were used?)
- Event planning cannot use assembled packages (workflow incomplete)
- **Package model uses removed field** (`finished_good.total_cost` removed in F045)

**Current State**: 
- FinishedGood model exists but incomplete (no cost snapshot architecture)
- Package model exists but broken (references removed `total_cost` field)
- AssemblyRun model exists but lacks critical fields (no cost tracking)
- No UI for FinishedGood management
- No assembly recording workflow

**Solution**: Complete the Finished Goods → Package → Event chain:
- Implement FinishedGood CRUD with dynamic cost calculation (internal use only)
- **Fix Package model** to use dynamic cost calculation (for event planning)
- **Complete definition/instantiation pattern**: Add cost snapshots to AssemblyRun
- Add AssemblyConsumption junction to track component usage (follows ProductionRun pattern)
- Finished Goods tab in CATALOG mode (manage definitions, NO cost display)
- Assembly recording in MAKE mode (create instances with cost snapshots)

**Impact**:
- Completes Plan → Make → Assemble → Deliver workflow
- Enables full event planning (can now assign packages to recipients)
- Achieves architecture pattern compliance (costs on instances, not definitions)
- Foundation for F047 (Shopping Lists based on event assignments)
- Foundation for F048 (Assembly workflows with proper tracking)

**Scope**:
- FinishedGood model: Dynamic cost calculation methods (no stored costs, internal use only)
- **Package model: Fix cost calculations** (use dynamic, not removed `total_cost`)
- AssemblyRun model: Add `total_component_cost`, `per_assembly_cost` fields
- AssemblyConsumption model: Track which FinishedUnits consumed (NEW)
- Finished Goods tab (CATALOG mode): CRUD operations, **NO cost display**
- Assembly recording (MAKE mode): Record assembly with cost snapshots
- Service layer: FinishedGoodService, enhanced AssemblyService

---

## 1. Problem Statement

### 1.1 Missing Finished Goods Definitions

**From user testing (2026-01-07):**
> "Finished Goods button goes nowhere"

**From architectural analysis (2026-01-09):**
> AssemblyRun incomplete - no cost snapshot, violates definition/instantiation pattern

**From code review (2026-01-09):**
> Package.calculate_cost() references `finished_good.total_cost` which was REMOVED in F045

**Current Workflow (Broken):**
```
Baker: "I want to create a Holiday Gift Box with 4 Large Cookies + 2 Brownies"
System: "What's a 'Holiday Gift Box'? I only know individual cookies and brownies"
Baker: *Cannot proceed with event planning*

Event Planning: Tries to calculate package cost
System: AttributeError - 'FinishedGood' has no attribute 'total_cost'
Event Planning: *Crashes* ❌
```

**Desired Workflow:**
```
CATALOG Mode → Finished Goods tab:
  Baker: Creates FinishedGood "Holiday Gift Box"
    - Component 1: 4 × Large Cookie (FinishedUnit)
    - Component 2: 2 × Brownie (FinishedUnit)
  System: Stores structure only (NO costs displayed)

PLAN Mode → Event Planning:
  Baker: Assigns Package to recipient (Package contains Holiday Gift Box)
  System: Calculates current planning cost dynamically (for budgeting)
  System: $3.24 per box (based on current ingredient prices)

MAKE Mode → Assembly:
  Baker: Records "Assembled 50 Holiday Gift Boxes on 2026-01-09"
  System: Captures cost snapshot ($3.24 per box based on FIFO at assembly time)
  System: Tracks consumption (200 Large Cookies, 100 Brownies from inventory)
  System: Decrements FinishedUnit inventory_count via FIFO
```

### 1.2 Definition vs Instantiation Pattern Requirements

**Current State (Incomplete + Broken):**
```python
# Definition (correct - no stored costs, but broken Package reference)
class FinishedGood:
    display_name: str
    components: List[Composition]
    # total_cost: Decimal  ✅ REMOVED in F045

class Package:
    def calculate_cost(self):
        # ❌ BROKEN: references removed field
        fg_cost = pfg.finished_good.total_cost  # AttributeError!

# Instantiation (incomplete - missing cost fields)
class AssemblyRun:
    finished_good_id: int
    quantity: int
    assembled_at: datetime
    # ❌ Missing: total_component_cost
    # ❌ Missing: per_assembly_cost
```

**Target State (Complete Pattern):**
```python
# Definition (costs calculated dynamically, internal use only)
class FinishedGood:
    display_name: str
    components: List[Composition]
    
    def calculate_current_cost(self) -> Decimal:
        """Calculate cost from current component costs (no storage).
        INTERNAL USE: Assembly recording, event planning.
        NOT DISPLAYED: Catalog UI never shows costs."""
        return sum(comp.quantity * comp.finished_unit.calculate_current_cost() 
                   for comp in self.components)

class Package:
    def calculate_cost(self) -> Decimal:
        """Calculate package cost for event planning (dynamic).
        Uses FinishedGood.calculate_current_cost() not removed total_cost."""
        return sum(pfg.finished_good.calculate_current_cost() * pfg.quantity
                   for pfg in self.package_finished_goods)

# Instantiation (costs captured as immutable snapshots)
class AssemblyRun:
    finished_good_id: int
    quantity: int
    assembled_at: datetime
    total_component_cost: Decimal  # ✅ Snapshot at assembly time
    per_assembly_cost: Decimal     # ✅ Cost per assembled unit
    
# Component consumption tracking (NEW)
class AssemblyConsumption:
    assembly_run_id: int
    finished_unit_id: int
    quantity_consumed: int
    per_unit_cost: Decimal  # Cost of this component at assembly time
```

**Pattern Analogy** (follows ProductionRun precedent):
```
Recipe (definition) → ProductionRun (instantiation + cost snapshot)
  └─ ProductionConsumption tracks ingredients consumed

FinishedGood (definition) → AssemblyRun (instantiation + cost snapshot)
  └─ AssemblyConsumption tracks FinishedUnits consumed

Package (definition) → Uses FinishedGood.calculate_current_cost() for planning
  └─ No instantiation (packages assigned to events, not produced)
```

### 1.3 Real-World Use Cases

**Use Case 1: Holiday Gift Box**
```
FinishedGood: Holiday Gift Box (definition)
  Components:
    - 4 × Large Cookie (FinishedUnit)
    - 2 × Brownie (FinishedUnit)
    - 1 × Decorative Box (packaging ingredient)
  
Current Cost (dynamic, internal only): $3.24 per box
  (calculated from current component costs, not stored, not displayed in catalog)

AssemblyRun (instance):
  Date: 2026-01-09
  Quantity: 50 boxes
  total_component_cost: $162.00  # Snapshot at assembly
  per_assembly_cost: $3.24       # $162.00 ÷ 50
  
AssemblyConsumption records:
  - 200 Large Cookies consumed @ $0.42 each = $84.00
  - 100 Brownies consumed @ $0.65 each = $65.00
  - 50 Decorative Boxes consumed @ $0.26 each = $13.00
  Total: $162.00
```

**Use Case 2: Event Planning with Packages**
```
Package: Deluxe Holiday Package (definition)
  Contains:
    - 6 × Holiday Gift Box (FinishedGood)
  
Event Planning (dynamic cost for budgeting):
  Package.calculate_cost() = 6 × $3.24 = $19.44
  (uses FinishedGood.calculate_current_cost(), not removed total_cost)
  
Assign 10 packages to recipients:
  Total planned cost: 10 × $19.44 = $194.40
  
Later, after assembly:
  Actual cost from AssemblyRun snapshots: $198.00 (ingredients rose)
  Variance: +$3.60 (1.9% over budget)
```

**Use Case 3: Historical Cost Accuracy**
```
January: Chocolate chips cost $300
  - Assemble 100 gift boxes
  - AssemblyRun captures cost: $2.80 per box

June: Chocolate chips rise to $600
  - Assemble another 100 gift boxes
  - AssemblyRun captures cost: $4.20 per box

Report Query: "What did gift boxes cost in January?"
  Answer: $2.80 per box (from AssemblyRun snapshot, not current cost)

Event Planning Query: "What would gift boxes cost today?"
  Answer: $4.20 per box (from FinishedGood.calculate_current_cost())
```

### 1.4 Why This Blocks Other Features

**Event Planning (CURRENTLY BROKEN)**: Package cost calculation crashes
```
Cannot calculate: Package cost for event budgeting
Blocked: Package.calculate_cost() references removed total_cost field
Error: AttributeError: 'FinishedGood' object has no attribute 'total_cost'
```

**F047 (Shopping Lists)**: Cannot generate shopping lists without assembly definitions
```
Cannot calculate: Ingredients needed for "50 Holiday Gift Boxes"
Blocked: Need to know what components are in a gift box
```

**F048 (Assembly Workflows)**: Cannot track assembly without cost snapshots
```
Cannot record: "Assembled 50 gift boxes on 1/9/2026 at $3.24 each"
Blocked: AssemblyRun lacks cost fields
```

---

## 2. Proposed Solution

### 2.1 Architecture Overview

**Data Model Hierarchy:**
```
FinishedUnit (leaf node - produced by recipes)
  ↓ (used in)
FinishedGood (composite - assembly of FinishedUnits)
  ↓ (used in)
Package (collection of FinishedGoods)
  ↓ (assigned to)
EventRecipientPackage (recipient gets packages)
```

**Definition vs Instantiation:**
```
DEFINITIONS (no stored costs):
  - FinishedUnit: What recipes produce
  - FinishedGood: How to assemble units (costs calculated internally)
  - Package: What to give (costs calculated for planning)

INSTANTIATIONS (cost snapshots):
  - ProductionRun: Batch production with ingredient costs
  - AssemblyRun: Assembly with component costs (ENHANCED in F046)
  - AssemblyConsumption: Component tracking (NEW in F046)
```

**Cost Flow:**
```
Purchase (FIFO) → InventoryItem
  ↓ (consumed for)
ProductionRun → FinishedUnit inventory
  ↓ (consumed for)
AssemblyRun → Finished assemblies (not stored, delivered)
  ↓ (assigned via)
EventRecipientPackage → Delivery
```

**Cost Calculation Points:**
```
1. CATALOG mode (FinishedGood definition):
   - NO costs displayed
   - calculate_current_cost() exists but NOT called by UI

2. PLAN mode (Event planning):
   - Package.calculate_cost() uses FinishedGood.calculate_current_cost()
   - Shows "what would this cost NOW" for budgeting
   - Dynamic, changes as ingredient prices fluctuate

3. MAKE mode (Assembly recording):
   - AssemblyRun captures cost snapshot at assembly time
   - Immutable, shows "what DID this cost THEN"
   - Historical accuracy preserved
```

### 2.2 Database Schema Changes

#### 2.2.1 New Table: AssemblyConsumption

**Purpose**: Track which FinishedUnits were consumed in an assembly run (analogous to ProductionConsumption for ingredients)

```sql
CREATE TABLE assembly_consumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    
    -- Link to assembly run
    assembly_run_id INTEGER NOT NULL,
    FOREIGN KEY (assembly_run_id) REFERENCES assembly_runs(id) ON DELETE CASCADE,
    
    -- Link to finished unit consumed
    finished_unit_id INTEGER NOT NULL,
    FOREIGN KEY (finished_unit_id) REFERENCES finished_units(id) ON DELETE RESTRICT,
    
    -- Consumption details
    quantity_consumed INTEGER NOT NULL CHECK (quantity_consumed > 0),
    per_unit_cost NUMERIC(10, 4) NOT NULL CHECK (per_unit_cost >= 0),
    
    -- Audit timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assembly_consumption_assembly_run 
    ON assembly_consumptions(assembly_run_id);
CREATE INDEX idx_assembly_consumption_finished_unit 
    ON assembly_consumptions(finished_unit_id);
```

#### 2.2.2 Enhanced Table: AssemblyRun

**Add cost snapshot fields:**

```sql
ALTER TABLE assembly_runs 
    ADD COLUMN total_component_cost NUMERIC(10, 4) NOT NULL DEFAULT 0.0 
    CHECK (total_component_cost >= 0);

ALTER TABLE assembly_runs 
    ADD COLUMN per_assembly_cost NUMERIC(10, 4) NOT NULL DEFAULT 0.0 
    CHECK (per_assembly_cost >= 0);

COMMENT ON COLUMN assembly_runs.total_component_cost IS 
    'Total cost of all components at assembly time (snapshot)';
COMMENT ON COLUMN assembly_runs.per_assembly_cost IS 
    'Cost per assembled unit (total_component_cost / quantity)';
```

**Existing AssemblyRun fields (no changes):**
```sql
CREATE TABLE assembly_runs (
    id INTEGER PRIMARY KEY,
    finished_good_id INTEGER NOT NULL,  -- What was assembled
    event_id INTEGER,                   -- Optional event context
    quantity INTEGER NOT NULL,          -- How many assembled
    assembled_at TIMESTAMP NOT NULL,    -- When assembled
    notes TEXT,
    -- NEW FIELDS ADDED ABOVE
);
```

#### 2.2.3 No Changes to Package/PackageFinishedGood Tables

**Existing tables work correctly** - only model code needs fixing:
- Package table: No schema changes
- PackageFinishedGood junction: No schema changes
- Only code fix: Change `total_cost` → `calculate_current_cost()` in Package model

### 2.3 Model Changes

#### 2.3.1 FinishedGood Model (Enhanced)

**File**: `src/models/finished_good.py`

```python
class FinishedGood(BaseModel):
    """
    FinishedGood model (DEFINITION - no stored costs).
    
    Represents an assembly of FinishedUnits (e.g., "Holiday Gift Box").
    Costs calculated dynamically ONLY for internal operations.
    Costs NOT displayed in catalog UI.
    """
    
    __tablename__ = "finished_goods"
    
    display_name = Column(String(200), nullable=False, index=True)
    assembly_type = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    components = relationship(
        "Composition", 
        back_populates="finished_good",
        cascade="all, delete-orphan"
    )
    assembly_runs = relationship(
        "AssemblyRun",
        back_populates="finished_good"
    )
    
    def calculate_current_cost(self) -> Decimal:
        """
        Calculate current cost from component costs (dynamic, not stored).
        
        INTERNAL USE ONLY:
        - Called during assembly recording (creates cost snapshot)
        - Called during event planning (Package.calculate_cost())
        - NOT displayed in catalog UI (definitions don't show prices)
        
        Follows definition/instantiation pattern: definitions have no stored costs.
        Cost calculated fresh each time from current component inventory costs.
        
        Returns:
            Current total cost for one assembly
        """
        total = Decimal("0.0000")
        for composition in self.components:
            # Get current cost of component FinishedUnit
            component_cost = composition.finished_unit.calculate_current_cost()
            # Multiply by quantity needed
            total += component_cost * Decimal(str(composition.quantity))
        return total
    
    def get_component_breakdown(self) -> List[Dict]:
        """
        Get detailed component breakdown (NO COSTS).
        
        Used by catalog UI to show structure without prices.
        
        Returns:
            List of dicts with component details (NO costs included)
        """
        breakdown = []
        for comp in self.components:
            breakdown.append({
                "finished_unit_id": comp.finished_unit_id,
                "finished_unit_name": comp.finished_unit.display_name,
                "quantity": comp.quantity,
                # NO COSTS - catalog UI doesn't display prices
            })
        return breakdown
    
    def to_dict(self, include_relationships: bool = False) -> dict:
        """Convert to dictionary."""
        result = super().to_dict(include_relationships)
        
        # DO NOT include current_cost in default serialization
        # Cost only calculated when explicitly needed (assembly, planning)
        
        if include_relationships:
            result["component_breakdown"] = self.get_component_breakdown()
        
        return result
```

#### 2.3.2 Package Model (FIXED)

**File**: `src/models/package.py`

**CRITICAL FIX**: Change from removed `total_cost` field to dynamic `calculate_current_cost()` method

```python
class Package(BaseModel):
    """
    Package model (DEFINITION - no stored costs).
    
    Represents packages for events. Costs calculated dynamically
    for event planning (budgeting) using current ingredient prices.
    """
    
    # ... existing fields ...
    
    def calculate_cost(self) -> Decimal:
        """
        Calculate total cost of package from FinishedGood costs.
        
        FIXED IN F046: Uses FinishedGood.calculate_current_cost() instead
        of removed total_cost field.
        
        Used for event planning (budgeting): "what would this cost NOW?"
        
        Cost calculation chains through:
        Package → FinishedGood.calculate_current_cost() → 
        FinishedUnit.calculate_current_cost() → FIFO inventory costs
        
        Returns:
            Total cost as Decimal (sum of all FinishedGood costs * quantities)
        """
        if not self.package_finished_goods:
            return Decimal("0.00")

        total_cost = Decimal("0.00")
        for pfg in self.package_finished_goods:
            if pfg.finished_good:
                # FIXED: Use calculate_current_cost() not removed total_cost
                fg_cost = pfg.finished_good.calculate_current_cost()
                total_cost += fg_cost * Decimal(str(pfg.quantity))

        return total_cost

    def get_cost_breakdown(self) -> list:
        """
        Get detailed cost breakdown by FinishedGood.
        
        FIXED IN F046: Uses calculate_current_cost() not removed total_cost.
        
        Used for event planning cost analysis.
        
        Returns:
            List of dictionaries with item name, quantity, unit cost, and line total
        """
        if not self.package_finished_goods:
            return []

        breakdown = []
        for pfg in self.package_finished_goods:
            if pfg.finished_good:
                fg = pfg.finished_good
                # FIXED: Use calculate_current_cost() not removed total_cost
                unit_cost = fg.calculate_current_cost()
                line_total = unit_cost * Decimal(str(pfg.quantity))
                breakdown.append(
                    {
                        "finished_good_id": fg.id,
                        "name": fg.display_name,
                        "quantity": pfg.quantity,
                        "unit_cost": float(unit_cost),
                        "line_total": float(line_total),
                    }
                )

        return breakdown
```

#### 2.3.3 AssemblyRun Model (Enhanced)

**File**: `src/models/assembly_run.py`

```python
class AssemblyRun(BaseModel):
    """
    AssemblyRun model (INSTANTIATION - cost snapshot).
    
    Records when FinishedGoods are assembled, capturing:
    - WHAT was assembled (finished_good_id)
    - WHEN it was assembled (assembled_at)
    - HOW MANY were assembled (quantity)
    - WHAT IT COST at assembly time (total_component_cost, per_assembly_cost)
    
    Follows definition/instantiation pattern: costs captured as immutable snapshots.
    """
    
    __tablename__ = "assembly_runs"
    
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    quantity = Column(Integer, nullable=False)
    assembled_at = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)
    
    # F046: Cost snapshot fields (immutable after creation)
    total_component_cost = Column(
        Numeric(10, 4), 
        nullable=False, 
        default=Decimal("0.0000")
    )
    per_assembly_cost = Column(
        Numeric(10, 4), 
        nullable=False, 
        default=Decimal("0.0000")
    )
    
    # Relationships
    finished_good = relationship("FinishedGood", back_populates="assembly_runs")
    event = relationship("Event", back_populates="assembly_runs")
    consumptions = relationship(
        "AssemblyConsumption",
        back_populates="assembly_run",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_assembly_run_quantity_positive"),
        CheckConstraint(
            "total_component_cost >= 0", 
            name="ck_assembly_run_total_cost_non_negative"
        ),
        CheckConstraint(
            "per_assembly_cost >= 0", 
            name="ck_assembly_run_per_cost_non_negative"
        ),
    )
    
    def to_dict(self, include_relationships: bool = False) -> dict:
        """Convert to dictionary."""
        result = super().to_dict(include_relationships)
        
        # Format Decimals as strings for JSON
        if self.total_component_cost is not None:
            result["total_component_cost"] = str(self.total_component_cost)
        if self.per_assembly_cost is not None:
            result["per_assembly_cost"] = str(self.per_assembly_cost)
        
        if include_relationships:
            result["finished_good_name"] = (
                self.finished_good.display_name if self.finished_good else None
            )
            result["consumptions"] = [
                c.to_dict() for c in self.consumptions
            ]
        
        return result
```

#### 2.3.4 AssemblyConsumption Model (NEW)

**File**: `src/models/assembly_consumption.py` (NEW FILE)

```python
"""
AssemblyConsumption model for tracking component usage in assembly runs.

Analogous to ProductionConsumption for ingredient tracking.
"""

from decimal import Decimal
from sqlalchemy import Column, Integer, Numeric, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship

from .base import BaseModel


class AssemblyConsumption(BaseModel):
    """
    AssemblyConsumption junction model.
    
    Links AssemblyRun to FinishedUnit, tracking:
    - Which FinishedUnits were consumed
    - How many were consumed
    - What each unit cost at assembly time
    
    Enables:
    - Component consumption ledger (analogous to ingredient FIFO)
    - Historical cost accuracy per component
    - Assembly cost breakdown reports
    """
    
    __tablename__ = "assembly_consumptions"
    
    # Foreign keys
    assembly_run_id = Column(
        Integer,
        ForeignKey("assembly_runs.id", ondelete="CASCADE"),
        nullable=False
    )
    finished_unit_id = Column(
        Integer,
        ForeignKey("finished_units.id", ondelete="RESTRICT"),
        nullable=False
    )
    
    # Consumption details
    quantity_consumed = Column(Integer, nullable=False)
    per_unit_cost = Column(Numeric(10, 4), nullable=False)
    
    # Relationships
    assembly_run = relationship(
        "AssemblyRun",
        back_populates="consumptions"
    )
    finished_unit = relationship("FinishedUnit")
    
    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "quantity_consumed > 0",
            name="ck_assembly_consumption_quantity_positive"
        ),
        CheckConstraint(
            "per_unit_cost >= 0",
            name="ck_assembly_consumption_cost_non_negative"
        ),
        Index("idx_assembly_consumption_assembly_run", "assembly_run_id"),
        Index("idx_assembly_consumption_finished_unit", "finished_unit_id"),
    )
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost for this consumption."""
        return self.per_unit_cost * self.quantity_consumed
    
    def to_dict(self, include_relationships: bool = False) -> dict:
        """Convert to dictionary."""
        result = super().to_dict(include_relationships)
        
        # Format Decimal as string
        result["per_unit_cost"] = str(self.per_unit_cost)
        result["total_cost"] = str(self.total_cost)
        
        if include_relationships and self.finished_unit:
            result["finished_unit_name"] = self.finished_unit.display_name
        
        return result
```

### 2.4 Service Layer Changes

#### 2.4.1 Enhanced AssemblyService

**File**: `src/services/assembly_service.py`

```python
def record_assembly_run(
    finished_good_id: int,
    quantity: int,
    assembled_at: Optional[datetime] = None,
    event_id: Optional[int] = None,
    notes: Optional[str] = None,
    session=None
) -> AssemblyRun:
    """
    Record an assembly run with cost snapshot and component consumption.
    
    This is the instantiation of the FinishedGood definition:
    - Captures FIFO costs at assembly time (immutable snapshot)
    - Tracks which FinishedUnits were consumed
    - Decrements FinishedUnit.inventory_count
    
    Args:
        finished_good_id: FinishedGood being assembled
        quantity: Number of assemblies
        assembled_at: Assembly timestamp (defaults to now)
        event_id: Optional event context
        notes: Optional notes
        session: SQLAlchemy session
    
    Returns:
        Created AssemblyRun with cost snapshot
    
    Raises:
        ValueError: If insufficient inventory for components
    """
    if session is not None:
        return _record_assembly_run_impl(
            finished_good_id, quantity, assembled_at, event_id, notes, session
        )
    
    with session_scope() as session:
        return _record_assembly_run_impl(
            finished_good_id, quantity, assembled_at, event_id, notes, session
        )


def _record_assembly_run_impl(
    finished_good_id: int,
    quantity: int,
    assembled_at: Optional[datetime],
    event_id: Optional[int],
    notes: Optional[str],
    session
) -> AssemblyRun:
    """Implementation with session."""
    
    # 1. Get finished good definition
    finished_good = session.query(FinishedGood).get(finished_good_id)
    if not finished_good:
        raise ValueError(f"FinishedGood {finished_good_id} not found")
    
    # 2. Check inventory availability for all components
    for composition in finished_good.components:
        needed = composition.quantity * quantity
        available = composition.finished_unit.inventory_count
        
        if available < needed:
            raise ValueError(
                f"Insufficient inventory for {composition.finished_unit.display_name}: "
                f"need {needed}, have {available}"
            )
    
    # 3. Calculate costs and create consumption records
    total_component_cost = Decimal("0.0000")
    consumptions = []
    
    for composition in finished_good.components:
        # Get current cost of this component
        unit_cost = composition.finished_unit.calculate_current_cost()
        quantity_needed = composition.quantity * quantity
        component_total_cost = unit_cost * quantity_needed
        
        # Create consumption record
        consumption = AssemblyConsumption(
            finished_unit_id=composition.finished_unit_id,
            quantity_consumed=quantity_needed,
            per_unit_cost=unit_cost
        )
        consumptions.append(consumption)
        
        # Accumulate total cost
        total_component_cost += component_total_cost
        
        # Decrement inventory (FIFO consumption)
        composition.finished_unit.inventory_count -= quantity_needed
    
    # 4. Calculate per-assembly cost
    per_assembly_cost = total_component_cost / quantity if quantity > 0 else Decimal("0.0000")
    
    # 5. Create assembly run with cost snapshot
    assembly_run = AssemblyRun(
        finished_good_id=finished_good_id,
        quantity=quantity,
        assembled_at=assembled_at or utc_now(),
        event_id=event_id,
        notes=notes,
        total_component_cost=total_component_cost,  # Immutable snapshot
        per_assembly_cost=per_assembly_cost,        # Immutable snapshot
        consumptions=consumptions
    )
    
    session.add(assembly_run)
    session.flush()
    
    return assembly_run
```

### 2.5 UI Implementation

#### 2.5.1 Finished Goods Tab (CATALOG Mode)

**Location**: CATALOG mode → Finished Goods tab

**Purpose**: Manage FinishedGood definitions

**CRITICAL**: Costs are NOT displayed in catalog view. Definitions have no inherent cost - costs only exist when instantiated for events/assembly.

```
┌─ CATALOG Mode → Finished Goods Tab ─────────────────────┐
│                                                          │
│  CATALOG • 413 ingredients • 47 yield types • 12 FGs    │
│  [Ingredients] [Products] [Recipes] [Finished Units]    │
│  [Finished Goods]                                        │
│                                                          │
│  [+ Add Finished Good]                                   │
│                                                          │
│  ╔════════════════════════════════════════════════════╗  │
│  ║ Name               Type      Components            ║  │
│  ║ ─────────────      ────      ──────────            ║  │
│  ║ Holiday Gift Box   assembly  3 components          ║  │
│  ║ Cookie Sampler     assembly  2 components          ║  │
│  ║ Brownie Trio       assembly  3 components          ║  │
│  ║ ...                                                ║  │
│  ╚════════════════════════════════════════════════════╝  │
│                                                          │
│  12 finished goods                                       │
│                                                          │
│  ℹ️ No costs shown - definitions don't have prices      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Add Finished Good Dialog:**

```
┌─ Add Finished Good ──────────────────────────────────────┐
│                                                          │
│  Name: [Holiday Gift Box__________________________]      │
│                                                          │
│  Assembly Type: [gift_box ▼]                             │
│                                                          │
│  Components:                                             │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Finished Unit         Quantity                     │ │
│  │ ───────────────       ────────                     │ │
│  │ Large Cookie           4                           │ │
│  │ Brownie                2                           │ │
│  │ Decorative Box         1                           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  [+ Add Component]                                       │
│                                                          │
│  Notes:                                                  │
│  [____________________________________________]           │
│                                                          │
│  [Cancel]  [Save Finished Good]                          │
│                                                          │
│  ℹ️ Cost calculated when assembled (not stored)         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- ❌ NO "Cost" column in catalog grid
- ❌ NO "Unit Cost" or "Total" columns in Add dialog
- ✅ Footer note: "No costs shown - definitions don't have prices"
- ✅ Dialog note: "Cost calculated when assembled (not stored)"

**Rationale**: 
- Catalog view shows WHAT can be assembled (structure), not HOW MUCH it costs
- Cost varies based on current inventory prices (dynamic)
- Cost captured at assembly time as immutable snapshot in AssemblyRun
- Displaying current cost in catalog would:
  - Imply it's stored (architectural violation)
  - Become stale as ingredient prices change
  - Confuse users about where costs come from

**Where costs ARE shown:**
1. **PLAN mode → Event planning**: Shows package cost for budgeting (dynamic from `calculate_current_cost()`)
2. **MAKE mode → Assembly dialog**: Shows cost snapshot being captured
3. **MAKE mode → Assembly history**: Shows per_assembly_cost from AssemblyRun records
4. **Reports**: Historical cost analysis from AssemblyRun snapshots

#### 2.5.2 Assembly Recording (MAKE Mode)

**Location**: MAKE mode → Assembly tab

```
┌─ MAKE Mode → Assembly Tab ───────────────────────────────┐
│                                                          │
│  MAKE • 15 active production runs • 8 assemblies today   │
│  [Production] [Assembly] [Losses]                        │
│                                                          │
│  [+ Record Assembly]                                     │
│                                                          │
│  ╔════════════════════════════════════════════════════╗  │
│  ║ Date      Finished Good    Qty  Cost/Unit  Total   ║  │
│  ║ ────────  ──────────────   ───  ─────────  ──────  ║  │
│  ║ 1/9/2026  Holiday Gift Box  50   $3.24     $162.00 ║  │
│  ║ 1/8/2026  Cookie Sampler    30   $4.50     $135.00 ║  │
│  ║ 1/8/2026  Brownie Trio      40   $2.10     $84.00  ║  │
│  ║ ...                                                 ║  │
│  ╚════════════════════════════════════════════════════╝  │
│                                                          │
│  Recent assemblies shown with cost snapshots             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Record Assembly Dialog:**

```
┌─ Record Assembly ────────────────────────────────────────┐
│                                                          │
│  Finished Good: [Holiday Gift Box ▼]                     │
│                                                          │
│  Quantity: [50___]                                       │
│                                                          │
│  Assembly Date: [1/9/2026 ▼]                             │
│                                                          │
│  Event (optional): [Christmas 2026 ▼]                    │
│                                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Cost Snapshot (captured at assembly):                   │
│                                                          │
│  Components:                                             │
│    200 Large Cookies    @ $0.42 each = $84.00           │
│    100 Brownies         @ $0.65 each = $65.00           │
│    50 Decorative Boxes  @ $0.26 each = $13.00           │
│                                                          │
│  Total Component Cost: $162.00                           │
│  Per Assembly Cost: $3.24                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                          │
│  Inventory Check:                                        │
│    ✅ Large Cookies: 250 available (need 200)            │
│    ✅ Brownies: 120 available (need 100)                 │
│    ✅ Decorative Boxes: 60 available (need 50)           │
│                                                          │
│  Notes:                                                  │
│  [____________________________________________]           │
│                                                          │
│  [Cancel]  [Record Assembly]                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Plan

### Phase 1: Database & Models (5-6 hours)

**Deliverables:**
- AssemblyConsumption model (NEW)
- Enhanced AssemblyRun model (add cost fields)
- Enhanced FinishedGood model (dynamic cost methods, internal use only)
- **Fixed Package model** (use `calculate_current_cost()` not removed `total_cost`)
- Database migration script
- Model unit tests

**Files:**
- `src/models/assembly_consumption.py` (NEW)
- `src/models/assembly_run.py` (enhance)
- `src/models/finished_good.py` (enhance)
- `src/models/package.py` (FIX cost calculations)
- `tests/models/test_assembly_consumption.py` (NEW)
- `tests/models/test_assembly_run.py` (update)
- `tests/models/test_finished_good.py` (update)
- `tests/models/test_package.py` (update - verify fix)

### Phase 2: Service Layer (6-7 hours)

**Deliverables:**
- Enhanced AssemblyService (record_assembly_run with cost snapshot)
- FinishedGoodService CRUD operations
- Cost calculation services
- Service integration tests

**Files:**
- `src/services/assembly_service.py` (enhance record_assembly_run)
- `src/services/finished_good_service.py` (CRUD + cost calculation)
- `tests/services/test_assembly_service.py` (enhance)
- `tests/services/test_finished_good_service.py` (NEW)

### Phase 3: UI Implementation (6-8 hours)

**Deliverables:**
- Finished Goods tab (CATALOG mode) - NO cost display
- Add/Edit Finished Good dialogs - NO cost display
- Assembly recording dialog (MAKE mode) - WITH cost snapshot display
- Event planning integration (verify Package.calculate_cost() works)

**Files:**
- `src/ui/catalog/finished_goods_tab.py` (NEW or enhance)
- `src/ui/catalog/add_finished_good_dialog.py` (NEW)
- `src/ui/make/assembly_tab.py` (enhance)
- `src/ui/make/record_assembly_dialog.py` (enhance)

### Phase 4: Testing & Integration (3-4 hours)

**Deliverables:**
- End-to-end workflow tests
- UI integration tests
- Cost calculation validation
- Pattern compliance verification
- **Package model fix verification** (event planning doesn't crash)

**Test Scenarios:**
1. Create FinishedGood with components → verify NO costs in UI
2. Event planning: Assign package → verify Package.calculate_cost() works
3. Record AssemblyRun → verify cost snapshot captured
4. Verify AssemblyConsumption records created
5. Verify inventory_count decremented correctly
6. Query historical costs → verify immutability
7. Event cost report → verify planned vs actual costs

### Phase 5: Documentation (1-2 hours)

**Deliverables:**
- User guide updates
- Architecture.md compliance verification
- Service docstrings
- Migration notes

---

## 4. Success Criteria

### 4.1 Pattern Compliance

**✅ Definition/Instantiation separation complete:**
- FinishedGood has NO stored costs (calculates dynamically, internal only)
- Package uses dynamic calculation (NOT removed `total_cost` field)
- AssemblyRun captures cost snapshot at assembly time
- AssemblyConsumption tracks component usage
- Pattern analogous to Recipe/ProductionRun/ProductionConsumption

**✅ Architecture.md compliance:**
- Post-F046 grade: A (was B - incomplete)
- AssemblyRun pattern matches ProductionRun precedent
- All four entity pairs now compliant (see architecture.md Pattern Compliance Matrix)

### 4.2 Functional Completeness

**✅ CATALOG mode:**
- Can create/edit/delete FinishedGoods
- Can view components (NO costs displayed)
- Catalog shows structure only

**✅ PLAN mode:**
- Event planning works (Package.calculate_cost() fixed)
- Can assign packages to recipients
- Shows planning costs for budgeting (dynamic)

**✅ MAKE mode:**
- Can record assembly with quantity
- System captures cost snapshot automatically
- System creates AssemblyConsumption records
- System decrements inventory_count via FIFO
- Insufficient inventory prevents assembly (validation)

### 4.3 Data Integrity

**✅ Cost accuracy:**
- Current costs always match current inventory (FIFO)
- Historical costs immutable (AssemblyRun snapshots)
- Component consumption tracked accurately
- No stale costs in database
- **Package model uses dynamic calculation** (not removed field)

**✅ Inventory tracking:**
- FinishedUnit.inventory_count decrements on assembly
- AssemblyConsumption provides audit trail
- Insufficient inventory blocks assembly
- Component quantities validated

---

## 5. Risks & Mitigation

### Risk 1: Package Model Breaking Change

**Risk**: Existing event planning code may reference `finished_good.total_cost` in multiple places

**Mitigation**:
- Search entire codebase for `total_cost` references
- Update all Package-related code in Phase 1
- Add integration tests for event planning workflow
- Test with real event data before merge

### Risk 2: Performance Impact (cost calculations)

**Risk**: Dynamically calculating costs for every FinishedGood could be slow with large component lists

**Mitigation**:
- Cache calculated costs in UI (refresh on data change)
- Use eager loading for components (joinedload)
- Benchmark with realistic data (12 FGs × 3-5 components each)
- Acceptable for F046 scope (catalog management, not high-volume queries)

### Risk 3: Complexity Underestimation

**Risk**: 20-24 hour estimate may be insufficient given:
- New AssemblyConsumption model
- Enhanced AssemblyRun fields
- Package model fixes (search entire codebase)
- Pattern compliance requirements
- Testing overhead

**Mitigation**:
- Spec provides detailed implementation guidance
- Follow ProductionRun precedent (similar pattern)
- Phase 1-2 are well-defined (models + services = 11-13 hours)
- If needed, defer advanced UI polish (focus on core functionality)

### Risk 4: Import/Export Breaking Changes

**Risk**: Enhanced AssemblyRun fields require import/export updates

**Mitigation**:
- Export service adds new fields automatically
- Import service validates and rejects old formats (fail fast)
- Version 4.2 export format (post-F046)
- Sample data files updated with cost snapshots

---

## 6. Dependencies & Sequencing

### Prerequisites

**✅ F044**: Finished Units functionality complete
**✅ F045**: Cost architecture refactor complete (removed stored costs from definitions)

### Enables

**F047**: Shopping Lists Tab Implementation
- Depends on FinishedGood → Component hierarchy
- Generates ingredient shopping lists from event assignments

**F048**: Assembly Workflows
- Depends on AssemblyRun cost snapshots
- Enables assembly tracking reports
- Enables cost analysis over time

**Event Planning Completion**:
- Package cost calculation fixed (no longer crashes)
- Can assign packages to recipients
- Can calculate event costs

---

## 7. Constitutional Compliance

### Principle I: User-Centric Design

**✅ Compliant**: Implements user-requested functionality ("Finished Goods button goes nowhere")
**✅ Compliant**: Follows baker's mental model (Finished Goods → Packages)
**✅ Compliant**: Cost transparency where relevant (assembly recording, event planning)
**✅ Compliant**: No cost clutter in catalog (structure only)

### Principle III: Data Integrity

**✅ Compliant**: No stored costs on definitions (eliminates staleness)
**✅ Compliant**: Cost snapshots immutable (historical accuracy)
**✅ Compliant**: Component consumption tracked (audit trail)
**✅ Compliant**: Inventory validation prevents impossible assemblies
**✅ Compliant**: Package model uses dynamic calculation (not broken field reference)

### Principle V: Layered Architecture

**✅ Compliant**: Model/Service/UI separation maintained
**✅ Compliant**: Service layer handles cost calculation logic
**✅ Compliant**: Models enforce constraints (CHECK, FK, NOT NULL)
**✅ Compliant**: UI displays data, captures input (no business logic)

### Definition/Instantiation Pattern

**✅ Compliant**: FinishedGood = definition (no costs, internal calculation only)
**✅ Compliant**: Package = definition (uses dynamic calculation for planning)
**✅ Compliant**: AssemblyRun = instantiation (cost snapshot)
**✅ Compliant**: AssemblyConsumption = consumption ledger (analogous to ProductionConsumption)
**✅ Compliant**: Follows ProductionRun precedent exactly

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Models:**
- AssemblyConsumption: Constraints, relationships, total_cost property
- AssemblyRun: Cost snapshot fields, validation, to_dict with Decimals
- FinishedGood: calculate_current_cost (internal), get_component_breakdown (NO costs)
- **Package: calculate_cost using dynamic calculation (CRITICAL)**

**Services:**
- FinishedGoodService: CRUD, cost calculations
- AssemblyService: record_assembly_run with cost snapshot, insufficient inventory handling

### 8.2 Integration Tests

**Workflow Tests:**
1. Create FinishedGood → verify components, verify NO costs in UI
2. Event planning: Assign package → verify Package.calculate_cost() works (CRITICAL)
3. Record AssemblyRun → verify cost snapshot, verify AssemblyConsumption records
4. Verify inventory decrement → check inventory_count before/after
5. Multiple assemblies → verify separate cost snapshots (price changes)
6. Insufficient inventory → verify ValidationError raised

**Cost Accuracy Tests:**
1. Change ingredient price → verify FinishedGood.calculate_current_cost() reflects change
2. Change ingredient price → verify Package.calculate_cost() reflects change (CRITICAL)
3. Historical query → verify AssemblyRun.per_assembly_cost unchanged (immutable)
4. Component breakdown → verify quantities match (NO costs in catalog)

### 8.3 UI Tests

**Manual validation:**
- Finished Goods tab displays correctly (NO costs)
- Add Finished Good dialog (NO cost calculation shown)
- Assembly recording dialog shows cost snapshot
- Event planning doesn't crash (Package cost calculation works)
- Cost snapshot displayed in assembly history

---

## 9. Future Enhancements (Out of Scope)

### Deferred to F047+
- Shopping list generation from event assignments
- Cost reports over time
- Assembly efficiency metrics

### Deferred to Phase 3+
- FinishedUnit lot tracking (analogous to InventoryItem)
- Assembly yield loss tracking (analogous to ProductionLoss)
- Multi-stage assembly (sub-assemblies)

---

## 10. Approval & Sign-off

**Spec Author**: Claude (Anthropic AI)
**Date**: 2026-01-09
**Reviewed By**: [Pending]
**Approved By**: [Pending]

**Changes from initial scope:**
- Added AssemblyConsumption model (component tracking)
- Enhanced AssemblyRun with cost snapshot fields
- **Added Package model fix** (use dynamic calculation, not removed `total_cost`)
- Emphasized definition/instantiation pattern compliance
- **Clarified: NO cost display in catalog UI** (costs only for planning/assembly)
- Increased effort estimate: 18-22 hours → 21-25 hours (added 1 hour for Package fixes + testing)

---

**END OF SPECIFICATION**
