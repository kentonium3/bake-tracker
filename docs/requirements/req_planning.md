# Planning - Requirements Document

**Component:** Planning (Event Planning, Production Planning, Assembly Planning)
**Version:** 0.1
**Last Updated:** 2025-01-05
**Status:** Current
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Planning is the **strategic orchestration layer** in bake-tracker that answers the fundamental question: "How many batches of each recipe do I need to make for this event?" The planning system connects event requirements (finished goods) to production execution (recipe batches, ingredient purchases, assembly workflows).

### 1.2 Business Purpose

The Planning system serves critical business functions:

1. **Batch Calculation:** Automatically calculates recipe batches needed from finished goods requirements
2. **Ingredient Aggregation:** Determines total ingredients needed across all recipes
3. **Inventory Gap Analysis:** Identifies what must be purchased vs what's on hand
4. **Assembly Feasibility:** Validates that production plan enables assembly requirements
5. **Resource Optimization:** Minimizes waste while meeting event requirements

### 1.3 Design Rationale

**Core Problem:** Marianne consistently underproduces for events due to manual batch calculations. This year she ran short on nearly all finished goods, providing the primary motivation for building this application.

**Solution:** Automatic batch calculation from finished goods requirements. The system explodes event requirements (bundles, packages) down to FinishedUnit quantities, maps these to recipes, calculates optimal yield options, and presents a complete production plan.

**Mental Model:** Planning follows the cook's natural thinking process:
```
Event → Finished Goods → Recipes → Inventory → Purchasing → Production → Assembly → Delivery
```

---

## 2. Planning Mental Model

### 2.1 The Planning Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. EVENT DEFINITION                                     │
│    "Christmas 2025: 50 gift bags needed"                │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 2. FINISHED GOODS REQUIREMENTS                          │
│    "Each gift bag: 6 cookies + 3 brownies"              │
│    Total needed: 300 cookies, 150 brownies              │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 3. RECIPE SELECTION & BATCH CALCULATION                 │
│    Sugar Cookie Recipe (48 per batch): 7 batches        │
│    Brownie Recipe (24 per batch): 7 batches             │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 4. INGREDIENT AGGREGATION                               │
│    Flour: 14 cups (7 batches cookies × 2 cups)          │
│    Chocolate chips: 7 cups (variants)                    │
│    Cocoa powder: 3.5 cups (brownies)                     │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 5. INVENTORY GAP ANALYSIS                               │
│    Need: 14 cups flour                                   │
│    Have: 5 cups flour                                    │
│    Must purchase: 9 cups flour                           │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 6. PRODUCTION EXECUTION                                  │
│    Make 7 batches cookies (336 produced, 36 extra)      │
│    Make 7 batches brownies (168 produced, 18 extra)     │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 7. ASSEMBLY FEASIBILITY & COMPLETION                    │
│    ✅ Have 336 cookies (need 300)                       │
│    ✅ Have 168 brownies (need 150)                      │
│    ✅ Can assemble 50 gift bags                         │
│    [ ] Checklist: 50 gift bags assembled                │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Key Insight: Automatic Batch Calculation

**The Hard Problem:**
Users struggle to calculate: "I need 300 cookies and 150 brownies. How many batches?"

**System Solution:**
1. Group FinishedUnits by recipe (via recipe variant linkage)
2. Sum quantities needed per recipe
3. Find optimal yield option for each recipe
4. Calculate batches: `ceil(total_needed / yield_quantity)`

**Example:**
```
Need: 300 cookies
Recipe: Sugar Cookie (yield options: 24, 48, 96)

Calculation:
  - 96-cookie yield: 300 / 96 = 4 batches (384 total, 84 extra)
  - 48-cookie yield: 300 / 48 = 7 batches (336 total, 36 extra) ← OPTIMAL
  - 24-cookie yield: 300 / 24 = 13 batches (312 total, 12 extra)

Result: Use 48-cookie yield, make 7 batches
```

---

## 3. Scope & Boundaries

### 3.1 In Scope

**Event Planning:**
- ✅ Define event requirements (output mode, finished goods, quantities)
- ✅ Support multiple output modes (BULK_COUNT, BUNDLED)
- ✅ Event-scoped planning (Phase 2)
- ⏳ Multi-event planning (Phase 3)

**Production Planning:**
- ✅ Automatic batch calculation from finished goods requirements
- ✅ Recipe variant allocation (proportional distribution)
- ✅ Yield option optimization (minimize waste, minimize batches)
- ✅ Ingredient aggregation (base + variants)

**Inventory Planning:**
- ✅ Ingredient gap analysis (need vs have)
- ⏳ Phase 3: Inventory-aware planning (consider existing finished goods)
- ⏳ Phase 3: Substitution suggestions

**Assembly Planning:**
- ✅ Assembly feasibility check (event-scoped)
- ✅ Assembly completion checklist (Phase 2 minimal)
- ⏳ Phase 3: Assembly runs with inventory transactions

### 3.2 Out of Scope (Phase 2)

**Explicitly NOT Yet Supported:**
- ❌ Cross-event inventory awareness (Phase 3)
- ❌ Production shortfall calculation (use existing inventory) (Phase 3)
- ❌ Automatic substitution suggestions (Phase 3)
- ❌ Cost optimization (cheapest production plan)
- ❌ Schedule optimization (production timing)
- ❌ Shopping list generation (separate subsystem)

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. Know exactly how many batches to make for an event
2. See total ingredients needed across all recipes
3. Understand what I need to purchase vs what's on hand
4. Confirm that my production plan enables assembly
5. Track production and assembly progress

**As an event planner, I want to:**
1. Specify event requirements in terms I understand (bundles, packages, units)
2. Let the system calculate production details automatically
3. See a clear plan I can execute step-by-step
4. Be confident requirements will be met (no shortfalls)

**As a multi-event coordinator, I want to:**
1. Plan multiple events simultaneously (Phase 3)
2. Aggregate shopping needs across events (Phase 3)
3. Optimize production across events (Phase 3)

### 4.2 Use Case: Simple Event Planning (BULK_COUNT)

**Actor:** Baker
**Precondition:** Recipes and finished units defined
**Output Mode:** BULK_COUNT

**Main Flow:**
1. User creates event: "House Party"
2. Sets output mode: BULK_COUNT
3. Specifies requirements:
   - 100 Chocolate Chip Cookies (FinishedUnit)
   - 50 Brownies (FinishedUnit)
4. System calculates production plan:
   - Sugar Cookie Recipe (48/batch): 3 batches → 144 cookies (44 extra)
   - Brownie Recipe (24/batch): 3 batches → 72 brownies (22 extra)
5. System aggregates ingredients:
   - Flour: 6 cups (cookies) + 3 cups (brownies) = 9 cups
   - Chocolate chips: 3 cups (cookies)
   - Cocoa powder: 1.5 cups (brownies)
6. System checks inventory:
   - Have: 5 cups flour, 1 cup chocolate chips, 2 cups cocoa powder
   - Need to purchase: 4 cups flour, 2 cups chocolate chips
7. User reviews plan and proceeds to production

**Postconditions:**
- Production plan shows exact batches needed
- Ingredient shopping list generated
- User confident requirements will be met

### 4.3 Use Case: Bundle Event Planning (BUNDLED)

**Actor:** Baker
**Precondition:** Recipes, finished units, and bundles defined
**Output Mode:** BUNDLED

**Main Flow:**
1. User creates event: "Christmas Client Gifts"
2. Sets output mode: BUNDLED
3. Specifies requirements:
   - 50 Holiday Gift Bags (Bundle)
     - Each contains: 6 cookies, 3 brownies
4. System explodes to FinishedUnit quantities:
   - 300 cookies (50 × 6)
   - 150 brownies (50 × 3)
5. System groups by recipe (via FinishedUnit → RecipeVariant linkage):
   - Sugar Cookie Recipe produces Chocolate Chip Cookies
   - Brownie Recipe produces Fudge Brownies
6. System calculates batches:
   - Sugar Cookie (48/batch): 7 batches → 336 cookies (36 extra)
   - Brownie (24/batch): 7 batches → 168 brownies (18 extra)
7. System aggregates ingredients (scaled by batches)
8. System checks inventory gaps
9. System validates assembly feasibility:
   - After production: 336 cookies, 168 brownies
   - Can assemble: 50 bundles ✅ (need 300 cookies, 150 brownies)
10. User proceeds to production

**Postconditions:**
- Production plan meets bundle requirements
- Assembly feasibility confirmed
- User has clear execution path

### 4.4 Use Case: Recipe Variant Allocation

**Actor:** Baker
**Precondition:** Recipe with multiple variants, event requires mixed FinishedUnits

**Main Flow:**
1. Event requires:
   - 24 Chocolate Chip Cookies (FinishedUnit)
   - 24 Rainbow Sprinkle Cookies (FinishedUnit)
   - 24 Sugar Coated Cookies (FinishedUnit)
   - 24 Plain Cookies (FinishedUnit)
2. All produced by: Sugar Cookie Recipe
3. Recipe has variants:
   - Chocolate Chip variant → Chocolate Chip Cookies
   - Rainbow Sprinkle variant → Rainbow Sprinkle Cookies
   - Sugar Coated variant → Sugar Coated Cookies
   - Plain variant → Plain Cookies
4. System calculates:
   - Total needed: 96 cookies
   - Recipe yield options: 24, 48, 96
   - Optimal: 96-cookie yield, 1 batch
5. System allocates variants proportionally:
   - 24 cookies (25%) → Chocolate Chip variant
   - 24 cookies (25%) → Rainbow Sprinkle variant
   - 24 cookies (25%) → Sugar Coated variant
   - 24 cookies (25%) → Plain variant
6. System calculates variant ingredient needs:
   - Base ingredients × 1 batch
   - Chocolate chips for 25% of batch
   - Rainbow sprinkles for 25% of batch
   - Coarse sugar for 25% of batch
7. User proceeds with production

**Postconditions:**
- Single recipe produces multiple FinishedUnit types
- Variant ingredients calculated proportionally
- Production plan accounts for finishing variations

---

## 5. Functional Requirements

### 5.1 Event Planning

**REQ-PLAN-001:** System shall support event creation with name, date, and output mode
**REQ-PLAN-002:** Events shall have output_mode attribute (BULK_COUNT, BUNDLED, PACKAGED, etc.)
**REQ-PLAN-003:** Events shall define requirements based on output mode:
- BULK_COUNT: List of {finished_unit_id, quantity}
- BUNDLED: List of {bundle_id, quantity}
- PACKAGED: List of {package_id, quantity} [Phase 3]

**REQ-PLAN-004:** System shall validate event requirements reference valid entities
**REQ-PLAN-005:** System shall support event editing (requirements, quantities, dates)

### 5.2 Finished Goods Explosion

**REQ-PLAN-006:** System shall explode Bundle requirements to FinishedUnit quantities
**REQ-PLAN-007:** System shall explode Package requirements to Bundle then FinishedUnit quantities [Phase 3]
**REQ-PLAN-008:** Explosion shall multiply bundle/package contents by quantity needed
**REQ-PLAN-009:** System shall aggregate duplicate FinishedUnits across requirements

**Example:**
```
Event requirements:
  - 50 Gift Bag A (contains: 6 cookies, 3 brownies)
  - 25 Gift Bag B (contains: 12 cookies, 6 truffles)

Explosion:
  Cookies: (50 × 6) + (25 × 12) = 300 + 300 = 600 total
  Brownies: (50 × 3) = 150 total
  Truffles: (25 × 6) = 150 total
```

### 5.3 Recipe Grouping & Batch Calculation

**REQ-PLAN-010:** System shall group FinishedUnits by recipe (via recipe variant linkage)
**REQ-PLAN-011:** System shall sum quantities needed per recipe
**REQ-PLAN-012:** System shall retrieve recipe yield options for each recipe
**REQ-PLAN-013:** System shall calculate optimal yield option using these criteria:
1. Must meet or exceed requirement (never underproduce)
2. Minimize waste (extra units produced)
3. Minimize batches (fewer production runs if waste tied)

**REQ-PLAN-014:** System shall calculate batches needed: `ceil(total_needed / yield_quantity)`
**REQ-PLAN-015:** System shall calculate total yield: `batches × yield_quantity`
**REQ-PLAN-016:** System shall calculate extra units: `total_yield - total_needed`

**Example:**
```
Need: 300 cookies
Yield options: [24, 48, 96]

Option 1: 96-cookie yield
  Batches: ceil(300 / 96) = 4
  Total yield: 4 × 96 = 384
  Extra: 384 - 300 = 84

Option 2: 48-cookie yield ← OPTIMAL
  Batches: ceil(300 / 48) = 7
  Total yield: 7 × 48 = 336
  Extra: 336 - 300 = 36 (least waste)

Option 3: 24-cookie yield
  Batches: ceil(300 / 24) = 13
  Total yield: 13 × 24 = 312
  Extra: 312 - 300 = 12 (but more batches)
```

### 5.4 Variant Allocation

**REQ-PLAN-017:** System shall track which recipe variants produce which FinishedUnits
**REQ-PLAN-018:** System shall calculate variant proportions within a batch
**REQ-PLAN-019:** Variant proportion = (variant_quantity_needed / total_recipe_quantity)

**Example:**
```
Recipe: Sugar Cookie (96 per batch, 1 batch)
FinishedUnits needed:
  - 24 Chocolate Chip (variant A)
  - 24 Rainbow Sprinkle (variant B)
  - 48 Plain (variant C)

Proportions:
  - Variant A: 24/96 = 25%
  - Variant B: 24/96 = 25%
  - Variant C: 48/96 = 50%
```

### 5.5 Ingredient Aggregation

**REQ-PLAN-020:** System shall calculate base ingredients per recipe
**REQ-PLAN-021:** Base ingredients scaled by: batches × batch_multiplier (from yield option)
**REQ-PLAN-022:** System shall calculate variant ingredients per recipe
**REQ-PLAN-023:** Variant ingredients scaled by: base_scaled × variant_proportion
**REQ-PLAN-024:** System shall aggregate ingredients across all recipes
**REQ-PLAN-025:** Aggregation shall combine same ingredient from multiple recipes

**Example:**
```
Recipe A (Sugar Cookie): 7 batches
  Base: 2 cups flour per batch → 14 cups total
  Variant (25%): 0.5 cup chocolate chips → 3.5 cups total

Recipe B (Brownie): 7 batches
  Base: 1 cup flour per batch → 7 cups total
  Base: 0.5 cup cocoa per batch → 3.5 cups total

Aggregated:
  Flour: 14 + 7 = 21 cups (from both recipes)
  Chocolate chips: 3.5 cups (from cookie variant)
  Cocoa powder: 3.5 cups (from brownies)
```

### 5.6 Inventory Gap Analysis

**REQ-PLAN-026:** System shall query current ingredient inventory
**REQ-PLAN-027:** For each ingredient needed, system shall calculate gap:
- If `inventory_quantity >= needed_quantity`: gap = 0 (sufficient)
- If `inventory_quantity < needed_quantity`: gap = needed - inventory (purchase)

**REQ-PLAN-028:** System shall generate list of ingredients to purchase
**REQ-PLAN-029:** System shall display available ingredients (no purchase needed)

**Phase 3 Enhancement:**
**REQ-PLAN-030:** System shall suggest substitutions for missing ingredients [Phase 3]

### 5.7 Assembly Planning (Event-Scoped Phase 2)

**REQ-PLAN-031:** System shall calculate assembly requirements from event Bundle needs
**REQ-PLAN-032:** System shall validate assembly feasibility:
- After production, are there enough FinishedUnits?
- Compare: FinishedUnits_produced ≥ FinishedUnits_needed_for_assembly

**REQ-PLAN-033:** System shall display assembly feasibility status (visual indicator)
**REQ-PLAN-034:** System shall provide assembly completion checklist (Phase 2 minimal)
**REQ-PLAN-035:** Checklist shall disable until production complete
**REQ-PLAN-036:** Checking checklist item shall record assembly confirmation
**REQ-PLAN-037:** Phase 3: System shall create assembly runs with inventory transactions

**Phase 2 Assembly Feasibility Example:**
```
Event: Christmas 2025
Production Plan (after execution):
  - 336 Chocolate Chip Cookies produced
  - 168 Brownies produced

Bundle Requirements:
  - 50 Holiday Gift Bags
    - Needs: 300 cookies (50 × 6)
    - Needs: 150 brownies (50 × 3)

Feasibility Check:
  ✅ Have 336 cookies (need 300) - Sufficient
  ✅ Have 168 brownies (need 150) - Sufficient
  ✅ Can assemble 50 bundles

Assembly Checklist:
  [ ] 50 Holiday Gift Bags (ready to assemble)
```

### 5.8 Production Plan Validation

**REQ-PLAN-038:** System shall validate production plan completeness:
- All FinishedUnits needed have production plan
- All recipe linkages exist
- All yield options are valid

**REQ-PLAN-039:** System shall warn if production creates shortfall (never underproduce)
**REQ-PLAN-040:** System shall warn if excessive waste (user configurable threshold)

### 5.9 Multi-Event Planning (Phase 3)

**REQ-PLAN-041:** System shall support planning multiple events simultaneously [Phase 3]
**REQ-PLAN-042:** System shall aggregate ingredients across events [Phase 3]
**REQ-PLAN-043:** System shall consider cross-event inventory [Phase 3]
**REQ-PLAN-044:** System shall allow event prioritization [Phase 3]

---

## 6. Non-Functional Requirements

### 6.1 Usability

**REQ-PLAN-NFR-001:** Batch calculation shall be automatic (no manual math)
**REQ-PLAN-NFR-002:** Production plan shall display in user-friendly format
**REQ-PLAN-NFR-003:** Assembly feasibility shall use clear visual indicators (✅/⚠️/❌)
**REQ-PLAN-NFR-004:** Planning workflow shall follow natural mental model (event → finished goods → recipes)

### 6.2 Performance

**REQ-PLAN-NFR-005:** Batch calculation shall complete in <500ms for events with 10+ recipes
**REQ-PLAN-NFR-006:** Ingredient aggregation shall complete in <200ms
**REQ-PLAN-NFR-007:** Assembly feasibility check shall complete in <100ms

### 6.3 Accuracy

**REQ-PLAN-NFR-008:** Batch calculations shall always meet or exceed requirements (never short)
**REQ-PLAN-NFR-009:** Ingredient quantities shall be accurate to 2 decimal places
**REQ-PLAN-NFR-010:** Variant proportions shall sum to 100% (within rounding error)

---

## 7. Planning Algorithm

### 7.1 Core Batch Calculation Algorithm

```python
def calculate_production_plan(event_requirements, output_mode):
    """
    Calculate production plan from event requirements.

    Returns:
        production_plan: {
            recipes: [
                {
                    recipe: RecipeTemplate,
                    yield_option: RecipeYieldOption,
                    batches: int,
                    total_yield: int,
                    extra: int,
                    variant_allocations: [
                        {variant, finished_unit, quantity, proportion}
                    ]
                }
            ],
            ingredients: [
                {ingredient, total_quantity, unit}
            ],
            assembly_feasibility: {
                bundles: [{bundle, can_assemble, missing_components}]
            }
        }
    """

    # Step 1: Explode requirements to FinishedUnit quantities
    finished_units_needed = explode_requirements(
        event_requirements,
        output_mode
    )
    # Example: {
    #   "Chocolate Chip Cookie": 300,
    #   "Fudge Brownie": 150
    # }

    # Step 2: Group FinishedUnits by recipe
    recipe_groups = group_by_recipe(finished_units_needed)
    # Example: {
    #   "Sugar Cookie Recipe": {
    #     "Chocolate Chip Cookie": 300
    #   },
    #   "Brownie Recipe": {
    #     "Fudge Brownie": 150
    #   }
    # }

    # Step 3: Calculate batches for each recipe
    recipe_plans = []
    for recipe, finished_units in recipe_groups.items():
        total_needed = sum(finished_units.values())

        # Find optimal yield option
        optimal = find_optimal_yield(
            total_needed,
            recipe.yield_options
        )

        # Calculate variant allocations
        variant_allocations = calculate_variant_allocations(
            recipe,
            finished_units,
            optimal.total_yield
        )

        recipe_plans.append({
            'recipe': recipe,
            'yield_option': optimal.yield_option,
            'batches': optimal.batches,
            'total_yield': optimal.total_yield,
            'extra': optimal.extra,
            'variant_allocations': variant_allocations
        })

    # Step 4: Aggregate ingredients
    ingredients = aggregate_ingredients(recipe_plans)

    # Step 5: Check inventory gaps
    inventory_gaps = check_inventory_gaps(ingredients)

    # Step 6: Validate assembly feasibility
    assembly_feasibility = validate_assembly_feasibility(
        recipe_plans,
        event_requirements
    )

    return {
        'recipes': recipe_plans,
        'ingredients': ingredients,
        'inventory_gaps': inventory_gaps,
        'assembly_feasibility': assembly_feasibility
    }


def find_optimal_yield(total_needed, yield_options):
    """
    Find best yield option that meets requirement.

    Optimization criteria:
    1. Must meet or exceed requirement (never short)
    2. Minimize waste (extra units)
    3. Minimize batches (if waste tied)
    """
    solutions = []

    for yield_option in yield_options:
        batches = math.ceil(total_needed / yield_option.quantity)
        total_yield = batches * yield_option.quantity
        extra = total_yield - total_needed

        solutions.append({
            'yield_option': yield_option,
            'batches': batches,
            'total_yield': total_yield,
            'extra': extra
        })

    # Sort by: least waste, then fewest batches
    solutions.sort(key=lambda s: (s['extra'], s['batches']))

    return solutions[0]


def calculate_variant_allocations(recipe, finished_units, total_yield):
    """
    Calculate how variants are distributed within batches.

    Returns:
        variant_allocations: [
            {
                variant: RecipeIngredientVariant,
                finished_unit: FinishedUnit,
                quantity: int,
                proportion: Decimal (0.0 - 1.0)
            }
        ]
    """
    allocations = []

    for finished_unit_id, quantity_needed in finished_units.items():
        finished_unit = FinishedUnit.get(finished_unit_id)
        variant = finished_unit.recipe_variant
        proportion = Decimal(quantity_needed) / Decimal(total_yield)

        allocations.append({
            'variant': variant,
            'finished_unit': finished_unit,
            'quantity': quantity_needed,
            'proportion': proportion
        })

    return allocations


def aggregate_ingredients(recipe_plans):
    """
    Aggregate ingredients across all recipes.

    For each recipe:
    - Base ingredients × batches × batch_multiplier
    - Variant ingredients × batches × batch_multiplier × variant_proportion

    Combine same ingredients from different recipes.
    """
    ingredient_totals = {}

    for plan in recipe_plans:
        recipe = plan['recipe']
        batches = plan['batches']
        yield_option = plan['yield_option']
        batch_multiplier = yield_option.batch_multiplier

        # Base ingredients
        for recipe_ingredient in recipe.base_ingredients:
            scaled_quantity = (
                recipe_ingredient.quantity
                * batches
                * batch_multiplier
            )
            add_to_total(
                ingredient_totals,
                recipe_ingredient.ingredient,
                scaled_quantity,
                recipe_ingredient.unit
            )

        # Variant ingredients
        for allocation in plan['variant_allocations']:
            variant = allocation['variant']
            proportion = allocation['proportion']

            for variant_ingredient in variant.ingredient_changes:
                if variant_ingredient.action == "add":
                    scaled_quantity = (
                        variant_ingredient.quantity
                        * batches
                        * batch_multiplier
                        * proportion
                    )
                    add_to_total(
                        ingredient_totals,
                        variant_ingredient.ingredient,
                        scaled_quantity,
                        variant_ingredient.unit
                    )

    return ingredient_totals
```

### 7.2 Assembly Feasibility Algorithm (Phase 2 Event-Scoped)

```python
def validate_assembly_feasibility(recipe_plans, event_requirements):
    """
    Check if production plan enables assembly.

    Phase 2: Event-scoped only (no cross-event inventory)

    Returns:
        feasibility: {
            bundles: [
                {
                    bundle: Bundle,
                    quantity_needed: int,
                    can_assemble: bool,
                    components: [
                        {
                            finished_unit: FinishedUnit,
                            needed: int,
                            available_after_production: int,
                            sufficient: bool
                        }
                    ]
                }
            ]
        }
    """
    # Calculate FinishedUnits that will be available after production
    finished_units_produced = {}
    for plan in recipe_plans:
        for allocation in plan['variant_allocations']:
            finished_unit = allocation['finished_unit']
            quantity = allocation['quantity']
            finished_units_produced[finished_unit.id] = quantity

    # Check each bundle requirement
    bundle_feasibility = []

    for requirement in event_requirements:
        if requirement.type == 'bundle':
            bundle = requirement.bundle
            quantity_needed = requirement.quantity

            # Check each component
            components = []
            can_assemble = True

            for bundle_content in bundle.contents:
                finished_unit = bundle_content.finished_unit
                needed_per_bundle = bundle_content.quantity
                total_needed = needed_per_bundle * quantity_needed

                available = finished_units_produced.get(
                    finished_unit.id,
                    0
                )

                sufficient = available >= total_needed
                if not sufficient:
                    can_assemble = False

                components.append({
                    'finished_unit': finished_unit,
                    'needed': total_needed,
                    'available_after_production': available,
                    'sufficient': sufficient
                })

            bundle_feasibility.append({
                'bundle': bundle,
                'quantity_needed': quantity_needed,
                'can_assemble': can_assemble,
                'components': components
            })

    return {'bundles': bundle_feasibility}
```

---

## 8. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   USER INPUT LAYER                      │
│  Event: "Christmas 2025"                                │
│  Output Mode: BUNDLED                                   │
│  Requirements: 50 Holiday Gift Bags                     │
│    (6 cookies + 3 brownies each)                        │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              EXPLOSION LAYER                            │
│  explode_requirements()                                 │
│                                                         │
│  Bundle → FinishedUnit quantities:                      │
│    50 bags × 6 cookies = 300 cookies                    │
│    50 bags × 3 brownies = 150 brownies                  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              RECIPE GROUPING LAYER                      │
│  group_by_recipe()                                      │
│                                                         │
│  Via FinishedUnit.recipe_variant linkage:               │
│    "Sugar Cookie Recipe": 300 cookies                   │
│    "Brownie Recipe": 150 brownies                       │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│           BATCH CALCULATION LAYER                       │
│  find_optimal_yield()                                   │
│                                                         │
│  Sugar Cookie (yield options: 24, 48, 96):             │
│    Optimal: 48-cookie yield                             │
│    Batches: ceil(300 / 48) = 7                          │
│    Total: 336 cookies (36 extra)                        │
│                                                         │
│  Brownie (yield options: 24):                           │
│    Batches: ceil(150 / 24) = 7                          │
│    Total: 168 brownies (18 extra)                       │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│          INGREDIENT AGGREGATION LAYER                   │
│  aggregate_ingredients()                                │
│                                                         │
│  Base ingredients (scaled by batches):                  │
│    Flour: 14 cups (cookies) + 7 cups (brownies) = 21   │
│    Butter: 7 cups (cookies)                             │
│    Cocoa: 3.5 cups (brownies)                           │
│                                                         │
│  Variant ingredients (scaled by proportion):            │
│    Chocolate chips: 3.5 cups (cookies, 100% variant)    │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│          INVENTORY GAP ANALYSIS LAYER                   │
│  check_inventory_gaps()                                 │
│                                                         │
│  Current inventory:                                     │
│    Flour: 10 cups                                       │
│    Butter: 7 cups                                       │
│    Cocoa: 0 cups                                        │
│    Chocolate chips: 1 cup                               │
│                                                         │
│  Gaps (need to purchase):                               │
│    Flour: 11 cups (21 - 10)                             │
│    Cocoa: 3.5 cups (3.5 - 0)                            │
│    Chocolate chips: 2.5 cups (3.5 - 1)                  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│        ASSEMBLY FEASIBILITY LAYER                       │
│  validate_assembly_feasibility()                        │
│                                                         │
│  After production (event-scoped):                       │
│    Cookies available: 336                               │
│    Brownies available: 168                              │
│                                                         │
│  Bundle requirements:                                   │
│    50 bags × 6 cookies = 300 needed                     │
│    50 bags × 3 brownies = 150 needed                    │
│                                                         │
│  Feasibility:                                           │
│    ✅ Cookies: 336 ≥ 300 (sufficient)                   │
│    ✅ Brownies: 168 ≥ 150 (sufficient)                  │
│    ✅ Can assemble 50 gift bags                         │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                  OUTPUT LAYER                           │
│  Production Plan (to user)                              │
│                                                         │
│  Recipes to Make:                                       │
│    ✓ Sugar Cookie: 7 batches (336 cookies)             │
│    ✓ Brownies: 7 batches (168 brownies)                │
│                                                         │
│  Shopping List:                                         │
│    □ Flour: 11 cups                                     │
│    □ Cocoa powder: 3.5 cups                             │
│    □ Chocolate chips: 2.5 cups                          │
│                                                         │
│  Assembly Checklist:                                    │
│    □ 50 Holiday Gift Bags (ready to assemble)          │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Validation Rules

### 9.1 Event Planning Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PLAN-001 | Event name required | "Event name cannot be empty" |
| VAL-PLAN-002 | Output mode required | "Output mode must be selected" |
| VAL-PLAN-003 | At least one requirement needed | "Event must have at least one requirement" |
| VAL-PLAN-004 | Requirement quantities must be positive | "Quantity must be greater than zero" |

### 9.2 Production Plan Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PLAN-005 | All FinishedUnits must have recipe linkage | "Cannot plan production: {finished_unit} has no recipe" |
| VAL-PLAN-006 | All recipes must have yield options | "Recipe {recipe} has no yield options defined" |
| VAL-PLAN-007 | Batches must be positive integer | "Batch count must be at least 1" |

### 9.3 Assembly Validation

| Rule ID | Validation | Error Message |
|---------|-----------|---------------|
| VAL-PLAN-008 | Cannot assemble if components insufficient | "Cannot assemble: need {X}, have {Y}" |
| VAL-PLAN-009 | All bundle components must have production plan | "Cannot assemble: {component} not in production plan" |

---

## 10. Acceptance Criteria

### 10.1 Phase 2 (Current) Acceptance

**Must Have:**
- [ ] Event creation with output mode selection
- [ ] Bundle → FinishedUnit explosion
- [ ] Automatic batch calculation (meets/exceeds requirement)
- [ ] Yield optimization (minimize waste, minimize batches)
- [ ] Variant allocation calculation
- [ ] Ingredient aggregation (base + variants)
- [ ] Inventory gap analysis
- [ ] Assembly feasibility check (event-scoped)
- [ ] Assembly completion checklist (minimal UI)

**Should Have:**
- [ ] Clear production plan display
- [ ] Visual feasibility indicators (✅/⚠️/❌)
- [ ] Validation warnings (shortfalls, excessive waste)

**Nice to Have:**
- [ ] Production plan export (PDF, print)
- [ ] Multiple yield option comparison view
- [ ] "What if" scenario planning

### 10.2 Phase 3 (Future) Acceptance

**Cross-Event Planning:**
- [ ] Multi-event ingredient aggregation
- [ ] Cross-event inventory awareness
- [ ] Production shortfall calculation (use existing inventory)
- [ ] Event prioritization

**Advanced Features:**
- [ ] Ingredient substitution suggestions
- [ ] Cost optimization (cheapest plan)
- [ ] Schedule optimization (production timing)
- [ ] Shopping list generation UI

---

## 11. Dependencies

### 11.1 Upstream Dependencies (Blocks This)

- ✅ Recipe system with yield options (req_recipes.md)
- ✅ RecipeIngredientVariant → FinishedUnit linkage
- ✅ Finished goods hierarchy (req_finished_goods.md)
- ✅ Ingredient inventory tracking
- ⏳ Phase 3: Finished goods inventory (F040)

### 11.2 Downstream Dependencies (This Blocks)

- Production execution (requires production plan)
- Shopping list generation (requires ingredient gaps)
- Assembly execution (requires assembly feasibility)
- Event fulfillment tracking

---

## 12. Testing Requirements

### 12.1 Test Coverage

**Unit Tests:**
- Batch calculation logic (various yield options)
- Yield optimization (waste minimization)
- Variant proportion calculation
- Ingredient aggregation across recipes
- Assembly feasibility logic

**Integration Tests:**
- End-to-end event planning workflow
- Bundle explosion to FinishedUnits
- Recipe grouping via linkages
- Inventory gap calculation
- Assembly feasibility with production plan

**User Acceptance Tests:**
- Create event with BULK_COUNT mode
- Create event with BUNDLED mode
- Verify batch calculations meet requirements
- Confirm assembly feasibility checks work
- Validate ingredient shopping lists accurate

---

## 13. Open Questions & Future Considerations

### 13.1 Open Questions

**Q1:** Should system allow manual batch override (user knows better)?
**A1:** Phase 2: Auto-calculate only. Phase 3: Allow manual override with validation.

**Q2:** How to handle partial production (some batches done, some pending)?
**A2:** Phase 2: Track at event level (all or nothing). Phase 3: Granular batch tracking.

**Q3:** Should system suggest consolidating similar recipes?
**A3:** Good Phase 3+ optimization. "These recipes share 80% ingredients, consider combining?"

**Q4:** How to handle recipe yield changes after plan created?
**A4:** Phase 2: Require manual replan. Phase 3: Auto-detect and warn user.

### 13.2 Future Enhancements

**Phase 3 Candidates:**
- Multi-event planning dashboard
- Cross-event inventory optimization
- Production schedule optimization (order batches by urgency)
- Cost-based yield selection
- AI-suggested event templates based on history

**Phase 4 Candidates:**
- Predictive planning (ML-based demand forecasting)
- Collaborative planning (multi-user events)
- Real-time plan adjustments during production
- Mobile planning app

---

## 14. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-01-04 | Kent Gale | Initial seeded draft from planning discussions |

---

## 15. Approval & Sign-off

**Document Owner:** Kent Gale
**Last Review Date:** 2025-01-04
**Next Review Date:** TBD (after extension and refinement)
**Status:** 📝 DRAFT - SEEDED

---

## 16. Related Documents

- **Requirements:** `req_finished_goods.md` (finished goods hierarchy)
- **Requirements:** `req_recipes.md` (recipe → FinishedUnit linkage)
- **Requirements:** `req_ingredients.md` (ingredient inventory)
- **Design Specs:** `_F040_finished_goods_inventory.md` (Phase 3 inventory)
- **Design Specs:** `F026-deferred-packaging-decisions.md` (material deferral)
- **Constitution:** `/.kittify/memory/constitution.md` (architectural principles)

---

**END OF REQUIREMENTS DOCUMENT (DRAFT - SEEDED)**
