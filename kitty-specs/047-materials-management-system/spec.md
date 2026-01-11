# Feature Specification: Materials Management System

**Feature Branch**: `047-materials-management-system`
**Created**: 2026-01-10
**Status**: Draft
**Dependencies**: F046 (Finished Goods, Bundles & Assembly Tracking)
**Enables**: F048 (Shopping Lists), F049 (Assembly Workflows Enhancement)

## Overview

Implement a comprehensive materials management system that parallels the existing ingredient management system, enabling proper handling of non-edible materials (ribbon, boxes, bags, tissue, etc.) used in baking assemblies. Currently, materials are incorrectly modeled as ingredients (a temporary workaround), which pollutes the ingredient model and blocks complete FinishedGood assemblies.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Materials Catalog (Priority: P1)

As a baker, I need to organize my packaging materials in a logical hierarchy so I can find and manage them easily.

**Why this priority**: Without a materials catalog, nothing else works. This is the foundation for all material tracking.

**Independent Test**: Can be fully tested by creating a complete material hierarchy (Categories > Subcategories > Materials > Products) and verifying the catalog displays correctly.

**Acceptance Scenarios**:

1. **Given** an empty materials catalog, **When** I create a category "Ribbons", **Then** the category appears in the navigation tree
2. **Given** a category "Ribbons" exists, **When** I create a subcategory "Satin Ribbon", **Then** it appears nested under "Ribbons"
3. **Given** a subcategory "Satin Ribbon" exists, **When** I create a material "Red Satin Ribbon", **Then** it appears with an indicator showing "0 products"
4. **Given** a material exists, **When** I create a product "Michaels Red Satin 100ft Roll", **Then** it appears in the products panel with inventory "0"

---

### User Story 2 - Purchase and Track Material Inventory (Priority: P1)

As a baker, I need to record material purchases so I know what I have on hand and what it cost.

**Why this priority**: Inventory tracking is essential for planning assemblies and understanding costs. Without purchases, there's no inventory.

**Independent Test**: Can be fully tested by recording purchases for a material product and verifying inventory increases and weighted average cost updates.

**Acceptance Scenarios**:

1. **Given** a material product exists with 0 inventory, **When** I record a purchase of 2 packs containing 100 units each at $24 total, **Then** inventory shows 200 units at $0.12 per unit
2. **Given** a product has 200 units at $0.12/unit, **When** I purchase 100 more units at $0.15/unit, **Then** inventory shows 300 units at weighted average cost of $0.13/unit
3. **Given** a product has inventory, **When** I adjust inventory to "50% remaining", **Then** the inventory count is halved and unit cost remains unchanged

---

### User Story 3 - Define Material Units for Assembly (Priority: P1)

As a baker, I need to define how much material goes into each assembly (e.g., "6 inches of ribbon") so the system can calculate inventory and costs correctly.

**Why this priority**: Material Units are the bridge between raw material inventory and assembly consumption. Without them, materials cannot be added to finished goods.

**Independent Test**: Can be fully tested by creating a Material Unit and verifying it calculates available inventory from all associated products.

**Acceptance Scenarios**:

1. **Given** a material "Red Satin Ribbon" has products totaling 1200 inches, **When** I create a MaterialUnit "6-inch Red Ribbon" (6 inches per unit), **Then** available inventory shows 200 units
2. **Given** a MaterialUnit exists with products at different costs, **When** I view the unit, **Then** I see the current cost calculated as weighted average times quantity per unit
3. **Given** two products exist for the same material, **When** I view a MaterialUnit, **Then** available inventory aggregates across both products

---

### User Story 4 - Add Materials to Finished Goods (Priority: P2)

As a baker, I need to specify what materials go into each finished good so I can track costs and plan inventory needs.

**Why this priority**: Builds on P1 stories. This is where materials integrate with the existing assembly system.

**Independent Test**: Can be fully tested by adding materials to a FinishedGood composition and verifying cost calculations.

**Acceptance Scenarios**:

1. **Given** a FinishedGood "Holiday Gift Box" exists, **When** I add a MaterialUnit "6-inch Red Ribbon" with quantity 2, **Then** the composition shows the material with its estimated cost
2. **Given** a FinishedGood has both food and material components, **When** I view the cost summary, **Then** I see food costs separate from material costs with a total
3. **Given** I add a MaterialUnit, **When** that unit has multiple products available, **Then** I see a status indicator showing it's ready for assembly

---

### User Story 5 - Defer Material Selection to Assembly Time (Priority: P2)

As a baker, I want to defer specific material choices until assembly time so I can use whatever design/color is available or appropriate for that batch.

**Why this priority**: Supports flexible workflow where exact material selection happens at assembly time (e.g., choosing between snowflake or holly design bags based on what's in stock).

**Independent Test**: Can be fully tested by adding a generic Material placeholder to a FinishedGood and resolving it during assembly.

**Acceptance Scenarios**:

1. **Given** a FinishedGood exists, **When** I add a generic Material "Cellophane Bag 6-inch" instead of a specific MaterialUnit, **Then** the composition shows a warning indicator "selection pending"
2. **Given** a FinishedGood has a generic material placeholder, **When** I view the cost summary, **Then** material cost is marked as "estimated" using weighted average across all products
3. **Given** a FinishedGood has generic materials, **When** I attempt to record assembly, **Then** I'm prompted to select specific products before proceeding

---

### User Story 6 - Record Assembly with Material Consumption (Priority: P2)

As a baker, I need to record which specific materials I used during assembly so I have accurate cost records and inventory decrements.

**Why this priority**: This is where materials actually get consumed. Completes the inventory cycle.

**Independent Test**: Can be fully tested by recording an assembly and verifying material inventory decrements and cost snapshots are captured.

**Acceptance Scenarios**:

1. **Given** an assembly with resolved material assignments, **When** I record assembly of 50 units, **Then** material inventory decreases appropriately and costs are captured
2. **Given** a FinishedGood has generic material placeholders, **When** I view the assembly form, **Then** each pending material shows an inline dropdown to select a specific product
3. **Given** I'm assigning materials from multiple products, **When** I specify "30 from Snowflakes, 20 from Holly", **Then** the system validates the total equals my assembly quantity
4. **Given** assembly is recorded, **When** I view the AssemblyRun later, **Then** I see the complete identity of materials used (product names, quantities, costs at time of assembly)

---

### User Story 7 - Query Historical Material Usage (Priority: P3)

As a baker, I want to see what materials I used in past assemblies even if catalog data has changed.

**Why this priority**: Important for cost analysis and repeat planning, but not blocking core workflow.

**Independent Test**: Can be fully tested by recording an assembly, changing product names in catalog, and verifying historical query still shows original names.

**Acceptance Scenarios**:

1. **Given** an assembly was recorded 6 months ago, **When** I view that assembly's details, **Then** I see the exact material names, quantities, and costs from that time
2. **Given** a product was renamed after assembly, **When** I view historical assembly, **Then** I see the name it had at assembly time (snapshot), not current name

---

### User Story 8 - Import/Export Materials Catalog (Priority: P3)

As a baker, I need to import and export my materials catalog for backup and data transfer purposes.

**Why this priority**: Supports existing import/export infrastructure. Lower priority than core workflow.

**Independent Test**: Can be fully tested by exporting materials, clearing database, and re-importing.

**Acceptance Scenarios**:

1. **Given** a materials catalog exists, **When** I export, **Then** the export file includes all categories, subcategories, materials, products, and units
2. **Given** a valid materials export file, **When** I import, **Then** the catalog is recreated with all relationships intact
3. **Given** I import materials, **When** a material references a non-existent supplier, **Then** I see a clear error message

---

### Edge Cases

- What happens when attempting to delete a category that contains products with inventory > 0? (Validation error)
- What happens when deleting a material that's used in a Composition? (Validation error)
- How does the system handle purchasing 0 units? (Validation error - positive quantity required)
- What happens if material products have insufficient inventory during assembly? (Validation error - assembly blocked until inventory is corrected)
- How does weighted average handle first purchase for a new product? (First purchase sets initial cost)

## Requirements *(mandatory)*

### Functional Requirements

**Materials Catalog**
- **FR-001**: System MUST enforce a mandatory 3-level material hierarchy: Category > Subcategory > Material (all levels required)
- **FR-002**: System MUST allow multiple Products per Material (different brands/suppliers)
- **FR-003**: System MUST track inventory at the Product level (not Material level)
- **FR-004**: System MUST calculate weighted average unit cost per Product on each purchase
- **FR-005**: System MUST support Material Units defining atomic consumption amounts (e.g., "6 inches of ribbon")

**Purchasing**
- **FR-006**: System MUST record material purchases with package-level tracking (units per package, packages purchased)
- **FR-007**: System MUST calculate and store unit cost at purchase time (immutable snapshot)
- **FR-008**: System MUST update Product inventory and weighted average cost atomically on purchase
- **FR-009**: System MUST support manual inventory adjustments by count or percentage

**Composition**
- **FR-010**: System MUST allow FinishedGoods to include MaterialUnits (specific) as components
- **FR-011**: System MUST allow FinishedGoods to include Materials (generic placeholder) for deferred decisions
- **FR-012**: System MUST display clear visual indicators distinguishing specific vs pending materials
- **FR-013**: System MUST calculate separate cost totals for food components and material components

**Assembly**
- **FR-014**: System MUST enforce material resolution before assembly (hard stop for generic placeholders)
- **FR-015**: System MUST block assembly recording when material inventory is insufficient (no bypass option)
- **FR-016**: System MUST capture complete identity snapshot at consumption time (product, quantity, cost, name)
- **FR-017**: System MUST decrement Product inventory when materials are consumed in assembly
- **FR-018**: System MUST calculate and store total material cost per assembly run

**Import/Export**
- **FR-019**: System MUST include materials in catalog import/export
- **FR-020**: System MUST include material purchases in view data export

### Key Entities

- **MaterialCategory**: Top-level grouping (e.g., "Ribbons", "Boxes", "Bags")
- **MaterialSubcategory**: Second-level grouping within a category (e.g., "Satin Ribbon", "Gift Boxes")
- **Material**: Abstract material definition (e.g., "Red Satin Ribbon", "6-inch Cellophane Bag")
- **MaterialProduct**: Specific purchasable item from a supplier (e.g., "Michaels Red Satin 100ft Roll")
- **MaterialUnit**: Atomic consumption unit defining quantity per use (e.g., "6-inch ribbon" = 6 inches per unit)
- **MaterialPurchase**: Purchase transaction with immutable cost snapshot
- **MaterialConsumption**: Assembly consumption record with full denormalized snapshot (product_name, material_name, category_name, quantity, unit_cost, supplier_name) for historical accuracy

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can create a complete material hierarchy (category through product) in under 5 minutes
- **SC-002**: Recording a material purchase updates inventory and weighted average cost immediately (visible in UI)
- **SC-003**: MaterialUnit available inventory aggregates correctly across all associated products (verified by manual calculation)
- **SC-004**: Assembly recording decrements correct inventory amounts from the correct products
- **SC-005**: Historical assembly queries return original material names and costs even after catalog changes
- **SC-006**: User can complete the full workflow (catalog > purchase > add to finished good > assemble) without documentation assistance
- **SC-007**: Material costs appear correctly in event planning summaries (estimated for generic, actual for specific)
- **SC-008**: Import/export round-trip preserves all material data without loss

### User Acceptance

- **SC-009**: Primary user (Marianne) can create materials catalog for holiday baking
- **SC-010**: Primary user can successfully record material purchases and see inventory update
- **SC-011**: Primary user can add materials to FinishedGoods and plan events with material costs
- **SC-012**: Primary user can complete assembly with material selection workflow

## Clarifications

### Session 2026-01-10

- Q: How should material product quantities be stored and converted for inventory aggregation? → A: Products store native purchase units (feet/yards) with system converting to base unit (inches) for storage. "Each" items need no conversion.
- Q: When a user records assembly despite insufficient material inventory, what should happen? → A: Block the save entirely until inventory is corrected. No "Record Anyway" bypass option.
- Q: What fields should be captured in the MaterialConsumption snapshot for historical accuracy? → A: Full snapshot (product_name, material_name, category_name, quantity, unit_cost, supplier_name) - aligns with existing food consumption model.
- Q: When should the user resolve generic material placeholders to specific products? → A: Inline during assembly - each pending material shows a dropdown next to the quantity field.
- Q: Is the Subcategory level mandatory, or can Materials be added directly to Categories? → A: Mandatory - always require 3 levels for consistency and future organization.

## Assumptions

- Materials are non-perishable, so weighted average costing (not FIFO) is acceptable
- The existing Supplier table will be shared between ingredients and materials
- Material unit types are limited to: 'each', 'linear_inches', 'square_feet' (covers common packaging needs)
- Material products store quantity in native purchase units; system converts linear measurements to inches and area measurements to square inches for storage and aggregation
- The UI pattern will mirror the existing Ingredients tab to leverage user familiarity

## Dependencies

- **F046**: Finished Goods, Bundles & Assembly Tracking (Composition and AssemblyRun models)
- **Existing**: Supplier model (shared)
- **Existing**: Import/Export infrastructure (v4.x format)

## Out of Scope

- Rich material metadata (color codes, dimensions, UPC barcodes) - deferred to future enhancement
- Material templates for common packaging configurations
- Material shortage alerts and reorder suggestions
- Analytics and reporting beyond basic cost display
