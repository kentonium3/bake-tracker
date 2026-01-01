# Feature Specification: Ingredient Hierarchy Taxonomy

**Feature Branch**: `031-ingredient-hierarchy-taxonomy`
**Created**: 2025-12-30
**Status**: Draft
**Input**: User description: "Three-tier hierarchical ingredient taxonomy with self-referential schema, tree traversal services, UI tree widget, and AI-assisted migration of 500+ ingredients."
**Design Reference**: `docs/design/F031_ingredient_hierarchy.md`

---

## Problem Statement

The current ingredient catalog contains 487+ ingredients in a flat list with only a simple category string for organization. This creates significant usability problems:

1. **Navigation Friction**: Users must scroll through hundreds of ingredients to find what they need
2. **No Semantic Relationships**: Cannot express that "Semi-Sweet Chocolate Chips" is a type of "Dark Chocolate" which is a type of "Chocolate"
3. **Fixed Granularity**: Same level of detail used everywhere - can't generalize for shopping lists or filter broadly for reports
4. **Difficult Product Assignment**: Unclear which products belong to which ingredient types

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recipe Ingredient Selection (Priority: P1)

When creating or editing a recipe, the user needs to select specific ingredients. Currently they scroll through 487+ items in a flat list. With hierarchy, they navigate a tree: Chocolate → Dark Chocolate → Semi-Sweet Chocolate Chips.

**Why this priority**: This is the most frequent user interaction with ingredients. Recipe creation is a core workflow and reducing friction here has the highest impact.

**Independent Test**: Can be fully tested by creating a recipe and adding ingredients via the tree widget. Delivers immediate value by reducing selection time from scrolling through 487 items to 3 clicks.

**Acceptance Scenarios**:

1. **Given** a user is adding an ingredient to a recipe, **When** they open the ingredient selector, **Then** they see a hierarchical tree with expandable nodes (not a flat list)
2. **Given** the tree is displayed, **When** the user expands "Chocolate" → "Dark Chocolate", **Then** they see leaf ingredients like "Semi-Sweet Chocolate Chips" that can be selected
3. **Given** the user selects a leaf ingredient (Level 2), **When** they confirm selection, **Then** the ingredient is added to the recipe
4. **Given** the user attempts to select a non-leaf ingredient (Level 0 or 1), **When** they try to confirm, **Then** the system prevents selection and indicates they must choose a specific ingredient
5. **Given** the user types in the search box, **When** they enter "chocolate chips", **Then** matching ingredients are highlighted and their parent branches auto-expand

---

### User Story 2 - Ingredient Catalog Navigation (Priority: P1)

When browsing the ingredient catalog, the user needs to find and manage ingredients organized by type. The tree structure allows drilling down from broad categories to specific items.

**Why this priority**: Catalog management is essential for the primary user (Marianne) to maintain her ingredient database. Tied with P1 as it shares the same underlying infrastructure.

**Independent Test**: Can be fully tested by navigating the Ingredients tab using the tree view. Delivers value by making the 487-item catalog navigable.

**Acceptance Scenarios**:

1. **Given** the user opens the Ingredients tab, **When** the view loads, **Then** ingredients are displayed in a hierarchical tree structure
2. **Given** root-level categories are displayed, **When** the user clicks the expand arrow on "Flour", **Then** mid-tier items like "Wheat Flour" and "Alternative Flour" appear
3. **Given** the user views a leaf ingredient, **When** they look at its details, **Then** they see the full ancestry path (breadcrumb: Chocolate → Dark Chocolate → Semi-Sweet Chips)
4. **Given** the user filters by a root category, **When** they select "Chocolate" filter, **Then** all descendants (all chocolate-related ingredients) are shown

---

### User Story 3 - AI-Assisted Migration (Priority: P2)

The existing 487+ ingredients need to be organized into the three-tier hierarchy. An AI-assisted process analyzes ingredient names and suggests categorization, which the user reviews and approves.

**Why this priority**: Migration is required to populate the hierarchy, but the infrastructure (P1) must exist first. This is a one-time operation that enables the P1 features.

**Independent Test**: Can be tested by exporting ingredients, running AI categorization, reviewing suggestions, and importing the transformed data. Delivers value by automating what would be weeks of manual categorization.

**Acceptance Scenarios**:

1. **Given** the user initiates migration, **When** ingredients are exported, **Then** a JSON file is created with all current ingredient data
2. **Given** exported ingredients are processed, **When** AI analysis completes, **Then** suggested parent relationships and hierarchy levels are generated for each ingredient
3. **Given** AI suggestions are ready, **When** the user reviews them, **Then** they can see the proposed tree structure and modify incorrect assignments
4. **Given** the user approves the hierarchy, **When** they import the transformed data, **Then** all ingredients have correct parent_ingredient_id and hierarchy_level values
5. **Given** low-confidence suggestions exist, **When** displayed to the user, **Then** they are flagged for manual review

---

### User Story 4 - Hierarchy Management (Priority: P3)

Administrators need to create new hierarchy nodes (categories), move ingredients between categories, and maintain the tree structure over time.

**Why this priority**: Management capabilities are needed for ongoing maintenance but not for initial launch. The migration handles initial setup.

**Independent Test**: Can be tested by creating a new category, moving an ingredient to it, and verifying the tree updates correctly.

**Acceptance Scenarios**:

1. **Given** the user wants to add a new root category, **When** they create "Spices" at Level 0, **Then** it appears as a new expandable root node
2. **Given** the user wants to add a mid-tier category, **When** they create "Ground Spices" under "Spices", **Then** it appears at Level 1 under the parent
3. **Given** the user wants to move an ingredient, **When** they drag "Cinnamon" from one category to another, **Then** its parent relationship updates and the tree reflects the change
4. **Given** the user attempts to create a Level 3 ingredient (below leaf), **When** they try to add a child to a Level 2 ingredient, **Then** the system prevents it (max depth = 2)
5. **Given** the user attempts to move a category under itself, **When** they try to create a circular reference, **Then** the system detects and prevents the cycle

---

### Edge Cases

- **Empty categories**: What happens when a root or mid-tier category has no children? Display as empty expandable node.
- **Orphaned ingredients**: What happens if a parent is deleted? Block deletion if children exist.
- **Search with no matches**: What happens when search finds nothing? Display "No matching ingredients" message.
- **Very deep trees**: What happens if someone tries to nest beyond 3 levels? System enforces max depth of 3 (levels 0, 1, 2).
- **Duplicate names**: What happens if two ingredients have the same display name at different hierarchy levels? Allowed - slugs remain unique.
- **Migration failures**: What happens if AI categorization fails for some ingredients? Flag as "uncategorized" for manual assignment.

---

## Requirements *(mandatory)*

### Functional Requirements

**Schema & Data Model**

- **FR-001**: System MUST support a self-referential parent-child relationship on ingredients via `parent_ingredient_id` foreign key
- **FR-002**: System MUST track hierarchy depth via `hierarchy_level` field with values 0 (root), 1 (mid-tier), or 2 (leaf)
- **FR-003**: System MUST enforce maximum hierarchy depth of 3 levels (0, 1, 2)
- **FR-004**: System MUST prevent circular references in the hierarchy (an ingredient cannot be its own ancestor)
- **FR-005**: System MUST only allow leaf-level ingredients (Level 2) to have associated Products
- **FR-006**: System MUST only allow leaf-level ingredients (Level 2) to be used in Recipes

**Tree Traversal**

- **FR-007**: System MUST provide method to retrieve all root-level ingredients (Level 0)
- **FR-008**: System MUST provide method to retrieve direct children of any ingredient
- **FR-009**: System MUST provide method to retrieve all descendants (recursive) of any ingredient
- **FR-010**: System MUST provide method to retrieve ancestors (path to root) for breadcrumb display
- **FR-011**: System MUST provide method to retrieve all leaf ingredients, optionally filtered by ancestor

**User Interface**

- **FR-012**: System MUST display ingredients in a hierarchical tree widget with expand/collapse functionality
- **FR-013**: System MUST support search within the tree that auto-expands matching branches
- **FR-014**: System MUST display breadcrumb path showing ingredient ancestry
- **FR-015**: System MUST enforce context-appropriate selection (recipes require leaf-only selection)
- **FR-016**: System MUST visually distinguish selectable leaf nodes from non-selectable category nodes

**Migration**

- **FR-017**: System MUST support exporting all ingredients to JSON format for transformation
- **FR-018**: System MUST support AI-assisted categorization that suggests hierarchy relationships
- **FR-019**: System MUST support manual review and editing of suggested hierarchy before import
- **FR-020**: System MUST support importing transformed hierarchy data with validation
- **FR-021**: System MUST preserve all existing ingredient data during migration (no data loss)

**Validation & Integrity**

- **FR-022**: System MUST prevent deletion of ingredients that have children
- **FR-023**: System MUST prevent deletion of ingredients that have associated products
- **FR-024**: System MUST prevent deletion of ingredients that are used in recipes
- **FR-025**: System MUST validate hierarchy_level matches parent depth + 1 on create/update

### Key Entities

- **Ingredient** (modified): Existing entity gains `parent_ingredient_id` (self-referential FK, nullable) and `hierarchy_level` (integer 0-2). The existing `category` field is deprecated but retained for rollback safety.

- **Hierarchy Levels**:
  - Level 0 (Root): Broad categories like "Chocolate", "Flour", "Sugar" - cannot have products
  - Level 1 (Mid-tier): Functional types like "Dark Chocolate", "All-Purpose Flour" - cannot have products
  - Level 2 (Leaf): Specific ingredients like "Semi-Sweet Chocolate Chips" - CAN have products and be used in recipes

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from root to target leaf ingredient in 3 or fewer clicks for common selections
- **SC-002**: Search finds and highlights matching ingredients with parent branches auto-expanded in under 1 second
- **SC-003**: All 487+ existing ingredients are successfully migrated with hierarchy assignments and zero data loss
- **SC-004**: Recipe creation workflow requires no additional clicks compared to current flat selection (tree selection replaces scrolling)
- **SC-005**: 90%+ of AI-suggested categorizations are accepted without modification (measured during migration review)
- **SC-006**: System prevents 100% of invalid hierarchy operations (circular refs, over-depth, non-leaf in recipes)
- **SC-007**: Primary user (Marianne) can successfully create a recipe using the tree widget on first attempt without assistance

---

## Assumptions

1. **AI Categorization Accuracy**: AI analysis of ingredient names will achieve ~90%+ accuracy in suggesting hierarchy relationships based on naming patterns (e.g., "Semi-Sweet Chocolate Chips" → parent "Dark Chocolate" → grandparent "Chocolate")

2. **Three Tiers Sufficient**: The 3-level hierarchy (root/mid/leaf) provides adequate granularity for baking ingredients. Deeper nesting is not required for the current domain.

3. **Migration is One-Time**: The bulk AI-assisted migration is performed once during feature deployment. Ongoing hierarchy management uses the manual admin interface.

4. **Existing Category Field**: The current `category` string field will be deprecated but retained in schema for rollback safety. It will not be displayed in UI after migration.

5. **CustomTkinter Tree Widget**: The CustomTkinter framework supports or can be extended to support a hierarchical tree widget with expand/collapse and search functionality.

---

## Parallelization Opportunities

This feature has components that can be developed in parallel after initial schema work:

| Component | Dependencies | Safe for Parallel Dev |
|-----------|--------------|----------------------|
| Schema changes (columns, indexes) | None | Foundation - do first |
| Tree traversal services | Schema | Yes - isolated service module |
| UI tree widget | Schema, can stub services | Yes - different file set |
| Migration tooling | Schema, export services | Yes - separate scripts |
| Service integration tests | Services complete | After services |
| UI integration | All components | Final integration |

**Recommended parallel assignments**:
- **Claude**: Schema changes → Service layer integration → Final UI integration
- **Gemini**: UI tree widget prototype → Migration tooling → Service unit tests

---

## Out of Scope

- Multiple parallel taxonomies (e.g., separate hierarchies for baking vs. BBQ domains) - future platform consideration
- User-specific custom hierarchies - single global hierarchy for desktop phase
- Drag-and-drop tree reordering in UI - use explicit move operations instead
- Real-time collaborative hierarchy editing - desktop is single-user
