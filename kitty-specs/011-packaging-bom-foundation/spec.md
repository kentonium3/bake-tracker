# Feature Specification: Packaging & BOM Foundation

**Feature Branch**: `011-packaging-bom-foundation`
**Created**: 2025-12-08
**Status**: Draft
**Input**: User description: Add support for packaging materials as trackable inventory items that can be consumed when assembling finished goods and packages

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Packaging Materials to Inventory (Priority: P1)

As a baker, I want to add packaging materials (cookie bags, gift boxes, ribbon) to my inventory so I can track what supplies I have on hand.

**Why this priority**: This is the foundational capability - without being able to track packaging materials as inventory, none of the other features can work. This enables the baker to see all supplies in one place.

**Independent Test**: Can be fully tested by creating a packaging ingredient, adding a product variant, and recording inventory. Delivers immediate value by giving visibility into packaging supply levels.

**Acceptance Scenarios**:

1. **Given** I am on the Ingredients tab, **When** I create a new ingredient with category "Bags" and mark it as packaging, **Then** the ingredient is created with `is_packaging=True` and appears in my ingredient list.
2. **Given** I have a packaging ingredient "Cellophane Cookie Bags", **When** I add a product variant "Brand X - 100 count", **Then** the product is linked to the packaging ingredient and available for inventory tracking.
3. **Given** I have a packaging product, **When** I add it to my inventory with quantity 100, **Then** the inventory item appears in My Pantry alongside food ingredients.
4. **Given** I am viewing My Pantry, **When** I filter or browse inventory, **Then** I can distinguish packaging materials from food ingredients.

---

### User Story 2 - Define Packaging for Finished Goods (Priority: P2)

As a baker, I want to define what packaging is required for each type of finished good (e.g., "Cookie Dozen Bag" requires 1 cellophane bag + 2 twist ties) so the system knows what gets consumed during assembly.

**Why this priority**: This enables the Bill of Materials (BOM) concept for finished goods. Without this, packaging cannot be planned or tracked at the production level.

**Independent Test**: Can be tested by creating a finished good assembly definition and adding packaging requirements. Delivers value by documenting packaging needs per finished good type.

**Acceptance Scenarios**:

1. **Given** I am defining a FinishedGood assembly (e.g., "Cookie Dozen Bag"), **When** I add a packaging component, **Then** I can select from available packaging products and specify a quantity.
2. **Given** a FinishedGood with packaging requirements defined, **When** I view the finished good details, **Then** I see both the recipe components (cookies) and packaging components (bag, twist ties) listed.
3. **Given** a FinishedGood requires "2 ribbon pieces" per unit, **When** I save the assembly definition, **Then** the quantity of 2 is preserved and displayed correctly.
4. **Given** I want to update packaging requirements, **When** I edit the FinishedGood assembly, **Then** I can add, modify, or remove packaging components.

---

### User Story 3 - Define Packaging for Gift Packages (Priority: P2)

As a baker, I want to define what packaging is required for each gift package (e.g., "Holiday Gift Box" requires 1 gift box + tissue paper + a bow) so I can plan my packaging supply needs.

**Why this priority**: Same priority as User Story 2 - both are needed to complete the BOM foundation. Gift packages have their own packaging needs separate from individual finished goods.

**Independent Test**: Can be tested by creating a Package template and adding packaging requirements. Delivers value by documenting packaging needs per package type.

**Acceptance Scenarios**:

1. **Given** I am defining a Package (e.g., "Holiday Gift Box"), **When** I add packaging components, **Then** I can select packaging products and specify quantities for each.
2. **Given** a Package requires outer packaging (box, tissue, bow), **When** I view the package details, **Then** I see both the finished goods contents and the packaging components.
3. **Given** a Package needs "3 sheets tissue paper", **When** I specify quantity 3, **Then** the system stores and displays this variable quantity correctly.
4. **Given** a Package has both finished goods and packaging defined, **When** I view the full BOM, **Then** I see a complete list of all components needed.

---

### User Story 4 - Shopping List Includes Packaging (Priority: P3)

As a baker, I want to see packaging materials on my shopping list when planning an event, alongside food ingredients, so I do not forget to buy supplies.

**Why this priority**: This is the payoff feature - it aggregates all the packaging needs across an event. However, it depends on User Stories 1-3 being complete first.

**Independent Test**: Can be tested by creating an event with packages that have packaging requirements, then viewing the shopping list. Delivers value by ensuring complete supply planning.

**Acceptance Scenarios**:

1. **Given** an event with packages that require packaging materials, **When** I view the event shopping list, **Then** packaging materials appear alongside food ingredients with aggregated quantities needed.
2. **Given** an event needs 10 "Cookie Dozen Bags" (each requiring 1 cellophane bag + 2 twist ties), **When** I view the shopping list, **Then** I see "Cellophane Bags: 10" and "Twist Ties: 20" in the packaging section.
3. **Given** I have some packaging materials in inventory, **When** I view the shopping list, **Then** the "To Buy" quantity reflects what I need minus what I have on hand.
4. **Given** multiple packages in an event use the same packaging product, **When** I view the shopping list, **Then** quantities are aggregated across all packages.

---

### User Story 5 - Import/Export Packaging Data (Priority: P3)

As a baker, I want to export and import my data including packaging materials and their associations so I can back up my data or transfer it between systems.

**Why this priority**: Data portability is important but not critical for initial use. The baker needs to be able to work with packaging before worrying about export/import.

**Independent Test**: Can be tested by exporting data with packaging, then importing into a fresh database. Delivers value by ensuring data safety and portability.

**Acceptance Scenarios**:

1. **Given** I have packaging ingredients, products, and inventory, **When** I export all data, **Then** the export file includes packaging data with the `is_packaging` flag preserved.
2. **Given** I have FinishedGoods with packaging requirements, **When** I export, **Then** the packaging compositions are included in the export.
3. **Given** a valid export file with packaging data, **When** I import into an empty database, **Then** all packaging ingredients, products, inventory, and compositions are restored correctly.
4. **Given** the import file format has changed, **When** I attempt to import old-format data, **Then** the system rejects it with a clear error message indicating format incompatibility.

---

### Edge Cases

- What happens when a packaging product is deleted that is referenced in a FinishedGood or Package composition? (Should block deletion with clear error)
- What happens when viewing a shopping list for an event with no packaging requirements? (Should show only food ingredients, no empty packaging section)
- What happens when a packaging ingredient has no products defined? (Should be allowed - user may just be setting up categories first)
- How does the system handle packaging with fractional quantities like "0.5 yards ribbon"? (Should support decimal quantities)
- What happens when the same packaging product is used in both FinishedGood and Package definitions for the same event? (Should aggregate correctly)

## Requirements *(mandatory)*

### Functional Requirements

**Data Model:**
- **FR-001**: System MUST support marking an Ingredient as packaging material via an `is_packaging` boolean flag (default: false)
- **FR-002**: System MUST support packaging-specific categories: Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, and Other Packaging
- **FR-003**: Packaging ingredients MUST use the existing Ingredient -> Product -> InventoryItem chain (no separate entities)

**Composition Model:**
- **FR-004**: System MUST extend the Composition model to support packaging products as components via a `packaging_product_id` foreign key
- **FR-005**: A Composition row MUST reference exactly one of: FinishedUnit, FinishedGood, OR packaging Product (mutually exclusive)
- **FR-006**: Packaging compositions MUST support variable quantities (decimal values, not limited to 1)
- **FR-007**: System MUST support packaging compositions for both FinishedGood assemblies and Package definitions

**Inventory:**
- **FR-008**: Packaging products MUST be addable to inventory using the same workflow as food ingredients
- **FR-009**: System MUST display packaging inventory alongside food ingredient inventory in My Pantry

**Shopping List:**
- **FR-010**: Event shopping list calculation MUST include packaging materials from all Package definitions in the event
- **FR-011**: Event shopping list calculation MUST include packaging materials from all FinishedGood definitions used in the event
- **FR-012**: Shopping list MUST aggregate packaging quantities across all packages and finished goods in the event
- **FR-013**: Shopping list MUST calculate "To Buy" for packaging by subtracting on-hand inventory from total needed

**Import/Export:**
- **FR-014**: Export MUST include the `is_packaging` flag for all ingredients
- **FR-015**: Export MUST include packaging compositions (FinishedGood and Package packaging requirements)
- **FR-016**: Import MUST restore packaging ingredients, products, inventory, and compositions
- **FR-017**: Import format changes are acceptable; backward compatibility with previous export versions is NOT required

**Referential Integrity:**
- **FR-018**: System MUST prevent deletion of packaging products that are referenced in compositions
- **FR-019**: System MUST cascade delete compositions when a FinishedGood or Package is deleted

### Key Entities

- **Ingredient**: Extended with `is_packaging` boolean flag. Packaging ingredients use sub-categories (Bags, Boxes, Ribbon, etc.) instead of food categories.
- **Product**: Unchanged - represents a specific brand/package of a packaging ingredient (e.g., "Amazon Basics Cellophane Bags - 100 count")
- **InventoryItem**: Unchanged - tracks quantity on hand of a specific packaging product
- **Composition**: Extended with `packaging_product_id` FK. A composition row links a container (FinishedGood or Package) to a component (FinishedUnit, FinishedGood, or packaging Product) with a quantity.
- **FinishedGood**: Unchanged structurally - gains ability to have packaging compositions associated with it
- **Package**: Unchanged structurally - gains ability to have packaging compositions associated with it

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can create, view, edit, and delete packaging ingredients and products within the existing Ingredients workflow
- **SC-002**: User can define packaging requirements for any FinishedGood with variable quantities
- **SC-003**: User can define packaging requirements for any Package with variable quantities
- **SC-004**: Event shopping list displays all required packaging materials with correct aggregated quantities
- **SC-005**: Shopping list "To Buy" calculation correctly accounts for packaging inventory on hand
- **SC-006**: Full data export/import cycle preserves all packaging data without loss
- **SC-007**: All existing tests continue to pass (no regressions)
- **SC-008**: New packaging functionality has test coverage for service layer methods

## Assumptions

- Packaging categories (Bags, Boxes, Ribbon, Labels, Tissue Paper, Wrapping, Other Packaging) are sufficient for initial release; additional categories can be added later
- The existing Composition model's `quantity` field supports decimal values (if not, this will need migration)
- UI changes for defining packaging on FinishedGoods and Packages can reuse existing composition editing patterns
- FIFO consumption of packaging materials will be handled in Feature 012 (out of scope for this feature)

## Out of Scope

- Recording actual consumption when production occurs (Feature 012)
- BATCH entity and production runs (Feature 012)
- Production recording UI (Feature 013)
- Inventory depletion on assembly (Feature 012)
- Three-tier inventory views (raw/atomic/assembled) (Feature 012/013)
- Cost tracking for packaging materials (future enhancement)

## Dependencies

- TD-001 Schema Cleanup: COMPLETE
- Reference: `docs/workflow-refactoring-spec.md` - Full workflow gap analysis
- Reference: `docs/design/schema_v0.5_design.md` - Current schema design
