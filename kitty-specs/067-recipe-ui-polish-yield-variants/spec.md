# Feature Specification: Recipe UI Polish - Yield Information and Variant Grouping

**Feature Branch**: `067-recipe-ui-polish-yield-variants`
**Created**: 2025-01-25
**Status**: Draft
**Input**: See docs/func-spec/F067_recipe_ui_polish_yield_and_variants.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Edit Recipe Dialog Clarity (Priority: P1)

As a recipe manager, when I edit a recipe's yield information, I can clearly understand what each field represents because there are column labels above the input fields and the help text uses consistent "Finished Unit" terminology.

**Why this priority**: The Edit Recipe dialog is the primary interface for defining recipe yields. Unclear fields lead to data entry errors and user confusion.

**Independent Test**: Open Edit Recipe dialog, verify column labels ("Finished Unit Name", "Unit", "Qty/Batch") are visible and aligned above yield row inputs, verify help text reads "Each row defines a Finished Unit and quantity per batch for this recipe."

**Acceptance Scenarios**:

1. **Given** a user opens the Edit Recipe dialog, **When** viewing the Yield Information section, **Then** column labels "Finished Unit Name", "Unit", and "Qty/Batch" appear above the respective input fields
2. **Given** a user opens the Edit Recipe dialog, **When** viewing the Yield Information section, **Then** help text displays "Each row defines a Finished Unit and quantity per batch for this recipe." without excessive whitespace below the section title
3. **Given** a user opens the Edit Recipe dialog, **When** viewing the Yield Information section, **Then** the vertical spacing matches other sections (Basic Information, Recipe Ingredients)

---

### User Story 2 - Recipe Catalog Variant Grouping (Priority: P1)

As a recipe manager, when I view the recipe catalog grid, I can see variant recipes visually grouped under their base recipes with indentation and a visual indicator, making the parent-child relationship immediately clear.

**Why this priority**: Without visual grouping, users cannot easily identify which recipes are variants of which base recipes, making catalog management confusing.

**Independent Test**: View Recipe Catalog with base recipes and variants, verify variants appear indented under their base recipe with "↳" indicator.

**Acceptance Scenarios**:

1. **Given** a recipe catalog with base recipes and variants, **When** the grid is displayed, **Then** base recipes appear at top level and variant recipes appear indented with "↳" indicator under their base recipe
2. **Given** a recipe catalog with multiple variants per base, **When** the grid is displayed, **Then** all variants are grouped under their base recipe and sorted alphabetically within the group
3. **Given** a recipe catalog with only base recipes, **When** the grid is displayed, **Then** recipes appear in alphabetical order without indentation

---

### User Story 3 - Create Variant Dialog Polish (Priority: P2)

As a recipe manager, when I create a variant recipe, the dialog layout is clear with labels above fields, help text in logical positions, and the section for customizing finished unit names is clearly labeled "Finished Unit Name(s)".

**Why this priority**: The Create Variant dialog has confusing layout issues that slow down variant creation and cause user frustration.

**Independent Test**: Open Create Variant dialog, verify "Recipe Variant Name" label is above the input field with help text between them, verify "Finished Unit Name(s):" section title, verify no "Base:" labels clutter the interface.

**Acceptance Scenarios**:

1. **Given** a user opens Create Variant dialog, **When** viewing the variant name section, **Then** label reads "Recipe Variant Name" (left-justified above field), help text appears between label and input, input field appears below help text
2. **Given** a user opens Create Variant dialog, **When** viewing the finished unit section, **Then** section title reads "Finished Unit Name(s):" (not "Variant Yields:")
3. **Given** a user opens Create Variant dialog, **When** viewing the finished unit input fields, **Then** no "Base:" labels appear, and input fields are left-justified

---

### User Story 4 - Production Ready Default (Priority: P2)

As a recipe manager, when I create a new recipe, the "Production Ready" checkbox defaults to checked because most recipes are intended for production.

**Why this priority**: The current default (unchecked) is counterintuitive since most recipes are production-ready, causing unnecessary extra clicks.

**Independent Test**: Create a new recipe, verify "Production Ready" checkbox is checked by default.

**Acceptance Scenarios**:

1. **Given** a user opens the New Recipe dialog, **When** viewing the Production Ready checkbox, **Then** it is checked by default
2. **Given** a user edits an existing recipe with production_ready=False, **When** viewing the Production Ready checkbox, **Then** it remains unchecked (existing value preserved)

---

### User Story 5 - Finished Units Grid Variant Grouping (Priority: P3)

As a recipe manager, when I view the Finished Units grid, I can see variant finished units visually grouped under their base finished units, mirroring the recipe catalog behavior.

**Why this priority**: Consistency with recipe catalog grouping improves overall UX, but lower priority since finished units grid is used less frequently.

**Independent Test**: View Finished Units grid with base and variant finished units, verify variants appear indented under their corresponding base with "↳" indicator.

**Acceptance Scenarios**:

1. **Given** a finished units grid with base and variant units, **When** the grid is displayed, **Then** variant finished units appear indented with "↳" indicator under their base finished unit (relationship determined via recipe.base_recipe_id)
2. **Given** multiple variants per base recipe, **When** the grid is displayed, **Then** all variant finished units are grouped and sorted alphabetically under their base

---

### Edge Cases

- What happens when a base recipe has no variants? (Display normally without indentation)
- What happens when a variant recipe's base is deleted? (Orphaned variant should display at top level)
- What happens when recipe has multiple finished units? (Each finished unit gets its own row in yield section)
- How does system handle empty finished unit name in variant creation? (Validation error, require non-empty name)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Edit Recipe dialog MUST display column labels "Finished Unit Name", "Unit", "Qty/Batch" above yield input fields
- **FR-002**: Edit Recipe dialog MUST display help text "Each row defines a Finished Unit and quantity per batch for this recipe." with minimal whitespace after section title
- **FR-003**: Edit Recipe dialog MUST use consistent spacing in Yield Information section matching other sections
- **FR-004**: New recipes MUST default to production_ready=True (checkbox checked)
- **FR-005**: Recipe Catalog grid MUST display variant recipes indented under their base recipe with "↳" visual indicator
- **FR-006**: Recipe Catalog grid MUST sort base recipes alphabetically, with variants sorted alphabetically within each group
- **FR-007**: Create Variant dialog MUST display "Recipe Variant Name" label above input field with help text between label and field
- **FR-008**: Create Variant dialog MUST use section title "Finished Unit Name(s):" instead of "Variant Yields:"
- **FR-009**: Create Variant dialog MUST NOT display "Base:" labels before finished unit input fields
- **FR-010**: Create Variant dialog MUST left-justify all input fields
- **FR-011**: Finished Units grid MUST display variant finished units indented under their base finished unit with "↳" visual indicator
- **FR-012**: Finished Units grid MUST determine variant relationship via recipe.base_recipe_id

### Key Entities

- **Recipe**: Has optional base_recipe_id linking variants to their base recipe
- **FinishedUnit**: Linked to Recipe via recipe_id; variant relationship derived from parent recipe's base_recipe_id
- **RecipeFormDialog**: UI component for editing recipe yield information
- **VariantCreationDialog**: UI component for creating recipe variants
- **Recipe Catalog Grid**: Treeview displaying all recipes with hierarchical grouping
- **Finished Units Grid**: Treeview displaying all finished units with hierarchical grouping

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify yield field purposes without hovering or guessing due to visible column labels
- **SC-002**: Users can identify variant-base relationships at a glance in recipe catalog (visual grouping visible)
- **SC-003**: Users can create variant recipes with fewer clicks/corrections due to improved dialog layout
- **SC-004**: New recipe creation requires zero extra clicks for production_ready setting (correct default)
- **SC-005**: Visual consistency maintained across all modified sections (spacing matches existing patterns)
- **SC-006**: No layout regressions in other dialog sections after changes

## Out of Scope

- Changing yield inheritance logic (completed in F063/F066)
- Service primitive implementation (completed in F066)
- Yield editing restrictions for variants (completed in F066)
- Adding new recipe functionality
- Recipe deletion or archival features
- Database schema changes

## Assumptions

- CustomTkinter grid/pack layout patterns from existing codebase will be followed
- Existing recipe service queries are sufficient (may need minor grouping logic in UI layer)
- "↳" unicode character renders correctly in the UI font
- Window minimum size can accommodate additional column labels without scrolling issues
