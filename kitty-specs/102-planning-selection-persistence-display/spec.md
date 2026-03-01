# Feature Specification: Planning Selection Persistence Display

**Feature Branch**: `102-planning-selection-persistence-display`
**Created**: 2026-02-28
**Status**: Draft
**Input**: User description: "docs/func-spec/F102_planning_selection_persistence_display.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saved Recipe Selections Visible on Load (Priority: P1)

User opens the Planning tab and selects an event that has a saved draft plan with recipe selections. Instead of seeing a blank placeholder ("Select recipe category to see available recipes"), the user immediately sees the saved recipes displayed with checkboxes checked and a contextual label indicating these are the current plan selections. The selection count is accurate.

**Why this priority**: This is the core problem — the disconnect between blank selection areas and populated batch calculations confuses the user and risks accidental plan overwrites. Without this, the planning workspace is incoherent for any in-progress plan.

**Independent Test**: Can be fully tested by creating an event, selecting recipes, saving, relaunching the app (or switching away and back to the tab), and verifying the saved recipes are rendered with checkboxes checked.

**Acceptance Scenarios**:

1. **Given** an event with 5 saved recipe selections, **When** user selects this event in the Planning tab, **Then** all 5 recipes are displayed with checkboxes checked and a contextual label (e.g., "Saved plan selections") is shown.

2. **Given** an event with saved recipe selections displayed on load, **When** user selects a category filter, **Then** the display transitions to the filtered view with saved selections pre-checked where visible, and selections persist in memory for items not currently visible.

3. **Given** an event with NO saved recipe selections, **When** user selects this event in the Planning tab, **Then** the blank placeholder ("Select recipe category to see available recipes") is shown as before (no regression).

4. **Given** saved recipes displayed on load, **When** user views the selection count label, **Then** it accurately reflects the number of saved selections.

---

### User Story 2 - Saved FG Selections with Quantities Visible on Load (Priority: P1)

User opens the Planning tab and selects an event that has saved finished good selections with quantities. Instead of seeing a blank placeholder ("Select filters to see available finished goods"), the user immediately sees the saved FGs displayed with checkboxes checked, quantities populated in entry fields, and a contextual label.

**Why this priority**: Same core problem as recipes — FG selections are plan inputs that feed batch calculations. Equally important to display.

**Independent Test**: Can be fully tested by creating an event, selecting FGs with quantities, saving, relaunching the app, and verifying saved FGs and quantities are rendered.

**Acceptance Scenarios**:

1. **Given** an event with 3 saved FG selections (each with a quantity), **When** user selects this event in the Planning tab, **Then** all 3 FGs are displayed with checkboxes checked, quantities shown in entry fields, and a contextual label is shown.

2. **Given** an event with saved FG selections displayed on load, **When** user selects a filter (recipe category, item type, or yield type), **Then** the display transitions to the filtered view with saved selections pre-checked and quantities preserved for visible items.

3. **Given** an event with NO saved FG selections, **When** user selects this event in the Planning tab, **Then** the blank placeholder ("Select filters to see available finished goods") is shown as before (no regression).

4. **Given** saved FGs displayed on load, **When** user clicks "Show All Selected" toggle, **Then** it functions correctly (no conflict with the initial saved-selections display).

---

### User Story 3 - Coherent Plan View: Selections to Calculations (Priority: P2)

User opens the Planning tab for an event with a saved draft plan and sees the complete picture: recipe selections, FG selections with quantities, and batch calculations — all visible together. The user understands at a glance what the plan contains without needing to interact with any filters.

**Why this priority**: This is the UX payoff of Stories 1 and 2 — the planning workspace becomes a coherent summary of the plan in progress. Important but dependent on the rendering fixes.

**Independent Test**: Can be tested by loading a plan with recipes, FGs, and batch calculations, and verifying all three sections display populated data simultaneously.

**Acceptance Scenarios**:

1. **Given** an event with saved recipes, saved FGs with quantities, and batch calculations, **When** user selects this event, **Then** all three sections display their data — no blank areas between populated sections.

2. **Given** the coherent plan view is displayed, **When** user reads the contextual labels, **Then** user understands these are the current saved plan selections (not a filter result that needs to be re-entered).

---

### User Story 4 - Filter Workflow Preserved for Modifications (Priority: P2)

User views saved selections on load, decides to modify the plan, and uses the category/type filters to browse and change selections. The existing filter-first workflow works identically to how it works during initial plan creation.

**Why this priority**: Ensures the rendering fix doesn't break the established filter/modify workflow. Must not regress.

**Independent Test**: Can be tested by loading saved selections, applying filters, changing selections, and verifying save/cancel still works correctly.

**Acceptance Scenarios**:

1. **Given** saved recipe selections displayed on load, **When** user selects a recipe category from the dropdown, **Then** the display shows recipes in that category with saved selections pre-checked.

2. **Given** saved FG selections displayed on load, **When** user changes any of the three filter dropdowns, **Then** the display shows filtered FGs with saved selections pre-checked and quantities preserved.

3. **Given** modified selections after filtering, **When** user clicks Save, **Then** the updated selections persist to the database correctly.

4. **Given** modified selections after filtering, **When** user clicks Cancel, **Then** selections revert to the original saved state.

---

### Edge Cases

- What happens when an event has saved recipes but no saved FGs? (Recipe frame shows selections, FG frame shows blank placeholder — mixed state is valid)
- What happens when a previously selected recipe has been deleted from the catalog? (Saved ID won't match any recipe — should be silently excluded from display, count reflects only valid selections)
- What happens when the user rapidly switches between events? (Each event load should fully replace the previous display with the new event's selections or blank state)
- What happens when selections are displayed on load and user clicks Cancel without making changes? (No-op — plan unchanged)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render saved recipe selections with checked checkboxes when loading an event that has persisted recipe associations.
- **FR-002**: System MUST render saved FG selections with checked checkboxes and populated quantity fields when loading an event that has persisted FG associations.
- **FR-003**: System MUST display a contextual label (e.g., "Saved plan selections") to distinguish the initial loaded view from a filter result.
- **FR-004**: System MUST show the blank filter-first placeholder when loading an event with no saved selections (preserve current behavior for new plans).
- **FR-005**: System MUST transition smoothly from the saved-selections view to a filtered view when the user applies a filter, with saved selections pre-checked in the filtered results.
- **FR-006**: System MUST display accurate selection count labels on initial load (reflecting saved selection totals).
- **FR-007**: System MUST NOT require any service layer or model changes — the fix is purely in the UI rendering layer.
- **FR-008**: System MUST preserve all existing save/cancel, filter persistence, and "Show All Selected" functionality without regression.

### Key Entities *(existing — no changes)*

- **EventRecipe**: Junction table storing event-to-recipe associations (already persisted correctly)
- **EventFinishedGood**: Junction table storing event-to-FG associations with quantities (already persisted correctly)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User sees saved recipe selections within 1 second of selecting an event with a draft plan (no manual filter interaction required).
- **SC-002**: User sees saved FG selections with quantities within 1 second of selecting an event with a draft plan (no manual filter interaction required).
- **SC-003**: 100% of existing filter, save/cancel, and "Show All Selected" workflows continue to function without regression.
- **SC-004**: User can distinguish saved plan selections from filter results via contextual labeling on first viewing without guidance.
- **SC-005**: App relaunch produces the same plan display as the initial save — selections loaded from database and rendered identically.
