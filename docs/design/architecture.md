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
> - **Feature Roadmap:** [`/docs/feature_roadmap.md`](../feature_roadmap.md) - Completed and planned features
> - **Constitution:** [`/.kittify/memory/constitution.md`](../../.kittify/memory/constitution.md) - Core architectural principles
>
> **Document Status:**
> - Last comprehensive review: 2025-12-11
> - Schema version documented: v0.4 (Current production: v0.6+)
> - Last updated: 2025-12-24 (obsolete reference cleanup, schema evolution section added)
>
> **Known Gaps:**
> - Production tracking architecture (see F013, F014, F016 specs)
> - Enhanced inventory management (see F027, F028, F029 specs)
> - Deferred packaging decisions (see F026 spec)
> - Import/export enhancements (see F020, F030 specs)

---

## System Overview

The Seasonal Baking Tracker is a desktop application built with Python and CustomTkinter, using SQLite for data persistence.

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
  - Cost calculations
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

### 4. Data Storage Layer
- **Technology:** SQLite
- **Location:** `data/bake_tracker.db`
- **Features:**
  - Write-Ahead Logging (WAL) mode
  - Foreign key constraints
  - Transaction support

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
│  Core Catalog & Inventory:                                           │
│  ┌──────────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌─────────────────┐   │
│  │Ingredient│ │Product│ │Supplier│ │Purchase│ │ InventoryItem   │   │
│  │  Model   │ │Model │ │ Model  │ │ Model  │ │ (InventoryAdd.) │   │
│  └──────────┘ └──────┘ └────────┘ └────────┘ └─────────────────┘   │
│                                                                       │
│  Recipes & Production:                                               │
│  ┌──────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │Recipe│ │RecipeIngred. │ │RecipeComp.   │ │ProductionRun │       │
│  │Model │ │(Junction)    │ │(Nested)      │ │ Model        │       │
│  └──────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│  ┌──────────────┐ ┌──────────────┐                                  │
│  │FinishedUnit  │ │FinishedGood  │                                  │
│  │   Model      │ │   Model      │                                  │
│  └──────────────┘ └──────────────┘                                  │
│  ┌──────────────┐ ┌──────────────┐                                  │
│  │ AssemblyRun  │ │ProductionLoss│                                  │
│  │    Model     │ │    Model     │                                  │
│  └──────────────┘ └──────────────┘                                  │
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
│  ┌────────────────────┐ ┌──────────────────┐                        │
│  │EventPackagingReq   │ │EventPackagingAsn │                        │
│  │   (Requirement)    │ │   (Assignment)   │                        │
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

## Data Flow

### Example: Creating a Shopping List for an Event

1. **User Action:** User opens Event, clicks "View Details", then switches to "Shopping List" tab
2. **UI Layer:** `event_detail_window.py` calls `event_service.generate_shopping_list(event_id)`
3. **Service Layer (`event_service.py`):**
   - Retrieves event and all EventRecipientPackage assignments
   - For each assignment:
     - Gets package → bundles → finished goods → recipes
     - Calculates ingredient quantities needed (accounting for quantities at each level)
   - Aggregates ingredients by ID
   - Retrieves current inventory (from InventoryItem via Product → Ingredient)
   - Calculates shortfall: `to_buy = needed - on_hand`
   - Includes cost per ingredient: `cost = to_buy × (unit_cost / conversion_factor)`
   - Returns list with only items where `to_buy > 0`
4. **Data Layer:** SQLAlchemy models query with eager loading (joinedload)
5. **Response:** Service returns list of dicts: `{ingredient, needed, on_hand, to_buy, cost}`
6. **UI Layer:** Displays shopping list table with totals

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
- Added `Purchase` table for price history
- Added `Product.preferred_supplier_id` FK
- Added `Product.is_hidden` flag
- Added `InventoryAddition.purchase_id` FK (replaced `price_paid`)
- **Major Shift:** Purchase transactions as first-class entities, FIFO uses Purchase.unit_price

#### v0.6+ - Production Loss & Deferred Packaging (F025, F026)
**Date:** 2025-12-21, 2025-12-22  
**Specs:** F025 (Production Loss), F026 (Deferred Packaging)

- Added `ProductionLoss` table for loss tracking
- Added `production_status`, `loss_quantity`, `loss_notes` to ProductionRun
- Added `EventPackagingRequirement` and `EventPackagingAssignment` tables
- **Key Patterns:** Yield balance constraint, deferred material assignment

#### Current Schema (v0.7+)
**Complete Entity List:** See [`SCHEMA.md`](SCHEMA.md)

**Core Domains:**
- **Catalog:** Ingredient, Product, Supplier, Units (reference table)
- **Inventory:** InventoryItem, Purchase, InventoryAddition
- **Recipes:** Recipe, RecipeIngredient, RecipeComponent (nested)
- **Production:** ProductionRun, AssemblyRun, ProductionLoss
- **Products:** FinishedUnit, FinishedGood, Composition
- **Events:** Event, EventRecipientPackage, EventProductionTarget, EventAssemblyTarget, EventPackagingRequirement, EventPackagingAssignment
- **Packaging:** Bundle, Package, PackageBundle
- **People:** Recipient

**Schema Change Strategy:** See Constitution Principle VI - Export/Reset/Import workflow (no migration scripts for desktop phase)

### Core Entities

#### Inventory Management (Ingredient/Product Architecture)
- **Ingredient** - Generic ingredient definitions (e.g., "All-Purpose Flour")
  - Brand-agnostic, represents the "platonic ideal" of an ingredient
  - Stores category and physical properties (density via 4-field model)
  - Supports industry standard identifiers (FoodOn, FDC, FoodEx2, LanguaL)
- **Product** - Specific brand/package versions (e.g., "King Arthur 25 lb bag")
  - Links to parent Ingredient
  - Stores brand, package size, UPC/GTIN, supplier information
  - Preferred supplier flag for shopping recommendations
  - Can be hidden to preserve history without cluttering UI
- **Supplier** - Vendor/store tracking
  - Name, address, contact information
  - Links to Products via preferred_supplier_id
  - Can be deactivated to preserve history
- **Purchase** - Price history tracking for trend analysis
  - Links to Product and Supplier
  - Tracks purchase date, quantity, unit cost
  - Enables price trend calculations and alerts
  - Replaces static price data with temporal context
- **InventoryItem** - Actual inventory with FIFO support
  - Links to Product
  - Tracks quantity, addition date, location
  - **InventoryAddition** sub-entity links to Purchase for cost tracking
  - FIFO consumption for accurate cost calculations

#### Recipe & Event Planning
- **Recipes** - Instructions with ingredient lists
  - Can reference sub-recipes via RecipeComponent (nested recipes)
  - Recursive cost calculation
- **Finished Goods** - Baked items from recipes
- **Bundles** - Collections of finished goods
- **Packages** - Gift collections of bundles
- **Recipients** - People receiving packages
- **Events** - Holiday seasons with planning data
  - Production targets (batches per recipe)
  - Assembly targets (quantities per finished good)
  - Packaging requirements and assignments
  - Progress tracking and fulfillment status

#### Production Tracking
- **ProductionRun** - Records of recipe batches produced
  - Links to Recipe and optionally Event
  - Tracks actual yield, production date, loss quantity
  - Production status (COMPLETE/PARTIAL_LOSS/TOTAL_LOSS)
- **AssemblyRun** - Records of finished goods assembled
  - Links to FinishedGood and optionally Event
  - Tracks quantity assembled, packaging materials used
- **ProductionLoss** - Detailed loss tracking
  - Links to ProductionRun
  - Loss category (burnt/broken/contaminated/dropped/wrong_ingredients/other)
  - Per-unit cost and total loss cost

### Key Relationships

#### Ingredient/Product Hierarchy
```
Ingredient (generic)
├─ Product (brand-specific)
│  ├─ Purchase (price history)
│  │  └─ InventoryAddition.purchase_id → Purchase
│  └─ InventoryItem (actual inventory)
│     └─ InventoryAddition (tracks Purchase for FIFO costing)
└─ Density fields (4-field model for unit conversion)

Ingredient ←→ Recipe (many-to-many via RecipeIngredient)
  - Recipes reference generic Ingredients, not specific Products
  - Enables brand-agnostic recipes
  - Cost calculation uses FIFO from inventory via Purchase.unit_price
```

#### Recipe & Event Planning
```
Recipe → Finished Good (one-to-many)
  └─ RecipeComponent → Recipe (self-referential for nested recipes)

Finished Good → Bundle (one-to-many, simplified: each bundle has 1 FG type)

Bundle ←→ Package (many-to-many via PackageBundle)

Event ←→ Recipient ←→ Package (via EventRecipientPackage junction)
  └─ Event has ProductionTargets and AssemblyTargets
  └─ Event has PackagingRequirements and PackagingAssignments

ProductionRun → Event (optional FK for event-linked production)
AssemblyRun → Event (optional FK for event-linked assembly)
```

## Ingredient/Product Architecture (v0.4.0+ Refactor)

### Design Philosophy
The inventory system follows a **"future-proof schema, present-simple implementation"** approach:
- All industry standard fields added to schema as nullable
- Only required fields populated initially
- Incremental feature adoption without schema changes
- User NOT burdened with unnecessary data entry upfront
- Optional enhancements clearly documented for future phases

### Separation of Concerns

#### Ingredient (Generic Concept)
Represents the platonic ideal of an ingredient, independent of brand or package:
- **Purpose:** Brand-agnostic recipe references
- **Example:** "All-Purpose Flour" (not "King Arthur 25 lb All-Purpose Flour")
- **Recipe Usage:** Recipes reference Ingredients, allowing brand substitution
- **Industry Standards:** Supports FoodOn, FDC, FoodEx2, LanguaL identifiers
- **Physical Properties:** Density via 4-field model (`density_value`, `density_from_unit`, `density_to_unit`, `density_note`)

#### Product (Specific Purchasable Item)
Represents a specific purchasable version with brand and package details:
- **Purpose:** Track specific brands, packages, and suppliers
- **Example:** "King Arthur All-Purpose Flour, 25 lb bag"
- **Preferred Supplier:** Links to Supplier for shopping recommendations
- **UPC/GTIN:** Barcode support for future mobile scanning
- **Industry Standards:** GS1 GTIN, GPC brick codes, brand owner tracking
- **Hidden Flag:** Can hide products while preserving purchase/inventory history

#### Supplier (Vendor Tracking)
Tracks where products are purchased:
- **Purpose:** Enable supplier-based purchasing decisions ("Costco is cheaper for bulk chocolate")
- **Shopping Workflow:** "I just shopped at Costco with 20 items" becomes streamlined
- **Price Context:** Different suppliers may have different prices for same product

#### Purchase (Price History)
Tracks all purchase transactions for a product:
- **Purpose:** Price trend analysis and cost forecasting
- **Benefits:**
  - Identify price increases/decreases ($300 → $600 chocolate chips)
  - Calculate average cost over time periods
  - Support future price alerts
  - Audit trail for expense tracking
- **FIFO Integration:** InventoryAddition.purchase_id links to Purchase for accurate costing

#### InventoryItem (Actual Inventory)
Represents physical inventory with FIFO support:
- **Purpose:** Track what's actually on the shelf
- **FIFO Consumption:** Oldest items consumed first (matches physical flow)
- **Lot Tracking Ready:** Each item can represent a lot/batch
- **Location Tracking:** Store inventory location (future UI feature)
- **InventoryAddition:** Sub-entity links inventory to Purchase for cost tracking

### Key Design Decisions

1. **Recipes Reference Ingredients, Not Products**
   - Recipes say "2 cups All-Purpose Flour" (generic)
   - Not tied to specific brand
   - User can switch brands without updating recipes
   - Cost calculation adapts based on actual inventory contents

2. **FIFO Costing Matches Physical Reality**
   - Consume oldest inventory first
   - Accurate cost tracking when prices fluctuate
   - Uses Purchase.unit_price via InventoryAddition.purchase_id
   - Natural extension to lot/batch tracking
   - Industry standard approach

3. **Purchase Transactions as First-Class Entities**
   - Every inventory addition creates a Purchase record
   - Temporal price context (not just static price)
   - Enables trend analysis and price alerts
   - Supplier-specific pricing history

4. **Industry Standards as Optional Enhancements**
   - Schema supports FoodOn, GTIN, FDC, etc.
   - Fields nullable - populate as needed
   - No upfront data entry burden
   - Future-ready for commercial features

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

#### Historical Note
**Removed in F019:**
- `UnitConversion` model/table (redundant with density model)
- `Ingredient.recipe_unit` field (recipes declare their own units)

**Rationale:** 4-field density model is sufficient for all conversion needs. Removing redundant mechanisms simplifies codebase and eliminates inconsistency risk.

### Cost Calculation (FIFO Strategy)

The refactored architecture uses **FIFO (First In, First Out)** for accurate cost tracking:

```python
# Primary: FIFO costing from inventory using Purchase prices
def calculate_recipe_cost_fifo(recipe_id):
    total_cost = 0

    for recipe_ingredient in recipe.ingredients:
        ingredient_id = recipe_ingredient.ingredient_id
        quantity_needed = recipe_ingredient.quantity

        # Consume using FIFO and get cost breakdown
        # InventoryAddition.purchase_id → Purchase.unit_price
        consumed, cost_breakdown = consume_fifo(
            ingredient_id=ingredient_id,
            quantity_needed=quantity_needed
        )

        # Sum costs from each Purchase consumed
        total_cost += sum(item["cost"] for item in cost_breakdown)

        # Fallback: If insufficient inventory, estimate using preferred product
        if consumed < quantity_needed:
            remaining = quantity_needed - consumed
            preferred_product = get_preferred_product(ingredient_id)
            # Get most recent Purchase for this product
            latest_purchase = preferred_product.get_most_recent_purchase()
            fallback_cost = remaining * latest_purchase.unit_price
            total_cost += fallback_cost

    return total_cost
```

**Benefits:**
- Matches physical consumption (oldest first)
- Accurate when prices fluctuate ($300 → $450 → $600 chocolate chips)
- Natural fit for lot tracking (future enhancement)
- Industry standard for food/manufacturing
- Temporal price context via Purchase transactions

## Event Planning Strategy

### Purpose
Enable comprehensive planning for seasonal baking events with recipient-package assignments and production tracking.

### Implementation
- Events track year, name, and event date
- Recipients can be assigned packages via EventRecipientPackage junction
- **Production Targets:** Event specifies how many batches of each recipe to produce
- **Assembly Targets:** Event specifies how many of each finished good to assemble
- **Progress Tracking:** Compare actual production/assembly vs. targets
- **Fulfillment Status:** Track package status (pending/ready/delivered)
- **Packaging Workflow:** Generic packaging requirements, deferred material assignment until assembly
- Shopping lists compare needs vs **live inventory** (no snapshots)
- Event service calculates:
  - Recipe batches needed across all assignments
  - Ingredient quantities needed (aggregated)
  - Shopping list (what to buy = needed - on_hand)
  - Total event cost (via FIFO)

### Event Production Dashboard
**See:** Feature 018 spec for details

Provides "mission control" view for event production:
- Progress bars per recipe/finished good vs. targets
- Fulfillment status tracking with visual indicators
- Multi-event overview (compare progress across events)
- Quick actions (jump to record production, view shopping list)

### Recipient History
- `get_recipient_history(recipient_id)` shows packages received in past events
- Displayed in assignment form to avoid duplicate gifts year-over-year
- Sorted by most recent first

### Deferred Packaging Decisions
**See:** Feature 026 spec for details

Allows planning with generic packaging requirements:
- **Event Planning:** Select generic packaging product (e.g., "Cellophane Bags 6x10")
- **Decision Timing:** Anytime from planning through assembly
- **Material Assignment:** User assigns specific material during assembly definition
- **Cost Updates:** Estimated (average for generic) → Actual (specific material assigned)

## Production Tracking Architecture

**See:** Features 013, 014, 016 specs for details

### Core Concepts

**ProductionRun:**
- Records when recipe batches are produced
- Links to Recipe and optionally Event (for event-specific production)
- Tracks actual yield, expected yield, production date
- Production status: COMPLETE, PARTIAL_LOSS, TOTAL_LOSS
- Loss quantity and loss notes

**AssemblyRun:**
- Records when finished goods are assembled from finished units
- Links to FinishedGood and optionally Event
- Tracks quantity assembled, assembly date
- Material assignment for packaging (specific products selected during assembly)

**ProductionLoss:**
- Detailed loss tracking linked to ProductionRun
- Loss category: burnt, broken, contaminated, dropped, wrong_ingredients, other
- Per-unit cost and total loss cost
- Yield balance constraint: `actual_yield + loss_quantity = expected_yield`

### Event-Centric Production Model
**Schema v0.6 (Feature 016):**

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

## Security Considerations

- **No Network Exposure:** Offline application, no attack surface
- **Data Validation:** Input validation at UI and service layers
- **SQL Injection:** Prevented by SQLAlchemy parameterized queries
- **Backup:** User responsible for file backup (Carbonite, OneDrive, etc.)

## Performance Considerations

- **Database Indexes:** On foreign keys and frequently queried fields
- **Lazy Loading:** Related objects loaded on demand
- **Eager Loading:** Strategic use of `joinedload()` for performance
- **Query Optimization:** Efficient joins and batch operations
- **FIFO Optimization:** Indexed by addition_date for performance

## Testing Strategy

- **Unit Tests:** Services and unit converter logic
- **Integration Tests:** Database operations with in-memory SQLite
- **Manual UI Testing:** CustomTkinter difficult to automate
- **Coverage Goal:** >70% for services layer
- **Spec-Kitty Workflow:** Test-driven development via spec-kitty tooling

## Session Management (CRITICAL)

### The Nested Session Problem

**CRITICAL BUG PATTERN:** When a service function uses `session_scope()` and calls another service that also uses `session_scope()`, objects from the outer scope become **detached** and modifications are silently lost.

This issue was discovered during Feature 016 development and caused 5 test failures where `FinishedUnit.inventory_count` modifications were not persisting.

### Root Cause

When the inner `session_scope()` exits and calls `session.close()`:
1. All objects in the session's identity map are cleared
2. Objects queried in the outer scope are no longer tracked by any session
3. Modifications to these detached objects are silently ignored on commit

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

When calling other services within a transaction, ALWAYS pass the session:

```python
def multi_step_operation(...):
    with session_scope() as session:
        obj = session.query(Model).first()
        # CORRECT: Pass session to maintain object tracking
        helper_function(..., session=session)
        obj.field = new_value  # Persists correctly
```

### Reference

See `docs/design/session_management_remediation_spec.md` for full details.

## UI Widget Patterns (Emerging)

### Type-Ahead Filtering (F029)
**See:** Feature 029 spec for details

Custom `TypeAheadComboBox` widget for dropdown filtering:
- Keystroke-based filtering (contains matching)
- Word boundary priority (matches at start of words rank higher)
- Configurable character threshold (1-2 chars before filtering)
- Recency markers preserved (⭐)
- Used for Category, Ingredient, Product dropdowns

**Location:** `src/ui/widgets/type_ahead_combobox.py`

### Session State Management (F029)
**See:** Feature 029 spec for details

Application-level `SessionState` singleton for cross-dialog persistence:
- Remembers last selected supplier (across all inventory additions)
- Remembers last selected category (filter for ingredient selection)
- Survives dialog close/reopen, resets on app restart
- NOT persisted to disk (in-memory only)

**Pattern:**
```python
from src.ui.session_state import get_session_state

class AddInventoryDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        self.session_state = get_session_state()
        
        # Pre-select from session state
        if self.session_state.last_supplier_id:
            self._select_supplier(self.session_state.last_supplier_id)
```

**Location:** `src/ui/session_state.py`

### Recency Intelligence (F029)
**See:** Feature 029 spec for details

Service-layer queries for identifying frequently-used items:
- **Temporal recency:** Items added in last 30 days
- **Frequency recency:** Items added 3+ times in last 90 days
- Union of both criteria (item qualifies if either condition met)
- Used to mark dropdown items with ⭐ and sort to top

**Pattern:**
```python
from src.services.inventory_service import get_recent_product_ids

recent_ids = get_recent_product_ids()  # [42, 55, 67, ...]
for product in products:
    if product.id in recent_ids:
        dropdown_label = f"⭐ {product.display_name}"
```

**Location:** Methods in `src/services/inventory_service.py`

## Import/Export Architecture

### Catalog Import vs Unified Import (F020)
**See:** Feature 020 spec for details

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

### Enhanced Export/Import System (F030 - In Progress)
**See:** Feature 030 spec for details

**Coordinated Exports:**
- Manifest with checksums, dependencies, import order
- Individual entity files with FK resolution fields (id + slug/name)
- ZIP archive option
- Standard filenames for working files

**Denormalized Views for AI Augmentation:**
- `view_products.json` - Products with ingredient/supplier context
- `view_inventory.json` - Inventory with product/purchase context
- `view_purchases.json` - Purchases with product/supplier context
- Editable fields vs read-only context fields
- Export → AI fills fields → Import with merge

**Interactive FK Resolution:**
- Import can create missing entities (Suppliers, Ingredients, Products)
- UI default: Interactive wizard prompts for resolution
- CLI default: Fail-fast, require `--interactive` flag
- Skip-on-error mode logs problematic records for later correction

## Future Enhancements

### Near-Term (6-18 Months) - Web Application Learning Phase
**See:** Constitution Principle VII for full context

The web migration serves as a **learning laboratory** for cloud development:
- **Architecture:** Desktop → Web patterns (API design, state management)
- **Data Design:** Single-user → Multi-user schema (tenant isolation)
- **UI Design:** Desktop native → Responsive web (mobile-friendly)
- **Technologies:** Evaluate frameworks (FastAPI/Flask + React/Vue vs Django)
- **Deployment:** Cloud hosting basics (AWS/GCP/Azure, containerization, CI/CD)
- **Security:** Authentication, authorization, encryption, vulnerability management

**Scope constraints:**
- Hobby scale (10-50 users: family, friends, neighbors)
- Still baking-focused (validate core use case)
- Still English-only (i18n separate learning curve)
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
- Accounting system integrations
- Recipe sharing platforms and import tools

**Intelligence & Enhancement:**
- AI-powered menu generation and optimization
- Nutritional analysis and dietary accommodation
- Recipe scaling and cost optimization
- Smart inventory predictions
- Social features and community recipe sharing

---

**Document Status:** Living document - high-level architectural overview  
**Last Comprehensive Review:** 2025-12-11  
**Last Updated:** 2025-12-24 (Option C update: navigation guide, schema evolution, obsolete reference cleanup)  
**Schema Version Documented:** v0.4 baseline (Current production: v0.7+)  
**Next Review Recommended:** After web migration planning begins

