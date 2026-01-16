# Feature Specification: Workflow-Aligned Navigation Cleanup

**Feature Branch**: `055-workflow-aligned-navigation-cleanup`
**Created**: 2026-01-15
**Status**: Draft
**Input**: See docs/design/F055_ui_navigation_cleanup.md

---

## Problem Statement

The current UI navigation doesn't match how users actually work. Mode order is illogical (Observe is last but should be first), menu structure is inconsistent (Materials has submenus but Ingredients doesn't), and broken/unused UI elements waste screen space. Users need navigation that reflects their natural workflow: check status, manage catalog, plan events, purchase supplies, make goods, deliver to recipients.

---

## User Scenarios & Testing

### User Story 1 - Navigate Modes in Workflow Order (Priority: P1)

A user opens the application and wants to follow their natural workflow: first check the dashboard to see current status, then manage catalog items if needed, plan upcoming events, record purchases, produce goods, and track deliveries.

**Why this priority**: Core navigation affects every user session. If modes are in wrong order, every interaction feels awkward.

**Independent Test**: Can be fully tested by clicking through mode tabs and verifying order matches: Observe, Catalog, Plan, Purchase, Make, Deliver

**Acceptance Scenarios**:

1. **Given** the application is open, **When** user views mode tabs, **Then** they appear in order: Observe, Catalog, Plan, Purchase, Make, Deliver
2. **Given** the application is open, **When** user presses Ctrl+1, **Then** Observe mode activates
3. **Given** the application is open, **When** user presses Ctrl+2 through Ctrl+6, **Then** corresponding modes activate in order
4. **Given** the application is open, **When** user clicks Deliver mode, **Then** a placeholder message displays indicating "Delivery workflows coming soon"

---

### User Story 2 - Find Catalog Items in Logical Groups (Priority: P1)

A user in Catalog mode wants to find related items grouped together. Ingredients and their Products should be together, Recipes and their Finished Units should be together, and Packaging-related items (Finished Goods, Packages) should be grouped.

**Why this priority**: Users access Catalog mode frequently. Logical grouping reduces time to find items and matches mental model.

**Independent Test**: Can be fully tested by navigating Catalog menu and verifying 4 top-level groups with appropriate subitems

**Acceptance Scenarios**:

1. **Given** user is in Catalog mode, **When** they view the menu, **Then** they see 4 top-level groups: Ingredients, Materials, Recipes, Packaging
2. **Given** user expands Ingredients group, **When** they view subitems, **Then** they see: Ingredient Catalog, Food Products
3. **Given** user expands Materials group, **When** they view subitems, **Then** they see: Material Catalog, Material Units, Material Products
4. **Given** user expands Recipes group, **When** they view subitems, **Then** they see: Recipes Catalog, Finished Units
5. **Given** user expands Packaging group, **When** they view subitems, **Then** they see: Finished Goods (Food Only), Finished Goods (Bundles), Packages
6. **Given** user clicks any submenu item, **When** the tab loads, **Then** existing functionality works unchanged

---

### User Story 3 - Follow Purchase Workflow Order (Priority: P2)

A user in Purchase mode wants to follow the natural shopping workflow: first check what inventory they have, then record purchases they've made, then create shopping lists for what they still need.

**Why this priority**: Purchase mode is used frequently but less often than mode switching or catalog access. Correct order improves workflow but current order is just inconvenient, not blocking.

**Independent Test**: Can be fully tested by viewing Purchase mode tabs and verifying order

**Acceptance Scenarios**:

1. **Given** user is in Purchase mode, **When** they view tabs, **Then** they appear in order: Inventory, Purchases, Shopping Lists
2. **Given** user navigates between Purchase tabs, **When** they click each tab, **Then** existing functionality works unchanged

---

### User Story 4 - See More Data Without Broken Elements (Priority: P2)

A user wants to see as much data as possible in grids without broken UI elements wasting space. The top section showing "0 Ingredients 0 Products" is broken and unhelpful. The tree view in Catalog/Inventory is unused.

**Why this priority**: More visible data improves usability, but this is polish rather than core functionality.

**Independent Test**: Can be fully tested by measuring visible grid rows before and after, and verifying no errors

**Acceptance Scenarios**:

1. **Given** user is in Catalog mode, **When** viewing any tab, **Then** no broken top section with "0 counts" is visible
2. **Given** user is in any mode, **When** viewing data grids, **Then** 3-5 additional rows are visible compared to before
3. **Given** user is in Catalog/Inventory tab, **When** viewing the tab, **Then** no tree view component is present
4. **Given** user removes broken elements, **When** navigating the application, **Then** no errors occur

---

### Edge Cases

- What happens when user presses Ctrl+6 (Deliver mode)? Shows placeholder, no error.
- What happens when Finished Goods tab needs to show both Food and Bundles? User selects the appropriate filtered view from Packaging submenu.
- What happens if a menu group has no items? Groups always have items in current implementation.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display modes in order: Observe, Catalog, Plan, Purchase, Make, Deliver
- **FR-002**: System MUST map keyboard shortcuts Ctrl+1 through Ctrl+6 to the six modes in order
- **FR-003**: System MUST display Deliver mode with placeholder message "Delivery workflows coming soon"
- **FR-004**: Catalog mode MUST have 4 top-level menu groups: Ingredients, Materials, Recipes, Packaging
- **FR-005**: Ingredients group MUST contain: Ingredient Catalog, Food Products
- **FR-006**: Materials group MUST contain: Material Catalog, Material Units, Material Products (existing structure preserved)
- **FR-007**: Recipes group MUST contain: Recipes Catalog, Finished Units
- **FR-008**: Packaging group MUST contain: Finished Goods, Packages
- **FR-009**: ~~DEFERRED~~ Finished Goods Food/Bundle split requires model changes (no is_bundle flag exists)
- **FR-010**: ~~DEFERRED~~ See FR-009 - will be addressed in future feature when model supports distinction
- **FR-011**: Purchase mode tabs MUST display in order: Inventory, Purchases, Shopping Lists
- **FR-012**: System MUST remove the broken top section showing "0 Ingredients 0 Products 0 Recipes"
- **FR-013**: System MUST remove the tree view component from Catalog/Inventory tab
- **FR-014**: All existing tab functionality MUST be preserved after navigation restructuring

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can access any mode within 2 clicks or 1 keyboard shortcut
- **SC-002**: Users can find any catalog item within its logical group in the first location they check
- **SC-003**: Grid views display 3-5 additional rows after removing broken UI elements
- **SC-004**: Zero navigation-related errors occur during normal application use
- **SC-005**: 100% of existing tab functionality works unchanged after restructuring

---

## Out of Scope

- Deliver mode functionality (placeholder only - future feature)
- Shopping Lists tab functionality changes (preserve as-is)
- Tab content changes (only navigation/organization)
- Finished Goods Food/Bundle split (deferred - model lacks is_bundle distinction)
- Hierarchy Admin UI (completed in F052)

---

## Assumptions

1. The current Materials submenu structure is the pattern to follow for other groups
2. ~~Finished Goods can be filtered by a "is_bundle" or similar flag~~ - INVALID: Model lacks this distinction, deferred
3. The broken top section and tree view have no hidden dependencies that would break when removed
4. Keyboard shortcut handling can be extended from 5 shortcuts to 6

---

## Dependencies

- F052 (Hierarchy Admin) - completed, provides tree-based management so removing Catalog tree view is safe
- Existing Materials submenu implementation - pattern to copy for Ingredients/Recipes/Packaging
