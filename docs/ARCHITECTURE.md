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
- **Location:** `data/baking_tracker.db`
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
│  │Inventory │ │ Recipe │ │Finished Gd │ │Package │ │    Event     │ │
│  │ Service  │ │Service │ │  Service   │ │Service │ │   Service    │ │
│  └──────────┘ └────────┘ └────────────┘ └────────┘ └──────────────┘ │
│  ┌───────────┐ ┌──────────────┐ ┌────────────────────────────────┐  │
│  │ Recipient │ │Unit Converter│ │  Import/Export Service         │  │
│  │  Service  │ └──────────────┘ └────────────────────────────────┘  │
│  └───────────┘                                                       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                      Data Access Layer                                │
│  ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────┐ ┌─────────┐  │
│  │Ingredient│ │Recipe│ │Finished  │ │Bundle│ │Package│ │Recipient│  │
│  │  Model   │ │Model │ │Good Model│ │Model │ │Model  │ │ Model   │  │
│  └──────────┘ └──────┘ └──────────┘ └──────┘ └──────┘ └─────────┘  │
│  ┌──────┐  ┌───────────────────┐                                    │
│  │Event │  │EventRecipientPkg  │  (Junction tables for many-to-many)│
│  │Model │  │   (Junction)      │                                    │
│  └──────┘  └───────────────────┘                                    │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────────────┐
│                       Data Storage Layer                              │
│                       SQLite Database                                 │
│                 (C:\Users\Kent\Documents\BakingTracker\               │
│                      baking_tracker.db)                               │
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
- **Ingredients** - Raw materials with purchase/recipe units
- **Inventory Snapshots** - Point-in-time inventory captures
- **Recipes** - Instructions with ingredient lists
- **Finished Goods** - Baked items from recipes
- **Bundles** - Collections of finished goods
- **Packages** - Gift collections of bundles
- **Recipients** - People receiving packages
- **Events** - Holiday seasons with planning data

### Key Relationships
```
Ingredient ←→ Recipe (many-to-many via RecipeIngredient)
Recipe → Finished Good (one-to-many)
Finished Good → Bundle (one-to-many, simplified: each bundle has 1 FG type)
Bundle ←→ Package (many-to-many via PackageBundle)
Event ←→ Recipient ←→ Package (via EventRecipientPackage junction)
```

**Note:** Inventory Snapshot feature was simplified out - shopping lists use live inventory.

## Unit Conversion Strategy

### Challenge
Ingredients are purchased in bulk units (e.g., 50 lb bags) but recipes call for smaller units (e.g., cups).

### Solution
Each ingredient stores:
- `purchase_unit` - Unit purchased in (e.g., "bag")
- `purchase_unit_size` - Size of purchase unit (e.g., "50 lb")
- `recipe_unit` - Unit used in recipes (e.g., "cup")
- `conversion_factor` - Purchase units to recipe units (e.g., 200 = 1 bag = 200 cups)

### Conversion Table
Standard conversions maintained in `unit_converter.py`:
- Weight: oz ↔ lb ↔ g ↔ kg
- Volume: tsp ↔ tbsp ↔ cup ↔ ml ↔ l
- Custom: User-defined conversions per ingredient

### Cost Calculation
```python
recipe_cost = sum(
    (ingredient.unit_cost / ingredient.conversion_factor) * recipe_quantity
    for each ingredient
)
```

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

## Future Enhancements

- **Plugin System:** Allow custom reports/exporters
- **Cloud Sync:** Optional Dropbox/OneDrive integration
- **Mobile Companion:** Read-only shopping list app
- **Recipe Import:** Parse from websites

---

**Document Status:** Living document, updated as architecture evolves
**Last Updated:** 2025-11-04 (Phase 3b completion - Event planning features and import/export expansion)
