# Feature Specification: Nested Recipes (Sub-Recipe Components)

*Path: kitty-specs/012-nested-recipes/spec.md*

**Feature Branch**: `012-nested-recipes`
**Created**: 2025-12-09
**Status**: Draft
**Input**: User description: Add hierarchical recipe support where parent recipes can include other recipes as components with batch multiplier quantities, recursive cost calculation, shopping list aggregation, and circular reference prevention. Maximum 3 levels of nesting.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add Sub-Recipe to Parent Recipe (Priority: P1)

As a baker, I want to create a recipe that includes other recipes as components (e.g., "Frosted Layer Cake" includes "Chocolate Cake", "Vanilla Cake", and "Buttercream Frosting" recipes) so I can organize complex multi-part baked goods.

**Why this priority**: This is the core capability that enables all other features. Without the ability to add sub-recipes, no other functionality can exist.

**Independent Test**: Can be fully tested by creating two simple recipes, then creating a parent recipe that references both as components. Delivers value by allowing recipe organization.

**Acceptance Scenarios**:

1. **Given** I have an existing "Buttercream Frosting" recipe, **When** I create a new "Frosted Layer Cake" recipe and add "Buttercream Frosting" as a component with quantity "2" (batches), **Then** the parent recipe shows "Buttercream Frosting" in its components list with quantity "2x"
2. **Given** I am editing a recipe with existing components, **When** I remove a sub-recipe component, **Then** it is removed from the parent recipe without affecting the original sub-recipe
3. **Given** I have a recipe with sub-recipes, **When** I view the recipe details, **Then** I see both direct ingredients and sub-recipe components clearly distinguished

---

### User Story 2 - Recursive Cost Calculation (Priority: P2)

As a baker, I want to see the total cost of a recipe including all sub-recipe costs so I can accurately price complex items.

**Why this priority**: Cost accuracy is essential for pricing baked goods. This builds on Story 1's component structure.

**Independent Test**: Can be tested by creating a parent recipe with one sub-recipe where both have known ingredient costs. Verify the parent's total cost equals direct ingredients + (sub-recipe cost x quantity).

**Acceptance Scenarios**:

1. **Given** a parent recipe with direct ingredients costing $5 and a sub-recipe costing $3 (quantity 2x), **When** I view the parent recipe cost, **Then** I see total cost of $11 ($5 + $3 x 2)
2. **Given** a 3-level nested recipe (Parent → Child → Grandchild), **When** I view the parent recipe cost, **Then** the cost correctly includes all levels of the hierarchy
3. **Given** a sub-recipe's ingredient costs change, **When** I view the parent recipe cost, **Then** the parent cost reflects the updated sub-recipe cost

---

### User Story 3 - Shopping List Aggregation (Priority: P2)

As a baker, I want the shopping list to include all ingredients from all sub-recipes so I don't forget anything when planning an event.

**Why this priority**: Equal priority with cost calculation - both are core value propositions that build on Story 1.

**Independent Test**: Can be tested by creating a recipe with sub-recipes containing overlapping ingredients, then generating a shopping list. Verify all ingredients appear with aggregated quantities.

**Acceptance Scenarios**:

1. **Given** a parent recipe with direct ingredient "flour 2 cups" and a sub-recipe with "flour 1 cup", **When** I generate a shopping list, **Then** flour appears as "3 cups" (aggregated)
2. **Given** a recipe with 2x of a sub-recipe that uses "butter 0.5 cups", **When** I generate a shopping list, **Then** butter appears as "1 cup" (0.5 x 2)
3. **Given** a 3-level nested recipe, **When** I generate a shopping list, **Then** all ingredients from all levels are included and aggregated correctly

---

### User Story 4 - Sub-Recipe Reuse (Priority: P3)

As a baker, I want to reuse sub-recipes across multiple parent recipes (e.g., "Buttercream Frosting" used in both "Frosted Layer Cake" and "Cupcakes") so I don't have to duplicate ingredient lists.

**Why this priority**: Reuse is an efficiency feature that naturally emerges from the component model. Lower priority because it works implicitly once Stories 1-3 are complete.

**Independent Test**: Can be tested by adding the same sub-recipe to two different parent recipes, then verifying both parents reference the same sub-recipe and cost updates propagate to both.

**Acceptance Scenarios**:

1. **Given** "Buttercream Frosting" is a component of both "Frosted Layer Cake" and "Cupcakes", **When** I update "Buttercream Frosting" ingredients, **Then** both parent recipes reflect the updated cost
2. **Given** "Buttercream Frosting" is used in multiple recipes, **When** I view "Buttercream Frosting" details, **Then** I can see which recipes use it as a component (optional enhancement)

---

### User Story 5 - Import/Export with Sub-Recipes (Priority: P3)

As a baker, I want to import and export recipes that have sub-recipe components so I can share complex recipes or restore from backup.

**Why this priority**: Data portability is important but secondary to core functionality.

**Independent Test**: Can be tested by exporting a recipe with sub-recipes, then importing into a fresh database. Verify the hierarchy is preserved.

**Acceptance Scenarios**:

1. **Given** I export a recipe with sub-recipe components, **When** I import the export file, **Then** the recipe-component relationships are restored correctly
2. **Given** I import a recipe that references a sub-recipe by slug, **When** the sub-recipe already exists, **Then** the parent links to the existing sub-recipe
3. **Given** I import a recipe that references a non-existent sub-recipe, **When** import runs, **Then** I receive a warning and the component reference is skipped (not a fatal error)

---

### Edge Cases

- What happens when a user tries to create a circular reference (Recipe A includes B, B includes A)?
  - System prevents the save and displays an error message
- What happens when a user tries to nest deeper than 3 levels?
  - System prevents adding the component and displays an error explaining the limit
- What happens when a sub-recipe is deleted while it's a component of another recipe?
  - System prevents deletion and lists the parent recipes that depend on it
- What happens when a sub-recipe has no cost (ingredients without prices)?
  - Cost calculation shows partial cost with indicator that some costs are unknown
- How does the system handle a sub-recipe with quantity 0?
  - System validates quantity must be > 0

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to add an existing recipe as a component of another recipe
- **FR-002**: System MUST store a batch multiplier quantity for each recipe component (positive number, e.g., 0.5, 1, 2)
- **FR-003**: System MUST allow optional notes for each recipe component (e.g., "prepare day before")
- **FR-004**: System MUST prevent circular references at any depth (direct or indirect)
- **FR-005**: System MUST enforce maximum nesting depth of 3 levels
- **FR-006**: System MUST calculate recipe cost recursively including all sub-recipe costs multiplied by their quantities
- **FR-007**: System MUST aggregate ingredients from all recipe levels for shopping lists, combining quantities of identical ingredients
- **FR-008**: System MUST prevent deletion of a recipe that is used as a component in other recipes
- **FR-009**: System MUST validate that a sub-recipe exists before allowing it to be added as a component
- **FR-010**: System MUST support import/export of recipe component relationships using recipe slugs
- **FR-011**: System MUST handle import gracefully when referenced sub-recipes don't exist (warn, skip component, continue)
- **FR-012**: System MUST display sub-recipe components distinctly from direct ingredients in the recipe view
- **FR-013**: System MUST allow editing and removing recipe components from a parent recipe

### Key Entities

- **RecipeComponent**: Junction entity linking a parent recipe to a child recipe. Contains: parent recipe reference, child recipe reference, batch quantity (multiplier), optional notes. Represents "Recipe A uses N batches of Recipe B".
- **Recipe** (existing, extended): Gains relationship to its sub-recipes (components) and relationship to recipes that use it as a component (parents).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a 3-level nested recipe structure in under 5 minutes
- **SC-002**: Cost calculation for a 3-level nested recipe completes instantly (no perceptible delay)
- **SC-003**: Shopping list generation for recipes with sub-recipes includes 100% of required ingredients
- **SC-004**: Circular reference attempts are blocked with clear error message in 100% of cases
- **SC-005**: Existing recipes without sub-recipes continue to function identically (backward compatibility)
- **SC-006**: Import/export round-trip preserves all recipe component relationships

## Assumptions

- Batch multiplier is sufficient for quantity specification (no need for volume/weight units for sub-recipes)
- The existing Recipe model uses slugs as stable identifiers for import/export
- Shopping list aggregation can combine quantities when ingredients have the same unit
- The 3-level limit is sufficient for real-world baking scenarios (confirmed by user)

## Out of Scope

- Automatic scaling of sub-recipe quantities based on parent yield
- Batch/production tracking (Feature 013)
- Production recording UI (Feature 014)
- Conversion between different units when aggregating ingredients

## Dependencies

- Feature 011 (Packaging & BOM Foundation) - Complete
