# Architecture Document

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
  - Undo management

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
│  ┌─────────┐ ┌─────────┐ ┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │Dashboard│ │Inventory│ │Recipe│ │Finished│ │Bundles │ │Packages│ │
│  │   Tab   │ │   Tab   │ │ Tab  │ │ Goods  │ │  Tab   │ │  Tab   │ │
│  └─────────┘ └─────────┘ └──────┘ └────────┘ └────────┘ └────────┘ │
│  ┌────────┐  ┌──────────┐  ┌───────────────────────────────────┐   │
│  │Recipients │  │ Events   │  │   EventDetailWindow (4 tabs)    │   │
│  │   Tab   │  │   Tab    │  │  - Assignments                    │   │
│  └────────┘  └──────────┘  │  - Recipe Needs                   │   │
│                             │  - Shopping List                  │   │
│                             │  - Summary                        │   │
│                             └───────────────────────────────────┘   │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                       Business Logic Layer                            │
│  ┌──────────┐ ┌────────┐ ┌────────────┐ ┌────────┐ ┌──────────────┐ │
│  │Ingredient│ │Variant │ │  Pantry    │ │Purchase│ │    Recipe    │ │
│  │ Service  │ │Service │ │  Service   │ │Service │ │   Service    │ │
│  └──────────┘ └────────┘ └────────────┘ └────────┘ └──────────────┘ │
│  ┌────────────┐ ┌────────┐ ┌───────────┐ ┌─────────────────────────┐│
│  │Finished Gd │ │Package │ │  Event    │ │  Recipient              ││
│  │  Service   │ │Service │ │  Service  │ │  Service                ││
│  └────────────┘ └────────┘ └───────────┘ └─────────────────────────┘│
│  ┌──────────────┐ ┌────────────────────────────────┐                │
│  │Unit Converter│ │  Import/Export Service         │                │
│  └──────────────┘ └────────────────────────────────┘                │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                      Data Access Layer                                │
│  ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────┐ ┌─────────┐  │
│  │Ingredient│ │Recipe│ │Finished  │ │Bundle│ │Package│ │Recipient│  │
│  │  Model   │ │Model │ │Good Model│ │Model │ │Model  │ │ Model   │  │
│  └────┬─────┘ └──────┘ └──────────┘ └──────┘ └──────┘ └─────────┘  │
│       │                                                               │
│  ┌────┴──────┬──────────┬──────────────┬───────────────┐            │
│  │  Variant  │ Purchase │  PantryItem  │ UnitConversion│            │
│  │   Model   │  Model   │    Model     │     Model     │            │
│  └───────────┴──────────┴──────────────┴───────────────┘            │
│  ┌──────┐  ┌───────────────────┐                                    │
│  │Event │  │EventRecipientPkg  │  (Junction tables for many-to-many)│
│  │Model │  │   (Junction)      │                                    │
│  └──────┘  └───────────────────┘                                    │
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
   - Retrieves current inventory (ingredient.quantity)
   - Calculates shortfall: `to_buy = needed - on_hand`
   - Includes cost per ingredient: `cost = to_buy × (unit_cost / conversion_factor)`
   - Returns list with only items where `to_buy > 0`
4. **Data Layer:** SQLAlchemy models query with eager loading (joinedload)
5. **Response:** Service returns list of dicts: `{ingredient, needed, on_hand, to_buy, cost}`
6. **UI Layer:** Displays shopping list table with totals

## Database Schema Overview

(See [SCHEMA.md](SCHEMA.md) for detailed schema)

### Core Entities

#### Inventory Management (Ingredient/Variant Architecture)
- **Ingredient** - Generic ingredient definitions (e.g., "All-Purpose Flour")
  - Brand-agnostic, represents the "platonic ideal" of an ingredient
  - Stores recipe unit and category
  - Supports industry standard identifiers (FoodOn, FDC, FoodEx2, LanguaL)
- **Variant** - Specific brand/package versions (e.g., "King Arthur 25 lb bag")
  - Links to parent Ingredient
  - Stores brand, package size, UPC/GTIN, supplier information
  - Preferred variant flag for shopping recommendations
- **Purchase** - Price history tracking for trend analysis
  - Links to Variant
  - Tracks purchase date, quantity, unit cost, supplier
  - Enables price trend calculations and alerts
- **PantryItem** - Actual inventory with FIFO support
  - Links to Variant
  - Tracks quantity, purchase date, expiration date, location
  - FIFO consumption for accurate cost calculations
- **UnitConversion** - Ingredient-specific conversion factors
  - Links to Ingredient
  - Stores from/to unit conversions (e.g., 1 lb → 3.6 cups for flour)
  - Supports notes for context (e.g., "sifted", "packed")

#### Recipe & Event Planning
- **Recipes** - Instructions with ingredient lists
- **Finished Goods** - Baked items from recipes
- **Bundles** - Collections of finished goods
- **Packages** - Gift collections of bundles
- **Recipients** - People receiving packages
- **Events** - Holiday seasons with planning data

### Key Relationships

#### Ingredient/Variant Hierarchy
```
Ingredient (generic)
├─ Variant (brand-specific)
│  ├─ Purchase (price history)
│  └─ PantryItem (actual inventory)
└─ UnitConversion (conversion factors)

Ingredient ←→ Recipe (many-to-many via RecipeIngredient)
  - Recipes reference generic Ingredients, not specific Variants
  - Enables brand-agnostic recipes
  - Cost calculation uses FIFO from pantry or preferred variant
```

#### Recipe & Event Planning
```
Recipe → Finished Good (one-to-many)
Finished Good → Bundle (one-to-many, simplified: each bundle has 1 FG type)
Bundle ←→ Package (many-to-many via PackageBundle)
Event ←→ Recipient ←→ Package (via EventRecipientPackage junction)
```

**Migration Note:** RecipeIngredient currently has dual foreign keys (`ingredient_id` for legacy, `ingredient_new_id` for refactored architecture) to support gradual migration.

## Ingredient/Variant Architecture (v0.4.0 Refactor)

### Design Philosophy
The inventory system follows a **"future-proof schema, present-simple implementation"** approach:
- All industry standard fields added to schema as nullable
- Only required fields populated initially
- Incremental feature adoption without schema changes
- Ready for commercial product evolution

### Separation of Concerns

#### Ingredient (Generic Concept)
Represents the platonic ideal of an ingredient, independent of brand or package:
- **Purpose:** Brand-agnostic recipe references
- **Example:** "All-Purpose Flour" (not "King Arthur 25 lb All-Purpose Flour")
- **Recipe Usage:** Recipes reference Ingredients, allowing brand substitution
- **Industry Standards:** Supports FoodOn, FDC, FoodEx2, LanguaL identifiers
- **Physical Properties:** Density, moisture percentage, allergen information

#### Variant (Specific Product)
Represents a specific purchasable version with brand and package details:
- **Purpose:** Track specific brands, packages, and suppliers
- **Example:** "King Arthur All-Purpose Flour, 25 lb bag"
- **Preferred Flag:** Mark preferred variants for shopping recommendations
- **UPC/GTIN:** Barcode support for future mobile scanning
- **Industry Standards:** GS1 GTIN, GPC brick codes, brand owner tracking
- **Calculated Properties:**
  - `display_name` - Formatted display (brand + package)
  - `get_most_recent_purchase()` - Latest purchase for current price
  - `get_average_price(days)` - Price averaging over time period
  - `get_total_pantry_quantity()` - Aggregate across all pantry items

#### Purchase (Price History)
Tracks all purchase transactions for a variant:
- **Purpose:** Price trend analysis and cost forecasting
- **Benefits:**
  - Identify price increases/decreases
  - Calculate average cost over time periods
  - Support future price alerts
  - Audit trail for expense tracking

#### PantryItem (Actual Inventory)
Represents physical inventory with FIFO support:
- **Purpose:** Track what's actually on the shelf
- **FIFO Consumption:** Oldest items consumed first (matches physical flow)
- **Lot Tracking Ready:** Each item can represent a lot/batch
- **Expiration Tracking:** Monitor shelf life
- **Location Tracking:** Store inventory location (future UI feature)

### Key Design Decisions

1. **Recipes Reference Ingredients, Not Variants**
   - Recipes say "2 cups All-Purpose Flour" (generic)
   - Not tied to specific brand
   - User can switch brands without updating recipes
   - Cost calculation adapts based on actual pantry contents

2. **FIFO Costing Matches Physical Reality**
   - Consume oldest inventory first
   - Accurate cost tracking when prices fluctuate
   - Natural extension to lot/batch tracking
   - Industry standard approach

3. **Separate Product Management and Pantry Tabs**
   - "My Ingredients" tab: Manage catalog, variants, conversions
   - "My Pantry" tab: View/manage actual inventory
   - Cleaner separation of planning vs. execution
   - Reduces cognitive load

4. **Industry Standards as Optional Enhancements**
   - Schema supports FoodOn, GTIN, FDC, etc.
   - Fields nullable - populate as needed
   - No upfront data entry burden
   - Future-ready for commercial features

### Migration Strategy

**Gradual Migration Approach:**
1. Legacy `Ingredient` model renamed to `IngredientLegacy`
2. New architecture implemented in parallel
3. RecipeIngredient has dual FKs:
   - `ingredient_id` → IngredientLegacy (old)
   - `ingredient_new_id` → Ingredient (new)
4. Migration script populates new models from legacy data
5. After validation, legacy references can be removed

**Benefits:**
- Zero downtime migration
- Validate before committing
- Rollback capability
- Incremental testing

## Unit Conversion Strategy

### Challenge
Ingredients are purchased in bulk units (e.g., 50 lb bags) but recipes call for smaller units (e.g., cups).

### Solution (Refactored Architecture)

#### Variant Purchase/Package Information
Each Variant stores:
- `purchase_unit` - Unit purchased in (e.g., "bag")
- `purchase_quantity` - Quantity in package (e.g., 25)
- Package size details (net_content_value, net_content_uom for industry specs)

#### Ingredient-Specific Conversions
UnitConversion model stores ingredient-specific factors:
- Links to parent Ingredient
- `from_unit` / `from_quantity` → `to_unit` / `to_quantity`
- Example: 1 lb All-Purpose Flour → 3.6 cups (unsifted)
- Supports multiple conversions per ingredient (lb→cup, kg→cup, etc.)
- Optional notes field for context ("sifted", "packed brown sugar", etc.)

#### Standard Conversion Table
Standard unit conversions maintained in `unit_converter.py`:
- Weight: oz ↔ lb ↔ g ↔ kg
- Volume: tsp ↔ tbsp ↔ cup ↔ ml ↔ l
- Falls back to standard conversions when ingredient-specific not available

### Cost Calculation (FIFO Strategy)

The refactored architecture uses **FIFO (First In, First Out)** for accurate cost tracking:

```python
# Primary: FIFO costing from pantry
def calculate_recipe_cost_fifo(recipe_id):
    total_cost = 0

    for recipe_ingredient in recipe.ingredients:
        ingredient_id = recipe_ingredient.ingredient_id
        quantity_needed = recipe_ingredient.quantity

        # Consume using FIFO and get cost breakdown
        consumed, cost_breakdown = consume_fifo(
            ingredient_id=ingredient_id,
            quantity_needed=quantity_needed
        )

        # Sum costs from each lot consumed
        total_cost += sum(item["cost"] for item in cost_breakdown)

        # Fallback: If insufficient inventory, estimate using preferred variant
        if consumed < quantity_needed:
            remaining = quantity_needed - consumed
            preferred_variant = get_preferred_variant(ingredient_id)
            fallback_cost = remaining * preferred_variant.get_current_cost_per_unit()
            total_cost += fallback_cost

    return total_cost
```

**Benefits:**
- Matches physical consumption (oldest first)
- Accurate when prices fluctuate
- Natural fit for lot tracking (future enhancement)
- Industry standard for food/manufacturing

## Event Planning Strategy

### Purpose
Enable comprehensive planning for seasonal baking events with recipient-package assignments.

### Implementation (Simplified Approach)
- Events track year, name, and event date
- Recipients can be assigned packages via EventRecipientPackage junction
- Shopping lists compare needs vs **live inventory** (simplified - no snapshots)
- Event service calculates:
  - Recipe batches needed across all assignments
  - Ingredient quantities needed (aggregated)
  - Shopping list (what to buy = needed - on_hand)
  - Total event cost

### Recipient History
- `get_recipient_history(recipient_id)` shows packages received in past events
- Displayed in assignment form to avoid duplicate gifts year-over-year
- Sorted by most recent first

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
- Migration support for schema changes

## Security Considerations

- **No Network Exposure:** Offline application, no attack surface
- **Data Validation:** Input validation at UI and service layers
- **SQL Injection:** Prevented by SQLAlchemy parameterized queries
- **Backup:** User responsible for file backup (Carbonite)

## Performance Considerations

- **Database Indexes:** On foreign keys and frequently queried fields
- **Lazy Loading:** Related objects loaded on demand
- **Caching:** Recently accessed data cached in memory
- **Query Optimization:** Efficient joins and batch operations

## Testing Strategy

- **Unit Tests:** Services and unit converter logic
- **Integration Tests:** Database operations with in-memory SQLite
- **Manual UI Testing:** CustomTkinter difficult to automate
- **Coverage Goal:** >70% for services layer

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

## Future Enhancements

- **Plugin System:** Allow custom reports/exporters
- **Cloud Sync:** Optional Dropbox/OneDrive integration
- **Mobile Companion:** Read-only shopping list app
- **Recipe Import:** Parse from websites

---

**Document Status:** Living document, updated as architecture evolves
**Last Updated:** 2025-12-11 (Added Session Management section - critical fix for nested session_scope issues)
