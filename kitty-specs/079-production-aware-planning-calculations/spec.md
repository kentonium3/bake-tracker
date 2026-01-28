# Feature Specification: Production-Aware Planning Calculations

**Feature Branch**: `079-production-aware-planning-calculations`
**Created**: 2026-01-28
**Status**: Draft
**Input**: F079 functional spec - Integrate production status with planning calculations for remaining needs, real-time feasibility, and amendment validation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Remaining Production Needs (Priority: P1)

As a bakery planner, I want the system to show me how many batches I still need to produce (not total planned), so that I can focus on what's left to do.

**Why this priority**: Remaining needs calculation is the foundation for all other production-aware features. Without knowing "what's left", feasibility and shopping lists are meaningless during production.

**Independent Test**: Can be tested by recording partial production for an event (e.g., 3 of 5 batches for a recipe), then viewing the planning dashboard to verify it shows "2 remaining" instead of "5 planned".

**Acceptance Scenarios**:

1. **Given** an event with EventProductionTarget of 5 batches for a recipe and 3 batches already recorded in ProductionRun, **When** I view the planning dashboard, **Then** I see "2 batches remaining" for that recipe
2. **Given** an event with EventProductionTarget of 5 batches and 5 batches already recorded, **When** I view the planning dashboard, **Then** I see "0 batches remaining" (complete)
3. **Given** an event with EventProductionTarget of 5 batches and 7 batches recorded (overage), **When** I view the planning dashboard, **Then** I see "0 batches remaining" with an overage indicator (+2)
4. **Given** an event with no production records yet, **When** I view the planning dashboard, **Then** remaining equals total planned

---

### User Story 2 - Production-Aware Ingredient Feasibility (Priority: P2)

As a bakery planner, I want the ingredient feasibility check to consider only what I still need to produce, so that I don't see false "missing ingredient" warnings for already-completed batches.

**Why this priority**: Incorrect feasibility warnings during production create confusion and undermine trust in the planning system.

**Independent Test**: Can be tested by setting up an event requiring 10 batches, recording 7 batches, then checking feasibility to verify it only checks ingredients for the remaining 3 batches.

**Acceptance Scenarios**:

1. **Given** an event with 10 target batches, 7 completed batches, and sufficient inventory for 3 batches (but not 10), **When** I check production feasibility, **Then** status shows CAN_PRODUCE (not missing ingredients)
2. **Given** an event with 10 target batches, 7 completed batches, and insufficient inventory even for 3 batches, **When** I check production feasibility, **Then** status shows missing ingredients for the remaining 3 batches only
3. **Given** an event with all batches completed, **When** I check production feasibility, **Then** status shows COMPLETE (no ingredients needed)

---

### User Story 3 - Production-Aware Assembly Feasibility (Priority: P2)

As a bakery planner, I want the assembly feasibility check to account for both finished goods already produced AND what will be produced from remaining batches, so that I can plan assembly accurately.

**Why this priority**: Assembly depends on production output. Feasibility must reflect actual + projected finished goods availability.

**Independent Test**: Can be tested by checking assembly feasibility mid-production to verify it considers both produced FGs and the projected yield from remaining planned batches.

**Acceptance Scenarios**:

1. **Given** an assembly target of 20 units, 15 units already produced, and remaining production will yield 10 more, **When** I check assembly feasibility, **Then** status shows CAN_ASSEMBLE (15 + projected 10 >= 20)
2. **Given** an assembly target of 20 units, 5 units already produced, and remaining production will yield 5 more, **When** I check assembly feasibility, **Then** status shows PARTIAL with "10 units available, 10 short"
3. **Given** assembly target fully met by completed production, **When** I check assembly feasibility, **Then** status shows CAN_ASSEMBLE based on actual production alone

---

### User Story 4 - Production-Aware Shopping List (Priority: P3)

As a bakery planner, I want the shopping list to show ingredient gaps for remaining production only, so that I don't over-purchase ingredients for batches I've already completed.

**Why this priority**: Shopping list accuracy saves money and reduces waste. Depends on remaining needs calculation (P1).

**Independent Test**: Can be tested by completing half the production, then generating a shopping list to verify it calculates gaps only for the remaining batches.

**Acceptance Scenarios**:

1. **Given** 10 target batches requiring 100g flour each, 7 completed batches, and 200g flour in inventory, **When** I generate the shopping list, **Then** it shows "100g flour needed" (3 batches * 100g = 300g - 200g inventory)
2. **Given** all production completed, **When** I generate the shopping list, **Then** it shows no ingredients needed for production
3. **Given** inventory sufficient for remaining production, **When** I generate the shopping list, **Then** it shows no ingredients needed

---

### User Story 5 - Amendment Validation Against Production (Priority: P3)

As a bakery planner, I want the system to prevent me from modifying batch decisions for recipes that already have production recorded, so that I don't create confusion between planned and actual work.

**Why this priority**: Data integrity protection. Amendments should only affect pending work, not historical records.

**Independent Test**: Can be tested by recording some production for a recipe, then attempting a MODIFY_BATCH amendment to verify it's rejected with a clear error.

**Acceptance Scenarios**:

1. **Given** a recipe with 0 completed batches, **When** I attempt a MODIFY_BATCH amendment, **Then** the amendment is accepted
2. **Given** a recipe with 1+ completed batches, **When** I attempt a MODIFY_BATCH amendment, **Then** the amendment is rejected with error "Cannot modify batch decision for recipe with completed production"
3. **Given** a recipe with 0 completed batches, **When** I attempt a DROP_FG amendment for an FG produced by that recipe, **Then** the amendment is accepted
4. **Given** an FG with production already recorded, **When** I attempt a DROP_FG amendment, **Then** the amendment is rejected with error "Cannot drop finished good with completed production"

---

### User Story 6 - Display Production Progress (Priority: P4)

As a bakery planner, I want to see actual vs planned production in the UI with real-time updates, so that I can track progress at a glance.

**Why this priority**: User experience enhancement. Builds on the core remaining needs calculation.

**Independent Test**: Can be tested by recording production and verifying the UI updates to show progress bars, completed/remaining counts, and percentage complete.

**Acceptance Scenarios**:

1. **Given** an event in production, **When** I view the planning dashboard, **Then** I see a progress indicator for each recipe showing "X of Y batches complete (Z%)"
2. **Given** production is recorded for a recipe, **When** the dashboard refreshes, **Then** the progress indicator updates to reflect the new count
3. **Given** an event with some recipes complete and others in progress, **When** I view the dashboard, **Then** complete recipes show a "complete" badge and in-progress recipes show progress bars

---

### Edge Cases

- What happens if production exceeds target (overage)? (Display remaining as 0 with overage indicator; no negative remaining)
- What happens if target is modified via amendment after partial production? (Recalculate remaining from new target - completed)
- What happens if a recipe has no EventProductionTarget? (No remaining calculation needed; recipe not part of plan)
- How do we handle production recorded against wrong event? (Out of scope - data entry validation is separate)
- What if feasibility check occurs while production is being recorded? (Use transaction isolation; feasibility reads committed data)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST calculate remaining batches as `target_batches - completed_batches` for each recipe in an event
- **FR-002**: System MUST treat remaining as 0 (not negative) when completed exceeds target
- **FR-003**: System MUST display overage amount when completed exceeds target
- **FR-004**: System MUST check production feasibility against remaining batches only (not total planned)
- **FR-005**: System MUST calculate assembly feasibility using: produced FG inventory + projected yield from remaining batches
- **FR-006**: System MUST calculate shopping list ingredient gaps based on remaining production needs only
- **FR-007**: System MUST reject MODIFY_BATCH amendments for recipes with any completed production records
- **FR-008**: System MUST reject DROP_FG amendments for finished goods with any completed production records
- **FR-009**: System MUST allow amendments for recipes/FGs with zero completed production
- **FR-010**: System MUST display progress indicators showing completed vs target for each recipe
- **FR-011**: System MUST update progress displays when new production is recorded
- **FR-012**: System MUST provide error messages that explain why an amendment was rejected due to production status

### Key Entities

- **ProductionRun**: Existing model that records completed production (batch count, yield). Used as the source of truth for "completed" batches.
- **EventProductionTarget**: Existing model that specifies planned batches per recipe. Used as the source of truth for "target" batches.
- **RemainingNeeds**: Calculated data structure (not persisted) representing remaining production needs per recipe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Remaining batch calculations are mathematically correct 100% of the time (target - completed = remaining, minimum 0)
- **SC-002**: Production feasibility checks correctly assess ingredient availability for remaining batches only
- **SC-003**: Assembly feasibility accurately reflects both produced inventory and projected remaining yield
- **SC-004**: Shopping lists show ingredient gaps only for remaining production needs
- **SC-005**: Amendments are rejected for recipes/FGs with production 100% of the time; accepted for those without production
- **SC-006**: Progress indicators display accurate counts and update within 2 seconds of production recording
- **SC-007**: Amendment rejection messages clearly state the production-related reason

## Assumptions

- The ProductionRun model exists and tracks completed batches per recipe per event (from production_service.py)
- The EventProductionTarget model exists and specifies target batches per recipe per event
- The PlanAmendment model and amendment types (DROP_FG, ADD_FG, MODIFY_BATCH) exist from F078
- Recording a ProductionRun marks those batches as "completed" (no separate in-progress state)
- A batch is "pending" if no ProductionRun record exists for it
- The planning services (feasibility.py, shopping_list.py, progress.py) exist and will be modified
- UI components for progress display exist and will be enhanced

## Out of Scope

- Production scheduling (when to produce batches)
- Production cost tracking (handled by existing cost calculation)
- Production quality tracking (defects, yields)
- In-progress batch state tracking (batches are either recorded/completed or pending)
- Partial batch completion (a batch is either fully complete or not started)
- Real-time WebSocket updates (use polling or manual refresh)
