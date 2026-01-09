# Feature Specification: Finished Units Yield Type Management

**Feature Branch**: `044-finished-units-yield-type-management`
**Created**: 2026-01-09
**Status**: Draft
**Input**: See docs/design/F044_finished_units_functionality_ui.md
**Priority**: P1 - FOUNDATIONAL (blocks F045, F046, F047)

## Problem Statement

From user testing (2026-01-07): **"Finished Units button goes nowhere"**

Users cannot define what finished products their recipes make, blocking the entire Plan -> Make -> Deliver workflow. The system only knows abstract recipes (e.g., "Cookie Dough") but cannot understand concrete outputs (e.g., "30 Large Cookies per batch").

**Current broken workflow:**
- Baker wants to make "100 large cookies for the party"
- System doesn't know what a "Large Cookie" is
- Event planning cannot proceed

**Desired workflow:**
- Baker defines yield types in Recipe Edit: "Large Cookie = 30 per batch"
- Event planning can now select "Large Cookie" and calculate batches needed
- System calculates: 100 cookies / 30 per batch = 4 batches needed

## User Scenarios & Testing

### User Story 1 - Define Yield Types for a Recipe (Priority: P1)

A baker opens a recipe and defines the different finished products that recipe can produce, including the quantity each batch makes.

**Why this priority**: This is the core functionality - without yield type definitions, no downstream features (event planning, production tracking) can work.

**Independent Test**: Can be fully tested by creating a recipe, adding yield types inline, saving, and verifying persistence. Delivers immediate value by enabling yield definitions.

**Acceptance Scenarios**:

1. **Given** a recipe "Cookie Dough" exists, **When** the user opens Recipe Edit, **Then** they see a "Yield Types" section showing any existing yield types for that recipe.

2. **Given** the user is in Recipe Edit with the Yield Types section visible, **When** they enter "Large Cookie" and "30" in the inline entry row and click Add, **Then** the yield type appears in the list above the entry row.

3. **Given** the user has added yield types, **When** they click Save Recipe, **Then** all yield types are persisted to the database.

4. **Given** a yield type "Large Cookie" exists, **When** the user clicks Edit, changes it to "Extra Large Cookie" with 24 per batch, and saves, **Then** the changes are persisted.

5. **Given** a yield type exists, **When** the user clicks Delete and confirms, **Then** the yield type is removed from the list (persisted on recipe save).

---

### User Story 2 - Browse All Finished Units (Priority: P2)

A baker wants to see all the finished products defined across all recipes in one place to understand what they can produce.

**Why this priority**: Important for overview and discovery, but users can function with just Recipe Edit. This is a convenience/browsing feature.

**Independent Test**: Can be tested by navigating to the Finished Units tab and verifying all yield types from all recipes appear with search/filter working.

**Acceptance Scenarios**:

1. **Given** multiple recipes have yield types defined, **When** the user opens the Finished Units tab in CATALOG mode, **Then** they see a list of all yield types showing Name, Recipe, and Items Per Batch.

2. **Given** the Finished Units tab is open, **When** the user types "cookie" in the search box, **Then** only yield types containing "cookie" in the name are displayed.

3. **Given** the Finished Units tab is open, **When** the user selects "Cookie Dough" from the Recipe filter dropdown, **Then** only yield types belonging to that recipe are displayed.

4. **Given** a yield type row is displayed, **When** the user double-clicks it, **Then** the system navigates to open the parent Recipe Edit form.

---

### User Story 3 - Validation Prevents Invalid Data (Priority: P1)

The system prevents users from creating invalid yield type definitions that would cause calculation errors downstream.

**Why this priority**: Data integrity is critical - invalid data would break batch calculations and event planning.

**Independent Test**: Can be tested by attempting to create yield types with empty names, zero/negative quantities, and duplicate names within the same recipe.

**Acceptance Scenarios**:

1. **Given** the user is adding a yield type, **When** they leave the name field empty and click Add, **Then** an error message appears and the yield type is not added.

2. **Given** the user is adding a yield type, **When** they enter 0 or a negative number for Items Per Batch and click Add, **Then** an error message appears and the yield type is not added.

3. **Given** recipe "Cookie Dough" already has a yield type "Large Cookie", **When** the user tries to add another "Large Cookie" to the same recipe, **Then** an error message indicates the name already exists.

4. **Given** recipe "Brownie Batter" exists, **When** the user adds a yield type "Large Cookie" (same name as in Cookie Dough), **Then** it succeeds because uniqueness is per-recipe, not global.

---

### Edge Cases

- What happens when a recipe has no yield types? The Yield Types section shows empty with just the entry row.
- What happens when user cancels Recipe Edit after adding yield types? Changes are discarded (not persisted until Save).
- What happens with very long yield type names? Names are limited to 200 characters.
- How does the system handle 10+ yield types on one recipe? The list scrolls while remaining responsive.
- What happens when a recipe is deleted? All associated FinishedUnits are cascade-deleted automatically.

## Requirements

### Functional Requirements

**Recipe Edit Form - Yield Types Section:**
- **FR-001**: Recipe Edit form MUST include a "Yield Types" section
- **FR-002**: The section MUST display a list of existing yield types showing Name and Items Per Batch
- **FR-003**: Each yield type row MUST have Edit and Delete action buttons
- **FR-004**: The section MUST include an inline entry row for adding new yield types
- **FR-005**: The inline entry row MUST have fields for Name and Items Per Batch, plus an Add button
- **FR-006**: Clicking Add MUST add the yield type to the list (pending save)
- **FR-007**: Clicking Edit MUST allow inline modification of the yield type
- **FR-008**: Clicking Delete MUST prompt for confirmation before removal
- **FR-009**: Saving the recipe MUST persist all yield type changes (adds, edits, deletes)

**Finished Units Tab:**
- **FR-010**: A Finished Units tab MUST exist in CATALOG mode
- **FR-011**: The tab MUST display all yield types from all recipes
- **FR-012**: The list MUST show columns: Name, Recipe, Items Per Batch
- **FR-013**: A search field MUST filter yield types by name
- **FR-014**: A recipe dropdown MUST filter yield types by parent recipe
- **FR-015**: Double-clicking a row MUST navigate to the parent Recipe Edit form
- **FR-016**: The tab MUST be read-only (no Add/Edit/Delete buttons)
- **FR-017**: The tab MUST display a message indicating yield types are edited via Recipe Edit

**Validation:**
- **FR-018**: Yield type name MUST NOT be empty
- **FR-019**: Yield type name MUST be unique within the same recipe
- **FR-020**: Items Per Batch MUST be a positive integer (greater than zero)
- **FR-021**: Validation errors MUST display specific, actionable messages

**Service Layer:**
- **FR-022**: System MUST support creating finished units with name, items per batch, and recipe association
- **FR-023**: System MUST support updating finished unit name and items per batch
- **FR-024**: System MUST support deleting finished units
- **FR-025**: System MUST support querying finished units by recipe
- **FR-026**: System MUST support querying all finished units with optional filters

### Key Entities

- **FinishedUnit**: Represents a specific yield type from a recipe. Key attributes: display_name (what it's called), items_per_batch (how many one batch produces), recipe association.
- **Recipe**: Parent entity that can have multiple FinishedUnits (one-to-many relationship).

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can define a yield type for a recipe in 3 clicks or fewer (open edit, enter data, click add)
- **SC-002**: All yield types across the system are viewable in the Finished Units tab within 1 second of tab selection
- **SC-003**: Search results in Finished Units tab update as user types (no submit button required)
- **SC-004**: 100% of validation errors display user-friendly messages explaining what to fix
- **SC-005**: Double-click navigation from Finished Units tab to Recipe Edit works for all yield types
- **SC-006**: Recipe Edit form with 10+ yield types remains responsive (no noticeable lag)

## Dependencies

- **F037 (Recipe Redesign)**: Provides Recipe model with relationship support - COMPLETED
- **F042 (UI Polish)**: Establishes tab layout patterns - COMPLETED

## Assumptions

- The FinishedUnit model already exists in the database with all required fields
- The Recipe model supports the `finished_units` relationship
- CATALOG mode tab infrastructure is already in place
- Users understand the concept of "yield types" as different products from the same recipe

## Clarifications

### Session 2026-01-09

- Q: When a Recipe is deleted, what should happen to its associated FinishedUnits? → A: Cascade delete - FinishedUnits are automatically deleted with the recipe

## Out of Scope

- Cost calculations for yield types (deferred to F045+)
- Inventory tracking for finished units (deferred to F045+)
- Production recording against finished units (deferred to F047)
- Yield mode selection (DISCRETE_COUNT vs BATCH_PORTION) - system defaults to DISCRETE_COUNT
- Description, category, and notes fields for finished units (can be added later)
