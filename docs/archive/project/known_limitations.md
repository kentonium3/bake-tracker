# Known Limitations

This document tracks intentional design limitations in the Seasonal Baking Tracker application.

---

## Nested FinishedGood Assembly Ledger

**Feature**: 013 (Production & Inventory Tracking)
**Status**: Intentional limitation
**Location**: `src/services/assembly_service.py:293-311`

### Behavior

When a FinishedGood is used as a component of another FinishedGood during assembly, the system:

- Decrements the nested FinishedGood's `inventory_count`
- Includes the nested FinishedGood's cost in assembly cost calculation
- Does NOT create a consumption ledger entry for the nested FinishedGood

### Why This Limitation Exists

The current data model has dedicated consumption ledger tables:
- `AssemblyFinishedUnitConsumption` - tracks FinishedUnit consumption
- `AssemblyPackagingConsumption` - tracks packaging product consumption

There is no `AssemblyFinishedGoodConsumption` table for tracking nested FinishedGood consumption. This was intentional to keep the initial implementation scope manageable.

### Impact

- **Inventory is correctly tracked**: The nested FG's `inventory_count` is properly decremented
- **Costs are correctly calculated**: The nested FG's cost is included in the parent FG's `total_component_cost`
- **Audit trail is incomplete**: There is no queryable ledger showing which assembly runs consumed which nested FinishedGoods

### Future Enhancement

To add full ledger tracking for nested FinishedGoods:

1. Create `AssemblyFinishedGoodConsumption` model with:
   - `assembly_run_id` (FK to AssemblyRun)
   - `finished_good_id` (FK to FinishedGood - the consumed one)
   - `quantity_consumed` (int)
   - `unit_cost_at_consumption` (Decimal)
   - `total_cost` (Decimal)

2. Update `record_assembly()` to create consumption records alongside inventory decrement

3. Add relationship to `AssemblyRun` model for eager loading

### Workaround

Until this enhancement is implemented, nested FinishedGood consumption can be tracked by:
- Querying `AssemblyRun` records filtered by parent `finished_good_id`
- Cross-referencing with `Composition` table to identify which nested FGs were components
- Calculating consumed quantities from `quantity_assembled * component_quantity`
