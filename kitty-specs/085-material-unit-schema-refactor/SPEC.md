# Feature Specification: MaterialUnit Schema Refactor

**Feature Branch**: `085-material-unit-schema-refactor`  
**Created**: 2026-01-29  
**Status**: Draft  
**Input**: User description: "F085 MaterialUnit Schema Refactor - Make MaterialUnit child of MaterialProduct instead of Material, add auto-generation for 'each' type products, update Composition model to remove generic Material placeholder, and move MaterialUnit creation to MaterialProduct sub-form."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Generated MaterialUnits for 'Each' Products (Priority: P1)

As a user purchasing bags, boxes, or other per-unit materials, I need the system to automatically create a MaterialUnit when I add a MaterialProduct, so that I can immediately use these materials in FinishedGoods without manual unit definition.

**Why this priority**: This is the core value proposition - reducing toil for the majority case. Most material products are "each" type (bags, boxes, labels) and should work out-of-the-box without requiring users to manually create MaterialUnits.

**Independent Test**: Can be fully tested by creating a MaterialProduct with package_count (e.g., "Clear Bags 100ct") and verifying a MaterialUnit named "1 Clear Bags 100ct" is auto-created with quantity_per_unit=1.

**Acceptance Scenarios**:

1. **Given** I create a MaterialProduct "Clear Cellophane Bags 100ct" with package_count=100, **When** the product is saved, **Then** a MaterialUnit "1 Clear Cellophane Bags 100ct" is auto-created with quantity_per_unit=1
2. **Given** a MaterialProduct with package_length_m (linear type), **When** the product is saved, **Then** NO MaterialUnit is auto-created (manual definition required)
3. **Given** a MaterialProduct with package_sq_m (area type), **When** the product is saved, **Then** NO MaterialUnit is auto-created (manual definition required)
4. **Given** an auto-generated MaterialUnit exists for a product, **When** the product name is updated, **Then** the MaterialUnit name is also updated to match

---

### User Story 2 - Manual MaterialUnit Creation for Linear/Area Products (Priority: P1)

As a user purchasing ribbon, twine, or parchment paper, I need to define multiple consumption units (6", 12", 18") for each product, so that I can use different lengths in different FinishedGoods recipes.

**Why this priority**: Linear and area materials require flexible consumption definitions. A single 25-meter ribbon roll can be consumed as 6-inch pieces, 12-inch pieces, or 18-inch pieces depending on the FinishedGood being assembled.

**Independent Test**: Can be tested by creating a MaterialProduct "Red Satin Ribbon 25m", then manually adding MaterialUnits "6-inch Red Ribbon", "12-inch Red Ribbon", and verifying each has correct quantity_per_unit in base units (cm).

**Acceptance Scenarios**:

1. **Given** a MaterialProduct "Red Satin Ribbon 25m" (linear type), **When** I add a MaterialUnit "6-inch Red Ribbon" with quantity_per_unit=15.24cm, **Then** the unit is saved and associated with that specific product
2. **Given** a MaterialProduct "Parchment Paper 50 sq ft" (area type), **When** I add MaterialUnit "8x10 sheet" with quantity_per_unit in sq_cm, **Then** the unit is saved correctly
3. **Given** multiple MaterialUnits for a single product, **When** I view the product, **Then** all associated MaterialUnits are displayed in a list
4. **Given** a MaterialUnit "12-inch Red Ribbon" on product A, **When** I create a different product B with identical ribbon, **Then** product B does NOT share the MaterialUnit (duplication accepted)

---

### User Story 3 - FinishedGoods Use Product-Specific MaterialUnits (Priority: P1)

As a user assembling FinishedGoods, I need to select MaterialUnits that are specific to the products I've purchased, so that inventory calculations and costing accurately reflect which specific ribbon or bag product I'm using.

**Why this priority**: This is the whole reason for the schema change. FinishedGoods need to reference specific MaterialUnits tied to specific MaterialProducts to ensure accurate inventory tracking and cost calculation.

**Independent Test**: Can be tested by creating a FinishedGood that includes "6-inch Red Ribbon" MaterialUnit from product A, then verifying inventory calculations use product A's inventory (not other ribbon products).

**Acceptance Scenarios**:

1. **Given** FinishedGood "Cookie Gift Box" includes MaterialUnit "12-inch Red Ribbon" from product "Michaels Ribbon", **When** I check assembly feasibility, **Then** the system checks Michaels Ribbon inventory specifically
2. **Given** I have two identical ribbon products with separate MaterialUnits, **When** I select a MaterialUnit for a FinishedGood, **Then** the dropdown shows both options with product names for clarity
3. **Given** a FinishedGood uses MaterialUnit from product A, **When** product A runs out but product B (identical) has stock, **Then** the system shows shortage (no automatic substitution)

---

### User Story 4 - Composition Model Only References MaterialUnits (Priority: P1)

As a developer maintaining the codebase, I need the Composition model to only reference specific MaterialUnits (not generic Materials), so that all component relationships are concrete and resolvable at assembly time.

**Why this priority**: Removing the generic Material placeholder simplifies the data model and eliminates ambiguity. Every FinishedGood component must be a specific, actionable item.

**Independent Test**: Can be tested by attempting to create a Composition with material_id (should fail validation), and verifying Composition with material_unit_id works correctly.

**Acceptance Scenarios**:

1. **Given** the Composition model, **When** I attempt to create a record with material_id populated, **Then** validation fails (foreign key removed)
2. **Given** a Composition record, **When** I set material_unit_id, **Then** the record saves successfully and references the specific MaterialUnit
3. **Given** existing Compositions with material_id (legacy data), **When** I run the migration, **Then** those records are flagged for manual resolution or deleted (documented in migration plan)
4. **Given** the Composition XOR constraint, **When** checked, **Then** it enforces exactly one of: finished_unit_id, finished_good_id, packaging_product_id, or material_unit_id (4-way, not 5-way)

---

### User Story 5 - MaterialUnit Creation on MaterialProduct Form (Priority: P2)

As a user managing material products, I need to create and edit MaterialUnits directly on the MaterialProduct sub-form, so that I can define consumption units in context of the product I'm viewing.

**Why this priority**: This improves UX by co-locating related functionality. When viewing a ribbon product, I should be able to add "6-inch" and "12-inch" units right there, not in a separate tab.

**Independent Test**: Can be tested by opening a MaterialProduct in the Materials tab, seeing a MaterialUnits sub-section, and successfully adding/editing units.

**Acceptance Scenarios**:

1. **Given** I'm viewing MaterialProduct "Red Satin Ribbon 25m", **When** I click "Add Unit" in the MaterialUnits sub-section, **Then** a form appears to create a new MaterialUnit for this product
2. **Given** I've added MaterialUnit "6-inch Red Ribbon", **When** I save the product form, **Then** the MaterialUnit is persisted with correct material_product_id
3. **Given** the MaterialProduct has multiple MaterialUnits, **When** I view the product, **Then** all units are displayed in a list with edit/delete options
4. **Given** I delete a MaterialUnit that's referenced by a FinishedGood, **When** I attempt to save, **Then** validation prevents deletion with a clear error message

---

### User Story 6 - Materials Units Tab Becomes Read-Only List (Priority: P2)

As a user needing an overview of all MaterialUnits, I want the Materials → Units tab to show a comprehensive list of all units across all products, but creation/editing happens on the MaterialProduct form.

**Why this priority**: The Units tab serves as a useful reference view, but creation should happen in context (on the product form) to maintain clear parent-child relationship.

**Independent Test**: Can be tested by navigating to Materials → Units tab and verifying it displays all MaterialUnits with product context, but has no "Add Unit" button.

**Acceptance Scenarios**:

1. **Given** I navigate to Materials → Units tab, **When** the tab loads, **Then** I see a list of all MaterialUnits with columns: Name, Material, Product, Quantity per Unit, Available
2. **Given** I'm on the Units tab, **When** I look for creation controls, **Then** there is no "Add Unit" button (creation removed from this view)
3. **Given** I click on a MaterialUnit in the list, **When** the action completes, **Then** I'm taken to the parent MaterialProduct form with that unit highlighted for editing
4. **Given** the Units tab, **When** I apply filters, **Then** I can filter by Material category, subcategory, or product name

---

### User Story 7 - Data Migration for Existing MaterialUnits (Priority: P1)

As a system administrator, I need existing MaterialUnit records to be migrated from material_id to material_product_id during the schema change, so that my current data continues to work after the refactor.

**Why this priority**: This is a mandatory prerequisite. Without proper migration, existing data is lost or broken.

**Independent Test**: Can be tested by exporting current database, running migration transformation script, importing into fresh database, and verifying all MaterialUnits have valid material_product_id references.

**Acceptance Scenarios**:

1. **Given** existing MaterialUnits with material_id, **When** I export the data, **Then** export includes both material_id and inferred material_product_id (via material's products)
2. **Given** a Material has 3 products and 2 MaterialUnits, **When** migration runs, **Then** each product gets a copy of both MaterialUnits (duplication strategy)
3. **Given** a Material has no products, **When** migration encounters MaterialUnits for it, **Then** those MaterialUnits are flagged as unmigrateable with clear error message
4. **Given** migration completes, **When** I validate the database, **Then** all MaterialUnits have valid material_product_id and material_id column is removed
5. **Given** Composition records with material_id, **When** migration runs, **Then** these are flagged for manual review (cannot auto-migrate without product selection)

---

### Edge Cases

- What happens when a MaterialProduct is deleted that has MaterialUnits? (Cascade delete - MaterialUnits are deleted, but warn if referenced by FinishedGoods)
- What happens when auto-generating MaterialUnit name conflicts with existing unit? (Append numeric suffix: "1 Clear Bags-2")
- How does system handle MaterialUnit creation when material_product_id is null? (Validation rejects - foreign key is NOT NULL)
- What happens when importing MaterialUnits with invalid material_product_id? (Error logged, record skipped, import continues)
- How does migration handle Materials with dozens of products? (Creates MaterialUnit copies for each - accept duplication)
- What happens when user tries to create MaterialUnit on Units tab after refactor? (UI doesn't allow it - only product form has creation)

## Requirements *(mandatory)*

### Functional Requirements

#### Schema Changes

- **FR-001**: System MUST change MaterialUnit.material_id to MaterialUnit.material_product_id (Integer, ForeignKey to material_products.id, NOT NULL, indexed, ondelete=CASCADE)
- **FR-002**: System MUST remove material_id column from MaterialUnit model completely
- **FR-003**: System MUST remove material_id column from Composition model completely
- **FR-004**: System MUST update Composition XOR constraint from 5-way to 4-way (finished_unit_id, finished_good_id, packaging_product_id, material_unit_id)
- **FR-005**: System MUST add unique constraint on MaterialUnit (material_product_id, slug) to prevent duplicate units per product

#### Auto-Generation Logic

- **FR-006**: System MUST auto-generate MaterialUnit on MaterialProduct creation IF package_count is NOT NULL (per-unit type)
- **FR-007**: System MUST NOT auto-generate MaterialUnit IF package_length_m or package_sq_m is populated (linear/area types)
- **FR-008**: System MUST set auto-generated MaterialUnit name as "1 {product.name}"
- **FR-009**: System MUST set auto-generated MaterialUnit quantity_per_unit to 1.0
- **FR-010**: System MUST auto-generate slug for MaterialUnit following pattern: lowercase, hyphens, alphanumeric-only
- **FR-011**: System MUST update auto-generated MaterialUnit name when parent MaterialProduct name changes
- **FR-012**: System MUST handle slug conflicts during auto-generation by appending numeric suffix (-2, -3, etc.)

#### UI Changes

- **FR-013**: System MUST add MaterialUnits sub-section to MaterialProduct create/edit form
- **FR-014**: System MUST display list of MaterialUnits within MaterialProduct form with columns: Name, Quantity per Unit, Available Inventory
- **FR-015**: System MUST provide "Add Unit" button within MaterialProduct form for linear/area products only
- **FR-016**: System MUST hide "Add Unit" button for per-unit products (auto-generated unit already exists)
- **FR-017**: System MUST remove "Add Unit" button from Materials → Units tab
- **FR-018**: System MUST convert Materials → Units tab to read-only list view
- **FR-019**: System MUST make MaterialUnit rows in Units tab clickable, navigating to parent MaterialProduct form
- **FR-020**: System MUST add "Product" column to Units tab showing parent MaterialProduct name

#### Service Layer

- **FR-021**: System MUST implement MaterialProductService.create() to auto-generate MaterialUnit for per-unit products
- **FR-022**: System MUST implement MaterialProductService.update() to sync auto-generated MaterialUnit name when product name changes
- **FR-023**: System MUST implement MaterialProductService.delete() to prevent deletion if MaterialUnits are referenced by Compositions
- **FR-024**: System MUST implement MaterialUnitService.create() with validation for material_product_id NOT NULL
- **FR-025**: System MUST implement MaterialUnitService.get_by_product() to retrieve all units for a product
- **FR-026**: System MUST update CompositionService to validate material_unit_id references exist (remove material_id validation)

#### Data Migration

- **FR-027**: System MUST provide export transformation script to map material_id to material_product_id
- **FR-028**: System MUST duplicate MaterialUnits across all products of a Material during migration (accept duplication)
- **FR-029**: System MUST flag MaterialUnits orphaned (Material has no products) during migration with clear error
- **FR-030**: System MUST flag Composition records with material_id for manual review during migration
- **FR-031**: System MUST log all migration decisions (duplications, conflicts, failures) to migration.log file
- **FR-032**: System MUST validate post-migration that all MaterialUnits have valid material_product_id
- **FR-033**: System MUST validate post-migration that no Composition records have material_id populated

#### Import/Export

- **FR-034**: System MUST export MaterialUnits with material_product_slug (not material_slug)
- **FR-035**: System MUST import MaterialUnits by resolving material_product_slug to material_product_id
- **FR-036**: System MUST fail MaterialUnit import with clear error if material_product_slug doesn't resolve
- **FR-037**: System MUST export Compositions with material_unit_id and material_unit_slug (remove material_id/material_slug)
- **FR-038**: System MUST import Compositions by resolving material_unit_slug to material_unit_id

### Key Entities

- **MaterialUnit**: Modified entity now child of MaterialProduct (not Material). Has material_product_id FK, name, slug, quantity_per_unit. Auto-generated for per-unit products.
- **MaterialProduct**: Existing entity enhanced to be parent of MaterialUnits. One-to-many relationship with cascade delete.
- **Material**: Existing entity no longer directly related to MaterialUnits (relationship is now MaterialProduct → MaterialUnit).
- **Composition**: Modified junction model with material_id removed. Now 4-way XOR: finished_unit_id, finished_good_id, packaging_product_id, material_unit_id.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All MaterialProducts with package_count have exactly one auto-generated MaterialUnit after creation
- **SC-002**: MaterialProduct name updates successfully propagate to auto-generated MaterialUnit names within 1 second
- **SC-003**: MaterialUnit creation on MaterialProduct form succeeds for linear/area products with valid quantity_per_unit
- **SC-004**: Materials → Units tab displays all MaterialUnits with correct product associations and zero creation controls
- **SC-005**: Composition model successfully validates 4-way XOR constraint (no material_id validation)
- **SC-006**: Data migration script successfully transforms 100% of valid MaterialUnits from material_id to material_product_id
- **SC-007**: Migration logs clearly identify all orphaned MaterialUnits and unresolvable Compositions
- **SC-008**: Round-trip export/import with new schema preserves all MaterialUnit → MaterialProduct relationships
- **SC-009**: FinishedGoods assembly calculations correctly use MaterialUnit inventory from specific products
- **SC-010**: Zero MaterialUnit records exist with NULL material_product_id after migration
- **SC-011**: Zero Composition records exist with material_id populated after migration
- **SC-012**: Service layer tests achieve >80% coverage for MaterialUnit auto-generation and sync logic
