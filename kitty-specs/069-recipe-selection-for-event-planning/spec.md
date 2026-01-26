# Feature Specification: Recipe Selection for Event Planning

**Feature Branch**: `069-recipe-selection-for-event-planning`
**Created**: 2026-01-26
**Status**: Draft
**Input**: User description: "see docs/func-spec/F069_recipe_selection_ui.md for the feature inputs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select Recipes for Event (Priority: P1)

As a baker planning an event, I need to select which recipes I want to make so that my recipe choices are recorded and can drive downstream planning (finished goods, quantities, batch calculations).

**Why this priority**: Recipe selection is the foundational step in the planning workflow. Without selected recipes, no downstream features (F070-F079) can function. This enables the entire planning pipeline.

**Independent Test**: Open an event in Planning mode, view the recipe selection UI, check several recipes (both bases and variants), save, and verify selections persist when reopening the event.

**Acceptance Scenarios**:

1. **Given** I have an event open in planning mode, **When** I navigate to recipe selection, **Then** I see a flat list of all recipes (bases and variants) with checkboxes
2. **Given** I am viewing the recipe list, **When** I check recipes I want to make, **Then** each checkbox operates independently and selection count updates immediately
3. **Given** I have selected recipes, **When** I save my selections, **Then** the selections persist to the database and are loaded when I reopen the event

---

### User Story 2 - Distinguish Base Recipes from Variants (Priority: P1)

As a baker, I need to visually distinguish base recipes from their variants so I can make informed selection decisions without confusion about recipe relationships.

**Why this priority**: Bases and variants have different implications for production. Selecting a variant without understanding its relationship to the base could lead to planning errors. Visual clarity is essential for correct selections.

**Independent Test**: View the recipe list and verify that base recipes are visually distinct from variants (through indentation, icons, labels, or other visual cues).

**Acceptance Scenarios**:

1. **Given** I am viewing the recipe selection list, **When** the list displays, **Then** base recipes are visually distinct from variant recipes
2. **Given** I see a variant recipe, **When** I look at its display, **Then** I can tell it is a variant (not a base) at a glance

---

### User Story 3 - Explicit Selection Without Auto-Inclusion (Priority: P1)

As a baker, I need each recipe selection to be independent so that the system never assumes I want related recipes - I decide exactly what to make.

**Why this priority**: Auto-inclusion would violate user intent. A baker may want only specific variants without the base, or only the base without variants. Each selection must be an explicit user choice.

**Independent Test**: Select a base recipe and verify its variants remain unchecked. Select a variant and verify its base remains unchecked.

**Acceptance Scenarios**:

1. **Given** I check a base recipe, **When** I look at its variants, **Then** the variants remain unchecked (no auto-inclusion)
2. **Given** I check a variant recipe, **When** I look at its base, **Then** the base remains unchecked (no auto-inclusion)
3. **Given** I want only certain recipes, **When** I make my selections, **Then** I can select any arbitrary combination of bases and variants

---

### User Story 4 - View Selection Count and Feedback (Priority: P2)

As a baker, I need to see how many recipes I've selected so I can gauge the scope of my event planning at a glance.

**Why this priority**: Selection count provides important feedback but is secondary to the core selection functionality. It enhances usability but isn't blocking for the workflow.

**Independent Test**: Select several recipes and verify the count display updates in real-time, showing "X of Y recipes selected."

**Acceptance Scenarios**:

1. **Given** I am viewing the recipe list, **When** I check/uncheck recipes, **Then** the selection count updates immediately
2. **Given** no recipes are selected, **When** I view the count, **Then** it shows "0 of Y recipes selected"
3. **Given** the recipe list is long, **When** I scroll, **Then** the selection count remains visible

---

### User Story 5 - Load Existing Selections (Priority: P2)

As a baker returning to an event I previously worked on, I need to see my prior recipe selections pre-checked so I can continue planning where I left off.

**Why this priority**: Persistence was covered in P1, but the loading/pre-checking UX is important for returning users. Without it, users would have to re-select recipes each time.

**Independent Test**: Create an event, select recipes, save, close and reopen the event, verify previously selected recipes are pre-checked.

**Acceptance Scenarios**:

1. **Given** I saved recipe selections for an event, **When** I reopen that event, **Then** my previously selected recipes are pre-checked
2. **Given** I modify selections and save, **When** I reopen the event, **Then** only my latest selections are checked (replace behavior, not append)

---

### Edge Cases

- What happens when the recipe catalog is empty? Display "No recipes available" message
- What happens when a previously selected recipe is deleted? The orphaned event_recipe record should be cascade-deleted; the UI shows only existing recipes
- What happens if save fails? Maintain selection state in UI, show error message without losing selections
- How does system handle 100+ recipes? List must be scrollable; consider performance testing during planning phase

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all recipes (bases and variants) in a single flat list
- **FR-002**: System MUST visually distinguish base recipes from variant recipes
- **FR-003**: System MUST provide a checkbox for each recipe enabling explicit selection
- **FR-004**: System MUST NOT auto-include variant recipes when a base recipe is selected
- **FR-005**: System MUST NOT auto-include base recipes when a variant recipe is selected
- **FR-006**: System MUST display selection count in format "X of Y recipes selected"
- **FR-007**: System MUST update selection count immediately when checkboxes change
- **FR-008**: System MUST persist recipe selections to the event_recipes table
- **FR-009**: System MUST load and pre-check existing selections when an event is opened
- **FR-010**: System MUST replace (not append) selections when saving
- **FR-011**: System MUST support scrolling for recipe lists exceeding viewport height

### Key Entities

- **Event**: The planning event for which recipes are being selected (from F068)
- **Recipe**: A base recipe or variant recipe that can be selected for production
- **EventRecipe**: Junction table linking an event to its selected recipes (from F068)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can select recipes for an event and save selections in under 30 seconds
- **SC-002**: Recipe selection list loads and displays within 2 seconds for catalogs up to 100 recipes
- **SC-003**: Selection count updates within 100ms of checkbox interaction
- **SC-004**: 100% of saved selections correctly persist and reload on subsequent visits
- **SC-005**: Base and variant recipes are distinguishable with 100% accuracy by users (no confusion)

## Out of Scope

The following are explicitly NOT included in this feature:

- Finished goods filtering based on recipe selections (F070)
- Quantity specification for selected items (F071)
- Batch calculations (F073)
- Recipe search or filtering within the list (future enhancement)
- Recipe details display or preview (separate feature)
- Recipe reordering or custom grouping (use natural database order)

## Dependencies

- **F068** (Event Management & Planning Data Model): Provides Event model with planning fields and event_recipes junction table
- **Existing RecipeService**: Provides access to recipe catalog including base/variant relationships

## Assumptions

- Recipe catalog size is expected to be under 100 recipes for typical users
- Base/variant relationships are already defined in the Recipe model
- The event_recipes table from F068 is ready for use
- Planning UI context (current event) is accessible from the recipe selection component
