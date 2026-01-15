# Feature Specification: Context-Rich Export Fixes

**Feature Branch**: `053-context-rich-export-fixes`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "See docs/design/F053_context_rich_export_fixes.md"

## Summary

Context-rich export functionality has several usability issues discovered during first use: incorrect file prefix, missing entity types, single-select limitation, no bulk export option, and inconsistent button text. This feature addresses all five issues to make the export workflow more intuitive and complete.

## User Scenarios & Testing

### User Story 1 - Export Multiple Entity Types at Once (Priority: P1)

As a user preparing data for AI-assisted augmentation, I want to export multiple entity types in a single operation so that I don't have to repeat the export process for each entity type.

**Why this priority**: This is the primary workflow improvement. Users frequently need to export all or multiple entity types for AI processing but are currently forced to export one at a time, requiring 5+ repetitive actions.

**Independent Test**: Can be fully tested by selecting multiple checkboxes and verifying all selected entities are exported to separate files.

**Acceptance Scenarios**:

1. **Given** the export dialog is open with checkboxes for entity types, **When** I check Ingredients, Recipes, and Products, **Then** clicking export creates three separate files (aug_ingredients.json, aug_recipes.json, aug_products.json)
2. **Given** checkboxes are available, **When** I check "All", **Then** all 7 entity checkboxes become checked
3. **Given** "All" is checked, **When** I uncheck any single entity, **Then** "All" becomes unchecked but other entities remain checked
4. **Given** all individual entities are manually checked, **When** the last one is checked, **Then** "All" checkbox automatically becomes checked
5. **Given** no checkboxes are checked, **When** I click export, **Then** validation prevents export and shows message to select at least one entity

---

### User Story 2 - Export Products and Material Products (Priority: P1)

As a user maintaining my catalog, I want to export Products and Material Products with context-rich data so that I have complete coverage of my inventory for AI-assisted data enhancement.

**Why this priority**: These entity types contain critical catalog data (brand information, pricing, supplier details) but are currently missing from export options, creating an incomplete workflow.

**Independent Test**: Can be fully tested by selecting Products or Material Products and verifying the export file contains the entity data with context.

**Acceptance Scenarios**:

1. **Given** the export dialog is open, **When** I view the entity list, **Then** I see Products and Material Products as available options
2. **Given** Products is selected, **When** I click export, **Then** aug_products.json is created with product data including context
3. **Given** Material Products is selected, **When** I click export, **Then** aug_material_products.json is created with material product data including context

---

### User Story 3 - Correct File Naming for Augmentation Exports (Priority: P2)

As a user organizing export files, I want context-rich exports to use the "aug_" prefix so that I can easily distinguish augmentation files from other export types in my file system.

**Why this priority**: File naming consistency helps users manage their workflow. The current "view_" prefix works functionally but is misleading about the file's purpose.

**Independent Test**: Can be fully tested by exporting any entity type and verifying the filename starts with "aug_" instead of "view_".

**Acceptance Scenarios**:

1. **Given** I export Ingredients, **When** the file is created, **Then** it is named aug_ingredients.json (not view_ingredients.json)
2. **Given** I export any entity type, **When** files are saved, **Then** all use the "aug_" prefix consistently

---

### User Story 4 - Clear Button Text (Priority: P3)

As a user navigating the export dialog, I want the button text to say "File" instead of "View" so that the action (exporting to file) is clear and consistent with other export buttons.

**Why this priority**: Cosmetic consistency improvement. Lower priority but improves overall UI coherence.

**Independent Test**: Can be visually verified by opening the export dialog and reading the button text.

**Acceptance Scenarios**:

1. **Given** the export dialog is open, **When** I view the context-rich export button, **Then** it reads "Export Context-Rich File" (not "Export Context-Rich View")

---

### Edge Cases

- What happens when user clicks export with no entities selected? System prevents export with validation message requiring at least one selection.
- What happens when exporting entity types with no data? Creates file with empty array or shows informative message that no records exist.
- What if export location is not writable? Standard file dialog error handling applies (existing behavior).

## Requirements

### Functional Requirements

- **FR-001**: System MUST use "aug_" prefix for all context-rich export filenames instead of "view_"
- **FR-002**: System MUST include Products in the entity type selection list
- **FR-003**: System MUST include Material Products in the entity type selection list
- **FR-004**: System MUST use checkboxes for entity type selection to enable selecting multiple entities
- **FR-005**: System MUST provide an "All" checkbox that selects all entity types when checked
- **FR-006**: System MUST deselect all entity types when "All" checkbox is unchecked
- **FR-007**: System MUST automatically check "All" when all individual entities are manually checked
- **FR-008**: System MUST automatically uncheck "All" when any individual entity is unchecked
- **FR-009**: System MUST validate that at least one entity is selected before allowing export
- **FR-010**: System MUST export all selected entities when multiple are checked (creating separate files for each)
- **FR-011**: Button text MUST read "Export Context-Rich File" instead of "Export Context-Rich View"

### Key Entities

- **Products**: Food items with brand/package information - currently missing from export options
- **Material Products**: Material items with brand/supplier information - currently missing from export options
- **Entity Types**: Complete list after this feature: Ingredients, Products, Recipes, Finished Units, Finished Goods, Materials, Material Products (7 total, up from 5)

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 7 entity types are available for context-rich export (increased from 5)
- **SC-002**: Users can export all entities in a single operation (reduced from 5+ separate operations)
- **SC-003**: 100% of context-rich export files use "aug_" prefix
- **SC-004**: Button text matches pattern of other export buttons ("File" instead of "View")
- **SC-005**: Full catalog export requires only 2 user actions (check "All", click export) instead of 5+

## Out of Scope

- Adding new entity types beyond Products and Material Products
- Changing the export file format or data structure
- Import functionality (separate feature)
- Export location/path selection changes
- Progress indicator enhancements

## Assumptions

- Export service already has patterns for exporting Products and Material Products data (similar to other entities)
- Multi-file export is supported by the existing export infrastructure
- Checkbox widgets are available in the UI framework being used
