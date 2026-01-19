# Planning Workspace - Feature Specification

**Feature ID**: F039
**Feature Name**: Planning Workspace
**Priority**: CRITICAL (P0) - Core Value Proposition
**Status**: Design Specification
**Created**: 2026-01-05
**Dependencies**: F037 (Recipe Redesign) ✅, F038 (UI Mode Restructure) ✅
**Constitutional References**: Principle I (Data Integrity), V (Layered Architecture), VII (Pragmatic Aspiration)

---

## Important Note on Specification Approach

**This document contains detailed technical illustrations** including code samples, algorithm pseudocode, service method signatures, and UI mockups. These are provided as **examples and guidance**, not as prescriptive implementations.

**When using spec-kitty to implement this feature:**
- The code samples are **illustrative** - they show one possible approach
- Spec-kitty should **validate and rationalize** the technical approach during its planning phase
- Spec-kitty may **modify or replace** these examples based on:
  - Current codebase patterns and conventions
  - Better architectural approaches discovered during analysis
  - Constitution compliance verification
  - Test-driven development requirements

**The requirements (req_planning.md) and business logic are the source of truth** - the technical implementation details should be determined by spec-kitty's specification and planning phases.

---

## Executive Summary

Planning Workspace is **THE** core value proposition of bake-tracker: automatic batch calculation that prevents the underproduction problem that consistently plagued Marianne's holiday baking. This feature transforms manual error-prone calculations ("How many batches do I need for 50 gift bags?") into automatic, validated production plans.

**The Hard Problem**: Manual batch math leads to consistent underproduction
**The Solution**: Event → FinishedGoods → Recipes → Batches (automatic)
**The Value**: Marianne never runs short on cookies again

**Key Capabilities**:
1. Explode event requirements (bundles/packages) to FinishedUnit quantities
2. Calculate optimal recipe batches (minimize waste, meet requirements)
3. Aggregate ingredients across all recipes (shopping list generation)
4. Validate assembly feasibility (can we make the bundles after production?)
5. Track progress (shopping → production → assembly → delivery)

**Phase 2 Scope**: Event-scoped planning (no cross-event inventory sharing)
**Phase 3 Deferred**: Multi-event planning, cross-event inventory optimization

---

## 1. Problem Statement

### 1.1 The Underproduction Problem

**Real-World Evidence (Christmas 2024):**
- Marianne planned 50 gift bags (6 cookies + 3 brownies each)
- Manually calculated: "I need about 300 cookies and 150 brownies"
- Produced: 288 cookies, 144 brownies
- Result: Only assembled 48 gift bags, **ran short on nearly everything**

**Root Cause:** Manual batch calculation errors
```
Mental math that went wrong:
"300 cookies needed, recipe makes 48... 
 That's about 6 batches, right?"
 
Actual: ceil(300 / 48) = 7 batches needed
Error: One batch short → 48 cookies missing → 2 gift bags impossible
```

### 1.2 Current State Gaps

**Gap 1: No Batch Calculator**
- User must manually calculate batches from requirements
- Prone to rounding errors, forgotten quantities
- Different yield options create confusion

**Gap 2: No Ingredient Aggregation**
- User manually sums ingredients across recipes
- Variant calculations done by hand
- Shopping list created ad hoc

**Gap 3: No Assembly Validation**
- User discovers shortfalls during assembly
- No early warning of insufficient production
- Too late to fix (already day of event)

**Gap 4: No Progress Visibility**
- Cannot see "Where am I in the workflow?"
- No status indicators (shopping done? production complete?)
- Must track mentally

### 1.3 User Impact

**Without Planning Workspace:**
```
User workflow (error-prone):
1. Create event, list what's needed
2. Guess batches needed (math errors)
3. Calculate ingredients manually
4. Shop based on mental estimate
5. Produce batches (maybe short)
6. Discover shortfall during assembly ❌
7. Panic, make emergency batch
8. Miss delivery deadline
```

**With Planning Workspace:**
```
System workflow (validated):
1. Create event, specify requirements
2. System calculates exact batches ✅
3. System aggregates all ingredients ✅
4. System generates shopping list ✅
5. User shops from generated list
6. User produces exact batches
7. System validates assembly feasible ✅
8. User assembles confidently
9. Deliver on time with no shortfalls ✅
```

---

## 2. Proposed Solution

### 2.1 Planning Workspace Location

**Navigation Path:**
```
PLAN Mode → Planning Workspace tab
```

**Mode Structure (from F038):**
```
PLAN Mode:
├─ Events tab (event CRUD, select for planning)
└─ Planning Workspace tab (THIS FEATURE)
   ├─ Event Requirements Input
   ├─ Production Plan (calculated)
   ├─ Shopping List (generated)
   ├─ Assembly Status (validated)
   └─ Progress Tracking
```

### 2.2 Core Workflow

```
┌─────────────────────────────────────────────────┐
│ Step 1: Select Event                            │
│  Dropdown: [Christmas 2025 ▼]                   │
│  Output Mode: BUNDLED                           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Step 2: Define Requirements                     │
│  [Add FinishedGood]                             │
│  • Holiday Gift Bag × 50                        │
│    (6 cookies + 3 brownies each)                │
│                                                  │
│  [Calculate Plan] ← Button triggers calculation │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Step 3: Review Production Plan (Auto-Calc)      │
│                                                  │
│  FinishedUnits Needed:                          │
│  • 300 Chocolate Chip Cookies                   │
│  • 150 Fudge Brownies                           │
│                                                  │
│  Recipe Production Plan:                        │
│  ✓ Sugar Cookie Recipe: 7 batches → 336 cookies│
│  ✓ Brownie Recipe: 7 batches → 168 brownies    │
│                                                  │
│  Waste Analysis:                                │
│  • Extra cookies: 36 (11%)                      │
│  • Extra brownies: 18 (12%)                     │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Step 4: Shopping List (Auto-Generated)          │
│                                                  │
│  Ingredients Needed:                            │
│  □ Flour: 21 cups (have: 10, buy: 11)          │
│  □ Butter: 14 sticks (have: 8, buy: 6)         │
│  □ Chocolate chips: 3.5 cups (have: 0, buy: 4) │
│  ✓ Sugar: 10 cups (have: 12, buy: 0)           │
│                                                  │
│  [Mark Shopping Complete]                       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Step 5: Production & Assembly                   │
│                                                  │
│  Production Status:                             │
│  ✓ Sugar Cookie: 7/7 batches complete          │
│  ⚠ Brownie: 4/7 batches complete                │
│                                                  │
│  Assembly Feasibility:                          │
│  ⚠ Cannot assemble yet (brownies incomplete)    │
│  Expected after production:                     │
│  • Cookies: 336 ✅ (need 300)                   │
│  • Brownies: In progress... (need 150)          │
│                                                  │
│  Assembly Checklist (disabled until complete):  │
│  □ 50 Holiday Gift Bags                         │
└─────────────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 Event Output Modes (NEW FIELD)

**Schema Addition:**
```python
class EventOutputMode(str, Enum):
    """Event requirement specification modes."""
    BULK_COUNT = "bulk_count"    # Direct FinishedUnit quantities
    BUNDLED = "bundled"           # FinishedGood (assembly) requirements
    PACKAGED = "packaged"         # Package requirements (Phase 3)

class Event(BaseModel):
    # Existing fields...
    name = Column(String(200))
    event_date = Column(Date)
    year = Column(Integer)
    
    # NEW FIELD
    output_mode = Column(
        String(20),
        nullable=False,
        default=EventOutputMode.BUNDLED.value
    )
    # "How does user specify what they need?"
    # BULK_COUNT: List FinishedUnits directly
    # BUNDLED: List FinishedGoods (bundles), system explodes
    # PACKAGED: List Packages, system explodes to bundles to units
```

**Migration Strategy:**
```sql
-- Add output_mode column
ALTER TABLE events 
ADD COLUMN output_mode VARCHAR(20) DEFAULT 'bundled';

-- Backfill existing events (assume BUNDLED if EventAssemblyTarget exists)
UPDATE events e
SET output_mode = 'bundled'
WHERE EXISTS (
    SELECT 1 FROM event_assembly_targets eat
    WHERE eat.event_id = e.id
);
```

### 3.2 Existing Models (No Changes)

**Event Planning Uses Existing:**
```python
# Event → FinishedUnit requirements (BULK_COUNT mode)
class EventProductionTarget(BaseModel):
    event_id = Column(Integer, ForeignKey("events.id"))
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id"))
    target_quantity = Column(Integer)  # How many FinishedUnits needed

# Event → FinishedGood requirements (BUNDLED mode)
class EventAssemblyTarget(BaseModel):
    event_id = Column(Integer, ForeignKey("events.id"))
    finished_good_id = Column(Integer, ForeignKey("finished_goods.id"))
    target_quantity = Column(Integer)  # How many FinishedGoods (bundles) needed

# FinishedGood → FinishedUnit linkage (explosion)
class Composition(BaseModel):
    assembly_id = Column(Integer, ForeignKey("finished_goods.id"))
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id"))
    component_quantity = Column(Float)  # How many per bundle

# FinishedUnit → Recipe linkage (F037 provides)
class FinishedUnit(BaseModel):
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    # Yield mode, items_per_batch from F037

# Recipe yield options (F037 provides)
class Recipe(BaseModel):
    # Base template with variants
    # YieldOptions via RecipeSnapshot or similar
```

**Key Insight:** All models exist! Planning Workspace is service layer + UI only.

---

## 4. Service Layer Architecture

### 4.1 Planning Service (New)

**File:** `src/services/planning_service.py`

**Core Methods:**

```python
class PlanningService:
    """
    Planning Workspace business logic.
    
    Responsibilities:
    - Calculate production plans from event requirements
    - Explode bundles/packages to FinishedUnits
    - Group FinishedUnits by recipe
    - Calculate optimal batches
    - Aggregate ingredients
    - Check inventory gaps
    - Validate assembly feasibility
    """
    
    def calculate_production_plan(
        self,
        event_id: int,
        session: Session
    ) -> ProductionPlan:
        """
        Calculate complete production plan for event.
        
        Returns ProductionPlan with:
        - finished_units_needed: {finished_unit_id: quantity}
        - recipe_plans: [{recipe, batches, yield, waste, variants}]
        - ingredients_needed: [{ingredient, quantity, unit}]
        - inventory_gaps: [{ingredient, need, have, gap}]
        - assembly_feasibility: {can_assemble, missing_components}
        """
        
    def explode_requirements(
        self,
        event: Event,
        session: Session
    ) -> Dict[int, int]:
        """
        Explode event requirements to FinishedUnit quantities.
        
        BULK_COUNT mode:
          EventProductionTarget → FinishedUnit quantities directly
          
        BUNDLED mode:
          EventAssemblyTarget → FinishedGood → Composition → FinishedUnits
          Multiply bundle contents by quantity needed
          
        Returns: {finished_unit_id: total_quantity}
        """
        
    def group_by_recipe(
        self,
        finished_units_needed: Dict[int, int],
        session: Session
    ) -> Dict[int, List[Tuple[FinishedUnit, int]]]:
        """
        Group FinishedUnits by recipe.
        
        Via: FinishedUnit.recipe_id linkage
        
        Returns: {
            recipe_id: [
                (finished_unit, quantity_needed),
                ...
            ]
        }
        """
        
    def calculate_optimal_batches(
        self,
        recipe: Recipe,
        total_needed: int,
        yield_options: List[RecipeYieldOption]
    ) -> BatchPlan:
        """
        Find optimal yield option for recipe.
        
        Criteria:
        1. Must meet or exceed requirement (never short)
        2. Minimize waste (extra units)
        3. Minimize batches (if waste tied)
        
        Returns BatchPlan with:
        - yield_option: Selected yield
        - batches: Number of batches
        - total_yield: batches × yield
        - waste: total_yield - needed
        """
        
    def calculate_variant_allocations(
        self,
        recipe: Recipe,
        finished_units: List[Tuple[FinishedUnit, int]],
        total_yield: int
    ) -> List[VariantAllocation]:
        """
        Calculate proportions for recipe variants.
        
        Example:
          Recipe produces 96 cookies total
          Need: 24 chocolate chip, 24 rainbow, 48 plain
          
          Proportions:
          - Chocolate: 24/96 = 25%
          - Rainbow: 24/96 = 25%
          - Plain: 48/96 = 50%
          
        Returns: [
            VariantAllocation(
                finished_unit=...,
                quantity_needed=...,
                proportion=Decimal(0.25)
            ),
            ...
        ]
        """
        
    def aggregate_ingredients(
        self,
        recipe_plans: List[RecipePlan],
        session: Session
    ) -> List[IngredientRequirement]:
        """
        Aggregate ingredients across all recipes.
        
        For each recipe:
        - Base ingredients × batches × batch_multiplier
        - Variant ingredients × batches × multiplier × proportion
        
        Combine same ingredients from different recipes.
        
        Returns: [
            IngredientRequirement(
                ingredient=...,
                total_quantity=Decimal(...),
                unit=...
            ),
            ...
        ]
        """
        
    def check_inventory_gaps(
        self,
        ingredients_needed: List[IngredientRequirement],
        session: Session
    ) -> List[InventoryGap]:
        """
        Compare needed vs available inventory.
        
        For each ingredient:
        - Query current inventory
        - Calculate gap: max(0, needed - available)
        
        Returns: [
            InventoryGap(
                ingredient=...,
                needed=Decimal(...),
                available=Decimal(...),
                gap=Decimal(...)  # Amount to purchase
            ),
            ...
        ]
        """
        
    def validate_assembly_feasibility(
        self,
        event: Event,
        recipe_plans: List[RecipePlan],
        session: Session
    ) -> AssemblyFeasibility:
        """
        Check if production enables assembly.
        
        Phase 2: Event-scoped (no cross-event inventory)
        
        For each FinishedGood in event requirements:
        - Calculate FinishedUnits produced (from recipe plans)
        - Compare to FinishedUnits needed (from bundle contents)
        - Flag insufficient components
        
        Returns AssemblyFeasibility with:
        - can_assemble: bool
        - bundles_feasible: List[BundleFeasibility]
        - missing_components: List[ComponentShortage]
        """
```

### 4.2 Data Transfer Objects (DTOs)

```python
@dataclass
class ProductionPlan:
    """Complete production plan for event."""
    event_id: int
    output_mode: EventOutputMode
    finished_units_needed: Dict[int, int]  # {fu_id: qty}
    recipe_plans: List['RecipePlan']
    ingredients_needed: List['IngredientRequirement']
    inventory_gaps: List['InventoryGap']
    assembly_feasibility: 'AssemblyFeasibility'
    
@dataclass
class RecipePlan:
    """Production plan for single recipe."""
    recipe: Recipe
    yield_option: RecipeYieldOption
    batches: int
    total_yield: int
    waste: int  # extra units produced
    variant_allocations: List['VariantAllocation']
    
@dataclass
class VariantAllocation:
    """Variant proportion within recipe batch."""
    finished_unit: FinishedUnit
    quantity_needed: int
    proportion: Decimal  # 0.0 - 1.0
    
@dataclass
class IngredientRequirement:
    """Ingredient needed across all recipes."""
    ingredient: Ingredient
    total_quantity: Decimal
    unit: str
    
@dataclass
class InventoryGap:
    """Ingredient gap analysis."""
    ingredient: Ingredient
    needed: Decimal
    available: Decimal
    gap: Decimal  # Amount to purchase
    unit: str
    
@dataclass
class AssemblyFeasibility:
    """Assembly validation results."""
    can_assemble: bool  # All bundles feasible
    bundles_feasible: List['BundleFeasibility']
    
@dataclass
class BundleFeasibility:
    """Feasibility for single bundle type."""
    finished_good: FinishedGood
    quantity_needed: int
    can_assemble: bool
    components: List['ComponentAvailability']
    
@dataclass
class ComponentAvailability:
    """Component availability after production."""
    finished_unit: FinishedUnit
    needed: int
    available_after_production: int
    sufficient: bool
```

---

## 5. UI Design

### 5.1 Planning Workspace Layout

```
┌─ Planning Workspace ────────────────────────────────────────────┐
│                                                                  │
│  Event: [Christmas 2025 ▼]  Output Mode: BUNDLED               │
│                                                                  │
│  ┌── Requirements ──────────────────────────────────────────┐  │
│  │  [+ Add FinishedGood]                                     │  │
│  │                                                            │  │
│  │  FinishedGood             Quantity     Actions            │  │
│  │  ──────────────────────   ────────     ───────            │  │
│  │  Holiday Gift Bag         50           [Edit] [Remove]    │  │
│  │    └─ 6 cookies + 3 brownies per bag                      │  │
│  │                                                            │  │
│  │  Deluxe Sampler           25           [Edit] [Remove]    │  │
│  │    └─ 12 cookies + 6 truffles per bag                     │  │
│  │                                                            │  │
│  │  [Calculate Production Plan] ← Triggers calculation       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌── Production Plan (Auto-Calculated) ─────────────────────┐  │
│  │  FinishedUnits Needed:                                    │  │
│  │  • 600 Chocolate Chip Cookies                             │  │
│  │  • 150 Fudge Brownies                                     │  │
│  │  • 150 Chocolate Truffles                                 │  │
│  │                                                            │  │
│  │  Recipe Batches:                                          │  │
│  │  ✓ Sugar Cookie Recipe: 13 batches → 624 cookies         │  │
│  │    (Yield: 48/batch, Waste: 24 cookies = 4%)             │  │
│  │                                                            │  │
│  │  ✓ Brownie Recipe: 7 batches → 168 brownies              │  │
│  │    (Yield: 24/batch, Waste: 18 brownies = 12%)           │  │
│  │                                                            │  │
│  │  ✓ Truffle Recipe: 7 batches → 168 truffles              │  │
│  │    (Yield: 24/batch, Waste: 18 truffles = 12%)           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌── Shopping List ────────────────────────────────────────┐   │
│  │  Ingredient          Need    Have    Buy                 │   │
│  │  ─────────────────   ────    ────    ───                 │   │
│  │  □ Flour             26 c    10 c    16 c                │   │
│  │  □ Butter            20 stk  8 stk   12 stk              │   │
│  │  □ Chocolate chips   6.5 c   0 c     7 c                 │   │
│  │  ✓ Sugar             15 c    18 c    0 c  (sufficient)   │   │
│  │  □ Cocoa powder      3.5 c   1 c     3 c                 │   │
│  │                                                            │   │
│  │  [Mark Shopping Complete] [Export Shopping List]          │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌── Production & Assembly Status ─────────────────────────┐   │
│  │  Production Progress:                                     │   │
│  │  ✓ Sugar Cookie: 13/13 batches ████████████ 100%        │   │
│  │  ✓ Brownie: 7/7 batches ████████████ 100%               │   │
│  │  ⚠ Truffle: 4/7 batches ███████░░░░░ 57%                │   │
│  │                                                            │   │
│  │  Assembly Feasibility:                                    │   │
│  │  ⚠ Cannot assemble yet (Truffle production incomplete)    │   │
│  │                                                            │   │
│  │  Expected after full production:                          │   │
│  │  ✅ Holiday Gift Bag: Can assemble 50                    │   │
│  │  ✅ Deluxe Sampler: Can assemble 25                      │   │
│  │                                                            │   │
│  │  Assembly Checklist (disabled until production complete): │   │
│  │  ░ 50 Holiday Gift Bags                                   │   │
│  │  ░ 25 Deluxe Samplers                                     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Requirements Input Dialog

**Add FinishedGood Dialog (BUNDLED mode):**
```
┌─ Add FinishedGood Requirement ─────────────────────┐
│                                                     │
│  FinishedGood: [Holiday Gift Bag ▼]                │
│                                                     │
│  Contents (read-only):                              │
│  • 6 × Chocolate Chip Cookies                       │
│  • 3 × Fudge Brownies                               │
│                                                     │
│  Quantity Needed: [50_______]                       │
│                                                     │
│  This will produce:                                 │
│  • 300 Chocolate Chip Cookies (50 × 6)              │
│  • 150 Fudge Brownies (50 × 3)                      │
│                                                     │
│  [Cancel]  [Add to Plan]                            │
└─────────────────────────────────────────────────────┘
```

**Add FinishedUnit Dialog (BULK_COUNT mode):**
```
┌─ Add FinishedUnit Requirement ─────────────────────┐
│                                                     │
│  FinishedUnit: [Chocolate Chip Cookies ▼]          │
│                                                     │
│  Recipe: Sugar Cookie Recipe (read-only)            │
│  Yield Options: 24, 48, 96 per batch (read-only)    │
│                                                     │
│  Quantity Needed: [100______]                       │
│                                                     │
│  [Cancel]  [Add to Plan]                            │
└─────────────────────────────────────────────────────┘
```

### 5.3 Production Plan Display

**Recipe Batch Detail View:**
```
┌─ Recipe: Sugar Cookie (Chocolate Chip variant) ────┐
│                                                     │
│  Requirement: 300 Chocolate Chip Cookies            │
│                                                     │
│  Yield Options Analysis:                            │
│  • 96/batch: 4 batches → 384 total (84 waste = 28%)│
│  • 48/batch: 7 batches → 336 total (36 waste = 12%)│ ← OPTIMAL
│  • 24/batch: 13 batches → 312 total (12 waste = 4%)│
│                                                     │
│  Selected: 48-cookie yield, 7 batches               │
│  Reasoning: Minimizes waste while avoiding excess  │
│             batches                                 │
│                                                     │
│  Base Ingredients (per batch):                      │
│  • Flour: 2 cups × 7 batches = 14 cups              │
│  • Butter: 1 stick × 7 batches = 7 sticks           │
│  • Sugar: 1 cup × 7 batches = 7 cups                │
│                                                     │
│  Variant Ingredients (100% Chocolate Chip):         │
│  • Chocolate chips: 0.5 cups × 7 batches = 3.5 cups │
│                                                     │
│  [Close]                                            │
└─────────────────────────────────────────────────────┘
```

### 5.4 Assembly Feasibility Indicators

**Visual Status Icons:**
```
✅ Sufficient   (green) - Can assemble, components available
⚠️  Pending     (yellow) - Production incomplete, check back
❌ Insufficient (red) - Shortfall, cannot assemble even after production
```

**Feasibility Detail:**
```
Holiday Gift Bag (50 needed):
  Components:
  ✅ Chocolate Chip Cookies: Have 336, need 300 (surplus: 36)
  ✅ Fudge Brownies: Have 168, need 150 (surplus: 18)
  
  Status: ✅ Can assemble 50 gift bags
  
Deluxe Sampler (25 needed):
  Components:
  ✅ Chocolate Chip Cookies: Have 624, need 300 (surplus: 324)
  ⚠️  Chocolate Truffles: Have 96, need 150 (short: 54)
  
  Status: ❌ Cannot assemble - need 3 more truffle batches
  Recommendation: Produce 3 more truffle batches (72 total)
```

---

## 6. Algorithms & Business Logic

### 6.1 Batch Optimization Algorithm

```python
def find_optimal_yield(
    total_needed: int,
    yield_options: List[RecipeYieldOption]
) -> BatchPlan:
    """
    Find best yield option.
    
    Optimization criteria:
    1. Must meet requirement (never short)
    2. Minimize waste (extra units)
    3. Minimize batches (if waste tied)
    """
    solutions = []
    
    for yield_option in yield_options:
        batches = math.ceil(total_needed / yield_option.quantity)
        total_yield = batches * yield_option.quantity
        waste = total_yield - total_needed
        
        solutions.append(
            BatchPlan(
                yield_option=yield_option,
                batches=batches,
                total_yield=total_yield,
                waste=waste
            )
        )
    
    # Sort: least waste first, then fewest batches
    solutions.sort(key=lambda s: (s.waste, s.batches))
    
    return solutions[0]  # Optimal
```

**Example:**
```python
find_optimal_yield(total_needed=300, yield_options=[24, 48, 96])

Analysis:
  96-yield: ceil(300/96) = 4 batches → 384 total (waste: 84)
  48-yield: ceil(300/48) = 7 batches → 336 total (waste: 36) ← OPTIMAL
  24-yield: ceil(300/24) = 13 batches → 312 total (waste: 12)
  
Sorted by (waste, batches):
  1. 24-yield (waste=12, batches=13)
  2. 48-yield (waste=36, batches=7)  ← Winner (better than #1 due to tie-break)
  3. 96-yield (waste=84, batches=4)
  
Wait, that's wrong! Let me reconsider...

Actually, sorting by (waste, batches) ascending means:
  1. 24-yield: (12, 13)   ← waste=12 (least)
  2. 48-yield: (36, 7)    ← waste=36
  3. 96-yield: (84, 4)    ← waste=84

So 24-yield wins? But that means 13 batches!

Hmm, maybe we want different criteria...
```

**REVISED Algorithm (User Preference):**
```python
# Option A: Minimize waste (current spec)
solutions.sort(key=lambda s: (s.waste, s.batches))
# Result: 24-yield (12 waste, 13 batches)

# Option B: Minimize batches
solutions.sort(key=lambda s: (s.batches, s.waste))
# Result: 96-yield (4 batches, 84 waste)

# Option C: Balanced (configurable threshold)
# "Acceptable waste" = 10% of requirement
acceptable_waste = total_needed * 0.10  # 30 cookies

acceptable = [s for s in solutions if s.waste <= acceptable_waste]
if acceptable:
    # Among acceptable waste, minimize batches
    acceptable.sort(key=lambda s: s.batches)
    return acceptable[0]
else:
    # No acceptable option, minimize waste
    solutions.sort(key=lambda s: (s.waste, s.batches))
    return solutions[0]

# Result with 10% threshold:
#   24-yield: waste=12 (4%) ← acceptable, 13 batches
#   48-yield: waste=36 (12%) ← NOT acceptable (>10%)
#   96-yield: waste=84 (28%) ← NOT acceptable
# Winner: 24-yield

# Result with 15% threshold:
#   24-yield: waste=12 (4%) ← acceptable, 13 batches
#   48-yield: waste=36 (12%) ← acceptable, 7 batches ← WINNER
# Winner: 48-yield (fewest batches among acceptable)
```

**Decision for Phase 2:**
Use Option C with 15% waste threshold (configurable in future).

### 6.2 Variant Proportion Algorithm

```python
def calculate_variant_allocations(
    recipe: Recipe,
    finished_units: List[Tuple[FinishedUnit, int]],
    total_yield: int
) -> List[VariantAllocation]:
    """
    Calculate proportions for variants.
    
    Example:
      Recipe: Sugar Cookie, total_yield=96
      FinishedUnits:
        - Chocolate Chip: 24 needed
        - Rainbow Sprinkle: 24 needed
        - Plain: 48 needed
      
      Proportions:
        - Chocolate: 24/96 = 0.25 (25%)
        - Rainbow: 24/96 = 0.25 (25%)
        - Plain: 48/96 = 0.50 (50%)
    """
    allocations = []
    
    for finished_unit, quantity_needed in finished_units:
        proportion = Decimal(quantity_needed) / Decimal(total_yield)
        
        allocations.append(
            VariantAllocation(
                finished_unit=finished_unit,
                quantity_needed=quantity_needed,
                proportion=proportion
            )
        )
    
    # Validation: proportions should sum to ~1.0
    total_proportion = sum(a.proportion for a in allocations)
    assert abs(total_proportion - Decimal("1.0")) < Decimal("0.001"), \
        f"Proportions sum to {total_proportion}, expected 1.0"
    
    return allocations
```

### 6.3 Ingredient Aggregation Algorithm

```python
def aggregate_ingredients(
    recipe_plans: List[RecipePlan],
    session: Session
) -> List[IngredientRequirement]:
    """
    Aggregate ingredients across recipes.
    
    For each recipe:
      Base: ingredient_qty × batches × batch_multiplier
      Variant: base_scaled × proportion
    
    Combine same ingredients.
    """
    ingredient_totals: Dict[int, Decimal] = {}  # {ingredient_id: total_qty}
    ingredient_units: Dict[int, str] = {}  # {ingredient_id: unit}
    
    for recipe_plan in recipe_plans:
        recipe = recipe_plan.recipe
        batches = recipe_plan.batches
        yield_option = recipe_plan.yield_option
        batch_mult = yield_option.batch_multiplier
        
        # Base ingredients
        for recipe_ingredient in recipe.ingredients:
            if recipe_ingredient.is_base:  # Not variant-specific
                scaled_qty = (
                    recipe_ingredient.quantity
                    * batches
                    * batch_mult
                )
                
                ingredient_id = recipe_ingredient.ingredient_id
                ingredient_totals[ingredient_id] = \
                    ingredient_totals.get(ingredient_id, Decimal(0)) + scaled_qty
                ingredient_units[ingredient_id] = recipe_ingredient.unit
        
        # Variant ingredients
        for variant_alloc in recipe_plan.variant_allocations:
            variant = variant_alloc.finished_unit.recipe_variant
            proportion = variant_alloc.proportion
            
            for variant_ingredient in variant.ingredient_changes:
                if variant_ingredient.action == "add":
                    scaled_qty = (
                        variant_ingredient.quantity
                        * batches
                        * batch_mult
                        * proportion
                    )
                    
                    ingredient_id = variant_ingredient.ingredient_id
                    ingredient_totals[ingredient_id] = \
                        ingredient_totals.get(ingredient_id, Decimal(0)) + scaled_qty
                    ingredient_units[ingredient_id] = variant_ingredient.unit
    
    # Convert to IngredientRequirement objects
    requirements = []
    for ingredient_id, total_qty in ingredient_totals.items():
        ingredient = session.query(Ingredient).get(ingredient_id)
        unit = ingredient_units[ingredient_id]
        
        requirements.append(
            IngredientRequirement(
                ingredient=ingredient,
                total_quantity=total_qty,
                unit=unit
            )
        )
    
    # Sort alphabetically
    requirements.sort(key=lambda r: r.ingredient.display_name)
    
    return requirements
```

---

## 7. Functional Requirements

### 7.1 Event Output Mode

**REQ-F039-001:** System shall support Event.output_mode attribute (BULK_COUNT, BUNDLED, PACKAGED)
**REQ-F039-002:** System shall validate output_mode is set before planning
**REQ-F039-003:** System shall show different requirement input based on output_mode

### 7.2 Requirements Input

**REQ-F039-004:** BULK_COUNT mode shall allow adding EventProductionTarget (FinishedUnit, quantity)
**REQ-F039-005:** BUNDLED mode shall allow adding EventAssemblyTarget (FinishedGood, quantity)
**REQ-F039-006:** System shall validate quantities are positive integers
**REQ-F039-007:** System shall allow editing/removing requirements before calculation

### 7.3 Production Plan Calculation

**REQ-F039-008:** System shall explode FinishedGood requirements to FinishedUnit quantities
**REQ-F039-009:** System shall group FinishedUnits by recipe (via recipe linkage)
**REQ-F039-010:** System shall calculate optimal yield option (minimize waste, minimize batches)
**REQ-F039-011:** Yield calculation shall use 15% waste threshold (configurable future)
**REQ-F039-012:** System shall calculate variant proportions (quantity_needed / total_yield)
**REQ-F039-013:** System shall aggregate ingredients (base + variant, across recipes)

### 7.4 Shopping List Generation

**REQ-F039-014:** System shall check current inventory for each ingredient
**REQ-F039-015:** System shall calculate gap: max(0, needed - available)
**REQ-F039-016:** System shall display shopping list with Need/Have/Buy columns
**REQ-F039-017:** User shall be able to mark shopping as complete (status tracking)

### 7.5 Assembly Feasibility

**REQ-F039-018:** System shall validate assembly feasibility (event-scoped, Phase 2)
**REQ-F039-019:** Feasibility check shall compare FinishedUnits produced vs needed
**REQ-F039-020:** System shall display visual indicators (✅/⚠️/❌) for feasibility
**REQ-F039-021:** System shall show component-level detail (what's short, how much)

### 7.6 Assembly Checklist (Phase 2 Minimal)

**REQ-F039-022:** System shall generate assembly checklist from FinishedGood requirements
**REQ-F039-023:** Checklist shall disable until production complete
**REQ-F039-024:** Checking checklist item shall record assembly confirmation (no inventory txn)
**REQ-F039-025:** Phase 3: Checking shall create AssemblyRun with inventory transactions

### 7.7 Progress Tracking

**REQ-F039-026:** System shall track production progress (batches complete / total)
**REQ-F039-027:** System shall show progress bars per recipe
**REQ-F039-028:** System shall update assembly feasibility as production progresses
**REQ-F039-029:** System shall show overall event readiness status

---

## 8. Non-Functional Requirements

### 8.1 Performance

**REQ-F039-NFR-001:** Production plan calculation shall complete in <500ms for 10+ recipes
**REQ-F039-NFR-002:** Ingredient aggregation shall complete in <200ms
**REQ-F039-NFR-003:** Assembly feasibility check shall complete in <100ms

### 8.2 Usability

**REQ-F039-NFR-004:** Batch calculation shall be automatic (user clicks "Calculate Plan")
**REQ-F039-NFR-005:** Production plan shall display in user-friendly format (not raw data)
**REQ-F039-NFR-006:** Assembly feasibility shall use clear visual indicators
**REQ-F039-NFR-007:** Workflow shall follow natural mental model (requirements → plan → execute)

### 8.3 Accuracy

**REQ-F039-NFR-008:** Batch calculations shall always meet/exceed requirements (never short)
**REQ-F039-NFR-009:** Ingredient quantities shall be accurate to 2 decimal places
**REQ-F039-NFR-010:** Variant proportions shall sum to 1.0 within rounding error (±0.001)

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Batch Calculation:**
```python
def test_find_optimal_yield_minimizes_waste():
    """Test that optimal yield minimizes waste."""
    yield_options = [24, 48, 96]
    result = find_optimal_yield(total_needed=300, yield_options=yield_options)
    
    # With 15% threshold (45 cookies):
    # 24-yield: 12 waste (4%) ← acceptable, 13 batches
    # 48-yield: 36 waste (12%) ← acceptable, 7 batches ← OPTIMAL
    assert result.yield_option.quantity == 48
    assert result.batches == 7
    assert result.total_yield == 336
    assert result.waste == 36

def test_variant_allocations_sum_to_one():
    """Test variant proportions sum to 1.0."""
    allocations = calculate_variant_allocations(
        recipe=sugar_cookie_recipe,
        finished_units=[
            (chocolate_chip_cookie, 24),
            (rainbow_cookie, 24),
            (plain_cookie, 48)
        ],
        total_yield=96
    )
    
    total_proportion = sum(a.proportion for a in allocations)
    assert abs(total_proportion - Decimal("1.0")) < Decimal("0.001")
```

**Ingredient Aggregation:**
```python
def test_aggregate_ingredients_combines_same():
    """Test that same ingredients from different recipes combine."""
    recipe_plans = [
        # Sugar Cookie: 14 cups flour
        RecipePlan(recipe=sugar_cookie, batches=7, ...),
        # Brownie: 7 cups flour
        RecipePlan(recipe=brownie, batches=7, ...)
    ]
    
    ingredients = aggregate_ingredients(recipe_plans, session)
    
    flour = next(i for i in ingredients if i.ingredient.name == "Flour")
    assert flour.total_quantity == Decimal("21.0")  # 14 + 7
```

### 9.2 Integration Tests

**End-to-End Planning:**
```python
def test_complete_planning_workflow():
    """Test full workflow from event requirements to assembly."""
    # 1. Create event
    event = Event(
        name="Christmas 2025",
        output_mode=EventOutputMode.BUNDLED
    )
    session.add(event)
    
    # 2. Add requirements
    target = EventAssemblyTarget(
        event=event,
        finished_good=holiday_gift_bag,  # 6 cookies + 3 brownies
        target_quantity=50
    )
    session.add(target)
    session.commit()
    
    # 3. Calculate production plan
    plan = planning_service.calculate_production_plan(event.id, session)
    
    # 4. Verify explosion
    assert plan.finished_units_needed[chocolate_chip_cookie.id] == 300
    assert plan.finished_units_needed[fudge_brownie.id] == 150
    
    # 5. Verify batch calculation
    cookie_plan = next(p for p in plan.recipe_plans if p.recipe.id == sugar_cookie.id)
    assert cookie_plan.batches == 7
    assert cookie_plan.total_yield == 336
    assert cookie_plan.waste == 36
    
    # 6. Verify ingredient aggregation
    flour = next(i for i in plan.ingredients_needed if i.ingredient.name == "Flour")
    assert flour.total_quantity == Decimal("21.0")
    
    # 7. Verify assembly feasibility
    assert plan.assembly_feasibility.can_assemble == True
    holiday_bag_feas = plan.assembly_feasibility.bundles_feasible[0]
    assert holiday_bag_feas.can_assemble == True
```

### 9.3 User Acceptance Tests

**UAT-001: Create Simple Event (BUNDLED)**
```
Given: User has defined recipes and bundles
When: User creates event with 50 Holiday Gift Bags
Then: System calculates exact batches needed
And: Shopping list shows ingredients to purchase
And: Assembly feasibility shows ✅ can assemble
```

**UAT-002: Verify No Shortfall**
```
Given: Event requires 300 cookies (yield options: 24, 48, 96)
When: System calculates batches
Then: Total yield ≥ 300 (never short)
And: Waste is minimized (within 15% threshold)
```

**UAT-003: Track Production Progress**
```
Given: Production plan shows 7 batches cookies needed
When: User completes 4 batches
Then: Progress bar shows 57% (4/7)
And: Assembly feasibility shows ⚠️ pending
When: User completes all 7 batches
Then: Progress bar shows 100%
And: Assembly feasibility shows ✅ can assemble
```

---

## 10. Implementation Phases

### Phase 1: Core Calculation (MVP)
**Effort:** 20-25 hours

**Scope:**
- Event.output_mode field (migration)
- PlanningService with core methods
- Batch calculation algorithm
- Ingredient aggregation algorithm
- Assembly feasibility (read-only)
- Basic UI (requirements input, display plan)

**Deliverables:**
- ✓ Can create event with BUNDLED mode
- ✓ Can add FinishedGood requirements
- ✓ Click "Calculate Plan" shows batches needed
- ✓ Shows shopping list (no inventory checking yet)
- ✓ Shows assembly feasibility (after full production)

### Phase 2: Inventory Integration
**Effort:** 10-12 hours

**Scope:**
- Inventory gap analysis
- Shopping list with Need/Have/Buy columns
- Shopping completion tracking
- Production progress tracking

**Deliverables:**
- ✓ Shopping list shows current inventory
- ✓ Can mark shopping as complete
- ✓ Production progress bars update
- ✓ Assembly feasibility updates as production progresses

### Phase 3: Assembly Checklist (Minimal)
**Effort:** 8-10 hours

**Scope:**
- Assembly checklist UI
- Checklist disable/enable logic
- Checklist completion tracking (no inventory txn)

**Deliverables:**
- ✓ Checklist shows bundle requirements
- ✓ Checklist disabled until production complete
- ✓ Checking checklist records confirmation
- ⏳ Phase 3 future: Inventory transactions

### Total Effort Estimate
**40-47 hours** (roughly 5-6 working days)

---

## 11. Open Questions & Decisions

**Q1:** Should system allow manual batch override?
**A1:** Phase 2: No (automatic only). Phase 3: Allow override with validation warning.

**Q2:** How to handle recipe changes after plan created?
**A2:** Phase 2: Manual replan (user clicks "Recalculate"). Phase 3: Auto-detect changes, warn user.

**Q3:** What waste threshold to use for optimization?
**A3:** Start with 15% (configurable in future). User can adjust via settings (Phase 3).

**Q4:** Should shopping list export to mobile?
**A4:** Phase 2: Export to CSV/PDF. Phase 3: Mobile app integration, AI barcode scanning.

---

## 12. Future Enhancements (Phase 3+)

**Multi-Event Planning:**
- Aggregate ingredients across multiple events
- Cross-event inventory sharing
- Production shortfall calculation (use existing FG inventory)

**Advanced Optimization:**
- Cost-based yield selection (cheapest plan)
- Schedule-based optimization (order by urgency)
- Waste minimization across events

**AI Integration:**
- Suggest event templates from history
- Predict quantities based on past events
- Anomaly detection (unusual waste, shortfalls)

---

## 13. Constitutional Compliance

**Principle I (Data Integrity):**
- ✓ Event.output_mode field with FK constraints
- ✓ Validation prevents invalid requirements
- ✓ Batch calculations always meet/exceed (never short)

**Principle V (Layered Architecture):**
- ✓ PlanningService in service layer (no UI logic)
- ✓ DTOs separate presentation from business logic
- ✓ UI calls service methods, doesn't calculate

**Principle VII (Pragmatic Aspiration):**
- ✓ Phase 2 builds core value (batch calculation)
- ✓ Phase 3 defers advanced features (multi-event, cost optimization)
- ✓ Simple checklist in Phase 2, full inventory txn in Phase 3

---

## 14. Success Criteria

**Must Have (Phase 2):**
- [ ] Event with output_mode selection
- [ ] FinishedGood requirements input
- [ ] Automatic batch calculation (optimal yield)
- [ ] Ingredient aggregation (shopping list)
- [ ] Inventory gap analysis
- [ ] Assembly feasibility check
- [ ] Assembly completion checklist (minimal)
- [ ] Production progress tracking

**Should Have:**
- [ ] Visual feasibility indicators (✅/⚠️/❌)
- [ ] Shopping list export (CSV/PDF)
- [ ] Batch detail view (yield options comparison)

**Nice to Have (Phase 3):**
- [ ] Multi-event planning dashboard
- [ ] Cost optimization
- [ ] "What if" scenario planning

---

## 15. Related Documents

- **Requirements:** `docs/requirements/req_planning.md` (core planning requirements)
- **Requirements:** `docs/requirements/req_finished_goods.md` (Bundle/FinishedGood hierarchy)
- **Requirements:** `docs/requirements/req_recipes.md` (recipe variants, yield options)
- **Dependencies:** `docs/func-spec/F037_recipe_redesign.md` (template/snapshot architecture)
- **Dependencies:** `docs/design/_F038_ui_mode_restructure.md` (PLAN mode structure)
- **Constitution:** `.kittify/memory/constitution.md` (architectural principles)

---

**END OF SPECIFICATION**
