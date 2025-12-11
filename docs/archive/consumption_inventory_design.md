# CONSUMPTION & INVENTORY MANAGEMENT DESIGN DOCUMENT

**Version:** 1.1
**Date:** 2025-11-13
**Status:** DRAFT - Feedback Incorporated

---

## EXECUTIVE SUMMARY

This document proposes a comprehensive redesign of consumption and inventory management based on user stories 9-11, addressing the fundamental architectural issue of **recipe definitions vs. production instances** and establishing a unified dense UI pattern. **Core focus:** Building a "batch calculation engine" to answer "How many production runs do I need?" while designing for future production scheduling extensibility.

---

## CORE ARCHITECTURAL INSIGHT

### **The Recipe vs. Production Instance Problem**

**Current Issue:** The application conflates **recipes** (passive definitions) with **production** (active instances), leading to conceptual confusion in the consumption workflow.

**Key Realization:** Borrowing from programming patterns:
- **Recipe** = Class definition (immutable blueprint)
- **Finished Unit** = Type specification (singular consumable item definition)
- **Production Run** = Object instantiation (actual making process)

### **User Mental Model**

The planning process starts with: **"I have an event and need to make items for it"**

**Not:** "I want to follow a recipe"
**But:** "I need to fulfill event requirements with specific quantities of items"

**Examples:**
- Simple: "Emma's birthday needs 1 cake" → Event → Single production run
- Complex: "Holiday cookie exchange needs packages" → Event → Multiple production runs → Bundling

**Key Insight:** All production is **event-driven**, whether the event is a birthday party, bake sale, or personal consumption.

---

## PROPOSED ARCHITECTURE

### **1. NEW CORE CONCEPT: PRODUCTION RUN**

A `ProductionRun` represents the execution of multiple batches of a single recipe to achieve target quantities for an event.

```python
class ProductionRun:
    # Core fields (Phase 1)
    id: int
    event_id: int           # Always associated with an event
    recipe_id: int          # Reference to recipe blueprint (single recipe per run)
    target_quantity: int    # Total finished units to produce
    batches_required: int   # How many recipe batches needed
    status: ProductionStatus # planned, in_progress, completed
    created_date: date

    # Execution tracking (Phase 1)
    batches_completed: int  # Progress tracking
    actual_yield: int       # Total finished units actually produced
    consumption_log: List[ConsumptionRecord]
    finished_units_created: List[FinishedUnit]

    # Future extensibility (for production scheduling)
    planned_start_date: Optional[date]    # Future: "when should this start?"
    planned_end_date: Optional[date]      # Future: "when must this finish?"
    predecessor_runs: List[int]           # Future: "dependency management"
    resource_requirements: Dict          # Future: "oven time, workspace, etc."
```

### **2. PRODUCTION WORKFLOW**

#### **Phase 1: Event Planning ("Emma needs a birthday cake")**
```
Event Trigger: "Emma's Birthday Party needs 1 chocolate cake"
↓
Create Event: "Emma's Birthday Party"
↓
Add Production Requirements to Event:
  - Need: 1 chocolate birthday cake
↓
System calculates ProductionRun:
  - event_id: emma_birthday_party
  - recipe: chocolate_birthday_cake
  - target_quantity: 1 finished unit (cake)
  - batches_required: 1 (recipe makes 1 cake)
  - status: planned
```

#### **Phase 2: Execution ("Actually making")**
```
User Action: "Start Production" (from Event dashboard)
↓
ProductionRun.begin_execution():
  - Calculate total ingredient needs (recipe × batches_required)
  - Preview FIFO consumption
  - Show availability/shortage
  - Confirm and execute
  - Update status: in_progress
```

#### **Phase 3: Completion ("Done making")**
```
User Action: "Complete Batch" or "Complete Production Run"
↓
ProductionRun.complete():
  - Record actual yield (finished units created)
  - Create finished unit instances in Finished Goods Inventory
  - Update pantry inventory (consumption recorded)
  - Status: completed
  - Event shows progress toward fulfillment
```

### **3. FINISHED GOODS INVENTORY STRUCTURE**

Based on feedback, we need to distinguish between **Finished Units** (singular items) and **Finished Goods Inventory** (collection of completed foods).

#### **Finished Unit Definition**
- **Singular consumable item** produced by a recipe batch
- Examples: 1 cookie, 1 piece of fudge, 1 truffle, 1 cake, 1 serving of mousse
- Purpose: Enable batch calculation and bundle construction
- **Not necessarily a serving**: A serving of crackers = multiple crackers

#### **Finished Goods Inventory Categories**

```python
class FinishedGoodsInventory:
    """Collection of completed foods ready for consumption/bundling"""

    # The foods I need to make
    discrete_items: Dict[str, int]     # "cookies": 156, "truffles": 48
    whole_items: Dict[str, int]        # "birthday_cakes": 2, "pies": 1

    # The groupings I need to make
    bundles: List[Bundle]              # Dozens of cookies, gift boxes
    packages: List[Package]            # Final delivery containers
```

#### **Production → Finished Goods Flow**
```
ProductionRun(chocolate_chip_cookies) → 48 Finished Units
↓
Finished Goods Inventory: discrete_items["chocolate_chip_cookies"] = 48
↓
Bundling Process: Create 4 dozen-packages
↓
Final Packages: 4 dozen packages + individual cookies remaining
```

---

## CORE FOCUS: BATCH CALCULATION ENGINE

### **The Fundamental Planning Problem**

**Primary Question:** "I need 200 cookies for the bake sale → How many batches do I need to make?"

This is essentially a **resource estimation problem** with parallels to software development sprint planning:

#### **Calculation Components**

1. **Recipe Yield Math**
   - Recipe makes 24 cookies per batch
   - Need 200 cookies total
   - Result: 1 ProductionRun with 9 batches (8 full + 1 partial = 9 batches total)

2. **Packaging Constraints**
   - Cookies must be packaged by the dozen
   - 200 cookies = 16.67 dozen → Round up to 17 dozen (204 cookies)
   - Adjusted: 1 ProductionRun with 9 batches (yields 216 cookies, accounting for packaging)

3. **Multiple Recipe Coordination**
   - Event needs 3 different cookie types
   - Result: 3 ProductionRuns (one per recipe), each with calculated batches
   - Future optimization: Can production timing be coordinated?

4. **Capacity Constraints** *(Future scope)*
   - Oven capacity: "Can only bake 2 batches per day"
   - Storage limits: "Frosted items last 3 days max"
   - Workspace: "Can only prep 1 recipe type at a time"

### **Market Opportunity**

> **Current State:** "All existing tools are basically spreadsheets meant to help cooks/bakers answer the question of 'how much of what do I need to make when to hit this deadline for all deliverables involved.'"

**Gap:** No purpose-built production planning tools for baking/cooking events

**Vision:** Evolution from spreadsheets → dedicated production management system

### **Software Development Parallels**

| Baking Concept | Software Equivalent |
|---|---|
| Recipe | Class definition |
| ProductionRun | Epic/Feature |
| Recipe Batch | Task/Story |
| Finished Unit | Object instance |
| Event | Sprint |
| Batch calculation | Story point estimation |
| Event deadline | Sprint deadline |
| Ingredient availability | Resource allocation |
| Multi-recipe event | Sprint with multiple features |

### **Phase 1 Scope: Calculation Engine**

**Focus:** Build the "how many batches per recipe" calculator **first**
- Batch requirement calculation (recipe yield vs. target quantity)
- Multi-recipe event planning (multiple ProductionRuns per event)
- Packaging constraint handling (round up calculations)
- Ingredient availability vs. total requirements analysis

**Simplified Assumptions:**
- Recipe scaling: Multiple batches instead of mathematical scaling
- Equipment constraints: Human manages oven/workspace capacity
- Ingredient substitution: Human creates new recipes as needed

**Out of Scope:** Scheduling/calendaring (leave to human for now)
- When to make each batch within a ProductionRun
- Production timeline optimization
- Resource scheduling (oven time, workspace allocation)
- Cross-ProductionRun dependency sequencing

**Extensibility:** Design data model to support future scheduling features

---

## DESIGN IMPLICATIONS

### **1. CONSUMPTION INTEGRATION POINTS**

**Key Principle:** All production is **event-driven**. Consumption happens through production execution for events, not arbitrary "I want to make something" scenarios.

#### **A) Event-Driven Planning (Primary Workflow)**

**Location:** Events tab - central planning hub
**Trigger:** External event (birthday, bake sale, dinner party) requires food items

```
┌─ EVENT PLANNING: Emma's Birthday Party ───────────────────────────────┐
│ Date: 2025-12-01 | Attendees: 12                                      │
│                                                                        │
│ Required Items & Production Status:                                    │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Item                     │ Need │ Recipe       │ Batches │ Status   │ │
│ │──────────────────────────│──────│──────────────│─────────│──────────│ │
│ │ Chocolate Birthday Cake  │ 1    │ ChocBdayCake │ 1       │ ⚠ Plan   │ │
│ │ Chocolate Chip Cookies   │ 48   │ ChocChip     │ 2       │ ✓ Ready  │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ [Add Required Item] [Check Total Ingredients] [Generate Shopping]      │
│ [View All Production Runs] [Start Next Production]                     │
└────────────────────────────────────────────────────────────────────────┘
```

**When "Start Next Production" clicked:**
```
┌─ PRODUCTION: Chocolate Birthday Cake (1 batch needed) ────────────────┐
│ Event: Emma's Birthday Party | Target: 1 cake                         │
│                                                                        │
│ Ingredient Requirements & Availability:                                │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Ingredient   │ Need     │ Available │ Status │ FIFO Source         │ │
│ │──────────────│──────────│───────────│────────│─────────────────────│ │
│ │ AP Flour     │ 2 cups   │ 8 cups    │ ✓ OK   │ King Arthur (5lb)   │ │
│ │ Cocoa        │ 0.5 cups │ 0.5 cups  │ ✓ OK   │ Hershey (8oz)       │ │
│ │ Sugar        │ 1.5 cups │ 0 cups    │ ❌ OUT │ Need to purchase    │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ [Begin Production] [Check Missing Ingredients] [Update Inventory]      │
└────────────────────────────────────────────────────────────────────────┘
```

#### **B) Production Execution (Secondary)**

**Location:** Individual ProductionRun detail view
**Purpose:** Execute specific production run with consumption tracking

**When "Begin Production" clicked:**
```
┌─ CONFIRM PRODUCTION START ─────────────────────────────────────────────┐
│                                                                        │
│ Will consume from inventory (FIFO order):                             │
│ • AP Flour: 2 cups from King Arthur 5lb lot (Purchased: 2024-10-15)  │
│ • Cocoa: 0.5 cups from Hershey 8oz lot (Purchased: 2024-11-01)       │
│ • Sugar: INSUFFICIENT - need 1.5 cups, have 0 cups                    │
│                                                                        │
│ [✓] I've purchased missing ingredients and updated inventory           │
│ [Proceed with Production] [Cancel] [Update Inventory First]            │
└────────────────────────────────────────────────────────────────────────┘
```

### **2. MANUAL INVENTORY ADJUSTMENTS**

**Purpose:** Handle the unglamorous realities (spills, waste, found items)

#### **Enhanced Pantry "Adjust Mode"**

```
┌─ MY PANTRY ────────────────────────────────────────────────────────────┐
│ [□ Adjust Mode]  [History] [Add Item] [Refresh]                      │
├────────────────────────────────────────────────────────────────────────┤
│ Ingredient   │ Variant         │ Current │ New Quantity │ Save         │
├──────────────┼─────────────────┼─────────┼──────────────┼──────────────┤
│ AP Flour     │ King Arthur 5lb │ 3.2 lb  │ [________]   │ [✓ Update]   │
│ Sugar        │ Domino 4lb      │ 80%     │ [________]   │ [✓ Update]   │
│ Cocoa        │ Hershey 8oz     │ 0.5 cup │ [________]   │ [✓ Update]   │
└──────────────┴─────────────────┴─────────┴──────────────┴──────────────┘
```

**Features:**
- **Dual Input Support:** Absolute quantities ("2.5 lb") OR percentages ("75%")
- **Inline Editing:** No separate dialogs needed
- **Individual Updates:** Update each item independently
- **Simple Interface:** No complex reason tracking for initial implementation

---

## UI PATTERN COMPARISON ANALYSIS

### **My Ingredients vs My Pantry - Why Pantry is Superior**

Based on code analysis, the pantry design provides:

#### **Density Advantages:**
- **12x less vertical padding** (`pady=1` vs `pady=12`)
- **Fixed-width columns** vs flowing text
- **15-20 items visible** vs 8-12 items per screen

#### **Clarity Advantages:**
- **Inline action buttons** (paired with data) vs separated toolbar
- **Always-enabled buttons** vs disabled state confusion
- **Bold quantity emphasis** for critical data
- **Column-based scanning** vs line-by-line reading

#### **Interaction Advantages:**
- **1-click actions** vs 2-click select-then-act pattern
- **No state management** complexity
- **Visual status indicators** (expiration warnings)

---

## DESIGN DECISIONS RESOLVED

**Based on feedback, the following design questions have been resolved:**

### **1. Recipe Scaling → Multiple Batches** ✅
- ProductionRun executes multiple batches of same recipe to reach target quantity
- No mathematical scaling or recipe modification in initial implementation
- Baker can create new recipes for variations as needed

### **2. Production Run Structure → Per-Recipe Multi-Batch** ✅
- One ProductionRun = one recipe executed multiple times
- Events contain multiple ProductionRuns (one per recipe needed)
- Batch tracking within ProductionRun for progress monitoring

### **3. Event Integration → Always Event-Driven** ✅
- All ProductionRuns must be associated with an Event
- No standalone "I want to make something" scenarios
- Events are the entry point for all production planning

### **4. Finished Goods → Individual Unit Tracking** ✅
- Track individual Finished Units (1 cookie, 1 cake, 1 serving)
- Aggregate into Finished Goods Inventory categories
- Support bundling and packaging as separate workflow

---

## UI PATTERN UNIFICATION

### **Applying Dense Pattern Everywhere**

Based on pantry superiority analysis, standardize on:

- **Padding:** `pady=1` (not 12px)
- **Layout:** Fixed-width columns, not flowing text
- **Actions:** Inline buttons, not separate toolbars
- **State:** Always-enabled buttons, no disabled states
- **Emphasis:** Bold for key data (quantities, status)
- **Scanning:** Column-based, not line-by-line reading

### **Proposed Standard Column Patterns**

#### **My Ingredients (Redesigned)**
```
│ Name (200px) │ Category (120px) │ Variants (80px) │ Actions (160px) │
```

#### **Event Items/Tasks (New UI Pattern)**
```
│ Recipe (180px) │ Target Qty (100px) │ Batches (80px) │ Status (120px) │ Actions (180px) │
```

**Note:** Avoid "Production Run" terminology in UI. Present as tasks/items within events.

#### **My Pantry (Current - Keep)**
```
│ Ingredient (180px) │ Variant (200px) │ Qty (120px) │ Purchase (110px) │ Expiration (110px) │ Location (120px) │ Actions (180px) │
```

---

## IMPLEMENTATION STRATEGY

### **Phase 1: Batch Calculation Engine (Core Focus)**
**Goal:** Answer "How many batches per recipe do I need for this event?"

1. **Create `ProductionRun` model** with multi-batch support and event association
2. **Create `FinishedUnit` model** replacing current FinishedGood concept
3. **Build calculation service**:
   - Batch requirement calculation (target quantity ÷ recipe yield = batches needed)
   - Multi-recipe event planning (multiple ProductionRuns per event)
   - Packaging constraint handling (round up calculations)
   - Ingredient availability vs. total requirements analysis
4. **Create event-driven planning UI**:
   - Event → Add required items → Auto-calculate ProductionRuns
   - Show batch requirements per recipe
   - Display total ingredient needs across all ProductionRuns
5. **Enhanced pantry "Adjust Mode"**:
   - Percentage-based quantity input
   - Simplified inline editing without reason codes

### **Phase 2: Production Execution Workflow**
1. Add consumption preview/confirmation to ProductionRuns
2. Implement FIFO consumption when starting production
3. Connect to Finished Unit creation when completing production
4. Add batch progress tracking within ProductionRuns (X of Y batches completed)
5. Create Finished Goods Inventory management

### **Phase 3: Event Integration & Shopping**
1. Event-level production planning dashboard
2. Cross-run ingredient analysis (consolidate shopping lists)
3. Availability checking and shortage alerts
4. Shopping list generation with quantities

### **Phase 4: UI Standardization**
1. Redesign My Ingredients with pantry's dense pattern
2. Apply consistent column widths across all tabs
3. Standardize inline action patterns throughout app

### **Future: Production Scheduling (Beyond Current Year)**
- Production calendaring and timeline optimization
- Dependency management between production runs
- Resource scheduling (oven time, workspace allocation)
- Multi-day/week production campaign planning

---

## REMAINING IMPLEMENTATION DETAILS

**All major design questions resolved. Ready for feature breakdown and implementation.**

### **Technical Implementation Notes:**

1. **Code Refactoring Required**: Global rename "FinishedGood" → "FinishedUnit" throughout codebase
2. **UI Terminology**: Avoid "Production Run" in user-facing text, present as event tasks/items
3. **Data Model**: ProductionRun always requires event_id (no orphaned production runs)
4. **Calculation Priority**: Focus on batch count calculation before scheduling features

### **Next Steps:**
1. Break down work into discrete spec-kitty compatible features
2. Prioritize batch calculation engine as foundation
3. Implement event-driven workflow as primary entry point

---

## RELATED USER STORIES

**User Story 9:** As an operator of the program, I consume items in the pantry automatically through the completion of finished goods, or I can easily take an inventory of pantry items associated with the recipes associated with an event, or I can adjust the quantities of ad hoc items in the pantry to account for loss, untracked usage, or untracked purchases. I can get a historical report of pantry inventory adjustments covering all cases.

**User Story 10:** As an operator of the program, I can take an inventory using as few clicks as possible so taking an inventory is quick and easy and it avoids multiple dialogs and screens. Ideally, I could do this on the inventory list directly in a "adjust inventory" mode where I can see the current variant brand, packaging, current quantity and other information in line for context.

**User Story 11:** As an operator of the program, when taking an inventory I can specify either by quantity in the unit of the variant packaging (lbs, oz, grams) or by percentage, the amount left in inventory of a variant.

---

**Next Steps:** Discuss these open questions to refine the design before implementation begins.