# Feature Specification: Finished Goods Catalog UI

**Feature Branch**: `088-finished-goods-catalog-ui`
**Created**: 2026-01-30
**Status**: Draft
**Input**: F088 func-spec (docs/func-spec/F088_finished_goods_creation_ux.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Finished Goods Catalog (Priority: P1)

As a user (Marianne), I want to see all my FinishedGoods in a searchable list so I can browse and manage my assembled product catalog.

**Why this priority**: Foundation for all other interactions - users must be able to see what exists before creating or editing.

**Independent Test**: Can be fully tested by opening Catalog mode, selecting Finished Goods tab, and verifying the list displays with search/filter working.

**Acceptance Scenarios**:

1. **Given** the user is in Catalog mode, **When** they click the Finished Goods tab, **Then** they see a list of all FinishedGoods with columns: Name, Assembly Type, Component Count, Notes (truncated)
2. **Given** the Finished Goods tab is active, **When** the user types in the search field, **Then** the list filters to show only matching items
3. **Given** the Finished Goods tab is active, **When** the user selects an Assembly Type filter, **Then** the list shows only items of that type
4. **Given** no FinishedGoods exist, **When** the user views the tab, **Then** they see a helpful empty state message

---

### User Story 2 - Create Simple FinishedGood with Foods (Priority: P1)

As a user, I want to create a FinishedGood by selecting foods (FinishedUnits) with quantities so I can define assembled products like "Biscotti Variety Bag".

**Why this priority**: Core creation flow - without this, the feature has no value. Foods are the most common component type.

**Independent Test**: Can be tested by creating a new FinishedGood, adding 2-3 foods with quantities, saving, and verifying it appears in the list.

**Acceptance Scenarios**:

1. **Given** the user clicks "Create New", **When** the form opens, **Then** they see sections for Basic Info, Foods, Materials, and Components
2. **Given** the user is in the Foods section, **When** they click "Add Food", **Then** they see a selection UI with category filter and search
3. **Given** the user selects a food and enters quantity, **When** they click Add, **Then** the food appears in the Foods list with correct quantity
4. **Given** the user has added foods and filled basic info, **When** they click Save, **Then** the FinishedGood is created and appears in the list

---

### User Story 3 - Add Materials to FinishedGood (Priority: P2)

As a user, I want to add materials (MaterialUnits) to my FinishedGood so I can include packaging items like bags, ribbons, and boxes.

**Why this priority**: Completes the assembly model - most real products need packaging materials.

**Independent Test**: Can be tested by creating a FinishedGood, adding a material (e.g., ribbon, bag), saving, and verifying materials are persisted.

**Acceptance Scenarios**:

1. **Given** the user is in the Materials section, **When** they click "Add Material", **Then** they see a selection UI with category filter (Material hierarchy) and search
2. **Given** the user selects a material and enters quantity, **When** they click Add, **Then** the material appears in the Materials list showing Name, Product, Quantity
3. **Given** the user saves a FinishedGood with materials, **When** they edit it later, **Then** all materials are still present with correct quantities

---

### User Story 4 - Nest FinishedGoods as Components (Priority: P2)

As a user, I want to add other FinishedGoods as components so I can create hierarchical assemblies like "Gift Box containing Variety Bag".

**Why this priority**: Enables complex product definitions - critical for gift boxes and combo packages.

**Independent Test**: Can be tested by creating a simple FinishedGood first, then creating another that includes the first as a component.

**Acceptance Scenarios**:

1. **Given** the user is in the Components section, **When** they click "Add Component", **Then** they see a selection UI with Assembly Type filter and search
2. **Given** the user tries to add the current FinishedGood to itself, **Then** they see an error preventing circular reference
3. **Given** FinishedGood A contains B, **When** editing B and trying to add A, **Then** the system prevents the circular reference with clear error message
4. **Given** the user adds nested components, **When** they save, **Then** all component relationships are persisted correctly

---

### User Story 5 - Edit Existing FinishedGood (Priority: P2)

As a user, I want to edit an existing FinishedGood to modify its components so I can update product definitions as my catalog evolves.

**Why this priority**: Essential for catalog maintenance - products change over time.

**Independent Test**: Can be tested by selecting a FinishedGood, clicking Edit, modifying components, saving, and verifying changes persist.

**Acceptance Scenarios**:

1. **Given** the user selects a FinishedGood in the list, **When** they click Edit (or double-click), **Then** the form opens with all current data populated
2. **Given** the user modifies the name or assembly type, **When** they save, **Then** the changes are reflected in the list
3. **Given** the user removes a component, **When** they save, **Then** the component is no longer associated with the FinishedGood
4. **Given** the user adds new components, **When** they save, **Then** the new components are persisted alongside existing ones

---

### User Story 6 - Delete FinishedGood with Safety Checks (Priority: P3)

As a user, I want to delete FinishedGoods I no longer need, but be prevented from deleting ones that are in use.

**Why this priority**: Catalog cleanup is lower priority but necessary for long-term maintenance.

**Independent Test**: Can be tested by deleting an unused FinishedGood successfully, then attempting to delete one referenced by another.

**Acceptance Scenarios**:

1. **Given** the user selects an unused FinishedGood, **When** they click Delete and confirm, **Then** the FinishedGood is removed from the catalog
2. **Given** the user selects a FinishedGood that is a component of another, **When** they click Delete, **Then** they see an error explaining what references it
3. **Given** the user selects a FinishedGood used in event planning, **When** they click Delete, **Then** they see an error explaining where it's used

---

### Edge Cases

- What happens when a user tries to save with zero components? → System requires at least one component (food, material, or nested FinishedGood)
- How does system handle very long component lists (50+ items)? → Scrollable list with search/filter to manage large selections
- What if a FinishedUnit or MaterialUnit is deleted after being added to a FinishedGood? → Cascade rules prevent orphaned references; deletion blocked if in use
- What if user cancels mid-edit? → Changes discarded, original data preserved

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a Finished Goods tab in Catalog mode following F087 layout pattern (3-row: controls, actions, grid)
- **FR-002**: System MUST use ttk.Treeview for the list view with trackpad scrolling support
- **FR-003**: System MUST provide search and filter controls for the list view
- **FR-004**: System MUST allow creation of new FinishedGoods via a create form
- **FR-005**: System MUST allow editing of existing FinishedGoods via an edit form
- **FR-006**: System MUST support adding FinishedUnits (foods) to a FinishedGood with quantities
- **FR-007**: System MUST support adding MaterialUnits (materials) to a FinishedGood with quantities
- **FR-008**: System MUST support adding other FinishedGoods (components) for hierarchical assemblies
- **FR-009**: System MUST validate that at least one component exists before saving
- **FR-010**: System MUST prevent circular references in nested FinishedGoods
- **FR-011**: System MUST provide category filter + type-ahead search for component selection
- **FR-012**: System MUST allow deletion of FinishedGoods with confirmation dialog
- **FR-013**: System MUST prevent deletion of FinishedGoods that are referenced by other FinishedGoods or events
- **FR-014**: System MUST save FinishedGood and all components atomically (all-or-nothing)
- **FR-015**: System MUST auto-generate slug from name on creation

### Key Entities

- **FinishedGood**: An assembled product containing foods, materials, and/or other finished goods. Key attributes: name, slug, assembly_type, packaging_instructions, notes
- **Composition**: Junction entity linking FinishedGood to its components (FinishedUnits, MaterialUnits, or nested FinishedGoods) with quantity and sort order
- **FinishedUnit**: A yield type from a Recipe (e.g., "Almond Biscotti - 30 cookies/batch")
- **MaterialUnit**: A product-specific material definition (e.g., "12-inch red ribbon")

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a new FinishedGood with 3+ components in under 2 minutes
- **SC-002**: Users can find any FinishedGood using search in under 5 seconds
- **SC-003**: All CRUD operations complete without error when following valid workflows
- **SC-004**: Circular reference validation catches 100% of invalid nesting attempts
- **SC-005**: Service layer tests achieve >80% coverage for create/update/delete operations
- **SC-006**: UI follows F087 pattern exactly (verified by visual inspection against other catalog tabs)
- **SC-007**: Real user (Marianne) can define her actual product catalog (Biscotti Variety Bag, Gift Boxes, etc.)

## Assumptions

- FinishedGood and Composition models already exist in the schema (no schema changes needed)
- The F087 pattern is established and can be followed for consistency
- MaterialUnit model is available from F085
- Existing finished_good_service.py provides foundation for CRUD operations
- Composition factory methods exist for creating component relationships
