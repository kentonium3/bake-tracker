# Feature Specification: Batch Calculation & User Decisions

**Feature Branch**: `073-batch-calculation-user-decisions`
**Created**: 2026-01-27
**Status**: Draft
**Input**: see docs/func-spec/F073_batch_calculation_user_decisions.md for the feature's inputs

## Overview

This feature implements the core value proposition: automatic batch calculation with informed user decisions. It replaces error-prone manual calculations that consistently cause underproduction.

**Problem solved:** Manual batch calculations lead to consistent underproduction. The system currently knows quantities needed per recipe (F072), but lacks batch calculation, user decision points, and persistence of batch decisions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Batch Options (Priority: P1)

As a baker, I want the system to automatically calculate batch options for each recipe so that I can see my choices without doing manual math.

**Why this priority**: Core value proposition - this is the primary calculation that all other features depend on. Without accurate batch options, users cannot make informed decisions.

**Independent Test**: Can be fully tested by providing recipe requirements (from F072) and verifying floor/ceil batch options are calculated correctly with accurate yield and difference values.

**Acceptance Scenarios**:

1. **Given** recipe requirements exist (e.g., Sugar Cookies: need 200), **When** batch options are calculated, **Then** system shows floor option (8 batches = 192, 8 short) and ceil option (9 batches = 216, 16 extra)
2. **Given** a recipe where quantity needed is exact multiple of yield (e.g., need 72 cookies, yield 24/batch), **When** batch options are calculated, **Then** system identifies exact match (3 batches = 72)
3. **Given** a recipe with multiple yield options (Small: 12, Large: 24), **When** batch options are calculated, **Then** system calculates options for each yield type

---

### User Story 2 - Present Options with Clear Trade-offs (Priority: P1)

As a baker, I want to see my batch options with clear numbers showing batches, total yield, and shortfall/excess so that I can make informed strategic decisions.

**Why this priority**: Equally critical to P1 calculation - users cannot benefit from calculations if presentation is unclear. Core user experience.

**Independent Test**: Can be tested by verifying UI displays all recipes with their options, shortfall warnings are prominent, and exact matches are highlighted.

**Acceptance Scenarios**:

1. **Given** batch options have been calculated, **When** user views the options, **Then** each recipe shows: name, quantity needed, and all options with batch count, yield, and difference
2. **Given** an option creates a shortfall, **When** displayed to user, **Then** shortfall warning indicator is prominently shown
3. **Given** an option is an exact match, **When** displayed to user, **Then** exact match is clearly highlighted

---

### User Story 3 - Confirm Shortfall Selections (Priority: P2)

As a baker, I want to be warned and asked to confirm when I select an option that creates a shortfall so that I don't accidentally underplan.

**Why this priority**: Protection against user error. Depends on US1 and US2 being complete, but critical for preventing the very problem this feature solves.

**Independent Test**: Can be tested by selecting a shortfall option and verifying confirmation dialog appears with specific numbers.

**Acceptance Scenarios**:

1. **Given** user selects a shortfall option (e.g., 8 batches = 192, need 200), **When** selection is made, **Then** confirmation dialog shows specific impact ("You'll be 8 short")
2. **Given** confirmation dialog is shown, **When** user clicks Cancel, **Then** selection is reverted
3. **Given** user selects a non-shortfall option, **When** selection is made, **Then** no confirmation is required

---

### User Story 4 - Save Batch Decisions (Priority: P2)

As a baker, I want my batch decisions saved with the event so that I can return later and see what I decided.

**Why this priority**: Data persistence is required for downstream features (F074, F075, F076) to use batch decisions. Depends on user being able to make selections (US1-US3).

**Independent Test**: Can be tested by saving decisions, closing event, reopening, and verifying decisions are pre-selected.

**Acceptance Scenarios**:

1. **Given** user has selected batch options for all recipes, **When** user saves, **Then** decisions are persisted to batch_decisions table
2. **Given** batch decisions exist for an event, **When** event is opened, **Then** previous selections are pre-selected
3. **Given** user attempts to save without selecting for all recipes, **When** save is attempted, **Then** validation prevents save and shows which recipes need decisions

---

### User Story 5 - Modify Batch Decisions (Priority: P3)

As a baker, I want to change my batch decisions after initial selection so that I can adjust my plan based on new information.

**Why this priority**: Nice-to-have for flexibility. Core functionality (US1-US4) works without this, but users expect to be able to change their minds.

**Independent Test**: Can be tested by changing a selection and verifying the change saves and displays correctly.

**Acceptance Scenarios**:

1. **Given** batch decisions have been saved, **When** user changes a selection, **Then** new decision replaces previous decision
2. **Given** user changes from non-shortfall to shortfall option, **When** change is made, **Then** confirmation dialog still required

---

### Edge Cases

- What happens when a recipe has zero yield? (Invalid configuration - should not occur, but validate gracefully)
- What happens when quantity needed is zero? (Skip recipe from batch calculation)
- What happens when recipe has no yield options? (Validation error - recipe not properly configured)
- What happens when floor calculation results in zero batches? (Show as 0 batches = 0 yield, full shortfall)
- What happens when user changes FG quantities after making batch decisions? (Decisions become stale - future enhancement to detect/warn)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST calculate floor batch option for each recipe (batches = floor(needed / yield_per_batch))
- **FR-002**: System MUST calculate ceil batch option for each recipe when ceil differs from floor
- **FR-003**: System MUST calculate total yield for each option (batches × yield_quantity)
- **FR-004**: System MUST calculate difference for each option (total_yield - quantity_needed)
- **FR-005**: System MUST flag options with negative difference as shortfalls
- **FR-006**: System MUST identify exact matches where difference equals zero
- **FR-007**: System MUST display all recipes needing batch decisions
- **FR-008**: System MUST present options with radio button or similar selection mechanism
- **FR-009**: System MUST show shortfall warnings prominently (visual indicator)
- **FR-010**: System MUST highlight exact matches clearly
- **FR-011**: System MUST require confirmation when user selects shortfall option
- **FR-012**: System MUST allow cancellation from shortfall confirmation (revert selection)
- **FR-013**: System MUST persist batch decisions to batch_decisions table (event_id, recipe_id, batches, yield_option_id)
- **FR-014**: System MUST load existing batch decisions when event is opened
- **FR-015**: System MUST validate all recipes have decisions before allowing final save
- **FR-016**: System MUST allow modification of batch decisions after initial selection
- **FR-017**: System MUST handle recipes with multiple yield options by showing options for each

### Key Entities

- **BatchDecision**: User's selected batch count for a recipe within an event. Links event_id, recipe_id, batches (count), and yield_option_id.
- **RecipeYieldOption**: Defines yield variants for a recipe (e.g., "Small batch: 12 cookies", "Large batch: 24 cookies"). Contains yield_quantity and yield_type.
- **Recipe**: The recipe being produced. Referenced by batch decisions and has one or more yield options.
- **Event**: The planning event that batch decisions belong to. One-to-many relationship with batch decisions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System correctly calculates floor and ceil options for 100% of test scenarios
- **SC-002**: User can view and select batch options for all recipes in under 30 seconds per recipe
- **SC-003**: Shortfall confirmation prevents accidental selection 100% of the time
- **SC-004**: Batch decisions persist correctly across session close/reopen
- **SC-005**: All recipes must have batch decisions before event plan is considered complete
- **SC-006**: User can modify any batch decision without data loss
- **SC-007**: Multiple yield options per recipe are handled correctly
- **SC-008**: Zero shortfall options can be confirmed if user explicitly chooses
- **SC-009**: UI clearly communicates the trade-off (shortfall vs excess) for each option
- **SC-010**: Exact matches are identifiable without reading detailed numbers

## Assumptions

- F072 (Recipe Decomposition & Aggregation) is complete and provides recipe requirements via `calculate_recipe_requirements()`
- `batch_decisions` table exists from F068 schema
- `recipe_yield_options` table exists with yield_quantity and yield_type fields
- Existing UI patterns for radio buttons, confirmation dialogs can be followed

## Out of Scope

- Variant allocation within batches (F074)
- Ingredient aggregation from batch decisions (F074)
- Inventory gap analysis (F075)
- Optimization suggestions ("minimize waste" recommendations)
- Historical batch decision tracking
- Custom batch override ("I want exactly 7 batches" - future enhancement)
- Staleness detection when upstream data changes (future enhancement)
