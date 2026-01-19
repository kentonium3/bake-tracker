# User Story: Deferred Packaging Decisions

## Story Overview

**As a** holiday baker planning events  
**I want to** specify generic packaging requirements without committing to specific designs  
**So that** I can plan food production with cost estimates and inventory awareness while deferring aesthetic packaging decisions until later

## User Value

- **Planning flexibility**: Make food decisions first, packaging aesthetics later
- **Cost visibility**: Get ballpark estimates without premature commitment
- **Inventory awareness**: Know what's available without forced selection
- **Decision timing**: Choose specific packaging anytime from planning through assembly
- **Real-world adaptability**: Handle scenarios like "cookies too big for boxes, switch to bags"

## Acceptance Criteria

### 1. Event Planning: Generic Packaging Selection

**Given** I am planning an event and defining finished goods  
**When** I specify packaging for a recipe  
**Then** I can choose between:
- Selecting a specific packaging material (existing behavior)
- Selecting a generic packaging product (new behavior)

**UI Requirements**:
- Radio button choice: "Specific material" vs "Generic product"
- When "Generic product" selected:
  - Dropdown shows packaging products (e.g., "Cellophane Bags 6x10")
  - Display available inventory summary: "82 bags across 4 designs"
  - Show inventory breakdown: "Snowflakes (30), Holly (25), Stars (20), Snowmen (7)"
  - Display estimated cost based on average price across available materials
  - Label clearly shows "Estimated cost"

**Example Flow**:
```
User planning 50 bags of cookies:
1. Select: ○ Specific material  ● Generic product
2. Choose: "Cellophane Bags 6x10" from dropdown
3. Enter quantity: 50
4. See: "Available: 82 bags (4 designs) ✓"
5. See: "Est. cost: $12.50"
6. Save requirement
```

### 2. Shopping List: Abstract Representation

**Given** I have planned events with generic packaging requirements  
**When** I generate a shopping list  
**Then** packaging items show as generic products until specific materials are assigned

**Display Requirements**:
- Generic item: "Cellophane Bags 6x10: 50 needed"
- Not: "Snowflake design (30), Holly design (20)"
- Rationale: User may not find exact designs when shopping

**Example**:
```
Shopping List - Holiday Cookie Event
Ingredients:
- Flour, All-Purpose: 10 lbs
- Chocolate Chips, Semi-Sweet: 3 lbs

Packaging:
- Cellophane Bags 6x10: 50 needed (estimated $12.50)
- Cardboard Boxes 4x3x2: 30 needed (estimated $18.75)
```

### 3. Production Dashboard: Pending Decision Indicator

**Given** I have in-progress productions with unassigned generic packaging  
**When** I view the production dashboard  
**Then** I see a clear indicator that packaging decisions are pending

**UI Requirements**:
- Visual indicator (⚠️ icon or badge) on affected productions
- Clickable link to packaging assignment screen
- Tooltip: "Packaging needs selection"

**Example**:
```
In Progress Productions:
┌──────────────────────────────────────┐
│ Chocolate Chip Cookies (200 units)   │
│ ├─ Mixing: Complete ✓                │
│ ├─ Baking: In Progress...            │
│ └─ Assembly: Pending ⚠️              │
│     └─ Packaging needs selection     │ ← Clickable
└──────────────────────────────────────┘
```

### 4. Assembly Definition: Material Assignment

**Given** I am ready to assign specific materials to generic packaging requirements  
**When** I open the assembly definition screen  
**Then** I can assign specific materials from available inventory

**UI Requirements**:
- Clear section showing unassigned requirements
- Checkbox interface to select materials
- Quantity input for each selected material
- Running total: "Assigned: X / Y needed"
- Validation: Total assigned must equal total needed
- Two action buttons:
  - "Assign Materials" - Saves assignments
  - "Keep Generic" - Defers decision (only if not at assembly stage)

**Example**:
```
Assembly Details: Chocolate Chip Cookies
┌─────────────────────────────────────────┐
│ Packaging Requirements:                  │
│                                           │
│ ⚠️ Selection needed:                     │
│   Cellophane Bags 6x10 (50 needed)      │
│                                           │
│   Assign specific materials:             │
│   ┌───────────────────────────────────┐ │
│   │ ☐ Snowflakes  Avail: 30  Use: [30]│ │
│   │ ☑ Holly       Avail: 25  Use: [20]│ │
│   │ ☐ Stars       Avail: 20  Use: [__]│ │
│   │ ☐ Snowmen     Avail:  7  Use: [__]│ │
│   │                                   │ │
│   │ Total assigned: 50 / 50 needed ✓  │ │
│   └───────────────────────────────────┘ │
│                                           │
│   [Assign Materials] [Keep Generic]      │
└─────────────────────────────────────────┘
```

### 5. Assembly Progress: Decision Enforcement

**Given** I am recording assembly progress for a recipe with unassigned packaging  
**When** I attempt to record assembly completion  
**Then** the system prompts me to finalize packaging decisions

**UI Requirements**:
- Show clear message about unassigned packaging
- Provide quick assignment interface OR link to full assignment screen
- Allow bypass option: "Record Assembly Anyway" for backfill scenarios
- If bypassed, flag the event for later packaging reconciliation

**Example**:
```
Record Assembly Progress:
┌─────────────────────────────────────────┐
│ ⚠️ Packaging not finalized               │
│                                           │
│ Cellophane Bags 6x10 (50 needed)        │
│                                           │
│ Quick assign or go to details:           │
│ [Quick Assign] [Assembly Details]        │
│                                           │
│ OR                                        │
│                                           │
│ [Record Assembly Anyway]                 │
│ (You can finalize packaging later)       │
└─────────────────────────────────────────┘
```

### 6. Cost Estimates: Dynamic Updates

**Given** I have generic packaging requirements  
**When** I view cost estimates at different stages  
**Then** costs update based on assignment status:
- **Generic (unassigned)**: Average price across available materials, labeled "Estimated"
- **Assigned**: Actual price of selected materials, labeled "Actual"
- **Shopping list**: Uses estimated costs for generic items

**Example**:
```
Event Cost Summary:
Ingredients: $125.50 (actual)
Packaging: $31.25 (estimated) ← Changes to "actual" when assigned
Total: $156.75
```

## Edge Cases & Scenarios

### Scenario A: Change of Plans During Assembly
**Context**: Cookies too large for planned boxes  
**Behavior**: 
- User can modify BOM in assembly definition
- Remove box requirement, add bag requirement
- System recalculates costs and inventory availability

### Scenario B: Insufficient Inventory at Assignment Time
**Context**: Planning used 50 bags, only 45 remain at assembly  
**Behavior**:
- System shows "Available: 45 / 50 needed ⚠️"
- User can assign partial quantities
- Flags shortage for shopping/substitution

### Scenario C: Multiple Stages of Refinement
**Context**: User assigns materials, then changes mind  
**Behavior**:
- Allow re-opening assignment screen
- Can change selections before assembly completion
- System updates cost estimates accordingly

### Scenario D: Shopping Before Assignment
**Context**: User purchases generic "6x10 bags" before deciding which designs  
**Behavior**:
- Add to inventory as specific materials (must choose design when purchasing)
- Generic requirement updates availability totals
- Assignment screen shows newly purchased materials

## Validated Design Decisions

Based on user validation with primary stakeholder (Marianne):

1. **Planning stage**: Radio button + inventory summary provides sufficient information for food decisions ✓
2. **Decision timing**: Dashboard indicator and assembly screen are appropriate touchpoints ✓
3. **Assembly enforcement**: Allow "record anyway" with backfill option (user-requested scenario) ✓
4. **Shopping list**: Generic representation is flexible and matches real-world shopping ✓
5. **Quick assign**: Quick assignment interface at assembly time is preferred ✓
6. **Cost estimates**: Average price is appropriate given substitution/replacement variability ✓
7. **Missing scenarios**: All discussed scenarios are covered ✓

## Out of Scope (Future Enhancements)

- Automatic assignment algorithms ("use oldest first", "spread evenly")
- Packaging templates ("use same as last holiday event")
- Partial commitment ("definitely use Snowflakes, undecided on rest")
- Multi-layer assembly with nested generic requirements

## Next Steps

This validated user story is ready for:
1. Technical specification generation via spec-kitty workflow
2. Implementation via Claude Code
3. User acceptance testing protocol development
