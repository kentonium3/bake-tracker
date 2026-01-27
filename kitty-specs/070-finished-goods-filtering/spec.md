# Feature Specification: Finished Goods Filtering for Event Planning

**Feature Branch**: `070-finished-goods-filtering`
**Created**: 2026-01-26
**Status**: Draft
**Input**: see docs/func-spec/F070_finished_goods_filtering.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Makeable Finished Goods (Priority: P1)

As a baker planning an event, after selecting which recipes I want to make (F069), I need to see only the finished goods I can actually produce with those recipes. This prevents me from accidentally selecting FGs that require recipes I haven't chosen.

**Why this priority**: This is the core value proposition. Without filtering, the FG list shows items the user cannot make, leading to confusion and invalid selections.

**Independent Test**: Can be fully tested by selecting recipes in the Planning Tab and verifying the FG list updates to show only available items.

**Acceptance Scenarios**:

1. **Given** an event with recipes A and B selected, **When** I view the finished goods list, **Then** I see only FGs that use recipe A or B (and no others)
2. **Given** an event with no recipes selected, **When** I view the finished goods list, **Then** I see an empty list (no FGs available)
3. **Given** an atomic FG that uses recipe C, **When** recipe C is not selected, **Then** that FG is hidden from the list

---

### User Story 2 - Bundle Availability Based on All Components (Priority: P1)

As a baker, when I have a bundle (gift box containing multiple items), I need it to appear only when ALL the component recipes are selected. Partial availability would lead to incomplete bundles.

**Why this priority**: Bundles are a key use case for gift packages. Incorrect bundle availability would cause production failures.

**Independent Test**: Can be tested by creating a bundle with 3 component FGs, selecting only 2 of the 3 required recipes, and verifying the bundle does not appear.

**Acceptance Scenarios**:

1. **Given** a bundle containing FGs that require recipes A, B, and C, **When** I have selected recipes A, B, and C, **Then** the bundle appears in the available FG list
2. **Given** a bundle containing FGs that require recipes A, B, and C, **When** I have selected only recipes A and B, **Then** the bundle is hidden (not available)
3. **Given** a nested bundle (bundle containing another bundle), **When** all atomic recipes at every level are selected, **Then** the nested bundle appears as available

---

### User Story 3 - Real-Time List Updates (Priority: P2)

As a baker, when I change my recipe selection, I need the FG list to update immediately so I can see the impact of my choices without refreshing or navigating away.

**Why this priority**: Real-time feedback is essential for an intuitive planning experience, but the feature works without it (manual refresh acceptable as fallback).

**Independent Test**: Can be tested by having the FG list visible, toggling a recipe selection, and observing the FG list update without any explicit refresh action.

**Acceptance Scenarios**:

1. **Given** I am viewing the FG list with recipe A selected, **When** I deselect recipe A, **Then** FGs requiring recipe A disappear from the list immediately
2. **Given** I am viewing the FG list without recipe B selected, **When** I select recipe B, **Then** FGs requiring recipe B appear in the list immediately

---

### User Story 4 - Automatic Removal of Invalid FG Selections (Priority: P2)

As a baker, if I deselect a recipe that an already-selected FG depends on, the system should automatically remove that FG selection and notify me. This prevents invalid state where I have FGs selected but can't actually make them.

**Why this priority**: Data integrity protection. Without this, users could end up with planning data that's internally inconsistent.

**Independent Test**: Can be tested by selecting an FG, then deselecting its required recipe, and verifying the FG selection is removed with a notification.

**Acceptance Scenarios**:

1. **Given** I have selected FG "Chocolate Cookies" which requires recipe "Cookie Base", **When** I deselect recipe "Cookie Base", **Then** FG "Chocolate Cookies" is automatically removed from my event's FG selections
2. **Given** an FG was automatically removed, **When** the removal occurs, **Then** I see a notification explaining what was removed and why
3. **Given** a bundle FG is selected, **When** I deselect any one of its required recipes, **Then** the bundle is automatically removed from selections

---

### Edge Cases

- What happens when a bundle contains itself (circular reference)? System must detect and handle gracefully (error or skip).
- What happens when decomposition encounters a deeply nested bundle (10+ levels)? System must handle without stack overflow.
- What happens when a recipe is deleted from the system while selected for an event? Handled by DB constraints (out of scope for this feature).
- What happens when user rapidly toggles recipe selections? UI must debounce updates to prevent race conditions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a service method to check if a finished good is available given a list of selected recipe IDs
- **FR-002**: System MUST recursively decompose bundles to determine all required atomic recipe IDs
- **FR-003**: System MUST return the list of missing recipe IDs when an FG is unavailable (for diagnostic purposes)
- **FR-004**: System MUST filter the finished goods display to show only available FGs (hide unavailable)
- **FR-005**: System MUST update the FG list immediately when recipe selection changes
- **FR-006**: System MUST automatically remove FG selections that become invalid when a recipe is deselected
- **FR-007**: System MUST notify the user when FG selections are automatically removed
- **FR-008**: System MUST detect and handle circular references in bundle structures
- **FR-009**: Bundle decomposition MUST return unique recipe IDs (no duplicates)

### Key Entities

- **FinishedGood**: Represents a producible item. Can be atomic (linked to single recipe) or bundle (contains other FGs).
- **Bundle**: A finished good composed of other finished goods. May be nested (bundle of bundles).
- **EventRecipe**: Junction between Event and Recipe, representing selected recipes (from F069).
- **EventFinishedGood**: Junction between Event and FinishedGood, representing selected FGs for production.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see only makeable FGs after selecting recipes - 100% accuracy in filtering
- **SC-002**: FG list updates within 500ms of recipe selection change (perceived as instant)
- **SC-003**: Bundle decomposition correctly identifies all required recipes for bundles up to 5 levels deep
- **SC-004**: Zero invalid FG selections persist after recipe deselection (data integrity maintained)
- **SC-005**: User receives clear notification within 1 second when FG selections are auto-removed

## Out of Scope

- Quantity specification for finished goods (F071)
- Recipe search or filtering within selection UI
- FG search or filtering (beyond availability filtering)
- Sorting FGs by category
- Favoriting or recently-used FG tracking
