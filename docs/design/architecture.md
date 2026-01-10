# Architecture Document

> **📍 Navigation Guide**
>
> This document provides **high-level architectural overview** and **core design patterns**.
>
> **For detailed current state, see:**
> - **Database Schema:** [`/docs/design/SCHEMA.md`](SCHEMA.md) - Complete entity definitions and relationships
> - **Feature Specifications:** [`/docs/design/F0XX_*.md`](.) - Detailed design docs for each feature
> - **Service Layer:** [`/src/services/`](../../src/services/) - Service docstrings and implementation
> - **UI Structure:** [`/src/ui/`](../../src/ui/) - Current UI organization and components
> - **Feature Roadmap:** [`/docs/feature_roadmap.md`](<../feature_roadmap.md>) - Completed and planned features
> - **Constitution:** [`/.kittify/memory/constitution.md`](../../.kittify/memory/constitution.md) - Core architectural principles
>
> **Document Status:**
> - Last comprehensive review: 2026-01-09
> - Architecture pattern analysis: 2026-01-09 (definition/instantiation)
> - Schema version documented: v0.7+
> - Last updated: 2026-01-09

---

## System Overview

The Seasonal Baking Tracker is a desktop application built with Python and CustomTkinter, using SQLite for data persistence. The architecture follows a **definition vs instantiation** pattern where catalog entities (recipes, products) are separate from their transaction records (production runs, purchases).

---

## Core Architectural Pattern: Definitions vs Instantiations

### Pattern Overview

The application distinguishes between two fundamental types of entities:

**Definition Objects** (Catalog/Templates):
- Describe **WHAT** can exist
- No temporal context (timeless, persist indefinitely)
- Can exist with zero instances
- Examples: Recipe "Chocolate Chip Cookies", Product "King Arthur Flour 5lb bag"
- **NO stored costs** - definitions don't have inherent prices

**Instantiation Objects** (Transactions/Events):
- Record **WHEN/WHERE/HOW** something happened
- Temporal context (specific date/time/circumstances)
- Snapshot state at time of use
- Examples: ProductionRun "Made 3 batches on 2026-01-05", Purchase "Bought flour for $4.50 on 2026-01-03"
- **Immutable snapshots** - capture point-in-time costs and details

### Why This Pattern?

**Problem solved:**
- Definitions persist even when instances are zero (recipe you haven't made yet, product you haven't bought recently)
- Historical accuracy (what did it cost WHEN we made it, not what does it cost now)
- Price fluctuations tracked (chocolate went from $300 → $600, both prices preserved)
- Data integrity (no stale costs on definitions)

**Core principle:**
> **"Costs on Instances, Not Definitions"**
> 
> A recipe doesn't have a cost - making a batch has a cost (depends on current ingredient prices).
> A product doesn't have a price - a purchase has a price (depends on supplier and date).

---

## Pattern Implementation Examples

### 1. Product/Purchase/InventoryItem ✅ Exemplar Pattern

**Definition: Product**
```python
class Product:
    """Brand-specific product definition (e.g., "King Arthur AP Flour 5lb")"""
    ingredient_id: int          # Links to generic Ingredient
    brand: str                  # "King Arthur"
    package_size: str           # "5 lb"
    preferred_supplier_id: int  # Preferred, not required
    # NO stored prices, NO inventory counts
```

**Instantiation: Purchase**
```python
class Purchase:
    """Records specific purchase transaction"""
    product_id: int             # WHAT was purchased
    supplier_id: int            # WHERE purchased (actual supplier used)
    purchase_date: date         # WHEN purchased
    unit_price: Decimal         # Price at THIS purchase
    quantity_purchased: int     # How many packages
    # IMMUTABLE after creation (no updated_at field)
```

**Instantiation: InventoryItem**
```python
class InventoryItem:
    """Records actual inventory lot"""
    product_id: int             # WHAT product
    purchase_id: int            # Links to SPECIFIC purchase
    quantity: float             # Current quantity on hand
    purchase_date: date         # WHEN added to inventory
    expiration_date: date       # THIS lot's expiration
    location: str               # WHERE stored physically
```

**Real-world scenario:**
```
Product (definition):
  "King Arthur All-Purpose Flour, 5 lb bag"
  - Persists even when inventory = 0
  - Persists even when no longer sold

Purchase (instantiation #1):
  King Arthur Flour from Costco on 2026-01-03 @ $4.50 each, bought 3

Purchase (instantiation #2):
  King Arthur Flour from Wegmans on 2026-01-08 @ $5.00 each, bought 2

InventoryItem (physical instance #1):
  10 lb remaining from Costco purchase (FIFO: oldest)

InventoryItem (physical instance #2):
  7.5 lb remaining from Wegmans purchase (FIFO: newer)
```

**Benefits:**
- Product definition persists when out of stock
- Product definition persists when discontinued (historical record intact)
- Each purchase captures supplier + price + date (audit trail)
- FIFO consumption matches physical reality (oldest first)
- Price trends tracked (identify $4.50 → $5.00 increase)

---

### 2. Recipe/ProductionRun ✅ Production Pattern

**Definition: Recipe**
```python
class Recipe:
    """Recipe definition (instructions)"""
    name: str                       # "Chocolate Chip Cookies"
    ingredients: List[RecipeIngredient]
    yield_quantity: int
    base_recipe_id: int             # Optional variant parent
    variant_name: str               # Optional variant identifier
    # NO stored costs (calculates fresh from current inventory)
```

**Instantiation: ProductionRun**
```python
class ProductionRun:
    """Records specific batch production"""
    recipe_id: int                  # WHAT recipe
    recipe_snapshot_id: int         # Immutable snapshot for historical accuracy
    event_id: int                   # Optional event context (WHY produced)
    num_batches: int                # HOW many batches
    expected_yield: int             # Expected output
    actual_yield: int               # Actual output (may differ due to loss)
    produced_at: datetime           # WHEN produced
    total_ingredient_cost: Decimal  # Snapshot at production time (FIFO)
    per_unit_cost: Decimal          # Cost per unit at production time
    production_status: str          # COMPLETE/PARTIAL_LOSS/TOTAL_LOSS
```

**Real-world scenario:**
```
Recipe (definition):
  "Chocolate Chip Cookies"
  - 2 cups flour, 1 cup sugar, ... (ingredients)
  - Yields 30 cookies per batch
  - Current cost calculation: $12.50/batch (based on current inventory prices)

ProductionRun (instantiation #1):
  Made 3 batches on 2026-01-05
  - Expected: 90 cookies, Actual: 87 cookies (3 burnt)
  - Cost: $12.50/batch × 3 = $37.50 total
  - Per cookie: $37.50 ÷ 87 = $0.431

ProductionRun (instantiation #2):
  Made 2 batches on 2026-01-10
  - Expected: 60 cookies, Actual: 60 cookies
  - Cost: $13.00/batch × 2 = $26.00 (flour price increased)
  - Per cookie: $26.00 ÷ 60 = $0.433
```

**Benefits:**
- Recipe definition persists even when never produced
- Each production captures actual yield (accounts for loss)
- Costs snapshot at production time (historical accuracy)
- Recipe snapshots ensure immutability (ingredients can't change retroactively)
- Can answer "what did it cost to make cookies on Jan 5?" (not just "what does it cost now?")

---

### 3. FinishedUnit/ProductionRun ✅ Output Tracking Pattern

**Definition: FinishedUnit**
```python
class FinishedUnit:
    """Defines what a recipe produces"""
    display_name: str               # "Large Cookie"
    recipe_id: int                  # From "Chocolate Chip Cookie" recipe
    items_per_batch: int            # 30 per batch
    inventory_count: int            # Current aggregate inventory
    # NO unit_cost (removed in F045 - costs on instances only)
```

**Instantiation: ProductionRun (same as above)**
- ProductionRun.finished_unit_id links production to output type
- ProductionRun.actual_yield increments FinishedUnit.inventory_count
- ProductionRun.per_unit_cost captures cost at production time

**Pattern notes:**
- FinishedUnit.inventory_count is aggregate (current state, not historical)
- No per-lot tracking (deferred enhancement - finished goods consumed quickly)
- ProductionRun preserves historical production events and costs

---

### 4. FinishedGood/AssemblyRun ⚠️ Assembly Pattern (Incomplete)

**Definition: FinishedGood**
```python
class FinishedGood:
    """Defines assembly of FinishedUnits"""
    display_name: str               # "Holiday Gift Box"
    assembly_type: str              # "gift_box"
    components: List[Composition]   # 4 cookies + 2 brownies + box
    # NO total_cost (removed in F045 - costs on instances only)
```

**Instantiation: AssemblyRun**
```python
class AssemblyRun:
    """Records specific assembly event"""
    finished_good_id: int           # WHAT assembly
    event_id: int                   # Optional event context
    quantity: int                   # HOW many assembled
    assembled_at: datetime          # WHEN assembled
    # ⚠️ FUTURE (F046+): Add cost snapshot fields
    # total_component_cost: Decimal
    # per_assembly_cost: Decimal
```

**Pattern status: Incomplete**
- FinishedGood correctly has no stored cost (F045)
- AssemblyRun exists but lacks cost snapshot (future enhancement F046+)
- Missing component consumption tracking (analogous to ProductionConsumption)

**Future enhancement (F046+):**
```python
class AssemblyRun:
    # Add cost snapshot
    total_component_cost: Decimal   # Snapshot at assembly time
    per_assembly_cost: Decimal      # Cost per assembled unit

class AssemblyConsumption:
    """Track which FinishedUnits consumed (analogous to ProductionConsumption)"""
    assembly_run_id: int
    finished_unit_id: int           # Which component
    quantity_consumed: int
    per_unit_cost: Decimal          # Cost of this component at assembly time
```

---

## Pattern Compliance Matrix

| Entity Pair | Definition | Instantiation | Cost Handling | Status |
|-------------|-----------|---------------|---------------|---------|
| Ingredient → N/A | Ingredient | (used in recipes) | No costs | ✅ Correct |
| Product → Purchase → InventoryItem | Product | Purchase, InventoryItem | Purchase.unit_price | ✅ Exemplar |
| Recipe → ProductionRun | Recipe | ProductionRun | ProductionRun.total_ingredient_cost | ✅ Correct |
| FinishedUnit → ProductionRun | FinishedUnit | ProductionRun | ProductionRun.per_unit_cost | ✅ Correct (post-F045) |
| FinishedGood → AssemblyRun | FinishedGood | AssemblyRun | ⚠️ Missing cost snapshot | ⚠️ Incomplete (F046+) |

**Post-F045 compliance:**
- ✅ All definitions have NO stored costs
- ✅ All costs captured on instantiations (transactions)
- ⚠️ AssemblyRun cost snapshot deferred to F046+

---

## Architecture Layers

### 1. Presentation Layer (UI)
- **Technology:** CustomTkinter
- **Location:** `src/ui/`
- **Responsibilities:**
  - User interaction
  - Data display and input
  - Navigation between sections
  - Form validation feedback

### 2. Business Logic Layer (Services)
- **Technology:** Python
- **Location:** `src/services/`
- **Responsibilities:**
  - Business rules and calculations
  - Unit conversion logic
  - Cost calculations (dynamic from current inventory)
  - Report generation
  - Production tracking
  - Event planning

### 3. Data Access Layer (Models)
- **Technology:** SQLAlchemy ORM
- **Location:** `src/models/`
- **Responsibilities:**
  - Database schema definition
  - CRUD operations
  - Relationship management
  - Data validation
  - **Pattern enforcement:** Definitions vs Instantiations

### 4. Data Storage Layer
- **Technology:** SQLite
- **Location:** `data/bake_tracker.db`
- **Features:**
  - Write-Ahead Logging (WAL) mode
  - Foreign key constraints
  - Transaction support

---

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                             │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐       │
│  │Dashboard│ │Ingredients│ │Products │ │Inventory │ │Purchases│      │
│  │   Tab   │ │    Tab    │ │   Tab   │ │   Tab    │ │  Tab   │      │
│  └─────────┘ └──────────┘ └─────────┘ └──────────┘ └────────┘       │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ │
│  │Recipe│ │Finished│ │Finished│ │Bundles │ │Packages  │ │Recipients│
│  │ Tab  │ │ Units  │ │ Goods  │ │  Tab   │ │   Tab    │ │   Tab  │ │
│  └──────┘ └────────┘ └────────┘ └────────┘ └──────────┘ └────────┘ │
│  ┌────────┐  ┌──────────┐  ┌───────────────────────────────────┐   │
│  │ Events │  │Event Prod│  │   EventDetailWindow (4 tabs)      │   │
│  │  Tab   │  │Dashboard │  │  - Assignments                    │   │
│  └────────┘  └──────────┘  │  - Recipe Needs                   │   │
│                             │  - Shopping List                  │   │
│                             │  - Summary                        │   │
│                             └───────────────────────────────────┘   │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                       Business Logic Layer                            │
│  ┌──────────┐ ┌────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐  │
│  │Ingredient│ │Product │ │  Supplier  │ │ Purchase │ │ Inventory│  │
│  │ Service  │ │Service │ │  Service   │ │ Service  │ │ Service  │  │
│  └──────────┘ └────────┘ └────────────┘ └──────────┘ └──────────┘  │
│  ┌──────────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────────┐  │
│  │    Recipe    │ │  Finished  │ │   Package   │ │    Event     │  │
│  │   Service    │ │ Gd Service │ │   Service   │ │   Service    │  │
│  └──────────────┘ └────────────┘ └─────────────┘ └──────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐│
│  │  Production  │ │   Assembly   │ │     Recipient                ││
│  │   Service    │ │   Service    │ │     Service                  ││
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘│
│  ┌──────────────┐ ┌────────────────────────────────┐                │
│  │Unit Converter│ │  Import/Export Services        │                │
│  └──────────────┘ │  - Unified Import/Export       │                │
│                   │  - Catalog Import              │                │
│                   └────────────────────────────────┘                │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                      Data Access Layer                                │
│  Definition Objects (Catalog):                                        │
│  ┌──────────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌──────────────┐         │
│  │Ingredient│ │Product│ │Supplier│ │Recipe│ │RecipeIngred. │         │
│  │  Model   │ │Model │ │ Model  │ │Model │ │  (Junction)  │         │
│  └──────────┘ └──────┘ └────────┘ └──────┘ └──────────────┘         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │FinishedUnit  │ │FinishedGood  │ │Composition   │                 │
│  │   Model      │ │   Model      │ │  (Junction)  │                 │
│  └──────────────┘ └──────────────┘ └──────────────┘                 │
│                                                                       │
│  Instantiation Objects (Transactions):                               │
│  ┌────────┐ ┌─────────────────┐ ┌──────────────┐                    │
│  │Purchase│ │ InventoryItem   │ │ProductionRun │                    │
│  │ Model  │ │ (InventoryAdd.) │ │    Model     │                    │
│  └────────┘ └─────────────────┘ └──────────────┘                    │
│  ┌──────────────┐ ┌────────────────┐ ┌──────────────┐               │
│  │ AssemblyRun  │ │ProductionLoss  │ │RecipeSnapshot│               │
│  │    Model     │ │     Model      │ │    Model     │               │
│  └──────────────┘ └────────────────┘ └──────────────┘               │
│                                                                       │
│  Events & Planning:                                                  │
│  ┌──────┐ ┌─────────┐ ┌──────┐ ┌──────┐ ┌────────────────────┐     │
│  │Bundle│ │Package  │ │Event │ │Recip.│ │EventRecipientPkg   │     │
│  │Model │ │ Model   │ │Model │ │Model │ │   (Junction)       │     │
│  └──────┘ └─────────┘ └──────┘ └──────┘ └────────────────────┘     │
│  ┌────────────────────┐ ┌──────────────────┐                        │
│  │EventProductionTgt  │ │EventAssemblyTgt  │                        │
│  │      (Target)      │ │    (Target)      │                        │
│  └────────────────────┘ └──────────────────┘                        │
│                                                                       │
│  Reference Tables:                                                   │
│  ┌──────┐                                                            │
│  │Units │  (Standard unit reference table)                           │
│  │Model │                                                            │
│  └──────┘                                                            │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                       Data Storage Layer                              │
│                       SQLite Database                                 │
│                 (C:\Users\Kent\Documents\BakeTracker\                 │
│                      bake_tracker.db)                                 │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example: Shopping List Generation

### User Action
User opens Event, clicks "View Details", switches to "Shopping List" tab

### Service Layer Flow
1. `event_service.generate_shopping_list(event_id)` called
2. Retrieves event and all EventRecipientPackage assignments
3. For each assignment:
   - Gets package → bundles → finished goods → recipes
   - Calculates ingredient quantities needed (accounting for quantities at each level)
4. Aggregates ingredients by ID
5. Retrieves **current inventory** (from InventoryItem via Product → Ingredient)
6. Calculates shortfall: `to_buy = needed - on_hand`
7. Calculates cost per ingredient using **FIFO from Purchase records**:
   - `cost = to_buy × (unit_price_from_purchase / conversion_factor)`
8. Returns list with only items where `to_buy > 0`

### Pattern Application
- **Definition used**: Recipe (what ingredients needed)
- **Instantiation used**: Purchase (what prices to use for cost calculation)
- **Current state used**: InventoryItem.quantity (what we have on hand now)
- **No stored costs**: All costs calculated fresh from Purchase records

---

## Database Schema Overview

> **📋 For complete schema details:** See [`SCHEMA.md`](SCHEMA.md)

### Schema Evolution History

The database schema has evolved significantly through iterative feature development. This section provides high-level overview of major architectural shifts. **See individual feature specs for detailed design decisions.**

#### v0.4 - Ingredient/Product Refactor (F011, TD-001)
**Date:** 2025-12-06  
**Spec:** `docs/design/F011_packaging_and_bom_foundation.md`

- Separated generic Ingredients from brand-specific Products
- Established FIFO inventory tracking foundation
- Added packaging support via `is_packaging` flag on Ingredient
- **Migration:** Variant → Product terminology cleanup

#### v0.5 - Nested Recipes & Production Tracking (F012, F013)
**Date:** 2025-12-09  
**Specs:** Feature 012 (Nested Recipes), Feature 013 (Production & Inventory Tracking)

- Added `RecipeComponent` for hierarchical recipes
- Added `ProductionRun` and `AssemblyRun` for production tracking
- Established FIFO consumption ledgers
- **Key Pattern:** Recursive cost calculation for nested recipes

#### v0.6 - Event-Centric Production Model (F016)
**Date:** 2025-12-11  
**Spec:** `docs/design/schema_v0.6_design.md`

- Added `event_id` FK to ProductionRun and AssemblyRun
- Added `EventProductionTarget` and `EventAssemblyTarget` tables
- Added `fulfillment_status` to EventRecipientPackage
- **Major Shift:** Production runs now linked to events for progress tracking

#### v0.6+ - Unit Conversion Simplification (F019)
**Date:** 2025-12-14  
**Spec:** `docs/design/feature_019_unit_simplification.md`

- **DELETED:** `UnitConversion` model/table (redundant with density)
- **DELETED:** `Ingredient.recipe_unit` field (recipes declare their own units)
- **Canonical Source:** 4-field density model on Ingredient (`density_value`, `density_from_unit`, `density_to_unit`, `density_note`)
- **Rationale:** Removed redundant conversion mechanisms (Constitution VI - export/reset/import)

#### v0.6+ - Enhanced Inventory Management (F027, F028)
**Date:** 2025-12-24  
**Specs:** F027 (Product Catalog), F028 (Purchase Tracking)

- Added `Supplier` table for supplier tracking
- Added `Purchase` table for price history (IMMUTABLE transactions)
- Added `Product.preferred_supplier_id` FK
- Added `Product.is_hidden` flag
- Added `InventoryItem.purchase_id` FK (links to Purchase for FIFO costing)
- **Major Shift:** Purchase transactions as first-class entities, FIFO uses Purchase.unit_price
- **Pattern:** Definition (Product) vs Instantiation (Purchase) separation

#### v0.7 - Cost Architecture Refactor (F045)
**Date:** 2026-01-09  
**Spec:** `docs/design/F045_cost_architecture_refactor.md`

- **DELETED:** `FinishedUnit.unit_cost` field (stored cost)
- **DELETED:** `FinishedGood.total_cost` field (stored cost)
- **Philosophy:** "Costs on Instances, Not Definitions"
- **Pattern Enforcement:** All costs captured at transaction time (ProductionRun, Purchase)
- **Breaking Change:** Version 4.1 export format

#### Current Schema (v0.7+)
**Complete Entity List:** See [`SCHEMA.md`](SCHEMA.md)

**Core Domains:**
- **Catalog (Definitions):** Ingredient, Product, Supplier, Recipe, FinishedUnit, FinishedGood
- **Inventory (Instantiations):** Purchase, InventoryItem
- **Production (Instantiations):** ProductionRun, AssemblyRun, ProductionLoss
- **Events (Planning):** Event, EventRecipientPackage, EventProductionTarget, EventAssemblyTarget
- **Packaging:** Bundle, Package
- **People:** Recipient, Supplier
- **Reference:** Units (standard unit reference table)

**Schema Change Strategy:** See Constitution Principle VI - Export/Reset/Import workflow (no migration scripts for desktop phase)

---

## Cost Calculation Architecture

### FIFO Strategy (First In, First Out)

The application uses **FIFO (First In, First Out)** for accurate cost tracking across all inventory:

**Why FIFO?**
- Matches physical consumption (oldest items used first)
- Accurate when prices fluctuate (chocolate $300 → $450 → $600)
- Natural fit for lot tracking (future enhancement)
- Industry standard for food/manufacturing
- Temporal price context via Purchase transactions

**Implementation Pattern:**

```python
def calculate_recipe_cost_fifo(recipe_id):
    """Calculate recipe cost using FIFO from current inventory."""
    total_cost = Decimal("0.0000")

    for recipe_ingredient in recipe.ingredients:
        ingredient_id = recipe_ingredient.ingredient_id
        quantity_needed = recipe_ingredient.quantity

        # Consume using FIFO: oldest inventory first
        # InventoryItem.purchase_id → Purchase.unit_price
        consumed, cost_breakdown = consume_fifo(
            ingredient_id=ingredient_id,
            quantity_needed=quantity_needed
        )

        # Sum costs from each Purchase consumed
        for item in cost_breakdown:
            total_cost += item["cost"]

        # Fallback: If insufficient inventory, estimate using most recent purchase
        if consumed < quantity_needed:
            remaining = quantity_needed - consumed
            product = get_preferred_product(ingredient_id)
            latest_purchase = product.get_most_recent_purchase()
            fallback_cost = remaining * latest_purchase.unit_price
            total_cost += fallback_cost

    return total_cost
```

**Cost Snapshot Pattern:**

When production occurs, costs are captured as immutable snapshots:

```python
class ProductionRun:
    """Records batch production with cost snapshot"""
    recipe_id: int
    num_batches: int
    actual_yield: int
    produced_at: datetime
    
    # Cost snapshot at production time
    total_ingredient_cost: Decimal  # Sum of FIFO costs
    per_unit_cost: Decimal          # total_cost / actual_yield
    
    # Link to immutable recipe snapshot
    recipe_snapshot_id: int         # F037: Ensures historical accuracy
```

**Benefits:**
- Historical accuracy: Can answer "what did it cost on Jan 5?"
- Price trend analysis: Track ingredient cost changes over time
- Audit trail: Every production links to specific purchases
- Future-ready: Lot tracking extension point

---

## Ingredient/Product Architecture

### Design Philosophy
The inventory system follows a **"future-proof schema, present-simple implementation"** approach:
- All industry standard fields added to schema as nullable
- Only required fields populated initially
- Incremental feature adoption without schema changes
- User NOT burdened with unnecessary data entry upfront
- Optional enhancements clearly documented for future phases

### Hierarchy & Separation of Concerns

**Ingredient (Generic Concept)**
- Represents the platonic ideal of an ingredient, independent of brand or package
- Purpose: Brand-agnostic recipe references
- Example: "All-Purpose Flour" (not "King Arthur 25 lb All-Purpose Flour")
- Recipe Usage: Recipes reference Ingredients, allowing brand substitution
- Physical Properties: Density via 4-field model for unit conversion

**Product (Specific Purchasable Item - DEFINITION)**
- Represents a specific purchasable version with brand and package details
- Purpose: Track specific brands, packages, and suppliers
- Example: "King Arthur All-Purpose Flour, 25 lb bag"
- Preferred Supplier: Links to Supplier for shopping recommendations
- NO stored prices, NO inventory counts (definition only)

**Supplier (Vendor - DEFINITION)**
- Tracks where products are purchased
- Purpose: Enable supplier-based purchasing decisions
- Shopping Workflow: "I just shopped at Costco with 20 items" becomes streamlined

**Purchase (Transaction - INSTANTIATION)**
- Tracks specific purchase transactions
- Purpose: Price trend analysis and cost forecasting
- Benefits:
  - Identify price increases/decreases ($300 → $600 chocolate chips)
  - Calculate average cost over time periods
  - Support future price alerts
  - Audit trail for expense tracking
- **IMMUTABLE:** No updated_at field (transactions are permanent records)

**InventoryItem (Physical Lot - INSTANTIATION)**
- Represents physical inventory with FIFO support
- Purpose: Track what's actually on the shelf
- FIFO Consumption: Oldest items consumed first (matches physical flow)
- Links to Purchase: InventoryItem.purchase_id → Purchase for cost tracking

### Key Design Decisions

1. **Recipes Reference Ingredients, Not Products**
   - Recipes say "2 cups All-Purpose Flour" (generic)
   - Not tied to specific brand
   - User can switch brands without updating recipes
   - Cost calculation adapts based on actual inventory contents

2. **FIFO Costing Matches Physical Reality**
   - Consume oldest inventory first
   - Accurate cost tracking when prices fluctuate
   - Uses Purchase.unit_price via InventoryItem.purchase_id
   - Natural extension to lot/batch tracking

3. **Purchase Transactions as First-Class Entities**
   - Every inventory addition creates a Purchase record
   - Temporal price context (not just static price)
   - Enables trend analysis and price alerts
   - Supplier-specific pricing history
   - **Immutable:** Transactions never change (audit integrity)

4. **Industry Standards as Optional Enhancements**
   - Schema supports FoodOn, GTIN, FDC, etc.
   - Fields nullable - populate as needed
   - No upfront data entry burden
   - Future-ready for commercial features

---

## Unit Conversion Strategy

### Challenge
Ingredients are purchased in bulk units (e.g., 50 lb bags) but recipes call for smaller units (e.g., cups).

### Solution (Post-F019: 4-Field Density Model)

#### Ingredient Density Properties
Each Ingredient stores density information via 4 fields:
- `density_value` - Numeric density (e.g., 4.25)
- `density_from_unit` - Source unit (e.g., "cup")
- `density_to_unit` - Target unit (e.g., "lb")
- `density_note` - Optional context (e.g., "sifted", "packed")

**Example:** All-Purpose Flour
- density_value: 4.25
- density_from_unit: cup
- density_to_unit: lb
- density_note: "unsifted"
- **Meaning:** 4.25 cups = 1 lb

#### Standard Conversion Table
Standard unit conversions maintained in `unit_converter.py`:
- Weight: oz ↔ lb ↔ g ↔ kg
- Volume: tsp ↔ tbsp ↔ cup ↔ ml ↔ l
- Falls back to standard conversions when ingredient-specific density not available

---

## Event Planning Strategy

### Purpose
Enable comprehensive planning for seasonal baking events with recipient-package assignments and production tracking.

### Pattern Application

**Definitions:**
- Recipe (what to make)
- FinishedUnit (what recipes produce)
- FinishedGood (what assemblies create)
- Package (what to give)

**Instantiations:**
- EventProductionTarget (how many batches to produce)
- EventAssemblyTarget (how many assemblies to create)
- ProductionRun (actual batch production)
- AssemblyRun (actual assembly)

### Implementation
- Events track year, name, and event date
- Recipients can be assigned packages via EventRecipientPackage junction
- **Production Targets:** Event specifies how many batches of each recipe to produce
- **Assembly Targets:** Event specifies how many of each finished good to assemble
- **Progress Tracking:** Compare actual production/assembly vs. targets
- **Fulfillment Status:** Track package status (pending/ready/delivered)
- Shopping lists compare needs vs **live inventory** (no snapshots)
- Event service calculates:
  - Recipe batches needed across all assignments
  - Ingredient quantities needed (aggregated)
  - Shopping list (what to buy = needed - on_hand)
  - Total event cost (via FIFO from current Purchase records)

---

## Production Tracking Architecture

**See:** Features 013, 014, 016 specs for details

### Core Concepts

**ProductionRun (Instantiation):**
- Records when recipe batches are produced
- Links to Recipe (definition) and optionally Event (context)
- Tracks actual yield, expected yield, production date
- **Cost Snapshot:** total_ingredient_cost, per_unit_cost at production time
- Production status: COMPLETE, PARTIAL_LOSS, TOTAL_LOSS
- Links to RecipeSnapshot for historical accuracy (F037)

**AssemblyRun (Instantiation):**
- Records when finished goods are assembled from finished units
- Links to FinishedGood (definition) and optionally Event (context)
- Tracks quantity assembled, assembly date
- ⚠️ **Future (F046+):** Add cost snapshot fields

**ProductionLoss (Instantiation Detail):**
- Detailed loss tracking linked to ProductionRun
- Loss category: burnt, broken, contaminated, dropped, wrong_ingredients, other
- Per-unit cost and total loss cost
- Yield balance constraint: `actual_yield + loss_quantity = expected_yield`

### Event-Centric Production Model
Production and assembly can be linked to events:
- `ProductionRun.event_id` (nullable FK)
- `AssemblyRun.event_id` (nullable FK)
- `EventProductionTarget` - Target batches per recipe for event
- `EventAssemblyTarget` - Target quantity per finished good for event

**Benefits:**
- Track progress toward event goals
- Distinguish event-specific production from general inventory
- Enable "Where do I stand for Christmas 2025?" queries
- Support replacement batch workflows (lost batches must be remade)

---

## Technology Decisions

### Why CustomTkinter?
- Modern appearance vs standard Tkinter
- Cross-platform compatibility
- No dependencies on web technologies
- Mature and well-documented

### Why SQLite?
- No server setup required
- Portable database file
- Supports all needed features (foreign keys, transactions)
- Excellent Python integration
- Easy backup (single file)

### Why SQLAlchemy?
- ORM simplifies database operations
- Type safety with models
- Automatic relationship management
- Schema definition via models (no migration scripts needed for desktop phase)

### Why No Migration Scripts?
**See:** Constitution Principle VI

For single-user desktop application with robust import/export:
- Schema changes handled via **export → reset → import cycle**
- Export all data to JSON before schema change
- Delete database, update models, recreate empty database
- Programmatically transform JSON to match new schema if needed
- Import transformed data to restored database
- **Simpler, more reliable** than maintaining migration scripts
- **Eliminates** entire category of migration-related bugs

**Migration tooling reconsidered when:**
- Multi-user deployment (web phase)
- Independent databases that must upgrade in place

---

## Security Considerations

- **No Network Exposure:** Offline application, no attack surface
- **Data Validation:** Input validation at UI and service layers
- **SQL Injection:** Prevented by SQLAlchemy parameterized queries
- **Backup:** User responsible for file backup (Carbonite, OneDrive, etc.)

---

## Performance Considerations

- **Database Indexes:** On foreign keys and frequently queried fields
- **Lazy Loading:** Related objects loaded on demand
- **Eager Loading:** Strategic use of `joinedload()` for performance
- **Query Optimization:** Efficient joins and batch operations
- **FIFO Optimization:** Indexed by purchase_date for performance

---

## Testing Strategy

- **Unit Tests:** Services and unit converter logic
- **Integration Tests:** Database operations with in-memory SQLite
- **Manual UI Testing:** CustomTkinter difficult to automate
- **Coverage Goal:** >70% for services layer
- **Spec-Kitty Workflow:** Test-driven development via spec-kitty tooling

---

## Session Management (CRITICAL)

### The Nested Session Problem

**CRITICAL BUG PATTERN:** When a service function uses `session_scope()` and calls another service that also uses `session_scope()`, objects from the outer scope become **detached** and modifications are silently lost.

This issue was discovered during Feature 016 development and caused 5 test failures where `FinishedUnit.inventory_count` modifications were not persisting.

### Required Pattern

Service functions that may be called from other services MUST accept an optional `session` parameter:

```python
def service_function(..., session=None):
    """Service function that accepts optional session."""
    if session is not None:
        return _service_function_impl(..., session)
    with session_scope() as session:
        return _service_function_impl(..., session)
```

**Reference:** See `docs/design/session_management_remediation_spec.md` for full details.

---

## UI Widget Patterns (Emerging)

### Type-Ahead Filtering (F029)
Custom `TypeAheadComboBox` widget for dropdown filtering with word boundary priority.

**Location:** `src/ui/widgets/type_ahead_combobox.py`

### Session State Management (F029)
Application-level `SessionState` singleton for cross-dialog persistence (supplier, category selections).

**Location:** `src/ui/session_state.py`

### Recency Intelligence (F029)
Service-layer queries for identifying frequently-used items (temporal + frequency recency).

**Location:** Methods in `src/services/inventory_service.py`

---

## Import/Export Architecture

### Catalog Import vs Unified Import (F020)

**Two import pathways:**

1. **Catalog Import** - Reference data (ingredients, products, recipes)
   - `ADD_ONLY` mode: Create new records, skip existing (default)
   - `AUGMENT` mode: Update NULL fields on existing records
   - FK validation before import
   - Dry-run preview mode

2. **Unified Import** - Complete database restore (all entities)
   - Used for development workflow
   - Export → Reset → Import cycle
   - Lossless and version-controlled

### Version 4.1 Breaking Changes (F045)

**Export format v4.1 removes stored costs:**
- Removed `finished_units[].unit_cost` field
- Removed `finished_goods[].total_cost` field
- Import validates structure strictly and REJECTS old formats
- Users must manually update v4.0 exports before importing

**Philosophy enforcement:** Costs only exist on instantiations (transactions), not definitions (catalog).

---

## Future Enhancements

### Near-Term (6-18 Months) - Web Application Learning Phase
**See:** Constitution Principle VII for full context

The web migration serves as a **learning laboratory** for cloud development with constraints:
- Hobby scale (10-50 users: family, friends, neighbors)
- Still baking-focused (validate core use case)
- New capability: User accounts, data isolation, shared recipes (opt-in)

### Long-Term Vision (1-3+ Years)
After validating web deployment and multi-user patterns:

**Platform Expansion:**
- Any food type (BBQ, catering, meal prep, restaurant prep)
- Any event type (weddings, festivals, weekly planning, catering orders)
- Multi-language support with full internationalization
- Output flexibility (packages, people served, dishes, portions, orders)

**Data Integration & Automation:**
- Programmatic ingredient/recipe ingestion
- Supplier API connections (pricing, availability, ordering)
- Mobile companion app (shopping, inventory, notifications)

**Intelligence & Enhancement:**
- AI-powered menu generation and optimization
- Nutritional analysis and dietary accommodation
- Recipe scaling and cost optimization

---

## Pattern Checklist for New Features

When designing new features, verify compliance with core patterns:

**Definition vs Instantiation:**
- [ ] Definitions have NO stored costs (calculate fresh)
- [ ] Definitions persist when instances = 0
- [ ] Instantiations capture temporal context (date/time)
- [ ] Instantiations snapshot costs at transaction time
- [ ] Instantiations are immutable where appropriate

**FIFO Pattern:**
- [ ] Inventory consumption uses FIFO (oldest first)
- [ ] Costs link to Purchase records (temporal pricing)
- [ ] Cost snapshots captured at consumption time

**Model Responsibilities:**
- [ ] Models define schema and relationships
- [ ] Services handle business logic and calculations
- [ ] UI displays data and captures input
- [ ] No stored costs on definitions
- [ ] Cost calculations in service layer

---

**Document Status:** Living document - comprehensive architectural overview  
**Last Comprehensive Review:** 2026-01-09  
**Last Updated:** 2026-01-09 (definition/instantiation pattern analysis and documentation)  
**Schema Version Documented:** v0.7+ (post-F045 cost refactor)
