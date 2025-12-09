# Feature Specification: Production & Inventory Tracking

*Path: kitty-specs/013-production-inventory-tracking/spec.md*

**Feature Branch**: `013-production-inventory-tracking`
**Created**: 2025-12-09
**Status**: Draft
**Input**: User description: "Add production tracking entities and services to record batch production and assembly runs with FIFO consumption, yield-based costing, and full audit trail"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Batch Production (Priority: P1)

As a baker, I want to record when I make batches of a recipe so the system deducts ingredients from my inventory, increments my finished item count, and tracks the actual cost of what I produced.

**Why this priority**: This is the core production tracking functionality. Without batch recording, no inventory consumption or production history exists.

**Independent Test**: Can be fully tested by recording a batch production for a recipe with known inventory and verifying: (1) ingredients deducted via FIFO, (2) FinishedUnit inventory incremented, (3) ProductionRun record created with cost-at-consumption data.

**Acceptance Scenarios**:

1. **Given** a recipe "Chocolate Chip Cookies" exists with ingredients in inventory and a FinishedUnit defined (48 cookies/batch), **When** the user records "2 batches, actual yield 92 cookies", **Then** ingredients are deducted via FIFO, FinishedUnit.inventory_count increases by 92, and a ProductionRun is persisted with consumption ledger and costs.

2. **Given** a recipe with nested sub-recipes (e.g., "Decorated Sugar Cookies" using "Royal Icing"), **When** the user records 1 batch, **Then** ingredients from all recipe levels are aggregated and deducted via FIFO.

3. **Given** a recipe with packaging materials defined in its BOM (e.g., parchment paper per batch), **When** the user records production, **Then** packaging materials are also deducted from InventoryItem.

4. **Given** insufficient inventory for an ingredient, **When** the user attempts to record production, **Then** the operation fails with a clear error listing what's missing (ingredient, needed quantity, available quantity).

---

### User Story 2 - Check Production Availability (Priority: P1)

As a baker, I want to check if I have enough ingredients before I start baking so I don't discover shortages mid-production.

**Why this priority**: Pre-flight availability checks prevent failed production attempts and wasted time. This is a prerequisite for confident production recording.

**Independent Test**: Can be fully tested by calling check_can_produce() with various inventory states and verifying the structured response accurately reflects availability.

**Acceptance Scenarios**:

1. **Given** sufficient inventory for all ingredients, **When** check_can_produce(recipe_id, 2) is called, **Then** returns {can_produce: true, missing: []}.

2. **Given** insufficient inventory for flour (need 4 cups, have 2), **When** check_can_produce(recipe_id, 2) is called, **Then** returns {can_produce: false, missing: [{ingredient: "flour", needed: 4, have: 2}]}.

3. **Given** a nested recipe, **When** check_can_produce is called, **Then** availability is calculated for aggregated ingredients from all levels.

---

### User Story 3 - Record Assembly Run (Priority: P2)

As a baker, I want to record when I assemble finished goods (e.g., bag 24 cookies into 2 dozen-bags) so the system tracks my assembled inventory, deducts the components, and logs the event.

**Why this priority**: Assembly tracking completes the production pipeline. Depends on FinishedUnits existing from batch production.

**Independent Test**: Can be fully tested by recording an assembly with known component inventory and verifying: (1) FinishedUnit inventory decremented, (2) packaging deducted, (3) FinishedGood inventory incremented, (4) AssemblyRun record created.

**Acceptance Scenarios**:

1. **Given** FinishedUnit "Sugar Cookie" has inventory_count=100 and FinishedGood "Cookie Gift Bag" requires 12 cookies + 1 cellophane bag, **When** the user records assembly of 5 gift bags, **Then** FinishedUnit decrements by 60, InventoryItem (cellophane bags) decrements by 5, FinishedGood.inventory_count increments by 5, and AssemblyRun is persisted.

2. **Given** a FinishedGood with nested FinishedGood components (sub-assemblies), **When** assembly is recorded, **Then** component FinishedGoods are decremented appropriately.

3. **Given** insufficient FinishedUnit inventory, **When** the user attempts to record assembly, **Then** the operation fails with clear error details.

---

### User Story 4 - Check Assembly Availability (Priority: P2)

As a baker, I want to check if I have enough finished items and packaging before I start assembling so I can plan my work efficiently.

**Why this priority**: Pre-flight checks for assembly mirror the batch production pattern and enable confident assembly recording.

**Independent Test**: Can be fully tested by calling check_can_assemble() with various inventory states and verifying accurate structured responses.

**Acceptance Scenarios**:

1. **Given** sufficient FinishedUnit and packaging inventory, **When** check_can_assemble(finished_good_id, 10) is called, **Then** returns {can_assemble: true, missing: []}.

2. **Given** insufficient packaging (need 10 bags, have 5), **When** check_can_assemble is called, **Then** returns {can_assemble: false, missing: [{component: "cellophane bags", needed: 10, have: 5}]}.

---

### User Story 5 - View Production History (Priority: P3)

As a baker, I want to see a history of my production runs so I can track what I've made, when, and at what cost.

**Why this priority**: Historical reporting is valuable but secondary to the core recording functionality.

**Independent Test**: Can be fully tested by recording multiple production/assembly runs and querying history, verifying complete audit trail with consumption details.

**Acceptance Scenarios**:

1. **Given** multiple ProductionRun and AssemblyRun records exist, **When** the user queries production history, **Then** results include: timestamp, recipe/assembly name, quantity, actual yield, total cost, and consumption ledger details.

2. **Given** a ProductionRun with consumption ledger, **When** viewing details, **Then** the user can see which specific InventoryItems were consumed (FIFO trace) and their cost-at-time-of-consumption.

---

### User Story 6 - Import/Export Production History (Priority: P3)

As a baker, I want to export and import my production history so I can back up my data or migrate between systems.

**Why this priority**: Data portability is important but secondary to core production functionality.

**Independent Test**: Can be fully tested by exporting production/assembly runs, clearing data, importing, and verifying data integrity.

**Acceptance Scenarios**:

1. **Given** ProductionRun and AssemblyRun records exist, **When** export is performed, **Then** all records including consumption ledger and cost data are serialized.

2. **Given** an exported production history file, **When** import is performed, **Then** records are restored with all audit trail data intact.

---

### Edge Cases

- What happens when production consumes the last of an inventory item? (Item should be marked consumed, FIFO continues to next item or reports shortfall)
- What happens when actual yield is 0? (Should be allowed - production failed but ingredients still consumed)
- What happens when actual yield exceeds expected? (Should be allowed - yield variance is tracked)
- What happens with unit conversion during consumption? (Use existing unit_converter service, fail with clear error if conversion impossible)
- What happens if packaging product has no inventory? (Fail with clear error like ingredients)
- What happens with concurrent production attempts? (Transaction isolation should prevent race conditions)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record batch production with recipe_id, num_batches, actual_yield, produced_at timestamp, and optional notes
- **FR-002**: System MUST deduct ingredient quantities from InventoryItem using FIFO consumption when recording batch production
- **FR-003**: System MUST increment FinishedUnit.inventory_count by actual_yield when recording batch production
- **FR-004**: System MUST persist consumption ledger entries recording which specific InventoryItems were consumed and their cost-at-time-of-consumption
- **FR-005**: System MUST calculate and store per-unit cost based on actual yield (total_ingredient_cost / actual_yield)
- **FR-006**: System MUST support nested recipes by using RecipeService.get_aggregated_ingredients() to collect ingredients from all levels
- **FR-007**: System MUST deduct packaging materials from InventoryItem when Composition BOM includes packaging products
- **FR-008**: System MUST provide check_can_produce(recipe_id, num_batches) returning structured availability response
- **FR-009**: System MUST record assembly runs with finished_good_id, quantity, assembled_at timestamp, and optional notes
- **FR-010**: System MUST decrement FinishedUnit.inventory_count when assembling (deducting components)
- **FR-011**: System MUST deduct packaging from InventoryItem based on Composition BOM when assembling
- **FR-012**: System MUST increment FinishedGood.inventory_count when recording assembly
- **FR-013**: System MUST provide check_can_assemble(finished_good_id, quantity) returning structured availability response
- **FR-014**: System MUST execute all inventory changes within a single database transaction with rollback on failure
- **FR-015**: System MUST support import/export of ProductionRun and AssemblyRun records including consumption ledger data
- **FR-016**: System MUST calculate yield variance (expected_yield - actual_yield) and store for reporting

### Key Entities

- **ProductionRun**: Records a batch production event. Attributes: recipe_id, num_batches, expected_yield, actual_yield, produced_at, notes, total_ingredient_cost, per_unit_cost
- **ProductionConsumption**: Junction table recording which InventoryItems were consumed for a ProductionRun. Attributes: production_run_id, inventory_item_id, quantity_consumed, unit, cost_at_consumption
- **AssemblyRun**: Records an assembly event. Attributes: finished_good_id, quantity_assembled, assembled_at, notes, total_component_cost
- **AssemblyConsumption**: Junction table recording components/packaging consumed for an AssemblyRun. Attributes: assembly_run_id, component_type, component_id, quantity_consumed, cost_at_consumption

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can record batch production and see inventory updated within 2 seconds
- **SC-002**: Availability checks return accurate results 100% of the time (no false positives or negatives)
- **SC-003**: Production history includes complete audit trail showing exact items consumed and their costs
- **SC-004**: Yield-based costing accurately reflects per-unit cost based on actual production output
- **SC-005**: Nested recipe production correctly aggregates and deducts ingredients from all hierarchy levels
- **SC-006**: All production/assembly operations are atomic - either fully complete or fully rolled back
- **SC-007**: Import/export preserves 100% of production history data including consumption ledger details
- **SC-008**: Service layer achieves >70% test coverage with tests for happy path, edge cases, and error conditions

## Assumptions

- Feature 011 (Packaging Materials & BOM) is complete and Composition model supports packaging_product_id
- Feature 012 (Nested Recipes) is complete and RecipeService.get_aggregated_ingredients() is available
- InventoryItemService.consume_fifo() exists and supports dry_run mode for availability checking
- FinishedUnit and FinishedGood models have inventory_count fields with proper constraints
- Existing ProductionRecord model (event-based) will be preserved; new ProductionRun model is separate for general production tracking

## Out of Scope

- Production recording UI (Feature 014)
- Assembly recording UI (Feature 014)
- Production history views (Feature 014)
- Inventory dashboards (Feature 014)
- Automatic reorder alerts when inventory runs low
- Production scheduling/planning
- Multi-user concurrency beyond database transaction isolation

## Dependencies

- Feature 011 complete (packaging materials in Composition)
- Feature 012 complete (nested recipe aggregation via get_aggregated_ingredients)
- InventoryItemService with FIFO consumption methods
- FinishedUnitService and FinishedGoodService for inventory updates

## Technical Notes

- Ingredient consumption must use InventoryItemService FIFO methods
- Nested recipe support: use RecipeService.get_aggregated_ingredients() from Feature 012
- Packaging consumption: query Composition for packaging products, deduct from InventoryItem
- Transaction safety: all deductions in single transaction (rollback on failure)
- Availability check should return structured response: {can_produce: bool, missing: [{ingredient, needed, have}]}
- Per-unit cost calculation: total_consumed_cost / actual_yield (not expected_yield)

## Reference Documents

- `docs/workflow-refactoring-spec.md` - Workflow gap analysis (BATCH RUN, FG ASSEMBLY concepts)
- `src/models/production_record.py` - Existing event-based production tracking
- `src/services/production_service.py` - Existing production service to extend
- `src/services/recipe_service.py` - get_aggregated_ingredients() for nested recipes
- `src/models/composition.py` - BOM/packaging relationships
