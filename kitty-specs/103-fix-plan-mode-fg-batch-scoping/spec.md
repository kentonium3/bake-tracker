# Feature Specification: Fix Plan Mode FG and Batch Scoping

**Feature Branch**: `103-fix-plan-mode-fg-batch-scoping`
**Created**: 2026-03-15
**Status**: Draft
**Input**: Bug report from user testing of Plan mode with Easter 2026 event

## User Scenarios & Testing

### User Story 1 - Finished Goods Appear for Selected Recipes (Priority: P1)

A planner selects multiple recipes for an event (e.g., Easter 2026). When they navigate to the Finished Goods selection section, they see all finished units belonging to the recipes they selected. Each recipe's finished units appear regardless of whether other recipes are also selected -- the only requirement is that the finished unit's parent recipe is among the event's selected recipes.

**Why this priority**: This is the core planning workflow. Without seeing the correct finished goods, the planner cannot set production quantities or proceed to batch planning.

**Independent Test**: Select 3 recipes for an event. Verify that all finished units from those 3 recipes appear in the FG selection list. Deselect 1 recipe and verify its finished units disappear.

**Acceptance Scenarios**:

1. **Given** an event with recipes A, B, and C selected, **When** the user views the Finished Goods selection, **Then** all finished units from recipes A, B, and C are listed.
2. **Given** an event with recipe A selected (recipe A has 2 finished units), **When** the user views the Finished Goods selection, **Then** both finished units from recipe A are listed.
3. **Given** an event with no recipes selected, **When** the user views the Finished Goods selection, **Then** no finished units are listed and the placeholder message is shown.
4. **Given** an event with recipes selected, **When** the user applies the Recipe Category filter, **Then** only finished units from recipes matching that category are shown.

---

### User Story 2 - Batch Options Reflect Current Recipe Selections (Priority: P1)

A planner who previously selected finished goods and set quantities sees batch options only for recipes that are currently selected for the event. If a recipe was deselected after its finished goods were added, those finished goods and their batch options no longer appear in the Batch Options section.

**Why this priority**: Stale batch options showing unrelated recipes (e.g., "Pecan Shortbread Christmas Tree" for Easter 2026) cause confusion and undermine trust in the planning workflow.

**Independent Test**: Select recipe A, choose its FG, set a quantity. Then deselect recipe A from the event. Navigate to Batch Options and verify recipe A's batch does not appear.

**Acceptance Scenarios**:

1. **Given** an event with recipes A and B selected and their FGs saved with quantities, **When** the user views Batch Options, **Then** only batches for recipes A and B appear.
2. **Given** an event where recipe A was previously selected and its FG saved, **When** recipe A is deselected from the event, **Then** batch options for recipe A no longer appear.
3. **Given** an event with no recipes selected, **When** the user views Batch Options, **Then** no batch options are shown.

---

### User Story 3 - Stale FG Records Are Cleaned Up (Priority: P2)

When a recipe is deselected from an event, any EventFinishedGood records associated with that recipe's finished units are cleaned up so they do not pollute downstream calculations (batch options, shopping lists, cost estimates).

**Why this priority**: Without cleanup, stale records accumulate and cause cascading errors in batch decomposition and other planning calculations. This is the root cause of Issue 3.

**Independent Test**: Select recipe A, choose its FG, save. Deselect recipe A. Verify EventFinishedGood records for recipe A's FGs are removed or excluded from queries.

**Acceptance Scenarios**:

1. **Given** an event with recipe A's FG saved in EventFinishedGood, **When** recipe A is deselected from the event, **Then** EventFinishedGood records for recipe A's finished units are removed or filtered out of all downstream queries.
2. **Given** stale EventFinishedGood records exist, **When** batch options are calculated, **Then** only records for currently-selected recipes are included.

---

### Edge Cases

- What happens when a recipe is deselected and re-selected? Its finished units should reappear in the FG selection (fresh, without previously saved quantities).
- What happens when all recipes are deselected? FG selection and batch options should both be empty with appropriate placeholder messages.
- What happens with finished units that have no parent recipe (orphaned data)? They should not appear in the planning FG list.
- At this planning stage, assemblies/compositions are out of scope. Only finished units directly tied to recipes should appear. Assemblies are planned after component production.

## Requirements

### Functional Requirements

- **FR-001**: The Finished Goods selection list MUST show all finished units whose parent recipe is among the event's currently selected recipes.
- **FR-002**: The Finished Goods selection list MUST NOT require all component recipes of a composition to be selected -- at this planning stage, only simple recipe-to-finished-unit relationships are relevant.
- **FR-003**: The Batch Options section MUST only display batch options for recipes that are currently selected for the event.
- **FR-004**: When a recipe is deselected from an event, EventFinishedGood records for that recipe's finished units MUST be removed or excluded from all downstream planning queries (batch decomposition, shopping lists, etc.).
- **FR-005**: The FG selection category filter MUST continue to show all canonical recipe categories (fixed in prior commit, must not regress).
- **FR-006**: The FG selection filters MUST default to "All Categories", "All Types", "All Yields" (fixed in prior commit, must not regress).

### Key Entities

- **Recipe**: A recipe selected for an event via EventRecipe.
- **FinishedUnit**: A yield type belonging to a recipe (e.g., "Hot Cross Bun" from "Hot Cross Buns" recipe). Related to Recipe via `recipe_id` FK.
- **EventRecipe**: Junction table linking an event to its selected recipes.
- **EventFinishedGood**: Junction table linking an event to selected finished goods with planned quantities. Can become stale if its recipe is deselected.
- **Batch Options**: Calculated from EventFinishedGood records via planning_service.decompose_event_to_fu_requirements(). Must be scoped to current recipe selections.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All finished units for selected recipes appear in the FG selection list within 1 second of navigating to the section.
- **SC-002**: Deselecting a recipe causes its finished units to disappear from the FG selection list on the next view refresh.
- **SC-003**: Batch Options section shows zero batches for deselected recipes.
- **SC-004**: No stale EventFinishedGood records influence batch decomposition after their parent recipe is deselected.
- **SC-005**: Existing tests for planning workflow continue to pass (no regressions).

## Assumptions

- At this planning stage, only simple recipe-to-finished-unit relationships are relevant. Assemblies/compositions are planned in a later stage after component production.
- The "available finished goods" concept (all component recipes must be selected) may still be useful for assembly planning in a future feature, but is incorrect for the current recipe-based FG selection.
- Cleanup of stale EventFinishedGood records can happen either eagerly (on recipe deselection) or lazily (filtered out at query time). The implementation plan should evaluate both approaches.
