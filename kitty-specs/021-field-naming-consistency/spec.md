# Feature Specification: Field Naming Consistency Refactor

**Feature Branch**: `021-field-naming-consistency`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: Rename purchase_unit/purchase_quantity to package_unit/package_unit_quantity on Product model; standardize internal "pantry" references to "inventory" while preserving user-facing "Pantry" labels.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Maintains Consistent Codebase (Priority: P1)

A developer working on the bake-tracker codebase can understand and navigate the code without confusion from inconsistent terminology. When they see `package_unit` on the Product model, they understand it describes the package contents (not a purchase transaction). When they see `InventoryItem` in code, they understand it maps to the user-facing "Pantry" concept.

**Why this priority**: This is the core value of the refactor - reducing cognitive load and preventing bugs caused by misleading names.

**Independent Test**: Can be fully tested by grep/search for old terminology confirming zero matches in internal code.

**Acceptance Scenarios**:

1. **Given** the refactored codebase, **When** a developer searches for `purchase_unit` or `purchase_quantity`, **Then** no matches are found in Python code (only in comments explaining the change if any)
2. **Given** the refactored codebase, **When** a developer searches for `pantry` (case-insensitive) in models, services, database tables, or variable names, **Then** no matches are found in internal code (only in UI display strings and comments)
3. **Given** the refactored codebase, **When** a developer reads the Product model, **Then** they see `package_unit` and `package_unit_quantity` fields with clear semantics

---

### User Story 2 - User Sees Familiar "Pantry" Labels (Priority: P1)

The application user continues to see "Pantry" in the UI (tab names, form labels, buttons) because this is the domain-appropriate term they understand. The internal rename to "inventory" is invisible to them.

**Why this priority**: Equal priority to P1 because user experience must not regress - this is a refactor, not a UX change.

**Independent Test**: Can be tested by manually inspecting the UI or running the application and verifying all user-facing text still says "Pantry" where it did before.

**Acceptance Scenarios**:

1. **Given** the refactored application, **When** the user opens the main window, **Then** they see a "Pantry" tab (not "Inventory")
2. **Given** the refactored application, **When** the user interacts with pantry-related forms, **Then** all labels, buttons, and messages use "Pantry" terminology

---

### User Story 3 - Data Preserved Through Export/Import Cycle (Priority: P1)

Existing user data is fully preserved through the export/reset/import workflow required by Constitution v1.2.0. No data is lost, and all relationships remain intact.

**Why this priority**: Data integrity is non-negotiable per Constitution principles.

**Independent Test**: Can be tested by exporting before refactor, applying schema changes, importing, and verifying record counts and data integrity.

**Acceptance Scenarios**:

1. **Given** an existing database with data, **When** the user exports data before the refactor, **Then** all records are captured in the export file
2. **Given** exported data and the new schema, **When** the user imports into the fresh database, **Then** all records are restored with correct relationships
3. **Given** the import completes, **When** record counts are compared, **Then** counts match exactly (ingredients, products, inventory items, recipes, etc.)

---

### User Story 4 - Import/Export Uses Consistent Field Names (Priority: P2)

The import/export JSON format uses field names that match the internal model names, eliminating any aliasing or translation logic in the import/export code.

**Why this priority**: Secondary to core functionality but important for maintainability.

**Independent Test**: Can be tested by examining export JSON and verifying field names match model attributes.

**Acceptance Scenarios**:

1. **Given** the import/export specification, **When** updated to v3.4, **Then** it documents `package_unit` and `package_unit_quantity` for products (already present, confirm no aliasing needed)
2. **Given** the refactored export service, **When** data is exported, **Then** JSON field names match SQLAlchemy model attribute names directly

---

### User Story 5 - All Tests Pass After Refactor (Priority: P2)

The existing test suite passes completely after the refactor, confirming no regressions in business logic.

**Why this priority**: Tests validate that the refactor is purely cosmetic with no functional changes.

**Independent Test**: Run `pytest src/tests -v` and verify all tests pass.

**Acceptance Scenarios**:

1. **Given** the completed refactor, **When** the full test suite runs, **Then** all tests pass
2. **Given** any test that referenced old names, **When** tests are updated, **Then** they use new names and still validate the same behavior

---

### Edge Cases

- **Mixed terminology in comments**: Comments explaining the historical change are acceptable and expected
- **Third-party or generated code**: Any auto-generated code must also be updated if it contains old terminology
- **Case sensitivity**: Searches must be case-insensitive to catch `Pantry`, `PANTRY`, `pantry` variations
- **Partial matches**: Search must catch variations like `PantryItem`, `pantry_item`, `pantry_items`, `get_pantry`, etc.
- **Import files with old names**: Not supported - users must update their import files to new field names (no backward compatibility)

## Requirements *(mandatory)*

### Functional Requirements

#### Package Terminology (Product Model)

- **FR-001**: System MUST rename `purchase_unit` column to `package_unit` in the Product database table
- **FR-002**: System MUST rename `purchase_quantity` column to `package_unit_quantity` in the Product database table
- **FR-003**: System MUST update the SQLAlchemy Product model to use `package_unit` and `package_unit_quantity` attribute names
- **FR-004**: System MUST update all service layer code that references `purchase_unit` or `purchase_quantity`
- **FR-005**: System MUST update all test code that references `purchase_unit` or `purchase_quantity`

#### Inventory Terminology (Internal Code)

- **FR-006**: System MUST rename `pantry_items` database table to `inventory_items`
- **FR-007**: System MUST rename `PantryItem` SQLAlchemy model class to `InventoryItem`
- **FR-008**: System MUST rename `pantry_item_service.py` to `inventory_item_service.py`
- **FR-009**: System MUST rename all service class names from `PantryItem*` to `InventoryItem*`
- **FR-010**: System MUST update all service method names containing `pantry` to use `inventory`
- **FR-011**: System MUST update all variable names in services containing `pantry` to use `inventory`
- **FR-012**: System MUST update all model relationship names containing `pantry` to use `inventory`
- **FR-013**: System MUST update all test files and test code referencing `pantry` to use `inventory`
- **FR-014**: System MUST update UI code variable names (not user-facing labels) from `pantry` to `inventory`

#### User-Facing Labels (MUST NOT Change)

- **FR-015**: System MUST preserve "Pantry" in all user-facing UI text (tab names, form labels, button text, messages)
- **FR-016**: System MUST NOT change any string literals displayed to users from "Pantry" to "Inventory"

#### Import/Export

- **FR-017**: System MUST update import/export specification to version 3.4
- **FR-018**: System MUST ensure import/export code uses new field names without aliasing
- **FR-019**: System MUST document the field name changes in the v3.4 changelog

#### Data Migration

- **FR-020**: System MUST use export/reset/import workflow per Constitution v1.2.0 (no SQL migration scripts)
- **FR-021**: System MUST validate data integrity after import (record counts, relationships)

#### Documentation

- **FR-022**: System MUST update technical documentation referencing old field/class names
- **FR-023**: System MUST NOT change user-facing documentation that uses "Pantry" terminology

### Key Entities

- **Product**: Brand-specific product with `package_unit` (unit of measure) and `package_unit_quantity` (amount in package)
- **InventoryItem** (formerly PantryItem): FIFO lot tracking current inventory quantities by product
- **Import/Export Specification**: JSON format documentation at v3.4

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero matches for `purchase_unit` or `purchase_quantity` in Python source files (excluding comments)
- **SC-002**: Zero matches for `pantry` (case-insensitive) in model class names, database table names, service file names, service class names, or variable names
- **SC-003**: All existing tests pass (100% pass rate)
- **SC-004**: User-facing UI displays "Pantry" in all locations where it appeared before the refactor
- **SC-005**: Round-trip export/import preserves 100% of data (zero data loss)
- **SC-006**: Import/export specification updated to v3.4 with documented field changes

## Assumptions

- The import/export spec v3.3 already uses `package_unit`/`package_unit_quantity` and `inventory_items` in JSON - this feature aligns internal code to match (eliminating aliasing)
- The user has a working export capability to backup data before schema reset
- No third-party integrations depend on the internal field names
- Comments explaining historical context (e.g., "formerly purchase_unit") are acceptable

## Out of Scope

- Functional changes to business logic
- New features or capabilities
- Changing user-facing "Pantry" labels to "Inventory"
- Backward compatibility for import files with old field names
- Performance optimizations
- UI redesign
