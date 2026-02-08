# Feature Specification: Auto-Generation of Finished Goods from Finished Units

**Feature Branch**: `098-auto-generation-finished-goods`
**Created**: 2026-02-08
**Status**: Draft
**Input**: See docs/func-spec/F098_auto_generation_finished_goods.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recipe Creation Automatically Creates Selectable Item (Priority: P1)

Baker creates a recipe with EA yield and immediately wants to include it in event planning. Today, the baker must manually create a bare FinishedGood via the builder -- an unnecessary multi-step workflow that's easy to forget.

**Why this priority**: Core value proposition. Eliminates the manual step and ensures all EA-yield recipes immediately produce event-selectable FinishedGoods. Without this, every other story is moot.

**Independent Test**: Create a recipe with EA yield, verify FinishedUnit is created, verify a corresponding bare FinishedGood exists with a single Composition link to that FinishedUnit.

**Acceptance Scenarios**:

1. **Given** a new recipe with EA yield type, **When** recipe is saved, **Then** a FinishedUnit is created AND a bare FinishedGood is auto-created with a single Composition linking to that FinishedUnit
2. **Given** an auto-created bare FinishedGood, **When** querying finished goods, **Then** the new item appears and is distinguishable as a bare (non-assembled) item
3. **Given** a recipe variant created from a base recipe, **When** the variant is saved, **Then** a separate FinishedUnit + bare FinishedGood pair is created for the variant
4. **Given** a recipe with weight-based yield (not EA), **When** the recipe is saved, **Then** no FinishedUnit is created and no FinishedGood is auto-generated

---

### User Story 2 - Recipe Changes Propagate to Finished Good (Priority: P1)

Baker renames a recipe or changes its category and expects the change to appear everywhere automatically, without manually editing the corresponding FinishedGood.

**Why this priority**: Maintains data consistency without manual synchronization burden. Name/category drift between FinishedUnit and FinishedGood causes confusion in event planning.

**Independent Test**: Rename a recipe that has an auto-created bare FinishedGood, verify the FinishedUnit name is updated, verify the FinishedGood name is also updated within the same save operation.

**Acceptance Scenarios**:

1. **Given** an existing recipe with an auto-created bare FinishedGood, **When** the recipe name is changed, **Then** both the FinishedUnit name and the FinishedGood name are updated
2. **Given** a recipe whose category changes, **When** the update is saved, **Then** the FinishedGood category is updated accordingly
3. **Given** multiple recipes with similar names, **When** one is renamed, **Then** only its corresponding FinishedGood is updated (no cross-contamination)

---

### User Story 3 - Deletion Protection for Referenced Items (Priority: P1)

Baker tries to delete a recipe whose atomic FinishedGood is used as a component in assembled bundles. The system must prevent data corruption by blocking the delete and explaining why.

**Why this priority**: Prevents broken references and data corruption. Without this, deleting a recipe could silently orphan assembled FinishedGoods.

**Independent Test**: Create an assembled FinishedGood that uses an atomic FinishedGood as a component, attempt to delete the source recipe, verify deletion is blocked with a clear error listing the affected assemblies.

**Acceptance Scenarios**:

1. **Given** a recipe whose atomic FinishedGood is used in 2 assembled bundles, **When** the user attempts to delete the recipe, **Then** deletion is blocked with a message listing the affected assemblies
2. **Given** a recipe whose atomic FinishedGood is NOT used in any assembly, **When** the user deletes the recipe, **Then** the FinishedUnit, bare FinishedGood, and its Composition record are all deleted (cascade)
3. **Given** an assembled FinishedGood that references a deleted atomic FinishedGood, **When** the user opens the assembly, **Then** an appropriate error is displayed

---

### User Story 4 - Migration of Existing Bare Finished Goods (Priority: P2)

The system converts existing manually-created bare FinishedGoods to auto-managed status, establishing the 1:1 relationship with their FinishedUnits retroactively.

**Why this priority**: Important for data consistency but a one-time operation, not daily workflow. Existing bare FGs created via the builder should become auto-managed going forward.

**Independent Test**: With existing manually-created bare FinishedGoods in the database, run the migration logic, verify all are correctly identified and linked to their corresponding FinishedUnits with user metadata preserved.

**Acceptance Scenarios**:

1. **Given** existing manually-created bare FinishedGoods, **When** migration runs, **Then** each is linked to its corresponding FinishedUnit and marked as bare/atomic
2. **Given** a manually-created bare FinishedGood with user-added notes, **When** migration runs, **Then** notes are preserved
3. **Given** a bare FinishedGood with no corresponding FinishedUnit, **When** migration runs, **Then** the item is flagged for manual review rather than silently skipped

---

### User Story 5 - Bulk Import Handles Auto-Generation (Priority: P3)

Baker imports many recipes from backup. Each EA-yield recipe should auto-create its FinishedUnit + FinishedGood pair without errors or duplicates.

**Why this priority**: Important for data portability but less frequent than daily operations.

**Independent Test**: Import a dataset with many EA-yield recipes, verify all FinishedUnit + FinishedGood pairs are created without duplicates or errors.

**Acceptance Scenarios**:

1. **Given** an import file with 100 EA-yield recipes, **When** import executes, **Then** 100 FinishedUnit + bare FinishedGood pairs are created
2. **Given** a bulk import in progress, **When** one recipe fails validation, **Then** the entire import transaction rolls back (no partial state)
3. **Given** imported recipes with duplicate names, **When** FinishedGoods are auto-created, **Then** names are disambiguated to maintain uniqueness

---

### Edge Cases

- **Name conflicts**: Two recipes produce FinishedUnits with the same name; auto-generated FinishedGood names must remain unique
- **Recipe deleted with dependents**: Cascade must check assembly references before proceeding
- **Category deleted**: FinishedGoods must remain queryable if their category is removed (reassign or null)
- **Manual edit of auto-generated FG**: Decide whether manual overrides are preserved or overwritten on next propagation
- **FinishedUnit without recipe**: Orphaned FinishedUnit should still get a bare FinishedGood
- **Auto-creation triggered but FG already exists**: Skip creation, verify existing FG is bare, log warning
- **Recipe yield type changed from EA to weight**: Existing FinishedUnit + bare FinishedGood should be cleaned up if no longer applicable

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically create a bare FinishedGood whenever a FinishedUnit is created from an EA-yield recipe
- **FR-002**: The auto-created FinishedGood MUST have a single Composition record linking it to the source FinishedUnit
- **FR-003**: The auto-created FinishedGood MUST be marked as bare/non-assembled (distinct from user-built assemblies)
- **FR-004**: Auto-creation MUST be atomic with FinishedUnit creation (same transaction; all succeed or all rollback)
- **FR-005**: System MUST prevent duplicate FinishedGoods for the same FinishedUnit
- **FR-006**: System MUST propagate FinishedUnit name changes to the corresponding bare FinishedGood
- **FR-007**: System MUST propagate FinishedUnit category changes to the corresponding bare FinishedGood
- **FR-008**: Propagation MUST occur within the same transaction as the source update
- **FR-009**: System MUST cascade-delete the bare FinishedGood and its Composition when the FinishedUnit is deleted
- **FR-010**: System MUST block deletion of a FinishedUnit/bare FinishedGood if referenced by any assembled FinishedGood, with a clear error listing the affected assemblies
- **FR-011**: System MUST provide a migration path to convert existing manually-created bare FinishedGoods to auto-managed status
- **FR-012**: Migration MUST preserve user-added metadata (notes, custom attributes) on existing bare FinishedGoods
- **FR-013**: System MUST handle bulk recipe imports by auto-generating bare FinishedGoods for each EA-yield recipe in the batch
- **FR-014**: Bulk operations MUST maintain transactional integrity (all or nothing)
- **FR-015**: The bare FinishedGood MUST inherit its display name and category from the source FinishedUnit at creation time

### Key Entities

- **FinishedUnit**: Atomic building block produced by a recipe with EA yield. Represents a single countable item (e.g., "one loaf of bread", "one batch of cookies").
- **FinishedGood**: Event-selectable item. Bare FinishedGoods have a 1:1 relationship with a FinishedUnit. Assembled FinishedGoods are user-built bundles composed of multiple FinishedUnits and/or materials.
- **Composition**: Polymorphic junction table linking a FinishedGood to its components (FinishedUnits, other FinishedGoods, materials, packaging). For bare FinishedGoods, exactly one Composition record exists linking to the source FinishedUnit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero bare FinishedGoods require manual creation via the builder after implementation; all are auto-generated from FinishedUnits
- **SC-002**: Every FinishedUnit has exactly one corresponding bare FinishedGood, and every bare FinishedGood links to exactly one FinishedUnit (1:1 integrity)
- **SC-003**: When a recipe name or category changes, the corresponding bare FinishedGood reflects the change within the same save operation (100% propagation accuracy)
- **SC-004**: Deleting a recipe that is referenced by assembled FinishedGoods is blocked with a clear, actionable error message listing all affected assemblies
- **SC-005**: Primary user (Marianne) confirms she no longer needs to manually create bare FinishedGoods for recipes and can immediately see new recipes in event planning
