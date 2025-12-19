# Feature Specification: Product Name Differentiation

**Feature Branch**: `023-product-name-differentiation`
**Created**: 2025-12-19
**Status**: Draft
**Input**: User description: "Add product_name field to Product table to distinguish variants with identical packaging (e.g., 'Lindt 70% Cacao' vs 'Lindt 85% Cacao' both 3.5oz bars). Includes schema migration, UI updates, and import/export handling."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Product Variant with Distinct Name (Priority: P1)

When a user adds a new product that has the same brand, package size, and unit as an existing product, they can differentiate it by entering a product name. This enables tracking multiple variants of the same product line (e.g., different chocolate percentages, flavors, or formulations).

**Why this priority**: This is the core use case that motivates the feature. Without product_name, users cannot track variants like "Lindt 70% Cacao" and "Lindt 85% Cacao" as separate products.

**Independent Test**: Can be fully tested by adding two products with identical brand/size/unit but different product_name values and verifying both are saved successfully.

**Acceptance Scenarios**:

1. **Given** the user is on the Add Product form, **When** they enter brand="Lindt", package_size="3.5 oz", package_unit="oz", and product_name="70% Cacao", **Then** the product is saved successfully
2. **Given** a product exists with brand="Lindt", size="3.5 oz", unit="oz", name="70% Cacao", **When** the user adds another product with the same brand/size/unit but product_name="85% Cacao", **Then** the second product is saved successfully as a distinct record
3. **Given** the Add Product form is displayed, **When** the user views the form fields, **Then** a "Product Name" field appears (optional, can be left blank)

---

### User Story 2 - Migrate Existing Products (Priority: P1)

When the database schema is updated, all existing products must be preserved with product_name set to NULL. The migration must not lose any data and must be reversible.

**Why this priority**: Data integrity during migration is critical. Existing products must continue to work without requiring manual updates.

**Independent Test**: Can be fully tested by exporting current data, applying migration, and verifying all products exist with correct values and product_name=NULL.

**Acceptance Scenarios**:

1. **Given** the database contains 15+ existing products, **When** the migration is applied, **Then** all products are preserved with their original field values
2. **Given** the migration is applied, **When** querying existing products, **Then** product_name is NULL for all pre-existing records
3. **Given** an export was created before migration, **When** comparing pre/post product counts, **Then** the counts match exactly

---

### User Story 3 - Export/Import Products with Product Name (Priority: P2)

When exporting or importing product data, the product_name field must be included. This ensures data portability and backup/restore functionality works with the new field.

**Why this priority**: Import/export is essential for data backup and migration, but is secondary to core CRUD operations.

**Independent Test**: Can be fully tested by exporting products with product_name values, clearing database, importing, and verifying product_name values are restored.

**Acceptance Scenarios**:

1. **Given** products exist with various product_name values (including NULL), **When** exporting to JSON, **Then** the export includes product_name for each product
2. **Given** a JSON file with products containing product_name values, **When** importing, **Then** product_name values are correctly stored
3. **Given** a JSON file from before this feature (no product_name field), **When** importing, **Then** products are imported successfully with product_name=NULL

---

### User Story 4 - Edit Product Name on Existing Products (Priority: P2)

When a user edits an existing product, they can add or modify the product_name field. This allows users to differentiate products that were previously indistinguishable.

**Why this priority**: Editing is important for data correction but is secondary to initial data entry.

**Independent Test**: Can be fully tested by editing an existing product to add a product_name and verifying the change persists.

**Acceptance Scenarios**:

1. **Given** an existing product with product_name=NULL, **When** the user edits it and enters product_name="Original Recipe", **Then** the product_name is saved
2. **Given** an existing product with product_name="70% Cacao", **When** the user edits it to product_name="72% Cacao", **Then** the updated name is saved
3. **Given** the Edit Product form is displayed, **When** viewing the form, **Then** the current product_name value (or empty) is shown in the field

---

### Edge Cases

- What happens when product_name is an empty string vs NULL?
  - Empty strings are treated as NULL for constraint purposes (normalized on save)
- What happens when two products have identical (ingredient_id, brand, NULL, package_size, package_unit)?
  - This is allowed (NULL values are distinct in SQLite unique constraints) but may cause user confusion; UI should warn about potential duplicates
- How does the system handle very long product names?
  - Product name is limited to 200 characters; UI should enforce this limit

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add a `product_name` column (VARCHAR 200, nullable) to the Product table
- **FR-002**: System MUST update the unique constraint to include product_name: `(ingredient_id, brand, product_name, package_size, package_unit)`
- **FR-003**: System MUST preserve all existing products during migration with product_name=NULL
- **FR-004**: UI MUST display a "Product Name" text field in the Add/Edit Product form
- **FR-005**: UI MUST allow product_name to be left blank (optional field)
- **FR-006**: Export functionality MUST include product_name in JSON output for each product
- **FR-007**: Import functionality MUST accept product_name field and store it correctly
- **FR-008**: Import functionality MUST handle JSON files without product_name field (backward compatible, defaults to NULL)
- **FR-009**: System MUST normalize empty string product_name values to NULL on save
- **FR-010**: System MUST block duplicate products with identical (ingredient_id, brand, product_name, package_size, package_unit) when all values are non-NULL

### Key Entities

- **Product**: Extended with `product_name` attribute
  - Represents a variant descriptor within a brand/size combination
  - Examples: "70% Cacao", "Original Recipe", "Extra Virgin", "Unsweetened"
  - Optional (nullable) - many products don't need this level of differentiation
  - Used in display alongside brand (e.g., "Lindt 70% Cacao 3.5 oz")

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 15+ existing products are preserved after migration with product_name=NULL
- **SC-002**: Users can create two products with same brand/size/unit but different product_name values
- **SC-003**: Users cannot create two products with identical (ingredient_id, brand, product_name, package_size, package_unit) when all fields are non-NULL
- **SC-004**: Export/import round-trip preserves product_name values exactly
- **SC-005**: All existing tests continue to pass after implementation
- **SC-006**: Product form clearly shows optional product_name field with appropriate label

## Clarifications

### Session 2025-12-19

- Q: What format should display_name use when product_name is present? → A: "Brand ProductName Size" (e.g., "Lindt 70% Cacao 3.5 oz")

## Assumptions

- SQLite's unique constraint behavior with NULL values is acceptable (two NULLs are considered distinct)
- Product name is a free-form text field (no validation against a predefined list)
- The display_name property on Product will be updated to include product_name when present, using format: "Brand ProductName Size" (e.g., "Lindt 70% Cacao 3.5 oz")
- Migration follows Constitution VI (export/reset/import cycle)

## Out of Scope

- Automatic product name suggestions or autocomplete
- Product name validation against external databases
- Bulk update of existing products to add product_name values
- UI for searching/filtering by product_name (can be added in future feature)
