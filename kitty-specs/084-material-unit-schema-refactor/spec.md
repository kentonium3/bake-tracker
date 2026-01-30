# Feature Specification: MaterialUnit Schema Refactor

**Feature Branch**: `084-material-unit-schema-refactor`
**Created**: 2026-01-30
**Status**: Draft
**Input**: F085 MaterialUnit Schema Refactor - Change MaterialUnit parent from Material to MaterialProduct, add auto-generation for "each" type products, remove generic Material references from Composition model

## Problem Statement

MaterialUnits currently reference abstract Materials instead of specific MaterialProducts, which prevents product-specific unit definitions and breaks the mental model for how materials are consumed in FinishedGoods assembly.

**Current Issues:**
- MaterialUnit.material_id references abstract Material (not specific product)
- Cannot distinguish between different ribbon widths from different products
- Forces all products of same Material to share MaterialUnits (inappropriate duplication prevention)
- No auto-generation for "each" type products (bags, boxes require manual unit creation)
- Composition model allows generic Material placeholder (ambiguous at assembly time)

**Target State:**
- MaterialUnit becomes child of MaterialProduct (not Material)
- Auto-generation of MaterialUnits for package_count products reduces user toil
- Composition model only references concrete MaterialUnits (no ambiguity)

## User Scenarios & Testing

### User Story 1 - Create MaterialProduct with Auto-Generated Unit (Priority: P1)

When a user creates a MaterialProduct for items sold by count (bags, boxes, labels), the system automatically creates a corresponding MaterialUnit so the product is immediately usable in FinishedGoods composition.

**Why this priority**: This is the majority use case - most materials are "each" type products. Auto-generation eliminates manual toil and makes products immediately usable.

**Independent Test**: Create a new MaterialProduct with package_count=100. Verify a MaterialUnit "1 {product name}" is auto-created and visible in the product form.

**Acceptance Scenarios**:

1. **Given** a user is creating a new MaterialProduct, **When** they save with package_count=100 (no length/area), **Then** a MaterialUnit named "1 {product name}" with quantity_per_unit=1.0 is auto-created
2. **Given** an auto-generated MaterialUnit exists, **When** the user views the MaterialProduct form, **Then** the MaterialUnit appears in the MaterialUnits sub-section
3. **Given** an auto-generated MaterialUnit exists, **When** the user edits its name, **Then** the change is saved (fully editable)
4. **Given** the user tries to create a MaterialUnit with a duplicate name within the same product, **When** they save, **Then** validation error prevents the duplicate

---

### User Story 2 - Define Custom MaterialUnits for Linear/Area Products (Priority: P1)

When a user has a MaterialProduct measured by length (ribbon) or area (fabric), they can manually define consumption units like "6-inch cut" or "12-inch piece" specific to that product.

**Why this priority**: Linear/area products require explicit unit definitions - there's no sensible default. Users need this to specify how materials are consumed in FinishedGoods.

**Independent Test**: Create a MaterialProduct with package_length_m=25. Verify no auto-generated unit. Add a custom MaterialUnit "6-inch ribbon" manually.

**Acceptance Scenarios**:

1. **Given** a user is creating a MaterialProduct with package_length_m=25 (linear product), **When** they save, **Then** no MaterialUnit is auto-generated
2. **Given** a linear MaterialProduct exists, **When** the user views the MaterialProduct form, **Then** an "Add Unit" button is visible in the MaterialUnits sub-section
3. **Given** the user clicks "Add Unit", **When** they enter name "6-inch ribbon" and quantity_per_unit=0.1524 (6 inches in meters), **Then** the MaterialUnit is created for this product

---

### User Story 3 - View All MaterialUnits Across Products (Priority: P2)

A user can view all MaterialUnits across all products in a read-only reference list, with accordion expansion to see parent product details.

**Why this priority**: Provides overview visibility without duplicating the creation workflow. Users need to see what units exist across their inventory.

**Independent Test**: Navigate to Materials > Units tab. Verify read-only list with no "Add Unit" button. Click a row and verify accordion expansion shows parent product details.

**Acceptance Scenarios**:

1. **Given** a user navigates to Materials > Units tab, **When** the tab loads, **Then** all MaterialUnits are displayed with columns: Name, Material, Product, Quantity per Unit
2. **Given** the Units tab is displayed, **When** the user looks for an "Add Unit" button, **Then** no such button exists (read-only)
3. **Given** a MaterialUnit row is displayed, **When** the user clicks the row, **Then** it expands accordion-style to show parent MaterialProduct details inline

---

### User Story 4 - Compose FinishedGoods with Product-Specific Units (Priority: P2)

When composing a FinishedGood, users select MaterialUnits that are specific to purchased products, enabling accurate inventory tracking and cost calculation.

**Why this priority**: This is the downstream benefit of the schema change - FinishedGoods compositions reference concrete products for accurate costing.

**Independent Test**: Create a FinishedGood composition using a MaterialUnit. Verify the Composition references material_unit_id only (no material_id).

**Acceptance Scenarios**:

1. **Given** a user is adding a material component to a FinishedGood, **When** they select a MaterialUnit, **Then** the composition stores material_unit_id (not material_id)
2. **Given** a Composition is created with material_unit_id, **When** inventory is checked, **Then** availability reflects the specific product's inventory

---

### User Story 5 - Export and Import MaterialUnits (Priority: P3)

Users can export MaterialUnits with product references and import them back, maintaining referential integrity via material_product_slug.

**Why this priority**: Required for the reset/re-import migration strategy. Enables data portability and backup/restore workflows.

**Independent Test**: Export MaterialUnits, verify material_product_slug column. Import to fresh database, verify MaterialUnits link to correct products.

**Acceptance Scenarios**:

1. **Given** MaterialUnits exist, **When** the user exports data, **Then** MaterialUnits export includes material_product_slug (not material_slug)
2. **Given** an export file with MaterialUnits, **When** importing to a fresh database, **Then** MaterialUnits are created with correct material_product_id resolved from slug
3. **Given** an export file has MaterialUnit with invalid material_product_slug, **When** importing, **Then** clear error message identifies the invalid reference

---

### User Story 6 - Migration from Old Schema (Priority: P3)

Existing data can be migrated from the old schema (MaterialUnit->Material) to the new schema (MaterialUnit->MaterialProduct) with duplication strategy.

**Why this priority**: Required for existing users to upgrade. Deferred priority because it's a one-time operation.

**Independent Test**: Export old-format data. Run migration transformation. Import transformed data. Verify MaterialUnits correctly linked to products.

**Acceptance Scenarios**:

1. **Given** a Material has 3 products and 2 MaterialUnits, **When** migration runs, **Then** 6 MaterialUnits are created (3 products x 2 units)
2. **Given** a Material has 0 products and 2 MaterialUnits, **When** migration runs, **Then** those MaterialUnits are flagged as unmigrateable in the log
3. **Given** a Composition has material_id (generic placeholder), **When** migration runs, **Then** that Composition is skipped with clear log entry (user fixes externally)

---

### Edge Cases

- What happens when a MaterialUnit name already exists for a different unit within the same MaterialProduct? Validation prevents save with duplicate name error.
- What happens when deleting a MaterialUnit that is referenced by a Composition? Deletion is prevented with clear error indicating which FinishedGoods reference it.
- What happens when renaming a MaterialProduct that has an auto-generated unit? The auto-generated unit name does NOT auto-sync (user edited it, so it's their responsibility).
- What happens when package_count and package_length_m are both populated? This is invalid at the MaterialProduct level (mutual exclusivity) - auto-generation only triggers for pure package_count products.

## Requirements

### Functional Requirements

- **FR-001**: System MUST change MaterialUnit.material_id FK to MaterialUnit.material_product_id FK with NOT NULL constraint, index, and CASCADE delete
- **FR-002**: System MUST remove Material.units relationship and add MaterialProduct.material_units relationship
- **FR-003**: System MUST auto-generate a MaterialUnit named "1 {product.name}" with quantity_per_unit=1.0 when creating a MaterialProduct with package_count (and no package_length_m or package_sq_m)
- **FR-004**: System MUST allow editing of auto-generated MaterialUnits (name, quantity_per_unit are fully editable after creation)
- **FR-005**: System MUST prevent duplicate MaterialUnit names within the same MaterialProduct (validation error on save)
- **FR-006**: System MUST remove material_id field from Composition model
- **FR-007**: System MUST update Composition XOR constraint from 5-way to 4-way (finished_unit_id, finished_good_id, packaging_product_id, material_unit_id)
- **FR-008**: System MUST remove create_material_placeholder_composition() factory method from Composition
- **FR-009**: System MUST display MaterialUnits sub-section in MaterialProduct create/edit form with columns: Name, Quantity per Unit
- **FR-010**: System MUST show "Add Unit" button in MaterialProduct form only for products without package_count (linear/area products)
- **FR-011**: System MUST prevent deletion of MaterialUnits that are referenced by Compositions (validation error with affected FinishedGoods listed)
- **FR-012**: System MUST remove "Add Unit" button from Materials > Units tab (read-only view)
- **FR-013**: System MUST display MaterialUnits in Units tab with columns: Name, Material, Product, Quantity per Unit
- **FR-014**: System MUST expand Units tab rows accordion-style on click to show parent MaterialProduct details inline
- **FR-015**: System MUST export MaterialUnits with material_product_slug reference (not material_slug)
- **FR-016**: System MUST import MaterialUnits by resolving material_product_slug to material_product_id
- **FR-017**: System MUST skip Compositions with material_id during import (log skipped records for user to fix externally)
- **FR-018**: System MUST provide migration transformation that creates N x M MaterialUnits when Material has N products and M units
- **FR-019**: System MUST flag unmigrateable MaterialUnits (Materials with 0 products) in migration log

### Key Entities

- **MaterialUnit**: Defines a consumption unit for a specific MaterialProduct (e.g., "6-inch ribbon", "1 bag"). Has name, quantity_per_unit, slug. Parent is MaterialProduct (NEW - was Material).
- **MaterialProduct**: A specific purchasable product for a Material category (e.g., "Michaels 1/4-inch Red Satin Ribbon 25m"). Now owns MaterialUnits via one-to-many relationship.
- **Material**: Abstract material taxonomy (e.g., "Red Satin Ribbon"). No longer owns MaterialUnits directly.
- **Composition**: Junction table for FinishedGood components. References exactly one of: finished_unit_id, finished_good_id, packaging_product_id, material_unit_id (4-way XOR, was 5-way with material_id removed).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Zero MaterialUnits with NULL material_product_id after implementation (100% linked to products)
- **SC-002**: Zero Compositions with material_id after implementation (field removed from schema)
- **SC-003**: MaterialProduct creation with package_count completes with auto-generated unit in under 500ms
- **SC-004**: Users can create a MaterialProduct and immediately use its unit in FinishedGoods composition without additional manual steps
- **SC-005**: Export -> Import round-trip preserves 100% of MaterialUnit relationships (verified by data comparison)
- **SC-006**: All existing MaterialUnit service tests pass after FK migration (zero regressions)
- **SC-007**: Service layer test coverage for MaterialUnit operations exceeds 80%
- **SC-008**: Migration log documents all duplication decisions, orphaned units, and skipped Compositions

## Assumptions

- MaterialProduct already has inventory tracking via MaterialInventoryItem (no changes needed to inventory model)
- The reset/re-import migration strategy is acceptable (no incremental migration scripts needed)
- Users will fix Compositions with material_id references externally before re-importing (tool provides log, not automated fix)
- Slug conflicts during auto-generation will use numeric suffix pattern (e.g., -2, -3) consistent with existing slug generation patterns

## Dependencies

- Existing MaterialProduct CRUD operations in material_product_service.py
- Existing Composition XOR constraint implementation
- Existing export/import infrastructure with slug resolution patterns
- CustomTkinter sub-form patterns (Recipe -> FinishedUnits as reference implementation)
