# Phase 2 Planning: Workflow & UX Redesign

**Document Version**: 1.0  
**Status**: Ready for Design Discussion  
**Date**: December 2024

---

## Executive Summary

Phase 1 established a **stable, functional foundation** with core data models and basic workflows. Real-world testing during data augmentation revealed significant gaps in data architecture, workflows, and UX that must be addressed for the application to fulfill its purpose as a practical seasonal baking management tool.

**This document defines requirements for Phase 2 redesign** based on actual usage patterns and discovered limitations.

---

## Current State Assessment

### ✅ What's Working (Phase 1 Accomplishments)

**Data Foundation**:
- Core models implemented: Ingredients, Products, Suppliers, Purchases, Inventory, Recipes
- Referential integrity and validation working
- CRUD operations functional
- Import/export workflows established
- Data management tools (force delete with safety, online vendors, soft delete)

**Architecture**:
- Layered architecture (models, services, UI) established
- SQLite database with migration capability
- CustomTkinter UI framework operational
- Spec-kitty development workflow functional

### ⚠️ What Needs Refinement

**Data Models**: Stable but will evolve based on workflow requirements
- Ingredient taxonomy needs hierarchical structure
- Recipe system needs redesign for templates vs. instances
- Additional fields/tables likely needed

**Recipe System**: Basic structure exists but insufficient for real workflows
- No support for base/variant relationships
- No recipe instantiation for production runs
- Missing scaling capabilities

### ❌ Critical Gaps Blocking Real-World Use

1. **Ingredient Ontology** - Flat list insufficient for contextual selection/filtering
2. **Recipe Management** - Template vs. instance model needed
3. **Planning Workflow** - Disjointed, no clear entry point or progression
4. **UI Organization** - Doesn't reflect natural work modes (catalog vs. planning vs. production)
5. **Purchase Capture** - No low-friction way to record purchases and prices
6. **Observability** - No visibility into current state (inventory, recent purchases, event readiness)

---

## Phase 2 Requirements

### 1. Ingredient Ontology & Taxonomy 🔴 CRITICAL

**Priority**: Critical (Foundational - affects most other requirements)

#### Current Limitations
- Single, flat, fine-grained ingredient list
- Insufficient for contextual filtering, selection, and reporting
- Same granularity used regardless of context (recipe creation, shopping lists, catalog management)

#### Failure Example
Selecting chocolate for recipe requires scrolling through:
- Dark Chocolate Baking Chips (Semi-Sweet)
- Dark Chocolate Baking Chips (Bitter-Sweet)
- Milk Chocolate Baking Chips
- White Chocolate Chips
- etc.

When generating shopping list, user wants "chocolate chips" (any acceptable brand).  
When filtering product catalog, user wants "chocolate" category.

**Current system cannot provide appropriate granularity per context.**

#### Requirements

**Data Model**:
- **Three-tier hierarchical taxonomy** with parent/child relationships
  - Example: `Chocolate` → `Dark Chocolate` → `Semi-Sweet Chocolate Chips`
- Self-referential relationship: `parent_ingredient_id` (nullable)
- Maintain existing ingredient properties at all levels

**Management UI** (Admin function):
- Add, delete, rename, move ingredients within hierarchy
- Delete protection for terms in use
- System-wide cascade updates for renames/moves
- Validation: prevent cycles, orphans

**Context-Sensitive Selection**:
- When adding ingredient to recipe: Show full tree, select most granular level
- When generating shopping list: Allow selection at mid-level (e.g., "chocolate chips")
- When filtering catalog: Allow selection at any level
- Tree traversal widget (collapsible nodes, search within tree)

**Reporting & Filtering**:
- Filter by any level of hierarchy
- Report usage across all child ingredients (e.g., total chocolate usage)
- Support "profile" filters for different cooking domains (baking vs. BBQ)

#### Commentary
- Supports future extensibility to other cooking domains
- Unknown if industry ontology exists (USDA FoodData Central?); research needed
- Should evolve with user feedback in multi-user web version

---

### 2. Recipe System Redesign 🔴 HIGH

**Priority**: High (Core workflow blocker)

#### Current Limitations
1. **No Recipe Instantiation**: Recipe treated as "live" object; changes affect historical records
2. **No Base/Variant Structure**: Each recipe standalone; variants are unrelated duplicates
3. **No Scaling**: Must manually create new recipe for 2x, 3x batches
4. **No Production Flag**: Can't mark experimental recipes as non-production

#### Failure Examples
- Changing recipe retroactively changes all historical production costs/yields
- Doubling batch size requires two separate production runs (can't just "make 2x")
- Creating strawberry variant of raspberry recipe requires full duplication

#### Requirements

**Recipe as Template** (Class vs. Instance paradigm):
```
Recipe (Template/Definition)
  ├─ Recipe Snapshot (Instance for specific production run)
  │    ├─ Captured at production time
  │    ├─ Immutable for historical integrity
  │    └─ Links to ProductionRun
```

**Base/Variant Relationships**:
- `base_recipe_id` (nullable FK to self)
- "Duplicate to Variant" function
- Display hierarchy in recipe list
- Filter by base recipe

**Scaling Functions**:
- Simple scaling: Multiply all quantities (1x, 2x, 3x)
- Store scale factor with recipe snapshot
- Phase 3: Proportional scaling (non-linear adjustments)

**Additional Fields**:
- `is_production_ready` (boolean) - Hide experimental recipes from production selection
- `variant_name` (string) - "Strawberry", "Double Batch", etc.
- `base_recipe_id` (int, nullable) - Link to base recipe

**UI Requirements**:
- Tree view showing base recipes with variants
- "Scale Recipe" dialog when adding to production
- Ingredient selection via hierarchical tree (see Requirement #1)
- Clear visual distinction: Template vs. Instance

#### Data Model Changes
```sql
-- New table
CREATE TABLE recipe_snapshots (
    id INTEGER PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    production_run_id INTEGER REFERENCES production_runs(id),
    snapshot_date DATETIME NOT NULL,
    scale_factor DECIMAL NOT NULL DEFAULT 1.0,
    -- Denormalized recipe data at capture time
    recipe_name TEXT,
    ingredients_json TEXT,  -- JSON snapshot of ingredients/quantities
    yield_quantity DECIMAL,
    notes TEXT
);

-- Modified recipes table
ALTER TABLE recipes ADD COLUMN base_recipe_id INTEGER REFERENCES recipes(id);
ALTER TABLE recipes ADD COLUMN variant_name TEXT;
ALTER TABLE recipes ADD COLUMN is_production_ready BOOLEAN DEFAULT FALSE;
```

---

### 3. Output Modes 🟡 MEDIUM

**Priority**: Medium (Expands use cases)

#### Current Limitations
- Only supports "packages for individuals" output mode
- Two other common modes not supported

#### Requirements

**Three Output Modes**:

1. **Packages** (Current) - Individual recipient packages
   - Example: Gift boxes, mail-order packages
   
2. **Batch/Tray Delivery** (New) - Bulk service
   - Example: Trays for bake sale, fundraiser, fair
   - No per-person tracking needed
   - Count: "5 trays of 24 cookies each"
   
3. **Servings** (New) - Known guest count
   - Example: Wedding, party (200 guests, 2 cookies per person)
   - No individual names, but known quantities per person

**Implementation**:
- Event-level setting: Output mode
- Affects finished goods → package relationship
- Affects production quantity calculations
- Affects labeling/packaging workflows

---

### 4. UI/UX Organization 🔴 HIGH

**Priority**: High (Usability critical)

#### Current Limitations
- No clear distinction between work modes (catalog vs. planning vs. production)
- Inconsistent tab layouts (headers, search, filters, actions differ)
- No visibility into current state (recent purchases, inventory status)
- No dashboard/summary views
- No obvious workflow entry points

#### Failure Examples
- User doesn't know where to start when planning new event
- No way to see "am I ready for this event?" status
- Purchase activity invisible (no recent activity view)
- Switching between planning and catalog management is jarring

#### Requirements

**Work Mode Structure**:

Reorganize application into **5 clear modes**:

```
┌─ BAKE TRACKER ──────────────────────────────────────────────┐
│                                                              │
│  [Catalog] [Plan] [Shop] [Produce] [Observe]               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Mode 1: CATALOG** (Define things)
- Ingredients, Products, Recipes (templates)
- Finished Good definitions, Assembly definitions
- Relatively stable, infrequent changes
- Admin/maintenance activity

**Mode 2: PLAN** (Forward-looking)
- Events, Production planning
- Recipe selection, Quantity calculations
- Shopping list generation
- Cost estimation
- Primary entry point for new work

**Mode 3: SHOP** (Acquire materials)
- Shopping lists (by supplier)
- Purchase recording (with AI assist)
- Inventory updates
- Recent purchase view

**Mode 4: PRODUCE** (Execute production)
- Production runs, Baking/cooking
- Recipe execution (using snapshots)
- Yield tracking, Loss recording
- Assembly/packaging

**Mode 5: OBSERVE** (Monitor status)
- Dashboard showing:
  - Upcoming events
  - Inventory status vs. needs
  - Recent purchases
  - Production progress
  - Finished goods inventory
- Event readiness indicators

**Consistent Tab Layouts** (within each mode):
```
┌─ [Mode Name] ────────────────────────────────────────────────┐
│  [Action Buttons]                                [Refresh]   │
│                                                               │
│  Search: [_________]  Filters: [___] [___] [___]            │
│                                                               │
│  ┌─ List ───────────────────────────────────────────────┐   │
│  │ [Data Grid]                                           │   │
│  └───────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

**Mode-Specific Dashboards**:
- Each mode shows relevant status/context at top
- Example (PLAN mode): "3 events this month, 2 need shopping lists"
- Example (SHOP mode): "5 items on Costco list, last purchase 2 days ago"

---

### 5. Planning Workflow Redesign 🔴 HIGH

**Priority**: High (Core workflow blocker)

#### Current Limitations
- Planning only works smoothly if all recipes/assemblies pre-exist
- No guided workflow for new events
- User must jump between tabs to build prerequisites
- No clear progression or status visibility

#### Failure Example
1. Create event "Holiday Bake Sale"
2. Try to add packages → Not defined yet
3. Go to define packages → Finished goods not defined
4. Go to define finished goods → Recipes don't exist
5. Go to create recipes → Ingredients missing
6. **User is lost, frustrated, quits**

#### Requirements

**Guided Event Planning Wizard**:

```
┌─ Plan Event: Holiday Bake Sale ─────────────────────────────┐
│                                                              │
│  Step 1 of 5: Event Details                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                              │
│  Name: [Holiday Bake Sale__________]                        │
│  Date: [2024-12-15]                                         │
│  Output Mode: ○ Packages  ● Batch/Tray  ○ Servings         │
│                                                              │
│  [Cancel] [Next: Select Recipes →]                          │
└──────────────────────────────────────────────────────────────┘

```

**Workflow Steps**:

1. **Event Details**
   - Name, date, output mode
   
2. **Recipe Selection**
   - Select from existing recipes
   - Button: "+ Create New Recipe" (branches to recipe wizard, returns)
   - Shows if ingredient hierarchy needed

3. **Finished Goods Definition**
   - Auto-creates from recipes or select existing
   - Quantities needed
   - Yield calculations

4. **Assembly Definition** (if applicable)
   - Package types (boxes, trays, etc.)
   - Contents per package

5. **Review & Calculate**
   - Total batches needed
   - Shopping list preview (by supplier)
   - Cost estimate
   - Inventory check: ✅ Have / ⚠️ Need to purchase

**Context-Aware Branching**:
- At any step, can branch to create missing prerequisites
- Returns to wizard after creating item
- Wizard remembers state, doesn't lose progress

**AI-Assisted Planning** (Phase 3 vision, inform Phase 2 design):
```
User: I need to plan for a fundraiser on Sept 3rd
AI: What do you want to make?
User: Chocolate chip cookies, magic bars, mince tarts
AI: You have recipes for cookies and bars. No recipe for tarts. 
    Shall I search your sources?
[Continues conversation-style workflow]
```

**Phase 2 should enable manual version of this dialogue.**

---

### 6. Purchase Workflow & AI Assist 🔴 HIGH

**Priority**: High (Major friction point)

#### Current Limitations
- No low-effort way to record purchases + prices
- No shopping list generation
- No visibility into recent purchases
- Manual price entry is painful (100+ items = hours)

#### Failure Example
User shops at Costco with 20 items. Must:
1. Keep receipts
2. Later, manually type each item + price into system
3. Process takes 30-45 minutes
4. Error-prone, tedious
5. **User abandons price tracking**

#### Requirements

**Purchase Management UI** (Phase 2):
- View recent purchases (sortable, filterable)
- Manual add/edit purchases
- Bulk import from CSV
- Inventory status summary vs. event needs
- Shopping lists (generated, organized by supplier)

**AI-Assisted Purchase Capture** (Phase 2 Demo / Phase 3 Production):

**Architecture** (Async, batch-oriented for demo):
```
[Phone App] → Take photo of UPC + price tag
            ↓
[Google AI Studio] → Process images → Extract data
            ↓
[JSON File] → Uploaded to laptop
            ↓
[Bake Tracker] → Import purchases → Update inventory
```

**Requirements**:
1. **Phone component** (Gemini API / AI Studio):
   - Capture UPC code image
   - Capture price tag / shelf label image
   - Generate JSON: `{upc, price, quantity, timestamp}`
   
2. **Desktop component** (Bake Tracker):
   - Monitor folder for JSON files
   - Parse and validate
   - Match UPC → Product
   - Create Purchase records
   - Update Inventory
   
3. **Fallback** (Manual review):
   - Flag unmatched UPCs
   - Allow user to map UPC → Product
   - Learn from corrections

**Phase 3 Evolution**:
- Real-time sync (not batch)
- Voice input ("I'm buying 2 bags of flour at $5.99 each")
- Receipt photo scanning (OCR entire receipt)

**Commentary**:
- **This is THE critical usability blocker**
- Without easy purchase capture, app has no appeal
- Must prioritize even if means simplified demo version for Phase 2

---

### 7. Finished Goods Inventory 🟡 MEDIUM

**Priority**: Medium (Architecture prep for Phase 3)

#### Current State
- Deferred in Phase 1
- No finished goods inventory tracking

#### Requirements

**Put architecture in place now** (even if UI deferred):

**Data Model**:
```sql
CREATE TABLE finished_goods_inventory (
    id INTEGER PRIMARY KEY,
    finished_good_id INTEGER REFERENCES finished_goods(id),
    production_run_id INTEGER REFERENCES production_runs(id),
    quantity DECIMAL NOT NULL,
    date_produced DATE NOT NULL,
    expiration_date DATE,
    location TEXT,
    notes TEXT
);
```

**Why Now**:
- Affects "Inventory" concept (products + finished goods)
- Affects shopping list calculation (don't buy if finished goods exist)
- Easier to build architecture now than retrofit later

**UI**: Can defer to Phase 3

---

## Requirements Summary Table

| # | Requirement | Priority | Phase | Complexity | Dependencies |
|---|-------------|----------|-------|------------|--------------|
| 1 | Ingredient Hierarchy | 🔴 Critical | 2 | High | None (foundational) |
| 2 | Recipe Redesign | 🔴 High | 2 | High | #1 (ingredient selection) |
| 3 | Output Modes | 🟡 Medium | 2 | Low | None |
| 4 | UI/UX Organization | 🔴 High | 2 | Medium | None |
| 5 | Planning Workflow | 🔴 High | 2 | High | #1, #2, #4 |
| 6 | Purchase Workflow | 🔴 High | 2 | High | AI experimentation |
| 7 | Finished Goods Inventory | 🟡 Medium | 2 (arch) | Low | None |

---

## Implementation Approach

### Recommended Sequence

**Phase 2A: Foundations** (Must-haves)
1. Ingredient Hierarchy (#1) - Foundational, affects everything
2. UI Mode Restructuring (#4) - Framework for other changes
3. Recipe Redesign (#2) - Core workflow enabler

**Phase 2B: Workflows** (High-value)
4. Planning Wizard (#5) - Primary user workflow
5. Purchase Workflow - Basic UI (#6a)
6. Finished Goods Architecture (#7) - Future-proofing

**Phase 2C: Enhanced Purchase** (High-impact UX)
7. AI Purchase Assist - Demo version (#6b)

**Phase 3: Advanced Features**
- Output Modes (#3)
- Real-time AI sync
- Reporting
- Multi-user / Web migration

---

## Deferred to Phase 3

- **Reporting**: Cost analysis, trends, supplier performance
- **Proportional Recipe Scaling**: Non-linear adjustments for large batches
- **Voice-First AI Interface**: Conversational planning
- **Receipt OCR**: Full receipt scanning
- **Multi-User / Collaboration**: Web version
- **Real-Time Sync**: Phone ↔ Desktop

---

## Related Documents

### Project Foundation
- `/.kittify/memory/constitution.md` - Architecture principles
- `/docs/design/architecture.md` - System architecture
- `/docs/design/schema_v0.6_design.md` - Current schema

### Existing Designs
- `/docs/design/purchase_management_feature.md` - Needs update based on #6
- `/docs/workflows/workflow-refactoring-spec.md` - Current workflows

### Process
- `/docs/design/KICKOFF_phase2_redesign_chat.md` - Template for design discussion

---

## Next Steps

1. **Design Discussion** (New Chat):
   - Use `KICKOFF_phase2_redesign_chat.md` template
   - Include this requirements document
   - Work through data model changes
   - Prioritize implementation sequence

2. **Data Model Refinements**:
   - Design ingredient hierarchy schema
   - Design recipe template/snapshot schema
   - Design finished goods inventory schema
   - Create migration scripts

3. **Feature Specifications**:
   - Create detailed specs following spec-kitty patterns
   - One spec per major requirement
   - Include UI mockups, data flows, test cases

4. **Iterative Implementation**:
   - Build Phase 2A features first
   - Validate with real usage
   - Refine and continue

---

**Document Status**: Ready for design discussion and refinement

**Backup**: Original version saved as `PHASE2_workflow_ux_redesign.md.BACKUP`
