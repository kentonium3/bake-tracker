# Research: Deferred Packaging Decisions

**Feature**: 026-deferred-packaging-decisions
**Date**: 2025-12-21
**Status**: Complete

## Executive Summary

This feature enables users to plan events with generic packaging requirements (e.g., "Cellophane Bags 6x10") instead of committing to specific designs upfront. The implementation leverages existing schema patterns with minimal additions.

## Key Decisions

### D1: Generic Product Grouping Strategy

**Decision**: Use existing `product_name` field on Product as the grouping key.

**Rationale**:
- Products with the same `product_name` (e.g., "Cellophane Bags 6x10") represent variants of the same generic product
- Different designs (Snowflakes, Holly, etc.) are distinguished by `brand` field
- No new GenericProduct entity required - grouping is implicit via queries
- Leverages F023 (Product Name Differentiation) which added this field

**Alternatives Considered**:
- New GenericProduct table: Adds complexity, requires FK migration
- Product self-reference: Overly complex for this use case

### D2: Packaging Assignment Tracking

**Decision**: Extend Composition table with `is_generic` flag and create `CompositionAssignment` junction table.

**Rationale**:
- Composition already links packaging products to assemblies/packages via `packaging_product_id`
- Adding `is_generic` boolean distinguishes deferred vs immediate selection
- New junction table tracks which specific inventory items fulfill generic requirements
- Maintains referential integrity and supports partial assignments

**Alternatives Considered**:
- New PackagingRequirement table: Creates parallel structure, harder to maintain
- EventRecipientPackage extension: Wrong entity scope (event-level vs assembly-level)

### D3: Cost Estimation Strategy

**Decision**: Calculate average price across all available specific products grouped by `product_name`.

**Rationale**:
- User validated that average price is appropriate given substitution variability
- Matches real-world shopping behavior (buy whatever design is available)
- Simple aggregation query over Product + Purchase tables
- Clear "Estimated" vs "Actual" labeling prevents confusion

## Existing Schema Analysis

### Composition Model (`src/models/composition.py`)

Current capabilities:
- Polymorphic component references (FinishedUnit, FinishedGood, or packaging Product)
- Links to parent via `assembly_id` (FinishedGood) or `package_id` (Package)
- `packaging_product_id` FK to specific Product for packaging materials
- XOR constraint ensures exactly one component type per row

Required changes:
- Add `is_generic` boolean column (default False for backward compatibility)
- When `is_generic=True`, `packaging_product_id` references a "template" product whose `product_name` defines the generic requirement

### Product Model (`src/models/product.py`)

Current capabilities:
- `product_name` field distinguishes variants (e.g., "70% Cacao", "Extra Virgin")
- `brand` field for manufacturer/design
- `ingredient_id` links to Ingredient (which has `is_packaging` flag)
- `get_total_inventory_quantity()` method exists

For generic grouping:
- Query products WHERE `ingredient.is_packaging=True` AND `product_name=[X]`
- Aggregate inventory quantities across all matching products
- Calculate average cost from Purchase history

### InventoryItem Model (`src/models/inventory_item.py`)

Current capabilities:
- FIFO consumption support
- Links to Product via `product_id`
- Quantity tracking with purchase date

No changes required - assignments will reference InventoryItem.id directly.

## New Schema Elements

### CompositionAssignment Table

Purpose: Track which specific inventory items fulfill a generic packaging requirement.

```
composition_assignments
├── id (PK)
├── composition_id (FK → compositions.id)  -- The generic requirement
├── inventory_item_id (FK → inventory_items.id)  -- Specific material assigned
├── quantity_assigned (Float)  -- How many from this inventory item
├── assigned_at (DateTime)  -- When assignment was made
├── created_at (DateTime)
└── updated_at (DateTime)
```

Constraints:
- `composition_id` must reference a Composition where `is_generic=True`
- Sum of `quantity_assigned` across all assignments for a composition must equal `component_quantity`
- Cannot assign more than available in inventory item

## Service Layer Design

### New Service: `packaging_service.py`

Functions:
1. `get_generic_inventory_summary(product_name: str) -> dict`
   - Returns: `{total: int, breakdown: [{brand: str, product_id: int, available: int}]}`

2. `get_estimated_cost(product_name: str, quantity: int) -> float`
   - Calculates average price across all products with matching `product_name`

3. `create_generic_requirement(composition_id: int, product_name: str, quantity: int)`
   - Sets `is_generic=True` on composition

4. `assign_materials(composition_id: int, assignments: list[dict]) -> bool`
   - Creates CompositionAssignment records
   - Validates total matches requirement

5. `get_pending_packaging_requirements(event_id: int = None) -> list`
   - Returns compositions where `is_generic=True` and no assignments exist

### Existing Service Updates

- `assembly_service.py`: Add validation for unassigned packaging at assembly completion
- `shopping_list_service.py`: Group packaging by `product_name` for generic requirements

## UI Components

### Planning Screen Changes

- Add radio button: "Specific material" / "Generic product"
- When generic selected:
  - Dropdown populated with distinct `product_name` values from packaging products
  - Inventory summary widget showing total and breakdown
  - Estimated cost calculation

### Dashboard Changes

- Add pending indicator icon for productions with unassigned packaging
- Click navigates to assignment screen

### Assembly Definition Screen

- New "Assign Materials" section for generic requirements
- Checkbox list of available specific products
- Quantity input for each selected product
- Running total validation

## Migration Strategy

Per Constitution VI (Schema Change Strategy for Desktop Phase):
1. Export all data to JSON
2. Add `is_generic` column to compositions table
3. Create `composition_assignments` table
4. Import data (existing compositions get `is_generic=False`)

No data transformation required - feature is purely additive.

## Testing Strategy

### Unit Tests
- Generic inventory aggregation
- Estimated cost calculation
- Assignment validation (quantity matching, inventory bounds)
- Pending requirement queries

### Integration Tests
- Full workflow: plan with generic → assign → complete assembly
- Cost transition from estimated to actual
- Shopping list generation with generic items

### User Acceptance
- Primary user (Marianne) validated design document
- Test with real packaging inventory data
