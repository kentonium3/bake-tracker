# Feature Specification: Finished Goods Builder UI

**Feature Branch**: `097-finished-goods-builder-ui`
**Created**: 2026-02-06
**Status**: Draft
**Input**: Func spec F097 + paper prototype validation + discovery interview

## User Scenarios & Testing

### User Story 1 - Create Mixed Bundle (Priority: P1)

Baker creates a composite FinishedGood containing multiple food items with different quantities and optional packaging materials, using a guided 3-step accordion workflow.

**Why this priority**: Core value proposition. Mixed bundles (assorted biscotti bags, cookie variety boxes) are currently impossible to create. Directly addresses the validated user need from paper prototype testing.

**Independent Test**: Can be fully tested by creating a 3-item biscotti bundle with 2 materials and verifying all 5 components save correctly with proper quantities and relationships.

**Acceptance Scenarios**:

1. **Given** Catalog > Finished Goods tab is open, **When** user clicks "+ Create Finished Good", **Then** builder dialog opens with Step 1 (Food Selection) expanded and Steps 2-3 collapsed/greyed out
2. **Given** Step 1 is expanded, **When** user selects "Cookies" category and checks "Bare items only", **Then** only bare cookie FinishedUnits display (no manually-created assemblies)
3. **Given** bare cookie items displayed, **When** user checks "Almond Biscotti" (qty 6), "Hazelnut Biscotti" (qty 4), "Chocolate-Dipped Biscotti" (qty 2) and clicks Continue, **Then** Step 1 collapses showing checkmark + "3 items selected", Step 2 expands
4. **Given** Step 2 (Materials) is expanded, **When** user selects "Cellophane Bag" (qty 1) and "Ribbon" (qty 1) and clicks Continue, **Then** Step 2 collapses with checkmark + "2 materials selected", Step 3 expands
5. **Given** Step 3 (Review) shows summary of all 5 components with quantities, **When** user enters name "Assorted Biscotti Gift Bag" and clicks Save, **Then** FinishedGood saves with all 5 components atomically, dialog closes, Finished Goods list refreshes showing the new item

---

### User Story 2 - Filter and Search (Priority: P1)

Baker finds specific items quickly using category filters, bare/assembly toggles, and search when item lists are long.

**Why this priority**: Essential for usability with large catalogs. Paper prototype identified this as a critical pain point — without filtering, lists become overwhelming.

**Independent Test**: Can be tested with 50+ items in the catalog by verifying that category filter + search reduces list to a manageable subset within 2 keystrokes.

**Acceptance Scenarios**:

1. **Given** 100+ FinishedUnits exist across categories, **When** user selects "Cakes" category in Step 1, **Then** only cake items display
2. **Given** "Cakes" category selected with 20 items, **When** user types "choc" in search box, **Then** only chocolate-related cakes display
3. **Given** "Bare items only" active, **When** user toggles "Include assemblies", **Then** previously-created composite FinishedGoods appear alongside bare items
4. **Given** items filtered by category, **When** user checks items and then changes category filter, **Then** previously checked items from other categories remain selected (selections are global, not per-filter-view)
5. **Given** Step 2 (Materials) expanded, **When** user selects a MaterialCategory, **Then** only materials in that category display

---

### User Story 3 - Edit Existing FinishedGood (Priority: P1)

Baker opens an existing FinishedGood in the builder to modify its components, quantities, name, or other attributes.

**Why this priority**: Essential for iterating on bundle compositions. Without edit, users must delete and recreate to make any changes — unacceptable workflow friction.

**Independent Test**: Can be tested by creating a FinishedGood, reopening it in the builder, changing a quantity, saving, and verifying the update persisted.

**Acceptance Scenarios**:

1. **Given** Finished Goods list with existing items, **When** user double-clicks a FinishedGood, **Then** builder dialog opens in edit mode with all steps pre-populated from existing component data
2. **Given** Finished Goods list with an item selected/highlighted, **When** user clicks "Edit" button, **Then** builder dialog opens in edit mode with that item's data pre-populated
3. **Given** builder open in edit mode with Step 1 showing existing food selections, **When** user adds a new food item (qty 3) and clicks Continue, **Then** the new item appears alongside existing selections
4. **Given** builder open in edit mode, **When** user removes a previously-saved component by unchecking it and saves, **Then** the removed component is deleted from the database and remaining components are preserved
5. **Given** builder open in edit mode on Step 3 (Review), **When** user changes the name and clicks Save, **Then** the existing FinishedGood record is updated (not duplicated) with the new name and any component changes

---

### User Story 4 - Navigate and Edit Previous Steps (Priority: P2)

Baker realizes they need to change selections or quantities after progressing to a later step in the wizard.

**Why this priority**: Important for workflow flexibility. Users naturally change their minds during the building process.

**Independent Test**: Can be tested by completing Steps 1 and 2, clicking "Change" on Step 1, modifying a quantity, proceeding back through, and verifying the change persists to the Review step.

**Acceptance Scenarios**:

1. **Given** Step 3 (Review) is displayed, **When** user clicks "Change" on Step 1's collapsed summary, **Then** Step 1 expands with all previous selections intact and editable, Step 3 collapses
2. **Given** Step 1 re-expanded, **When** user changes biscotti quantity from 6 to 8 and clicks Continue, **Then** Step 3 summary reflects the updated quantity
3. **Given** Step 2 complete, **When** user clicks "Change" on Step 2 and adds another material, **Then** Step 3 summary includes the new material

---

### User Story 5 - Skip Materials Step (Priority: P2)

Baker creates a food-only bundle without any packaging materials (e.g., a variety box that goes into the customer's own container).

**Why this priority**: Valid use case for food-only bundles. Materials should not be forced when they aren't needed.

**Independent Test**: Can be tested by creating a FinishedGood with only food items, skipping materials, and verifying it saves with zero material components.

**Acceptance Scenarios**:

1. **Given** Step 2 (Materials) is expanded, **When** user clicks "Skip" without selecting any materials, **Then** Step 2 collapses with "No materials" summary, Step 3 expands
2. **Given** Step 3 displays food-only summary, **When** user clicks Save, **Then** FinishedGood saves with only food components (no material components)
3. **Given** editing a FinishedGood that previously had materials, **When** user unchecks all materials and saves, **Then** all material components are removed from the FinishedGood

---

### User Story 6 - Start Over (Priority: P3)

Baker decides to discard current progress and start fresh within the same dialog session.

**Why this priority**: Convenience feature. User can work around this by canceling and relaunching the dialog.

**Independent Test**: Can be tested by making selections in all steps, clicking "Start Over", and verifying all state is cleared with Step 1 re-expanded.

**Acceptance Scenarios**:

1. **Given** Step 3 with selections made across all steps, **When** user clicks "Start Over", **Then** all steps reset to initial state, Step 1 expands empty, all selections cleared
2. **Given** fresh state after "Start Over", **When** user begins making new selections, **Then** no previous selections reappear

---

### Edge Cases

- **Empty category**: User selects a category with no available items. System displays "No items in this category" message. Continue button disabled.
- **Duplicate name**: User tries to save a FinishedGood with a name that already exists. System shows error "A Finished Good with this name already exists" and keeps the dialog open for correction. In edit mode, the current item's own name is excluded from the uniqueness check.
- **Very long names**: Item names exceeding display width are truncated with ellipsis; full name shown on hover tooltip.
- **Zero or blank quantity**: User checks an item but leaves quantity blank or enters 0. Item is treated as unchecked and excluded from save. Only components with quantity >= 1 are persisted.
- **Cancel with unsaved changes**: User clicks Cancel (or X) after making any selections or changes. Confirmation dialog asks "Discard unsaved changes?" with "Discard" and "Keep Editing" options.
- **Navigation during edit**: User clicks "Change" on Step 1 while viewing Step 3. Step 3 collapses, Step 1 expands with all selections preserved.
- **Edit mode — deleted components**: In edit mode, if a component's source entity (FinishedUnit or MaterialProduct) has been deleted since the FinishedGood was created, that component is shown as "(unavailable)" in the review and excluded from save.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a dedicated modal builder dialog for creating FinishedGoods, launched from "+ Create Finished Good" button on the Finished Goods tab
- **FR-002**: System MUST support opening existing FinishedGoods in the same builder dialog for editing, launched by double-clicking a list item or selecting an item and clicking "Edit"
- **FR-003**: Builder dialog MUST implement a 3-step accordion workflow: Food Selection (Step 1) → Materials (Step 2) → Review & Save (Step 3)
- **FR-004**: Only one accordion step MUST be expanded at a time; completed steps collapse showing a checkmark and selection summary
- **FR-005**: Step 1 (Food Selection) MUST display available FinishedUnits and FinishedGoods with multi-select checkboxes and per-item quantity fields (range 1-999)
- **FR-006**: Step 1 MUST provide category filtering using existing ProductCategory, a "Bare items only" toggle (showing only auto-created items from recipes), an "Include assemblies" toggle (showing manually-created FinishedGoods), and a text search field
- **FR-007**: Step 1 MUST validate that at least 1 food item is selected with quantity >= 1 before allowing progression to Step 2
- **FR-008**: Step 2 (Materials) MUST display available MaterialProducts with multi-select checkboxes, per-item quantity fields, MaterialCategory filtering, and text search
- **FR-009**: Step 2 MUST be skippable — materials are optional for FinishedGoods that contain only food components
- **FR-010**: Step 3 (Review) MUST display a complete summary of all selected components with quantities, an editable name field, auto-suggested tags from component names, and a notes field
- **FR-011**: Save action MUST create or update the FinishedGood record and all FinishedGoodComponent records atomically in a single transaction
- **FR-012**: In edit mode, builder MUST pre-populate all steps with the existing FinishedGood's component data, name, tags, and notes
- **FR-013**: In edit mode, save MUST update the existing record (not create a duplicate) and handle added, modified, and removed components
- **FR-014**: Users MUST be able to navigate back to any completed step via a "Change" button to modify selections, with all state preserved
- **FR-015**: Cancel or close with unsaved changes MUST prompt for confirmation before discarding
- **FR-016**: Successful save MUST close the dialog and refresh the Finished Goods list to reflect the new or updated item
- **FR-017**: Name uniqueness MUST be validated before save, with the current item's name excluded during edit mode

### Key Entities

- **FinishedGood**: A composite product built from food components and/or materials. Has a name, optional tags, optional notes, and a collection of components. Can be nested (a FinishedGood containing other FinishedGoods).
- **FinishedGoodComponent**: Junction record linking a FinishedGood to one of its components. Stores component type (FinishedUnit, FinishedGood, or MaterialProduct), a reference to the component entity, and a quantity.
- **FinishedUnit**: A single finished food item produced from a recipe (e.g., "Almond Biscotti"). Bare items are auto-created from recipes with EA yield.
- **MaterialProduct**: A non-food item used in packaging or presentation (e.g., cellophane bag, ribbon, box). Categorized by MaterialCategory.
- **ProductCategory**: Category taxonomy for food items, used for filtering in Step 1.
- **MaterialCategory**: Category taxonomy for materials, used for filtering in Step 2.

## Success Criteria

### Measurable Outcomes

- **SC-001**: User can build a mixed bundle (e.g., assorted biscotti bag with 3 food types + 2 materials) from start to save in under 3 minutes
- **SC-002**: User can open an existing FinishedGood, modify component quantities, and save the update in under 1 minute
- **SC-003**: Category filter reduces visible items to the relevant subset; search narrows results within 2 keystrokes of typing
- **SC-004**: User can select and configure 5+ components without confusion; quantities are editable inline without requiring a separate dialog
- **SC-005**: Primary user (Marianne) completes 3 test scenarios successfully — (1) create assorted biscotti bag, (2) create cookie variety box, (3) edit an existing bundle to add a component — with zero critical issues
- **SC-006**: All FinishedGoodComponents save with correct quantities and foreign key relationships; no orphaned components or missing relationships after create, edit, or component removal
