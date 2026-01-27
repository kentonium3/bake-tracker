# Feature Specification: Recipe Decomposition & Aggregation

**Feature Branch**: `072-recipe-decomposition-aggregation`
**Created**: 2026-01-27
**Status**: Draft
**Input**: User description: "see docs/func-spec/F072_recipe_decomposition_aggregation.md for feature inputs."

## User Scenarios & Testing

### User Story 1 - Calculate Recipe Requirements for Event (Priority: P1)

As a system component preparing for batch calculation, I need to convert event FG quantities into aggregated recipe requirements, so that downstream features can determine how many batches of each recipe to produce.

**Why this priority**: This is the core calculation that enables all downstream planning features. Without aggregated recipe requirements, batch calculation (F073) cannot proceed. This is pure infrastructure that unlocks the production planning workflow.

**Independent Test**: Can be fully tested by calling `calculate_recipe_requirements(event_id)` with an event that has FG selections with quantities, and verifying the returned dictionary contains correct recipe-to-quantity mappings.

**Acceptance Scenarios**:

1. **Given** an event with a single atomic FG (quantity 24), **When** recipe requirements are calculated, **Then** the result contains one recipe with quantity 24.

2. **Given** an event with a bundle FG (quantity 10) containing 2 atomic items each, **When** recipe requirements are calculated, **Then** the result shows 20 units needed for each component's recipe.

3. **Given** an event with multiple FGs that share the same recipe, **When** recipe requirements are calculated, **Then** the quantities are summed for that recipe.

---

### User Story 2 - Decompose Nested Bundles (Priority: P2)

As a system handling complex product structures, I need to recursively decompose bundles that contain other bundles, so that deeply nested product hierarchies are correctly flattened to atomic recipe requirements.

**Why this priority**: Multi-level nesting is a real-world scenario (e.g., "Gift Set" contains "Cookie Box" which contains individual cookies). Without this, only single-level bundles would work.

**Independent Test**: Can be tested by creating a 3-level nested bundle structure and verifying the decomposition correctly multiplies quantities at each level.

**Acceptance Scenarios**:

1. **Given** a bundle containing another bundle (2-level nesting) with quantity 5, **When** decomposed, **Then** quantities are correctly multiplied through both levels.

2. **Given** a bundle with 3+ levels of nesting, **When** decomposed, **Then** all levels are traversed and final atomic quantities are correct.

3. **Given** a mix of atomic FGs and bundles in the same event, **When** decomposed, **Then** atomic FGs pass through unchanged while bundles are expanded.

---

### User Story 3 - Handle Edge Cases Safely (Priority: P3)

As a system that must be robust, I need to detect circular references and handle missing data gracefully, so that invalid data structures don't cause infinite loops or crashes.

**Why this priority**: Edge case handling ensures system stability. While circular references should be rare (prevented at creation time), the algorithm must handle them safely.

**Independent Test**: Can be tested by attempting to decompose a circular bundle structure and verifying an appropriate error is raised rather than infinite recursion.

**Acceptance Scenarios**:

1. **Given** a bundle that references itself (directly or indirectly), **When** decomposition is attempted, **Then** a circular reference error is raised.

2. **Given** an FG without a linked recipe, **When** mapping to recipe is attempted, **Then** an appropriate validation error is raised.

3. **Given** an event with no FG selections, **When** recipe requirements are calculated, **Then** an empty dictionary is returned.

---

### Edge Cases

- What happens when a bundle contains zero-quantity components? Skip them in decomposition.
- What happens with very large quantities (10,000+)? Python handles large integers natively; no overflow risk.
- What happens when the same atomic FG appears multiple times in a bundle? Each occurrence is processed separately, quantities aggregate correctly.
- What happens when a recipe produces multiple FGs? Each FG maps to its recipe independently; this is expected behavior.

## Requirements

### Functional Requirements

- **FR-001**: System MUST recursively decompose bundle FGs to atomic (FG, quantity) pairs.
- **FR-002**: System MUST multiply quantities correctly at each nesting level during decomposition.
- **FR-003**: System MUST map each atomic FG to its producing recipe (base or variant).
- **FR-004**: System MUST aggregate quantities by recipe, summing when multiple FGs use the same recipe.
- **FR-005**: System MUST return a dictionary mapping Recipe objects to total quantities needed.
- **FR-006**: System MUST detect circular references in bundle structures and raise an error.
- **FR-007**: System MUST handle atomic FGs (non-bundles) by returning them directly with their quantity.
- **FR-008**: System MUST validate that all atomic FGs have an associated recipe.
- **FR-009**: System MUST provide a single service method `calculate_recipe_requirements(event_id)` as the public API.
- **FR-010**: System MUST be pure calculation with no database writes or side effects.

### Key Entities

- **FinishedGood**: Product that can be atomic (linked to a recipe) or a bundle (containing other FGs). Key attributes: is_bundle flag, recipe relationship, bundle_contents.
- **Recipe**: The recipe that produces an atomic FG. Can be base or variant. Key attribute: id.
- **EventFinishedGood**: Junction table linking events to FGs with quantities. Source of input data.
- **Composition/BundleContent**: Junction defining what FGs are contained in a bundle and their quantities.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Decomposition correctly handles bundles with up to 5 levels of nesting.
- **SC-002**: Quantity multiplication is mathematically correct at all nesting levels (verified by test calculations).
- **SC-003**: Recipe aggregation produces correct totals when 3+ FGs share the same recipe.
- **SC-004**: Circular reference detection prevents infinite loops (algorithm terminates within 1 second for any input).
- **SC-005**: Service method returns results in under 100ms for events with up to 50 FG selections.
- **SC-006**: 100% of edge cases (empty event, missing recipe, circular reference) are handled with appropriate responses.

## Assumptions

- The event_finished_goods table contains valid FG IDs and positive quantities (validated by F071).
- Bundle structures are acyclic in normal operation (circular references are exceptional/error cases).
- All atomic FGs have a valid recipe relationship (enforced at FG creation time).
- The existing PlanningService from F068 provides patterns to follow for service method structure.
- F070 implemented bundle decomposition to recipes that can be studied for patterns.

## Out of Scope

- Batch calculation (F073 - consumes output from this feature)
- Variant allocation decisions (F074)
- Ingredient aggregation (F074)
- UI display of recipe requirements
- Caching of decomposition results (future optimization)
- Prevention of circular references at bundle creation time (separate feature)
