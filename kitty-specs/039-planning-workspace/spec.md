# Feature Specification: Planning Workspace

**Feature Branch**: `039-planning-workspace`
**Created**: 2026-01-05
**Status**: Draft
**Dependencies**: F037 (Recipe Redesign), F038 (UI Mode Restructure)
**Input**: User description: "Full Phase 2 Planning Workspace - automatic batch calculation to prevent underproduction"

## Problem Statement

**The Underproduction Problem**: Manual batch math leads to consistent production shortfalls during holiday baking.

**Real-World Evidence (Christmas 2024):**
- User planned 50 gift bags (6 cookies + 3 brownies each)
- Manually calculated "about 300 cookies and 150 brownies needed"
- Produced: 288 cookies, 144 brownies (one batch short each)
- Result: Only assembled 48 gift bags - **ran short on nearly everything**

**Root Cause:** Mental math errors when converting requirements to batches
- "300 cookies needed, recipe makes 48... that's about 6 batches" (wrong - needs 7)
- Rounding errors compound across multiple recipes
- No validation until assembly day when it's too late to fix

**The Solution:** Automatic batch calculation that:
1. Explodes bundle requirements to individual unit quantities
2. Calculates optimal batches (never short, minimize waste)
3. Aggregates ingredients across all recipes
4. Validates assembly feasibility before production begins
5. Tracks progress through shopping, production, and assembly

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Production Plan for Event (Priority: P1)

User has an upcoming event (e.g., Christmas 2025) and needs to know exactly how many batches of each recipe to make. The system automatically calculates optimal batches from bundle requirements, ensuring production never falls short.

**Why this priority**: This is THE core value proposition - preventing underproduction. Without accurate batch calculation, the entire feature has no value.

**Independent Test**: Can be fully tested by creating an event with bundle requirements and clicking "Calculate Plan". Delivers the critical batch numbers that prevent shortfalls.

**Acceptance Scenarios**:

1. **Given** an event with 50 Holiday Gift Bags (6 cookies + 3 brownies each), **When** user clicks "Calculate Plan", **Then** system shows:
   - 300 cookies needed, 150 brownies needed (exploded from bundles)
   - Optimal batch count for each recipe (e.g., 7 batches cookies, 7 batches brownies)
   - Total yield and waste percentage for each recipe

2. **Given** a recipe with multiple yield options (24, 48, 96 per batch), **When** calculating batches, **Then** system selects the yield option that minimizes waste while keeping waste under 15% threshold

3. **Given** calculated batches, **When** user reviews the plan, **Then** total yield always meets or exceeds the requirement (never short)

---

### User Story 2 - Generate Shopping List with Inventory Check (Priority: P2)

User needs to know what ingredients to buy. The system aggregates ingredients across all recipes, checks current inventory, and shows exactly what needs to be purchased.

**Why this priority**: After knowing batch counts, the next critical need is knowing what to buy. Without this, user must manually sum ingredients and check pantry - error-prone and time-consuming.

**Independent Test**: Can be tested by calculating a plan and viewing the shopping list. Delivers actionable buy list that accounts for existing inventory.

**Acceptance Scenarios**:

1. **Given** a calculated production plan with multiple recipes, **When** shopping list is generated, **Then** system shows aggregated ingredients with Need/Have/Buy columns

2. **Given** 14 cups flour needed and 10 cups in inventory, **When** viewing shopping list, **Then** system shows: Need: 14c, Have: 10c, Buy: 4c

3. **Given** ingredients with sufficient inventory (e.g., sugar), **When** viewing shopping list, **Then** item shows as "sufficient" with Buy: 0

4. **Given** a completed shopping list, **When** user clicks "Mark Shopping Complete", **Then** system records shopping status for progress tracking

---

### User Story 3 - Validate Assembly Feasibility (Priority: P3)

User needs confidence that after production, they can assemble all planned bundles. The system validates that planned production yields enough components for all bundles.

**Why this priority**: Assembly validation prevents discovering shortfalls on assembly day. Critical for peace of mind but depends on accurate production plan first.

**Independent Test**: Can be tested by viewing assembly feasibility after calculating plan. Shows clear indicators of what can/cannot be assembled.

**Acceptance Scenarios**:

1. **Given** a production plan that yields sufficient components, **When** viewing assembly feasibility, **Then** system shows green checkmark with "Can assemble 50 Holiday Gift Bags"

2. **Given** production is incomplete (e.g., 4/7 brownie batches done), **When** viewing assembly feasibility, **Then** system shows warning "Cannot assemble yet - brownie production incomplete"

3. **Given** a plan with insufficient production for some bundles, **When** viewing assembly feasibility, **Then** system shows red indicator with specific shortfall (e.g., "Need 54 more truffles")

---

### User Story 4 - Track Production Progress (Priority: P4)

User wants to see progress during production. The system shows batch completion status per recipe and updates assembly feasibility as production progresses.

**Why this priority**: Progress tracking provides visibility during execution but requires calculation and feasibility features to be meaningful.

**Independent Test**: Can be tested by recording batch completions and observing progress bars update. Delivers visual progress feedback.

**Acceptance Scenarios**:

1. **Given** a plan requiring 7 cookie batches, **When** 4 batches are recorded as complete, **Then** progress shows "4/7 batches (57%)" with progress bar

2. **Given** all recipe batches complete, **When** viewing production status, **Then** all recipes show 100% complete

3. **Given** production progress changes, **When** assembly feasibility is rechecked, **Then** feasibility status updates accordingly

---

### User Story 5 - Complete Assembly Checklist (Priority: P5)

User wants to track bundle assembly completion. The system provides a checklist that enables only when production is complete.

**Why this priority**: Assembly checklist is the final workflow step. Lower priority because it's confirmation-only (no inventory transactions in Phase 2).

**Independent Test**: Can be tested by completing production and checking off assembly items. Delivers completion tracking for event.

**Acceptance Scenarios**:

1. **Given** production yields 30 complete sets of bundle components (e.g., enough for 30 gift bags), **When** viewing assembly checklist, **Then** system shows "30 of 50 available to assemble" with partial assembly enabled

2. **Given** a bundle component has zero production complete, **When** viewing assembly checklist, **Then** that bundle's checklist item is disabled with explanation "Awaiting [component] production"

3. **Given** user assembles 30 of 50 Holiday Gift Bags, **When** checklist is saved, **Then** system records partial assembly (30/50) and updates remaining to-assemble count

4. **Given** all production complete, **When** viewing assembly checklist, **Then** all 50 bundles are available to assemble

---

### Edge Cases

- What happens when a bundle has no FinishedGood composition defined? System shows error "Bundle has no components defined"
- What happens when a FinishedUnit has no linked recipe? System shows error "No recipe found for [unit name]"
- What happens when a recipe has no yield options? System shows error "Recipe has no yield options configured"
- What happens when requirements are zero? System prevents calculation with validation error
- What happens when inventory check fails (database error)? Shopping list shows "Unable to check inventory" with graceful fallback
- How does system handle recipe with single yield option? Uses that option without optimization (no alternatives)
- What happens when waste threshold cannot be met? Uses option with minimum waste and displays warning

---

## Requirements *(mandatory)*

### Functional Requirements - Event Configuration

- **FR-001**: System MUST support Event output_mode attribute with values: BULK_COUNT (direct FinishedUnit quantities), BUNDLED (FinishedGood/bundle quantities)
- **FR-002**: System MUST validate output_mode is set before allowing plan calculation
- **FR-003**: System MUST show appropriate requirement input UI based on output_mode (FinishedUnit selector for BULK_COUNT, FinishedGood selector for BUNDLED)

### Functional Requirements - Requirements Input

- **FR-004**: BULK_COUNT mode MUST allow adding FinishedUnit requirements with quantity
- **FR-005**: BUNDLED mode MUST allow adding FinishedGood (bundle) requirements with quantity
- **FR-006**: System MUST validate all quantities are positive integers
- **FR-007**: System MUST allow editing and removing requirements before calculation
- **FR-008**: System MUST show bundle contents preview when adding FinishedGood requirement

### Functional Requirements - Production Plan Calculation

- **FR-009**: System MUST explode FinishedGood requirements to FinishedUnit quantities by multiplying bundle contents by bundle quantity
- **FR-010**: System MUST group FinishedUnits by their linked recipe
- **FR-011**: System MUST calculate optimal yield option using 15% waste threshold: select yield with minimum waste among those under threshold, preferring fewer batches for ties
- **FR-012**: System MUST ensure total yield always meets or exceeds requirement (never short)
- **FR-013**: System MUST calculate variant proportions when recipe has multiple variants (quantity_needed / total_yield for each variant)
- **FR-014**: System MUST display waste analysis (extra units, waste percentage) for each recipe

### Functional Requirements - Shopping List

- **FR-015**: System MUST aggregate ingredients across all recipes in the plan, combining same ingredients from different recipes
- **FR-016**: System MUST scale ingredient quantities by: base_quantity x batches x batch_multiplier for base ingredients; additionally x proportion for variant ingredients
- **FR-017**: System MUST check current inventory for each aggregated ingredient
- **FR-018**: System MUST calculate purchase gap: max(0, needed - available)
- **FR-019**: System MUST display shopping list with columns: Ingredient, Need, Have, Buy
- **FR-020**: System MUST allow user to mark shopping as complete (status tracking)
- **FR-021**: System MUST visually distinguish sufficient ingredients (Have >= Need) from those requiring purchase

### Functional Requirements - Assembly Feasibility

- **FR-022**: System MUST validate assembly feasibility using event-scoped inventory (no cross-event sharing)
- **FR-023**: Feasibility check MUST compare FinishedUnits produced (from plan) vs FinishedUnits needed (from bundle contents)
- **FR-024**: System MUST display visual status indicators: sufficient (green), pending/incomplete (yellow), insufficient (red)
- **FR-025**: System MUST show component-level detail for each bundle: what's available, what's needed, surplus or shortfall
- **FR-026**: System MUST show overall assembly status: can assemble / cannot assemble yet / cannot assemble

### Functional Requirements - Assembly Checklist

- **FR-027**: System MUST generate assembly checklist from FinishedGood requirements
- **FR-028**: Checklist items MUST show available quantity based on current production; items with zero available components are disabled with explanation
- **FR-029**: Checking a checklist item MUST record assembly confirmation (status tracking only, no inventory transaction in Phase 2)

### Functional Requirements - Progress Tracking

- **FR-030**: System MUST track production progress as batches_complete / batches_total per recipe
- **FR-031**: System MUST display progress bars for each recipe
- **FR-032**: System MUST update assembly feasibility dynamically as production progresses
- **FR-033**: System MUST show overall event readiness status summarizing shopping, production, and assembly states

### Functional Requirements - Workflow Navigation

- **FR-034**: System MUST allow free navigation between planning phases (Calculate, Shop, Produce, Assemble) without enforcing strict linear progression
- **FR-035**: System MUST display contextual warnings when user accesses a phase with incomplete prerequisites (e.g., "Production incomplete - 3/7 brownie batches done")
- **FR-036**: System MUST enable partial assembly when sufficient components exist, even while other production continues (e.g., can assemble 30 gift bags while awaiting remaining brownie batches)

### Functional Requirements - Plan Persistence

- **FR-037**: System MUST persist calculated production plan as a snapshot linked to the Event (batch counts, yield selections, ingredient aggregations)
- **FR-038**: System MUST track plan calculation timestamp and input versions (recipe yields, bundle compositions, requirements)
- **FR-039**: System MUST detect when plan inputs have changed since calculation (recipe modified, bundle composition changed, requirements updated)
- **FR-040**: System MUST display "Plan may be outdated" warning when inputs have changed, with option to recalculate
- **FR-041**: System MUST allow explicit recalculation that replaces the stored plan snapshot

### Key Entities

- **Event**: A planned occasion (e.g., Christmas 2025) with an output_mode determining how requirements are specified
- **EventAssemblyTarget**: Links an Event to a FinishedGood (bundle) with target quantity - "How many of this bundle for this event?"
- **EventProductionTarget**: Links an Event to a FinishedUnit with target quantity - "How many of this item for this event?" (BULK_COUNT mode)
- **ProductionPlanSnapshot**: Persisted calculation results for an Event - batch counts per recipe, selected yield options, aggregated ingredients, calculation timestamp, and input version hashes for staleness detection
- **FinishedGood**: A bundle/assembly containing multiple FinishedUnits (e.g., "Holiday Gift Bag" containing cookies and brownies)
- **Composition**: Links FinishedGood to its FinishedUnit components with quantities - "What's in this bundle?"
- **FinishedUnit**: A specific product variant linked to a recipe (e.g., "Chocolate Chip Cookie")
- **Recipe**: A production template with yield options and base ingredients
- **RecipeYieldOption**: A yield variant for a recipe (e.g., 24, 48, or 96 cookies per batch) with batch_multiplier

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can calculate a complete production plan (batch counts, shopping list, feasibility) within 3 clicks from event selection
- **SC-002**: Production plan calculation completes in under 500ms for events with 10+ recipes
- **SC-003**: Batch calculations NEVER result in production shortfall - total yield always >= requirement (100% accuracy)
- **SC-004**: Users can identify all items to purchase in a single view without manual calculation
- **SC-005**: Assembly feasibility status is accurate: if system shows "can assemble", production yields are mathematically sufficient
- **SC-006**: Users can track production progress in real-time with visual feedback
- **SC-007**: Waste percentage is minimized within the 15% threshold for all recipes where possible
- **SC-008**: Shopping list correctly identifies inventory gaps - Buy quantity = max(0, Need - Have) with 100% accuracy

### User Value Outcomes

- **SC-009**: User confidence: "I know exactly how many batches to make" (eliminates guesswork)
- **SC-010**: No surprises: Assembly feasibility checked BEFORE production begins (eliminates day-of shortfalls)
- **SC-011**: Complete visibility: User can see shopping, production, and assembly status in one workspace

---

## Assumptions

- F037 (Recipe Redesign) is complete and recipes have yield options configured
- F038 (UI Mode Restructure) is complete and PLAN mode navigation exists
- Existing Event, FinishedGood, FinishedUnit, Composition models are functional
- Inventory service can query current stock levels for ingredients
- Production recording (batch completions) exists or will be extended

## Scope Boundaries

**In Scope (Phase 2):**
- Event-scoped planning (single event at a time)
- BUNDLED and BULK_COUNT output modes
- Automatic batch calculation with 15% waste threshold
- Ingredient aggregation and inventory gap analysis
- Assembly feasibility validation
- Shopping completion status tracking
- Production progress tracking
- Assembly checklist (confirmation only, no inventory transactions)

**Out of Scope (Phase 3+):**
- Multi-event planning and cross-event inventory optimization
- PACKAGED output mode (packages containing bundles)
- Manual batch override with validation warning
- Auto-detect recipe changes and prompt recalculation
- Configurable waste threshold via settings
- Shopping list export to CSV/PDF
- Mobile app integration
- Cost-based yield optimization
- Assembly checklist with inventory transactions

---

## Clarifications

### Session 2026-01-05

- Q: Does an Event's planning state follow a linear workflow or can users jump between states freely? → A: Guided but flexible - users can work on any phase at any time with warnings when jumping ahead; partial assembly can begin while other production continues.
- Q: Should the production plan be persisted as a snapshot or computed fresh each time? → A: Persisted snapshot - calculate once, store results, show stale warning if inputs change.

---

## Design Reference

Detailed technical design, algorithms, and UI mockups are documented in:
`docs/design/_F039_PLANNING_WORKSPACE_SPEC.md`

This design document is illustrative guidance - implementation should be validated during the planning phase against current codebase patterns and constitution compliance.
