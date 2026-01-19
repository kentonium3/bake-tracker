# Architecture Document

> **Document Status:** Living architecture overview
> **Last Updated:** 2026-01-19
> **Schema Version:** v0.7+ (post-F059)

## Navigation

| Document | Purpose |
|----------|---------|
| [SCHEMA.md](SCHEMA.md) | Complete entity definitions and relationships |
| [func-spec/](../func-spec/) | Feature specification documents (F0xx) |
| [Constitution](../../.kittify/memory/constitution.md) | Core architectural principles and project vision |
| [src/services/](../../src/services/) | Service layer implementation |

---

## 1. System Overview

Bake Tracker is a desktop application for managing event-based food production: inventory, recipes, finished goods, and gift package planning. Built with Python and CustomTkinter using SQLite for persistence.

```mermaid
flowchart TB
    subgraph Presentation["Presentation Layer (CustomTkinter)"]
        UI[UI Components]
    end

    subgraph Business["Business Logic Layer (Python Services)"]
        Services[Service Modules]
    end

    subgraph Data["Data Access Layer (SQLAlchemy ORM)"]
        Models[Model Classes]
    end

    subgraph Storage["Storage Layer"]
        SQLite[(SQLite Database)]
    end

    UI --> Services
    Services --> Models
    Models --> SQLite
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **UI** | CustomTkinter | Modern cross-platform desktop widgets |
| **Business Logic** | Python 3.10+ | Service layer with type hints |
| **ORM** | SQLAlchemy 2.x | Database abstraction with relationships |
| **Database** | SQLite (WAL mode) | Portable single-file storage |
| **Testing** | pytest | Unit and integration testing |

---

## 2. Key Design Principles

### 2.1 Definitions vs Instantiations

The foundational pattern separating **what can exist** from **what actually happened**.

```mermaid
flowchart LR
    subgraph Definitions["Definitions (Catalog/Templates)"]
        direction TB
        D1[Recipe]
        D2[Product]
        D3[FinishedUnit]
        D4[MaterialProduct]
    end

    subgraph Instantiations["Instantiations (Transactions/Events)"]
        direction TB
        I1[ProductionRun]
        I2[Purchase]
        I3[InventoryItem]
        I4[MaterialInventoryItem]
    end

    D1 -->|"produced via"| I1
    D2 -->|"purchased as"| I2
    I2 -->|"creates lot"| I3
    D4 -->|"purchased as"| I4
```

| Aspect | Definition Objects | Instantiation Objects |
|--------|-------------------|----------------------|
| **Describes** | WHAT can exist | WHEN/WHERE/HOW it happened |
| **Temporal** | Timeless, persist indefinitely | Specific date/time/circumstances |
| **Costs** | NO stored costs | Snapshot costs at transaction time |
| **Examples** | Recipe, Product, MaterialProduct | ProductionRun, Purchase, InventoryItem |
| **Persistence** | Exists even with zero instances | Created when event occurs |

**Core Principle:** *"Costs on Instances, Not Definitions"*

A recipe doesn't have a cost - making a batch has a cost. A product doesn't have a price - a purchase has a price.

### 2.2 FIFO Inventory Consumption

First In, First Out consumption matches physical reality and enables accurate cost tracking.

```mermaid
flowchart LR
    subgraph Inventory["Inventory Lots (by purchase date)"]
        L1["Lot A: Jan 3<br/>$4.50/unit<br/>10 remaining"]
        L2["Lot B: Jan 8<br/>$5.00/unit<br/>7 remaining"]
        L3["Lot C: Jan 15<br/>$5.25/unit<br/>15 remaining"]
    end

    Consume["Consume 12 units"] --> L1
    L1 -->|"Use 10"| L2
    L2 -->|"Use 2"| Result["Cost: (10 x $4.50) + (2 x $5.00) = $55.00"]
```

### 2.3 Layered Architecture

Strict dependency flow: **UI -> Services -> Models -> Database**

- UI layer must NOT contain business logic
- Services must NOT import UI components
- Models define schema and relationships only
- Cross-layer dependencies flow downward only

---

## 3. Operational Workflow: Catalog -> Plan -> Purchase -> Make

The application supports a natural workflow mirroring physical baking operations.

```mermaid
flowchart TB
    subgraph Catalog["1. CATALOG (Define What Exists)"]
        direction TB
        C1[Ingredients/Products]
        C2[Materials/MaterialProducts]
        C3[Recipes]
        C4[FinishedUnits]
        C5[FinishedGoods/Bundles/Packages]
    end

    subgraph Plan["2. PLAN (Event Planning)"]
        direction TB
        P1[Create Event]
        P2[Assign Recipients to Packages]
        P3[Calculate Recipe Needs]
        P4[Generate Shopping List]
    end

    subgraph Purchase["3. PURCHASE (Acquire Inventory)"]
        direction TB
        B1[Record Purchases]
        B2[Create Inventory Lots]
        B3[Track Costs per Lot]
    end

    subgraph Make["4. MAKE (Production)"]
        direction TB
        M1[ProductionRuns - Make Batches]
        M2[AssemblyRuns - Assemble Goods]
        M3[FIFO Consumption]
        M4[Cost Snapshots]
    end

    Catalog --> Plan
    Plan --> Purchase
    Purchase --> Make
    Make -->|"Replenish"| Purchase
```

### Stage Descriptions

| Stage | Purpose | Key Entities |
|-------|---------|--------------|
| **Catalog** | Define reusable templates | Ingredient, Product, Recipe, FinishedUnit, Material, MaterialProduct |
| **Plan** | Event-based production planning | Event, EventRecipientPackage, EventProductionTarget |
| **Purchase** | Acquire and track inventory | Purchase, InventoryItem, MaterialPurchase, MaterialInventoryItem |
| **Make** | Execute production | ProductionRun, AssemblyRun, consumption records |

---

## 4. Domain Model Overview

### 4.1 Food Ingredients Domain

```mermaid
erDiagram
    IngredientCategory ||--o{ IngredientSubcategory : contains
    IngredientSubcategory ||--o{ Ingredient : contains
    Ingredient ||--o{ Product : "brand-specific versions"
    Supplier ||--o{ Product : "preferred supplier"
    Product ||--o{ Purchase : "purchased as"
    Purchase ||--|| InventoryItem : "creates lot"
    Ingredient ||--o{ RecipeIngredient : "used in"
    Recipe ||--o{ RecipeIngredient : contains
    Recipe ||--|| FinishedUnit : produces
    FinishedUnit ||--o{ ProductionRun : "made via"
```

### 4.2 Materials Domain (Non-Food)

```mermaid
erDiagram
    MaterialCategory ||--o{ MaterialSubcategory : contains
    MaterialSubcategory ||--o{ Material : contains
    Material ||--o{ MaterialProduct : "purchasable versions"
    MaterialProduct ||--o{ MaterialPurchase : "purchased as"
    MaterialPurchase ||--|| MaterialInventoryItem : "creates lot"
    Material ||--o{ MaterialUnit : "assembly components"
    FinishedGood ||--o{ MaterialUnit : "requires"
```

### 4.3 Assembly & Packaging Domain

```mermaid
erDiagram
    FinishedUnit ||--o{ Composition : "component of"
    FinishedGood ||--o{ Composition : contains
    FinishedGood ||--o{ BundleItem : "in bundles"
    Bundle ||--o{ BundleItem : contains
    Bundle ||--o{ PackageItem : "in packages"
    Package ||--o{ PackageItem : contains
    Package ||--o{ EventRecipientPackage : "assigned to"
    Recipient ||--o{ EventRecipientPackage : receives
    Event ||--o{ EventRecipientPackage : plans
```

---

## 5. Import/Export System

The import/export system serves multiple critical purposes beyond simple backup/restore.

### 5.1 Purposes

```mermaid
flowchart TB
    subgraph Purposes["Import/Export Purposes"]
        direction TB
        P1["Backup & Restore<br/>(disaster recovery)"]
        P2["Initial Population<br/>(catalog seeding)"]
        P3["Data Augmentation<br/>(enrich existing records)"]
        P4["AI-Assisted Input<br/>(batch JSON 'API')"]
        P5["Schema Migration<br/>(export -> reset -> import)"]
    end

    Export[JSON Export] --> P1
    Export --> P5
    Import[JSON Import] --> P1
    Import --> P2
    Import --> P3
    Import --> P4
```

| Purpose | Description | Mode |
|---------|-------------|------|
| **Backup/Restore** | Complete database backup to JSON | Full unified export/import |
| **Initial Population** | Seed catalog with ingredients, products, recipes | ADD_ONLY catalog import |
| **Data Augmentation** | Enrich existing records with additional data | AUGMENT catalog import |
| **AI-Assisted Input** | Crude JSON-based batch "API" for AI data entry | Structured JSON with validation |
| **Schema Migration** | Handle schema changes without migration scripts | Export -> Reset -> Import |

### 5.2 Import Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **ADD_ONLY** | Create new records, skip existing | Initial catalog seeding |
| **AUGMENT** | Update NULL fields on existing records | Enrich with prices, GTINs, etc. |
| **UNIFIED** | Complete database replacement | Restore from backup |

### 5.3 AI-Assisted Data Entry Pattern

The JSON import serves as a primitive batch API enabling AI-assisted data entry:

1. User describes purchases/inventory to AI assistant
2. AI generates structured JSON matching import schema
3. User imports JSON via CLI or UI
4. Validation catches errors before database modification

This pattern is foundational for future voice/chat AI interfaces.

---

## 6. Feature Maturity Assessment

### 6.1 Maturity Levels

| Level | Description |
|-------|-------------|
| **Mature** | Feature complete, tested, stable API |
| **Functional** | Working but may need polish or edge case handling |
| **Partial** | Core functionality exists, significant gaps remain |
| **Planned** | Designed but not implemented |

### 6.2 Current State

```mermaid
quadrantChart
    title Feature Maturity Matrix
    x-axis Low Complexity --> High Complexity
    y-axis Partial --> Mature
    quadrant-1 Mature & Complex
    quadrant-2 Mature & Simple
    quadrant-3 Partial & Simple
    quadrant-4 Partial & Complex

    "Ingredient Hierarchy": [0.3, 0.9]
    "Products Catalog": [0.4, 0.85]
    "Materials Catalog": [0.4, 0.85]
    "Recipes": [0.5, 0.8]
    "Finished Units": [0.4, 0.75]
    "Material Units": [0.35, 0.7]
    "Import/Export": [0.7, 0.75]
    "FIFO Inventory": [0.6, 0.8]
    "Finished Goods": [0.5, 0.4]
    "Event Planning": [0.6, 0.35]
    "Production Runs": [0.55, 0.45]
    "Assembly Runs": [0.5, 0.3]
    "Reporting": [0.4, 0.2]
    "Observation": [0.3, 0.15]
```

### 6.3 Detailed Assessment

| Domain | Feature | Maturity | Notes |
|--------|---------|----------|-------|
| **Taxonomy** | Ingredient Categories/Subcategories | Mature | 3-level hierarchy, admin UI |
| **Taxonomy** | Material Categories/Subcategories | Mature | Parallel to ingredients |
| **Catalog** | Products (food ingredients) | Mature | Full CRUD, FIFO tracking |
| **Catalog** | MaterialProducts (non-food) | Mature | F047-F059 complete |
| **Catalog** | Recipes | Mature | Nested recipes, snapshots |
| **Catalog** | Finished Units (yield types) | Mature | Per-recipe yield tracking |
| **Catalog** | Material Units | Functional | Assembly material requirements |
| **Inventory** | Food FIFO | Mature | Purchase-linked lots |
| **Inventory** | Materials FIFO | Mature | F058 foundation |
| **Import/Export** | Unified export/import | Mature | v4.1 format |
| **Import/Export** | Catalog import | Mature | ADD_ONLY/AUGMENT modes |
| **Assembly** | Finished Goods | Partial | Definition exists, cost tracking incomplete |
| **Assembly** | Bundles/Packages | Partial | Structure exists, workflow incomplete |
| **Planning** | Events | Partial | Basic CRUD, targets incomplete |
| **Planning** | Shopping Lists | Functional | Needs UI polish |
| **Production** | ProductionRuns | Functional | Cost snapshots work, loss tracking partial |
| **Production** | AssemblyRuns | Partial | Missing cost snapshots (F046+ deferred) |
| **Analytics** | Reporting | Planned | No dedicated reporting |
| **Analytics** | Observation/Dashboards | Planned | Basic event dashboard only |

---

## 7. Service Layer Architecture

### 7.1 Service Organization

```mermaid
flowchart TB
    subgraph Catalog["Catalog Services"]
        direction TB
        IS[ingredient_service<br/>ingredient_crud_service<br/>ingredient_hierarchy_service]
        PS[product_service<br/>product_catalog_service]
        MS[material_catalog_service<br/>material_hierarchy_service]
        RS[recipe_service<br/>recipe_snapshot_service]
        FS[finished_unit_service<br/>finished_good_service]
        SS[supplier_service]
    end

    subgraph Inventory["Inventory Services"]
        direction TB
        IIS[inventory_item_service]
        MIS[material_inventory_service]
        PUS[purchase_service<br/>material_purchase_service]
    end

    subgraph Production["Production Services"]
        direction TB
        BPS[batch_production_service]
        AS[assembly_service]
        PRS[production_service]
        MCS[material_consumption_service]
    end

    subgraph Planning["Planning Services"]
        direction TB
        ES[event_service]
        PKS[package_service<br/>packaging_service]
        RES[recipient_service]
    end

    subgraph Import["Import/Export Services"]
        direction TB
        IES[import_export_service]
        CIS[catalog_import_service]
        EIS[enhanced_import_service]
        CES[coordinated_export_service]
        DES[denormalized_export_service]
    end

    subgraph Infrastructure["Infrastructure Services"]
        direction TB
        DB[database]
        UC[unit_converter<br/>material_unit_converter]
        FKR[fk_resolver_service]
        SVS[schema_validation_service]
    end
```

### 7.2 Key Service Responsibilities

| Service Group | Responsibilities |
|---------------|-----------------|
| **Catalog Services** | CRUD for definition entities, hierarchy management, validation |
| **Inventory Services** | FIFO lot management, purchase recording, availability checks |
| **Production Services** | Batch production, assembly, consumption tracking, cost snapshots |
| **Planning Services** | Event CRUD, recipient/package assignments, target calculations |
| **Import/Export Services** | JSON serialization, validation, catalog vs unified modes |
| **Infrastructure Services** | Database sessions, unit conversion, FK resolution |

### 7.3 Service Interaction Pattern

```mermaid
sequenceDiagram
    participant UI as UI Layer
    participant SVC as Service Layer
    participant INV as Inventory Service
    participant FIFO as FIFO Algorithm
    participant DB as Database

    UI->>SVC: recordProduction(recipe_id, batches)
    SVC->>DB: Get recipe ingredients
    loop For each ingredient
        SVC->>INV: consume_fifo(ingredient_id, qty)
        INV->>FIFO: Calculate consumption
        FIFO->>DB: Update lot quantities
        FIFO-->>INV: Cost breakdown
        INV-->>SVC: Consumption result
    end
    SVC->>DB: Create ProductionRun with cost snapshot
    SVC-->>UI: Production result
```

---

## 8. Technology Decisions

### 8.1 Why These Technologies?

| Choice | Rationale |
|--------|-----------|
| **CustomTkinter** | Modern appearance, cross-platform, no web dependencies |
| **SQLite** | No server setup, portable single file, excellent Python support |
| **SQLAlchemy** | ORM simplifies operations, type safety, relationship management |
| **No Migrations** | Export/reset/import simpler for single-user desktop (Constitution VI) |

### 8.2 Session Management Pattern

**Critical:** Nested `session_scope()` calls cause object detachment.

```python
# CORRECT: Pass session through call chain
def outer_function(session=None):
    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)

def _impl(session):
    # All operations use same session
    obj = session.query(Model).first()
    inner_function(session=session)  # Pass session!
    obj.field = value  # Changes persist
```

---

## 9. Recommendations for Documentation Structure

### 9.1 This Document: Architecture Overview

Keep this document as the **architectural overview** covering:
- Technology stack
- Key design principles (definition/instantiation, FIFO)
- Domain model overview
- Feature maturity assessment
- Service organization

### 9.2 Recommended Child Documents

| Document | Purpose |
|----------|---------|
| `design/workflows.md` | Detailed workflow documentation (catalog->plan->purchase->make) |
| `design/import-export.md` | Complete import/export specification and formats |
| `design/services.md` | Detailed service responsibilities and APIs |
| `design/data-model.md` | Complete entity relationships and field documentation |

### 9.3 Items to Move to Child Documents

- Detailed import/export format specifications -> `import-export.md`
- Step-by-step workflow procedures -> `workflows.md`
- Service-by-service API documentation -> `services.md`
- Schema evolution history -> `SCHEMA.md` or `data-model.md`

---

## 10. Pattern Checklist for New Features

When designing new features, verify compliance with core patterns:

### Definition vs Instantiation
- [ ] Definitions have NO stored costs
- [ ] Definitions persist when instances = 0
- [ ] Instantiations capture temporal context
- [ ] Instantiations snapshot costs at transaction time

### FIFO Pattern
- [ ] Inventory consumption uses FIFO (oldest first)
- [ ] Costs link to Purchase records
- [ ] Cost snapshots captured at consumption time

### Layered Architecture
- [ ] UI contains no business logic
- [ ] Services contain no UI imports
- [ ] Models define schema only
- [ ] Session parameter pattern for composable transactions

---

**Document Status:** Living architecture overview
**Last Updated:** 2026-01-19
**Reviewed by:** Kent Gale, Claude Opus 4.5
