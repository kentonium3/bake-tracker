 # Schema v0.6 Design - Event-Centric Production Model

**Purpose:** Add event-production linkage to enable progress tracking and fulfillment workflows. This addresses a fundamental structural gap where production runs were "orphaned" from events.

**Status:** IMPLEMENTED
**Created:** 2025-12-10
**Last Updated:** 2025-12-28
**Previous Version:** v0.5 (TD-001 cleanup, Features 011-014)

---

## Implementation Status

The v0.6 schema has been fully implemented and extended with additional features:

| Feature                             | Status     | Notes                                                    |
| ----------------------------------- | ---------- | -------------------------------------------------------- |
| F015/F016: Event-Centric Production | ✅ Complete | ProductionRun/AssemblyRun event_id, targets, fulfillment |
| F025: Production Loss Tracking      | ✅ Complete | ProductionLoss model, loss categories, status tracking   |
| F026: Packaging Bypass              | ✅ Complete | CompositionAssignment, bypass flags on AssemblyRun       |
| F027: Product Catalog Management    | ✅ Complete | Supplier, Purchase models, GTIN support                  |
| F022: Unit Reference Table          | ✅ Complete | Unit model for measurement standardization               |

---

## 1) Problem Statement

### The Structural Gap

The v0.5 schema correctly models:
- **Definition:** What IS a Cookie Gift Box? (FinishedGood + Composition) ✓
- **Inventory:** How many Cookie Gift Boxes EXIST? (inventory_count) ✓

But cannot answer:
- **Commitment:** How many are FOR Christmas 2025? ✗
- **Progress:** How close am I to fulfilling this event? ✗
- **Attribution:** Which production runs were for which event? ✗

### Root Cause

ProductionRun and AssemblyRun have no `event_id`. When a user records "made 2 batches of cookies," the system cannot link that production to a specific event.

### Impact

- Event summary reports cannot show accurate "planned vs actual"
- Production dashboards cannot show event-specific progress
- Package fulfillment status is not tracked
- Multi-event planning (Christmas + Easter prep overlap) is impossible

---

## 2) Schema Changes (v0.6)

### 2.1 Modified Tables

#### ProductionRun

**Add column:**
```sql
ALTER TABLE production_run ADD COLUMN event_id INTEGER REFERENCES event(id);
```

| Column     | Type    | Constraints              | Description                                             |
| ---------- | ------- | ------------------------ | ------------------------------------------------------- |
| `event_id` | Integer | FK → Event, **NULLABLE** | Which event this production was for (null = standalone) |

**Model update:**
```python
class ProductionRun(BaseModel):
    # ... existing fields ...
    event_id = Column(Integer, ForeignKey("event.id"), nullable=True, index=True)

    # Relationship
    event = relationship("Event", back_populates="production_runs")
```

#### AssemblyRun

**Add column:**
```sql
ALTER TABLE assembly_run ADD COLUMN event_id INTEGER REFERENCES event(id);
```

| Column     | Type    | Constraints              | Description                                           |
| ---------- | ------- | ------------------------ | ----------------------------------------------------- |
| `event_id` | Integer | FK → Event, **NULLABLE** | Which event this assembly was for (null = standalone) |

**Model update:**
```python
class AssemblyRun(BaseModel):
    # ... existing fields ...
    event_id = Column(Integer, ForeignKey("event.id"), nullable=True, index=True)

    # Relationship
    event = relationship("Event", back_populates="assembly_runs")
```

#### EventRecipientPackage

**Add column:**
```sql
ALTER TABLE event_recipient_package ADD COLUMN fulfillment_status TEXT DEFAULT 'pending';
```

| Column               | Type       | Constraints                 | Description             |
| -------------------- | ---------- | --------------------------- | ----------------------- |
| `fulfillment_status` | String(20) | NOT NULL, DEFAULT 'pending' | Package workflow status |

**Valid values:** `pending`, `ready`, `delivered`

**Model update:**
```python
class FulfillmentStatus(str, Enum):
    PENDING = "pending"      # Not yet assembled
    READY = "ready"          # Assembled, awaiting delivery
    DELIVERED = "delivered"  # Given to recipient

class EventRecipientPackage(BaseModel):
    # ... existing fields ...
    fulfillment_status = Column(
        String(20),
        nullable=False,
        default=FulfillmentStatus.PENDING.value
    )
```

#### Event

**Add relationships:**
```python
class Event(BaseModel):
    # ... existing fields ...

    # New relationships for v0.6
    production_runs = relationship("ProductionRun", back_populates="event")
    assembly_runs = relationship("AssemblyRun", back_populates="event")
    production_targets = relationship("EventProductionTarget", back_populates="event", cascade="all, delete-orphan")
    assembly_targets = relationship("EventAssemblyTarget", back_populates="event", cascade="all, delete-orphan")
```

---

### 2.2 New Tables

#### EventProductionTarget

**Purpose:** Define explicit production targets for an event. Answers "For Christmas 2025, how many batches of each recipe do I need to make?"

```sql
CREATE TABLE event_production_target (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipe(id) ON DELETE RESTRICT,
    target_batches INTEGER NOT NULL CHECK (target_batches > 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, recipe_id)
);

CREATE INDEX idx_event_production_target_event ON event_production_target(event_id);
CREATE INDEX idx_event_production_target_recipe ON event_production_target(recipe_id);
```

| Column           | Type     | Constraints                     | Description                    |
| ---------------- | -------- | ------------------------------- | ------------------------------ |
| `id`             | Integer  | PK, Auto                        | Unique identifier              |
| `uuid`           | String   |                                 | UUID for distributed scenarios |
| `event_id`       | Integer  | FK → Event, NOT NULL, CASCADE   | Which event                    |
| `recipe_id`      | Integer  | FK → Recipe, NOT NULL, RESTRICT | Which recipe                   |
| `target_batches` | Integer  | NOT NULL, > 0                   | How many batches to produce    |
| `notes`          | Text     |                                 | Planning notes                 |
| `created_at`     | DateTime | NOT NULL                        | When created                   |
| `updated_at`     | DateTime | NOT NULL                        | When last modified             |

**Constraints:**
- Unique on (event_id, recipe_id) - one target per recipe per event
- Delete event → cascade delete targets
- Delete recipe → restrict (must remove target first)

**Model:**
```python
class EventProductionTarget(BaseModel):
    __tablename__ = "event_production_target"

    event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False, index=True)
    recipe_id = Column(Integer, ForeignKey("recipe.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_batches = Column(Integer, nullable=False)
    notes = Column(Text)

    # Relationships
    event = relationship("Event", back_populates="production_targets")
    recipe = relationship("Recipe")

    __table_args__ = (
        UniqueConstraint("event_id", "recipe_id", name="uq_event_recipe_target"),
        CheckConstraint("target_batches > 0", name="ck_target_batches_positive"),
    )
```

#### EventAssemblyTarget

**Purpose:** Define explicit assembly targets for an event. Answers "For Christmas 2025, how many of each finished good do I need to assemble?"

```sql
CREATE TABLE event_assembly_target (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    finished_good_id INTEGER NOT NULL REFERENCES finished_good(id) ON DELETE RESTRICT,
    target_quantity INTEGER NOT NULL CHECK (target_quantity > 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, finished_good_id)
);

CREATE INDEX idx_event_assembly_target_event ON event_assembly_target(event_id);
CREATE INDEX idx_event_assembly_target_fg ON event_assembly_target(finished_good_id);
```

| Column             | Type     | Constraints                           | Description                    |
| ------------------ | -------- | ------------------------------------- | ------------------------------ |
| `id`               | Integer  | PK, Auto                              | Unique identifier              |
| `uuid`             | String   |                                       | UUID for distributed scenarios |
| `event_id`         | Integer  | FK → Event, NOT NULL, CASCADE         | Which event                    |
| `finished_good_id` | Integer  | FK → FinishedGood, NOT NULL, RESTRICT | Which finished good            |
| `target_quantity`  | Integer  | NOT NULL, > 0                         | How many units to assemble     |
| `notes`            | Text     |                                       | Planning notes                 |
| `created_at`       | DateTime | NOT NULL                              | When created                   |
| `updated_at`       | DateTime | NOT NULL                              | When last modified             |

**Constraints:**
- Unique on (event_id, finished_good_id) - one target per finished good per event
- Delete event → cascade delete targets
- Delete finished good → restrict (must remove target first)

**Model:**
```python
class EventAssemblyTarget(BaseModel):
    __tablename__ = "event_assembly_target"

    event_id = Column(Integer, ForeignKey("event.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_good_id = Column(Integer, ForeignKey("finished_good.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_quantity = Column(Integer, nullable=False)
    notes = Column(Text)

    # Relationships
    event = relationship("Event", back_populates="assembly_targets")
    finished_good = relationship("FinishedGood")

    __table_args__ = (
        UniqueConstraint("event_id", "finished_good_id", name="uq_event_fg_target"),
        CheckConstraint("target_quantity > 0", name="ck_target_quantity_positive"),
    )
```

---

## 2.3 Additional Features (Post-v0.6 Design)

The following features were implemented after the initial v0.6 design and are now part of the current schema.

### Feature 025: Production Loss Tracking

#### ProductionLoss Table

Records detailed information about items lost during production for audit trail and trend analysis.

```sql
CREATE TABLE production_losses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    production_run_id INTEGER REFERENCES production_runs(id) ON DELETE SET NULL,
    finished_unit_id INTEGER NOT NULL REFERENCES finished_units(id) ON DELETE RESTRICT,
    loss_category TEXT NOT NULL DEFAULT 'other',
    loss_quantity INTEGER NOT NULL CHECK (loss_quantity > 0),
    per_unit_cost NUMERIC(10,4) NOT NULL DEFAULT 0,
    total_loss_cost NUMERIC(10,4) NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

| Column              | Type       | Constraints                           | Description                           |
| ------------------- | ---------- | ------------------------------------- | ------------------------------------- |
| `production_run_id` | Integer    | FK → ProductionRun, SET NULL          | Nullable for audit trail preservation |
| `finished_unit_id`  | Integer    | FK → FinishedUnit, NOT NULL, RESTRICT | What was being produced               |
| `loss_category`     | String(20) | NOT NULL, DEFAULT 'other'             | LossCategory enum value               |
| `loss_quantity`     | Integer    | NOT NULL, > 0                         | Number of units lost                  |
| `per_unit_cost`     | Numeric    | NOT NULL                              | Cost snapshot at production time      |
| `total_loss_cost`   | Numeric    | NOT NULL                              | loss_quantity × per_unit_cost         |

**LossCategory Enum Values:** `burnt`, `broken`, `contaminated`, `dropped`, `wrong_ingredients`, `other`

#### ProductionRun Extensions

Added columns for loss tracking:

| Column              | Type       | Description                                 |
| ------------------- | ---------- | ------------------------------------------- |
| `production_status` | String(20) | `complete`, `partial_loss`, or `total_loss` |
| `loss_quantity`     | Integer    | Total units lost in this run                |

**ProductionStatus Enum Values:** `complete`, `partial_loss`, `total_loss`

---

### Feature 026: Packaging Bypass

Allows assembly of finished goods without consuming packaging materials (for custom packaging scenarios).

#### AssemblyRun Extensions

| Column                   | Type    | Description                               |
| ------------------------ | ------- | ----------------------------------------- |
| `packaging_bypassed`     | Boolean | True if packaging consumption was skipped |
| `packaging_bypass_notes` | Text    | Reason for bypass                         |

#### CompositionAssignment Table

Tracks what actually got assembled vs what was defined in Composition.

```sql
CREATE TABLE composition_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    assembly_run_id INTEGER NOT NULL REFERENCES assembly_runs(id) ON DELETE CASCADE,
    composition_id INTEGER NOT NULL REFERENCES compositions(id) ON DELETE RESTRICT,
    quantity_used INTEGER NOT NULL CHECK (quantity_used >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

### Feature 027: Product Catalog Management

Full purchase tracking with suppliers and price history.

#### Supplier Table

```sql
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    name TEXT NOT NULL,
    street_address TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state = UPPER(state) AND LENGTH(state) = 2),
    zip_code TEXT NOT NULL,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

| Column      | Type        | Constraints                  | Description                    |
| ----------- | ----------- | ---------------------------- | ------------------------------ |
| `name`      | String(200) | NOT NULL                     | Supplier name (e.g., "Costco") |
| `city`      | String(100) | NOT NULL                     | City name                      |
| `state`     | String(2)   | NOT NULL, 2-letter uppercase | State code (e.g., "MA")        |
| `zip_code`  | String(10)  | NOT NULL                     | ZIP code                       |
| `is_active` | Boolean     | NOT NULL, DEFAULT true       | Soft delete flag               |

#### Purchase Table

Immutable record of purchase transactions.

```sql
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    purchase_date DATE NOT NULL,
    unit_price NUMERIC(10,4) NOT NULL CHECK (unit_price >= 0),
    quantity_purchased INTEGER NOT NULL CHECK (quantity_purchased > 0),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    -- No updated_at: purchases are immutable
);
```

| Column               | Type    | Constraints                       | Description               |
| -------------------- | ------- | --------------------------------- | ------------------------- |
| `product_id`         | Integer | FK → Product, NOT NULL, RESTRICT  | What was purchased        |
| `supplier_id`        | Integer | FK → Supplier, NOT NULL, RESTRICT | Where it was purchased    |
| `purchase_date`      | Date    | NOT NULL                          | When purchased            |
| `unit_price`         | Numeric | NOT NULL, ≥ 0                     | Price per package unit    |
| `quantity_purchased` | Integer | NOT NULL, > 0                     | Number of packages bought |

#### Product Extensions

| Column                  | Type        | Description                          |
| ----------------------- | ----------- | ------------------------------------ |
| `preferred_supplier_id` | Integer     | FK → Supplier (SET NULL on delete)   |
| `is_hidden`             | Boolean     | Hide from UI dropdowns               |
| `gtin`                  | String(20)  | GS1 GTIN (unique, replaces upc_code) |
| `brand_owner`           | String(200) | Brand owner/manufacturer             |
| `gpc_brick_code`        | String(20)  | GS1 GPC category code                |
| `net_content_value`     | Float       | Net content from label               |
| `net_content_uom`       | String(20)  | Net content unit (g, kg, ml, oz)     |
| `country_of_sale`       | String(3)   | ISO 3166-1 alpha-3 country code      |
| `off_id`                | String(50)  | Open Food Facts product code         |

#### InventoryItem Extensions

| Column         | Type        | Description                            |
| -------------- | ----------- | -------------------------------------- |
| `purchase_id`  | Integer     | FK → Purchase (nullable for migration) |
| `lot_or_batch` | String(100) | Lot/batch number for tracking          |

---

### Feature 022: Unit Reference Table

Standardized measurement units for consistency.

#### Unit Table

```sql
CREATE TABLE units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    name TEXT NOT NULL UNIQUE,
    abbreviation TEXT NOT NULL UNIQUE,
    unit_type TEXT NOT NULL,
    base_unit_id INTEGER REFERENCES units(id),
    conversion_factor REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

| Column              | Type    | Description                       |
| ------------------- | ------- | --------------------------------- |
| `name`              | String  | Full name (e.g., "tablespoon")    |
| `abbreviation`      | String  | Short form (e.g., "tbsp")         |
| `unit_type`         | String  | Category (volume, weight, count)  |
| `base_unit_id`      | Integer | FK to base unit for conversions   |
| `conversion_factor` | Float   | Multiply by this to get base unit |

---

## 3) Updated ERD (Current Implementation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVENT PLANNING LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                              EVENT                                    │  │
│  │  • name, year, event_date, notes                                      │  │
│  └───────┬──────────────┬──────────────┬──────────────┬─────────────────┘  │
│          │              │              │              │                     │
│          ▼              ▼              ▼              ▼                     │
│  ┌───────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│  │EventRecipient │ │EventProduc- │ │EventAssemb- │ │ ProductionRun &     │ │
│  │Package        │ │tionTarget   │ │lyTarget     │ │ AssemblyRun         │ │
│  │               │ │             │ │             │ │ (via event_id FK)   │ │
│  │• recipient_id │ │• recipe_id  │ │• finished_  │ │                     │ │
│  │• package_id   │ │• target_    │ │  good_id    │ │                     │ │
│  │• quantity     │ │  batches    │ │• target_    │ │                     │ │
│  │• fulfillment_ │ │• notes      │ │  quantity   │ │                     │ │
│  │  status       │ │             │ │• notes      │ │                     │ │
│  │• status       │ │             │ │             │ │                     │ │
│  └───────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRODUCTION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐        │
│  │       ProductionRun         │    │        AssemblyRun          │        │
│  │                             │    │                             │        │
│  │ • recipe_id                 │    │ • finished_good_id          │        │
│  │ • finished_unit_id          │    │ • event_id (nullable)       │        │
│  │ • event_id (nullable)       │    │ • quantity_assembled        │        │
│  │ • num_batches               │    │ • total_component_cost      │        │
│  │ • expected_yield            │    │ • per_unit_cost             │        │
│  │ • actual_yield              │    │ • assembled_at              │        │
│  │ • total_ingredient_cost     │    │ • packaging_bypassed (F026) │        │
│  │ • per_unit_cost             │    │ • packaging_bypass_notes    │        │
│  │ • produced_at               │    │ • notes                     │        │
│  │ • production_status (F025)  │    │                             │        │
│  │ • loss_quantity (F025)      │    │                             │        │
│  │ • notes                     │    │                             │        │
│  └──────────────┬──────────────┘    └──────────────┬──────────────┘        │
│                 │                                   │                       │
│       ┌─────────┴─────────┐               ┌────────┴────────┐              │
│       ▼                   ▼               ▼                 ▼              │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌─────────────┐ │
│  │ProductionCon-  │ │ProductionLoss  │ │AssemblyFU-     │ │AssemblyPkg- │ │
│  │sumption        │ │(F025)          │ │Consumption     │ │Consumption  │ │
│  │                │ │                │ │                │ │             │ │
│  │• ingredient_   │ │• loss_category │ │• finished_unit │ │• inventory_ │ │
│  │  slug          │ │• loss_quantity │ │  _id           │ │  item_id    │ │
│  │• quantity      │ │• per_unit_cost │ │• quantity      │ │• quantity   │ │
│  │• unit          │ │• total_loss_   │ │• cost_at_time  │ │• cost       │ │
│  │• cost_at_time  │ │  cost          │ │                │ │             │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ └─────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     CATALOG & INVENTORY LAYER (F027)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐      ┌───────────┐ │
│  │ Ingredient │──1:N─│  Product   │──1:N─│InventoryIt │◀─N:1─│ Purchase  │ │
│  │            │      │            │      │  em        │      │           │ │
│  │• name      │      │• brand     │      │• quantity  │      │• unit_    │ │
│  │• slug      │      │• product_  │      │• unit_cost │      │  price    │ │
│  │• category  │      │  name      │      │• purchase_ │      │• quantity │ │
│  │• recipe_   │      │• package_* │      │  date      │      │• purchase │ │
│  │  unit      │      │• gtin      │      │• expiration│      │  _date    │ │
│  │            │      │• preferred_│      │• location  │      │           │ │
│  │            │      │  supplier_ │      │• lot_or_   │      │           │ │
│  │            │      │  id (F027) │      │  batch     │      │           │ │
│  │            │      │• is_hidden │      │            │      │           │ │
│  └────────────┘      └─────┬──────┘      └────────────┘      └─────┬─────┘ │
│                            │                                       │       │
│                            └───────────────────┬───────────────────┘       │
│                                                ▼                           │
│                                         ┌────────────┐                     │
│                                         │  Supplier  │                     │
│                                         │            │                     │
│                                         │• name      │                     │
│                                         │• city      │                     │
│                                         │• state     │                     │
│                                         │• zip_code  │                     │
│                                         │• is_active │                     │
│                                         └────────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEFINITION LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐      ┌────────────────┐      ┌────────────┐                │
│  │   Recipe   │──1:N─│RecipeIngredient│      │   Unit     │                │
│  │            │      │                │      │  (F022)    │                │
│  │• name      │      │• ingredient_id │      │            │                │
│  │• yields    │      │• quantity      │      │• name      │                │
│  │• yield_    │      │• unit          │      │• abbrev    │                │
│  │  unit      │      │                │      │• unit_type │                │
│  └─────┬──────┘      └────────────────┘      │• base_unit │                │
│        │                                      │• conv_     │                │
│        │                                      │  factor    │                │
│        ▼                                      └────────────┘                │
│  ┌────────────────┐                                                         │
│  │RecipeComponent │  (Nested recipes)                                       │
│  │• parent_id     │                                                         │
│  │• child_id      │                                                         │
│  │• quantity      │                                                         │
│  └────────────────┘                                                         │
│                                                                              │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐                    │
│  │FinishedUnit│──1:N─│FinishedGood│──1:N─│Composition │                    │
│  │            │      │            │      │            │                    │
│  │• display_  │      │• display_  │      │• package_id│                    │
│  │  name      │      │  name      │      │  OR        │                    │
│  │• inventory │      │• inventory │      │• assembly_ │                    │
│  │  _count    │      │  _count    │      │  _id       │                    │
│  └────────────┘      └────────────┘      │• finished_ │                    │
│                                          │  unit_id   │                    │
│                                          │• quantity  │                    │
│                                          └────────────┘                    │
│                                                                              │
│  ┌────────────┐      ┌────────────────────┐                                │
│  │  Package   │──1:N─│PackageFinishedGood │                                │
│  │            │      │                    │                                │
│  │• name      │      │• finished_good_id  │                                │
│  │• notes     │      │• quantity          │                                │
│  └────────────┘      └────────────────────┘                                │
│                                                                              │
│  ┌────────────┐                                                             │
│  │ Recipient  │                                                             │
│  │            │                                                             │
│  │• name      │                                                             │
│  │• notes     │                                                             │
│  └────────────┘                                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4) Service Changes

### 4.1 BatchProductionService

**Update `record_batch_production()`:**

```python
def record_batch_production(
    self,
    recipe_id: int,
    num_batches: int,
    actual_yield: int,
    notes: str = None,
    session: Session = None,
    event_id: int = None  # NEW PARAMETER
) -> ProductionRun:
    """
    Record batch production, optionally linked to an event.

    Args:
        event_id: Optional event this production is for. If provided,
                  production counts toward event progress.
    """
```

### 4.2 AssemblyService

**Update `record_assembly()`:**

```python
def record_assembly(
    self,
    finished_good_id: int,
    quantity: int,
    notes: str = None,
    session: Session = None,
    event_id: int = None  # NEW PARAMETER
) -> AssemblyRun:
    """
    Record assembly, optionally linked to an event.

    Args:
        event_id: Optional event this assembly is for. If provided,
                  assembly counts toward event progress.
    """
```

### 4.3 EventService (New Methods)

```python
class EventService:
    # Existing methods...

    # === TARGET MANAGEMENT ===

    def set_production_target(
        self,
        event_id: int,
        recipe_id: int,
        target_batches: int,
        notes: str = None
    ) -> EventProductionTarget:
        """Set or update production target for a recipe in an event."""

    def set_assembly_target(
        self,
        event_id: int,
        finished_good_id: int,
        target_quantity: int,
        notes: str = None
    ) -> EventAssemblyTarget:
        """Set or update assembly target for a finished good in an event."""

    def get_production_targets(self, event_id: int) -> List[EventProductionTarget]:
        """Get all production targets for an event."""

    def get_assembly_targets(self, event_id: int) -> List[EventAssemblyTarget]:
        """Get all assembly targets for an event."""

    def delete_production_target(self, event_id: int, recipe_id: int) -> bool:
        """Remove a production target."""

    def delete_assembly_target(self, event_id: int, finished_good_id: int) -> bool:
        """Remove an assembly target."""

    # === PROGRESS TRACKING ===

    def get_production_progress(self, event_id: int) -> List[dict]:
        """
        Get production progress for an event.

        Returns list of:
        {
            'recipe': Recipe,
            'target_batches': int,
            'produced_batches': int,  # Sum of ProductionRun.num_batches where event_id matches
            'produced_yield': int,    # Sum of actual_yield
            'progress_pct': float,    # produced_batches / target_batches * 100
            'is_complete': bool
        }
        """

    def get_assembly_progress(self, event_id: int) -> List[dict]:
        """
        Get assembly progress for an event.

        Returns list of:
        {
            'finished_good': FinishedGood,
            'target_quantity': int,
            'assembled_quantity': int,  # Sum of AssemblyRun.quantity where event_id matches
            'progress_pct': float,
            'is_complete': bool
        }
        """

    def get_event_overall_progress(self, event_id: int) -> dict:
        """
        Get overall event progress summary.

        Returns:
        {
            'production_complete': bool,  # All recipes at target
            'assembly_complete': bool,    # All finished goods at target
            'packages_ready': int,        # Count with fulfillment_status='ready'
            'packages_delivered': int,    # Count with fulfillment_status='delivered'
            'packages_total': int
        }
        """

    # === FULFILLMENT STATUS ===

    def update_fulfillment_status(
        self,
        event_recipient_package_id: int,
        status: FulfillmentStatus
    ) -> EventRecipientPackage:
        """Update package fulfillment status (pending/ready/delivered)."""

    def get_packages_by_status(
        self,
        event_id: int,
        status: FulfillmentStatus = None
    ) -> List[EventRecipientPackage]:
        """Get packages filtered by fulfillment status."""
```

---

## 5) UI Changes

### 5.1 Record Production Dialog

**Add event selector:**

```
┌─────────────────────────────────────────────┐
│ Record Production: Sugar Cookies            │
├─────────────────────────────────────────────┤
│ Event (optional): [Christmas 2025      ▼]   │  ◄── NEW
│                   [None - standalone    ]   │
│                   [Christmas 2025       ]   │
│                   [Easter 2026          ]   │
│                                             │
│ Batches: [2    ]  [Check Availability]      │
│                                             │
│ Availability Status:                        │
│  ✓ All-Purpose Flour: need 5 cups, have 10  │
│  ✓ Sugar: need 2 cups, have 8               │
│                                             │
│ Actual Yield: [96   ] cookies               │
│ Notes: [                                ]   │
│                                             │
│         [Cancel]  [Record Production]       │
└─────────────────────────────────────────────┘
```

### 5.2 Record Assembly Dialog

**Add event selector:**

```
┌─────────────────────────────────────────────┐
│ Record Assembly: Cookie Gift Box            │
├─────────────────────────────────────────────┤
│ Event (optional): [Christmas 2025      ▼]   │  ◄── NEW
│                                             │
│ Quantity: [5   ]  [Check Availability]      │
│                                             │
│ Component Availability:                     │
│  ✓ Sugar Cookies: need 60, have 96          │
│  ✓ Gift Boxes: need 5, have 10              │
│                                             │
│ Notes: [                                ]   │
│                                             │
│         [Cancel]  [Record Assembly]         │
└─────────────────────────────────────────────┘
```

### 5.3 Event Detail View - Production Targets Tab

**New tab in Event Detail Window:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Christmas 2025                                                   │
├──────────┬──────────┬──────────────┬───────────┬────────────────┤
│Assignments│ Targets │ Progress     │Shopping   │ Summary        │
├──────────┴──────────┴──────────────┴───────────┴────────────────┤
│                                                                  │
│ Production Targets                          [+ Add Target]       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Recipe               │ Target  │ Produced │ Progress        │ │
│ ├──────────────────────┼─────────┼──────────┼─────────────────┤ │
│ │ Chocolate Chip       │ 4       │ 2        │ ████░░░░ 50%    │ │
│ │ Sugar Cookies        │ 2       │ 2        │ ████████ 100% ✓ │ │
│ │ Snickerdoodles       │ 1       │ 0        │ ░░░░░░░░ 0%     │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Assembly Targets                            [+ Add Target]       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Finished Good        │ Target  │ Assembled│ Progress        │ │
│ ├──────────────────────┼─────────┼──────────┼─────────────────┤ │
│ │ Cookie Gift Box      │ 5       │ 3        │ █████░░░ 60%    │ │
│ │ Simple Cookie Bag    │ 10      │ 10       │ ████████ 100% ✓ │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 Package Assignments - Fulfillment Status

**Add status column and control:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Package Assignments                                              │
├──────────────────┬────────────────┬─────┬──────────┬────────────┤
│ Recipient        │ Package        │ Qty │ Status   │ Actions    │
├──────────────────┼────────────────┼─────┼──────────┼────────────┤
│ Alice Johnson    │ Deluxe Box     │ 1   │ Ready ▼  │ [Edit][Del]│
│ Bob Smith        │ Simple Bag     │ 2   │ Pending▼ │ [Edit][Del]│
│ Carol Davis      │ Deluxe Box     │ 1   │ Delivered│ [Edit][Del]│
└──────────────────┴────────────────┴─────┴──────────┴────────────┘
```

---

## 6) Migration Strategy

### 6.1 Schema Migration

Since the application uses SQLite with export/import for migrations:

1. Export all data using existing import/export service
2. Update models with new columns/tables
3. Delete database file
4. Recreate database with new schema
5. Import data (new columns get defaults)

### 6.2 Data Defaults

- `ProductionRun.event_id` → NULL (standalone production)
- `AssemblyRun.event_id` → NULL (standalone assembly)
- `EventRecipientPackage.fulfillment_status` → 'pending'
- `EventProductionTarget` → Empty (user sets targets)
- `EventAssemblyTarget` → Empty (user sets targets)

### 6.3 Import/Export Updates

Add new entities to import/export:

```json
{
  "events": [...],
  "event_production_targets": [
    {
      "event_name": "Christmas 2025",
      "recipe_name": "Chocolate Chip Cookies",
      "target_batches": 4,
      "notes": "Need extras for neighbors"
    }
  ],
  "event_assembly_targets": [
    {
      "event_name": "Christmas 2025",
      "finished_good_name": "Cookie Gift Box",
      "target_quantity": 5,
      "notes": null
    }
  ],
  "production_runs": [
    {
      "recipe_name": "Chocolate Chip Cookies",
      "event_name": "Christmas 2025",  // NEW - nullable
      "num_batches": 2,
      "actual_yield": 96,
      "produced_at": "2025-12-15T10:00:00",
      "notes": "First batch for holiday"
    }
  ],
  "assembly_runs": [
    {
      "finished_good_name": "Cookie Gift Box",
      "event_name": "Christmas 2025",  // NEW - nullable
      "quantity": 3,
      "assembled_at": "2025-12-18T14:00:00",
      "notes": null
    }
  ],
  "event_recipient_packages": [
    {
      "event_name": "Christmas 2025",
      "recipient_name": "Alice Johnson",
      "package_name": "Deluxe Cookie Box",
      "quantity": 1,
      "fulfillment_status": "ready",  // NEW
      "notes": null
    }
  ]
}
```

---

## 7) Testing Requirements

### 7.1 Model Tests

- EventProductionTarget CRUD
- EventAssemblyTarget CRUD
- Unique constraint enforcement (one target per recipe/FG per event)
- Cascade delete (delete event → delete targets)
- Restrict delete (can't delete recipe with targets)
- FulfillmentStatus enum validation

### 7.2 Service Tests

- `set_production_target()` - create and update
- `set_assembly_target()` - create and update
- `get_production_progress()` - accurate calculation
- `get_assembly_progress()` - accurate calculation
- `record_batch_production(event_id=X)` - links to event
- `record_assembly(event_id=X)` - links to event
- `update_fulfillment_status()` - state transitions
- Progress calculation with partial completion
- Progress calculation with over-production

### 7.3 Import/Export Tests

- Export includes new entities and fields
- Import handles event_name references correctly
- Import handles null event_id (standalone production)
- Import handles fulfillment_status

### 7.4 UI Tests (Manual)

- Event selector appears in Record Production dialog
- Event selector appears in Record Assembly dialog
- Targets tab displays correctly in Event Detail
- Add/edit/delete targets works
- Progress bars update after recording production
- Fulfillment status dropdown works
- Status changes persist

---

## 8) Open Questions

### Resolved

1. **Derived vs explicit targets?**
   - Decision: Use explicit targets (EventProductionTarget, EventAssemblyTarget)
   - Rationale: Allows user to set buffer quantities, override calculated needs

2. **Nullable event_id?**
   - Decision: Yes, nullable
   - Rationale: Supports standalone production not tied to any event

### Previously For Discussion (Now Resolved)

1. **Auto-calculate initial targets from packages?**
   - Decision: Option B implemented - System suggests targets based on package assignments
   - UI allows manual adjustment of suggested values

2. **Progress percentage display?**
   - Decision: Option B implemented - Progress shows over-production indicator when exceeds target
   - Visual progress bars cap at 100% but show actual percentage in text

---

## 9) Implementation Checklist

### Models (v0.6 Core - Feature 015/016)
- [x] Add `event_id` column to ProductionRun model
- [x] Add `event_id` column to AssemblyRun model
- [x] Create EventProductionTarget model
- [x] Create EventAssemblyTarget model
- [x] Add `fulfillment_status` column to EventRecipientPackage
- [x] Create FulfillmentStatus enum
- [x] Add relationships to Event model
- [x] Update `__init__.py` exports

### Models (Additional Features)
- [x] Feature 025: ProductionLoss model
- [x] Feature 025: ProductionStatus, LossCategory enums
- [x] Feature 025: ProductionRun.production_status, loss_quantity
- [x] Feature 026: AssemblyRun.packaging_bypassed, packaging_bypass_notes
- [x] Feature 026: CompositionAssignment model
- [x] Feature 027: Supplier model
- [x] Feature 027: Purchase model
- [x] Feature 027: Product extensions (preferred_supplier_id, is_hidden, GTIN fields)
- [x] Feature 027: InventoryItem.purchase_id
- [x] Feature 022: Unit model

### Services
- [x] Update BatchProductionService.record_batch_production() with event_id param
- [x] Update AssemblyService.record_assembly() with event_id param
- [x] Add EventService.set_production_target()
- [x] Add EventService.set_assembly_target()
- [x] Add EventService.get_production_targets()
- [x] Add EventService.get_assembly_targets()
- [x] Add EventService.get_production_progress()
- [x] Add EventService.get_assembly_progress()
- [x] Add EventService.get_event_overall_progress()
- [x] Add EventService.update_fulfillment_status()
- [x] Add EventService.get_packages_by_status()

### Import/Export
- [x] Add EventProductionTarget to export
- [x] Add EventAssemblyTarget to export
- [x] Add event_name to ProductionRun export
- [x] Add event_name to AssemblyRun export
- [x] Add fulfillment_status to EventRecipientPackage export
- [x] Handle all new fields in import

### UI
- [x] Add event selector to RecordProductionDialog
- [x] Add event selector to RecordAssemblyDialog
- [x] Add Targets tab to EventDetailWindow
- [x] Add progress display to Targets tab
- [x] Add fulfillment status to package assignments view
- [x] Add target CRUD dialogs

### Tests
- [x] Model unit tests for new tables
- [x] Service unit tests for new methods
- [x] Service integration tests for progress calculation
- [x] Import/export tests for new entities
- [x] Manual UI testing checklist

### Documentation
- [x] Update CLAUDE.md with event-centric model
- [x] Update feature_roadmap.md
- [x] Update current_priorities.md
- [x] Update workflow-refactoring-spec.md

---

## Document History

- **2025-12-28:** Major update to reflect current implementation status
  - Changed status from PLANNING to IMPLEMENTED
  - Added Implementation Status summary table
  - Added section 2.3 documenting Features 022, 025, 026, 027
  - Updated ERD to show all current models including Supplier, Purchase, ProductionLoss
  - Marked all implementation checklist items as complete
- **2025-12-10:** Initial creation for Feature 015 (Event-Centric Production Model)
