# Feature 026: Deferred Packaging Decisions

**Validated by**: Marianne (Primary User)
**Date**: 2025-11-18
**Status**: VALIDATED

## User Story

**As a** holiday baker planning events,  
**I want to** specify generic packaging requirements without committing to specific designs,  
**So that** I can plan food production with cost estimates and inventory awareness while deferring aesthetic packaging decisions until later.

## Acceptance Criteria

### 1. Event Planning: Generic Packaging Selection
- **GIVEN** I am planning an event and defining finished goods
- **WHEN** I specify packaging for a recipe
- **THEN** I can choose between:
  - Selecting a specific packaging material (existing behavior)
  - Selecting a generic packaging product (new behavior)
- **UI REQUIREMENTS**:
  - Radio button choice: "Specific material" vs "Generic product"
  - When "Generic product" selected:
    - Dropdown shows packaging products (e.g., "Cellophane Bags 6x10")
    - Display available inventory summary: "82 bags across 4 designs"
    - Show inventory breakdown: "Snowflakes (30), Holly (25), Stars (20), Snowmen (7)"
    - Display estimated cost based on average price across available materials
    - Label clearly shows "Estimated cost"

### 2. Shopping List: Abstract Representation
- **GIVEN** I have planned events with generic packaging requirements
- **WHEN** I generate a shopping list
- **THEN** packaging items show as generic products until specific materials are assigned
- **DISPLAY REQUIREMENTS**:
  - Generic item: "Cellophane Bags 6x10: 50 needed"
  - Not: "Snowflake design (30), Holly design (20)"

### 3. Production Dashboard: Pending Decision Indicator
- **GIVEN** I have in-progress productions with unassigned generic packaging
- **WHEN** I view the production dashboard
- **THEN** I see a clear indicator that packaging decisions are pending
- **UI REQUIREMENTS**:
  - Visual indicator (⚠️ icon or badge) on affected productions
  - Clickable link to packaging assignment screen
  - Tooltip: "Packaging needs selection"

### 4. Assembly Definition: Material Assignment
- **GIVEN** I am ready to assign specific materials to generic packaging requirements
- **WHEN** I open the assembly definition screen
- **THEN** I can assign specific materials from available inventory
- **UI REQUIREMENTS**:
  - Clear section showing unassigned requirements
  - Checkbox interface to select materials
  - Quantity input for each selected material
  - Running total: "Assigned: X / Y needed"
  - Validation: Total assigned must equal total needed

### 5. Assembly Progress: Decision Enforcement
- **GIVEN** I am recording assembly progress for a recipe with unassigned packaging
- **WHEN** I attempt to record assembly completion
- **THEN** the system prompts me to finalize packaging decisions
- **UI REQUIREMENTS**:
  - Show clear message about unassigned packaging
  - Provide quick assignment interface OR link to full assignment screen
  - Allow bypass option: "Record Assembly Anyway" for backfill scenarios

### 6. Cost Estimates: Dynamic Updates
- **GIVEN** I have generic packaging requirements
- **WHEN** I view cost estimates at different stages
- **THEN** costs update based on assignment status:
  - **Generic (unassigned)**: Average price across available materials, labeled "Estimated"
  - **Assigned**: Actual price of selected materials, labeled "Actual"
  - **Shopping list**: Uses estimated costs for generic items
