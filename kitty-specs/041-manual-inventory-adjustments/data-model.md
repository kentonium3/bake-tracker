# Data Model (Discovery Draft)

## Entities

### Entity: InventoryDepletion (NEW)

- **Description**: Immutable audit record tracking every inventory reduction. Links to the specific InventoryItem being adjusted with reason, notes, cost, and user identifier.
- **Attributes**:
  - `id` (Integer, PK) - Auto-increment primary key
  - `uuid` (String(36), unique) - UUID for distributed scenarios
  - `inventory_item_id` (Integer, FK) - Reference to InventoryItem being depleted
  - `quantity_depleted` (Numeric(10,3)) - Amount reduced (stored as positive number)
  - `depletion_reason` (String(50)) - Enum value from DepletionReason
  - `depletion_date` (DateTime) - When depletion occurred
  - `notes` (Text, nullable) - User explanation (required for OTHER reason)
  - `cost` (Numeric(10,4)) - Calculated cost impact (quantity x unit_cost)
  - `created_by` (String(100)) - User identifier ("desktop-user" for now)
  - `created_at` (DateTime) - Record creation timestamp
- **Identifiers**: id (PK), uuid (alternate)
- **Lifecycle Notes**: Immutable after creation - no updates or deletes allowed for audit integrity

### Entity: DepletionReason (NEW ENUM)

- **Description**: Enumeration of valid reasons for inventory depletion
- **Values**:
  - `PRODUCTION` - Recipe execution (system-generated)
  - `ASSEMBLY` - Bundle assembly (system-generated, future)
  - `SPOILAGE` - Ingredient went bad (manual)
  - `GIFT` - Gave to friend/family (manual)
  - `CORRECTION` - Physical count adjustment (manual)
  - `AD_HOC_USAGE` - Personal/testing usage (manual)
  - `OTHER` - User-specified reason (manual, requires notes)
- **Location**: `src/models/enums.py`

### Entity: InventoryItem (EXISTING - No Changes)

- **Description**: Tracks physical inventory on hand per purchase
- **Relevant Attributes** (for this feature):
  - `quantity` (Float) - Current quantity on hand (modified by depletions)
  - `unit_cost` (Float) - Cost per unit for FIFO costing
- **Notes**: quantity field updated when manual_adjustment() called

## Relationships

| Source | Relation | Target | Cardinality | Notes |
|--------|----------|--------|-------------|-------|
| InventoryDepletion | belongs_to | InventoryItem | N:1 | Each depletion affects one inventory item |
| InventoryItem | has_many | InventoryDepletion | 1:N | Item can have multiple depletion records over time |

## Validation & Governance

- **Data quality requirements**:
  - `quantity_depleted` must be > 0
  - `quantity_depleted` cannot exceed InventoryItem.quantity (would result in negative inventory)
  - `notes` required when `depletion_reason` = OTHER
  - `cost` calculated as quantity_depleted * InventoryItem.unit_cost
- **Compliance considerations**:
  - InventoryDepletion records are immutable (audit trail)
  - All manual adjustments tracked with user identifier
- **Source of truth**:
  - InventoryItem.quantity is the authoritative quantity
  - InventoryDepletion provides the audit history

## Schema Notes

### New Table: inventory_depletions

```sql
CREATE TABLE inventory_depletions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    inventory_item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    quantity_depleted NUMERIC(10,3) NOT NULL CHECK (quantity_depleted > 0),
    depletion_reason VARCHAR(50) NOT NULL,
    depletion_date DATETIME NOT NULL,
    notes TEXT,
    cost NUMERIC(10,4) NOT NULL,
    created_by VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id)
);

CREATE INDEX idx_depletion_inventory_item ON inventory_depletions(inventory_item_id);
CREATE INDEX idx_depletion_reason ON inventory_depletions(depletion_reason);
CREATE INDEX idx_depletion_date ON inventory_depletions(depletion_date);
```

### Migration Strategy

Per Constitution Principle VI (Schema Change Strategy), schema changes use export/reset/import cycle:
1. Export all data to JSON
2. Delete database, update models, recreate empty database
3. Import transformed data

No migration scripts required for desktop phase.
