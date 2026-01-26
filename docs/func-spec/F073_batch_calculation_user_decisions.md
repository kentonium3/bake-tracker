# F073: Batch Calculation & User Decisions

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Layer + UI (Core Value Proposition)

---

## Executive Summary

Manual batch calculations lead to consistent underproduction - the primary problem this application solves:
- ❌ No automatic batch calculation from recipe requirements
- ❌ No presentation of rounding options (floor vs ceil)
- ❌ No user decision point for strategic batch choices
- ❌ No storage of user's batch decisions
- ❌ No shortfall warnings when rounding down

This spec implements the core value proposition: automatic batch calculation with informed user decisions, replacing error-prone manual calculations that consistently cause underproduction.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Recipe Requirements
└─ ✅ System knows quantities needed per recipe (F072)

Batch Calculation
└─ ❌ No calculation of batch options

User Decision Point
└─ ❌ No way for user to choose rounding strategy

Batch Decisions Storage
└─ ❌ batch_decisions table unused (exists from F068)
```

**Target State (COMPLETE):**
```
Batch Calculation
├─ ✅ Calculate floor option (may create shortfall)
├─ ✅ Calculate ceil option (meets or exceeds)
├─ ✅ Calculate exact match when applicable
└─ ✅ Show actual numbers (batches, yield, difference)

User Decision UI
├─ ✅ Present options per recipe
├─ ✅ Show trade-offs (shortfall/excess)
├─ ✅ Warn on shortfalls
├─ ✅ User selects option per recipe
└─ ✅ Shortfall confirmation required

Batch Decisions Persistence
└─ ✅ Decisions stored in batch_decisions table
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Recipe yield options**
   - Find recipe_yield_options model
   - Understand yield structure (quantity, batch_multiplier, yield_type)
   - Note how multiple yield options handled

2. **Recipe requirements (F072)**
   - Find calculate_recipe_requirements method
   - Understand output structure (Recipe → quantity)
   - Note how to iterate over requirements

3. **batch_decisions model (F068)**
   - Find table structure (event_id, recipe_id, batches, yield_option_id)
   - Understand constraints
   - Note how decisions linked to yield options

4. **Decision presentation patterns**
   - Find radio button or option selection patterns
   - Study how options presented with detail
   - Note warning/alert UI patterns

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-028**: For each recipe, system shall calculate batch requirement options
- **REQ-PLAN-029**: System shall present at least two options (rounding down and up) where applicable
- **REQ-PLAN-030**: For each option, system shall display batches, total yield, shortfall/excess with warnings
- **REQ-PLAN-031**: User shall select which batch option to use for each recipe
- **REQ-PLAN-032**: System shall NOT allow selection of options that create shortfalls unless user explicitly confirms
- **REQ-PLAN-033**: System shall persist user's batch decisions with the event
- **REQ-PLAN-034**: System shall allow user to modify batch decisions after selection
- **VAL-PLAN-009**: Batch count must be positive integer
- **VAL-PLAN-010**: Shortfall selection requires confirmation
- **VAL-PLAN-011**: Each recipe must have batch decision

From: `docs/requirements/req_planning.md` (v0.4) - Section 7.3, Mental Model Section 2.2.3

---

## Functional Requirements

### FR-1: Calculate Batch Options Per Recipe

**What it must do:**
- Given recipe requirements (recipe → quantity_needed), calculate batch options
- For each recipe's yield options, calculate floor and ceil batch counts
- Calculate total yield for each option (batches × yield_quantity)
- Calculate difference (yield - needed): negative = shortfall, positive = excess
- Identify exact matches (yield == needed)

**Calculation logic:**
```
for each yield_option:
  floor_batches = floor(quantity_needed / yield_quantity)
  floor_yield = floor_batches * yield_quantity
  floor_diff = floor_yield - quantity_needed
  
  ceil_batches = ceil(quantity_needed / yield_quantity)
  ceil_yield = ceil_batches * yield_quantity
  ceil_diff = ceil_yield - quantity_needed
  
  options.append({
    batches: floor_batches,
    yield: floor_yield,
    difference: floor_diff,
    is_shortfall: floor_diff < 0
  })
  
  if ceil_batches != floor_batches:
    options.append({
      batches: ceil_batches,
      yield: ceil_yield,
      difference: ceil_diff,
      is_shortfall: False
    })
```

**Pattern reference:** Mathematical calculation, straightforward logic

**Success criteria:**
- [ ] Floor option calculated correctly
- [ ] Ceil option calculated correctly
- [ ] Exact matches identified
- [ ] Difference calculations correct
- [ ] Shortfall flag accurate

---

### FR-2: Present Batch Options to User

**What it must do:**
- Display all recipes needing batch decisions
- For each recipe, show calculated options
- Present actual numbers (not percentages): batches, total yield, needed, difference
- Highlight shortfall warnings prominently
- Mark exact matches clearly
- Enable user to select one option per recipe

**UI Requirements:**
- Recipe name clear
- Quantity needed shown
- Options presented with radio buttons or similar
- Shortfall options have warning indicator (⚠️ or similar)
- Exact matches have success indicator (exact match!)
- Numbers formatted clearly (e.g., "8 batches = 192 cookies (8 short)")

**Presentation format example:**
```
Recipe: Sugar Cookie (yield: 24/batch)
Need: 200 cookies

Options:
  ○ 8 batches = 192 cookies (8 short ⚠️ SHORTFALL)
  ● 9 batches = 216 cookies (16 extra)
  ○ 10 batches = 240 cookies (40 extra)
```

**Pattern reference:** Study radio button groups, option selection patterns

**Success criteria:**
- [ ] All recipes displayed
- [ ] Options clear and readable
- [ ] Shortfalls prominently warned
- [ ] Exact matches highlighted
- [ ] Selection mechanism works

---

### FR-3: Shortfall Confirmation Flow

**What it must do:**
- When user selects shortfall option, trigger confirmation dialog
- Explain consequence clearly (will produce X short of needed Y)
- Require explicit confirmation
- Allow cancellation (revert to previous selection or no selection)

**Confirmation dialog:**
- Title: "Shortfall Warning"
- Message: "This will produce 192 cookies but you need 200. You'll be 8 short. Confirm this choice?"
- Buttons: Confirm / Cancel

**Pattern reference:** Confirmation dialog patterns

**Success criteria:**
- [ ] Shortfall selection triggers confirmation
- [ ] Message clear and specific
- [ ] User can confirm or cancel
- [ ] Cancellation reverts selection
- [ ] Non-shortfall options don't trigger confirmation

---

### FR-4: Persist Batch Decisions

**What it must do:**
- Save user's batch decisions to batch_decisions table
- Store: event_id, recipe_id, batches, yield_option_id
- Replace existing decisions on save (not append)
- Validate all recipes have decisions before allowing save
- Load existing decisions when event opened

**Service operations:**
```
save_batch_decision(event_id, recipe_id, batches, yield_option_id)
get_batch_decision(event_id, recipe_id) → BatchDecision
get_all_batch_decisions(event_id) → List[BatchDecision]
delete_batch_decision(event_id, recipe_id)
```

**Pattern reference:** PlanningService CRUD patterns (F068)

**Success criteria:**
- [ ] Decisions save correctly
- [ ] Decisions load on event open
- [ ] Pre-selection works
- [ ] Replace behavior correct
- [ ] Validation enforces completeness

---

### FR-5: Batch Decision Modification Support

**What it must do:**
- Allow user to change batch decisions after initial selection
- Recalculate downstream (F074, F075, F076 will use new decisions)
- Show impact of change if feasible

**Modification workflow:**
- User changes selection
- System saves new decision
- Downstream calculations automatically update (handled by those features)

**Success criteria:**
- [ ] User can change decisions
- [ ] Changes save correctly
- [ ] UI updates to reflect change
- [ ] Downstream features react to changes

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Variant allocation within batches (F074 - separate calculation)
- ❌ Ingredient aggregation (F074 - uses batch decisions)
- ❌ Inventory gap analysis (F075 - uses batch decisions)
- ❌ Optimization suggestions (future: "minimize waste" recommendation)
- ❌ Historical batch decision tracking (future analytics)
- ❌ Custom batch override (future: "I want exactly 7 batches")

---

## Success Criteria

**Complete when:**

### Batch Calculation
- [ ] Options calculated correctly per recipe
- [ ] Floor and ceil options present
- [ ] Exact matches identified
- [ ] Shortfall detection accurate
- [ ] Multiple yield options handled

### User Interface
- [ ] All recipes displayed
- [ ] Options clear and readable
- [ ] Numbers formatted well
- [ ] Shortfall warnings prominent
- [ ] Exact matches highlighted
- [ ] Selection mechanism intuitive

### Shortfall Confirmation
- [ ] Confirmation triggers on shortfall selection
- [ ] Message clear and specific
- [ ] User can confirm or cancel
- [ ] Cancellation works correctly

### Persistence
- [ ] Decisions save to database
- [ ] Decisions load correctly
- [ ] Pre-selection works
- [ ] Validation enforces completeness
- [ ] Modification support works

### Quality
- [ ] Math calculations correct
- [ ] Code follows patterns
- [ ] Error handling robust
- [ ] Performance acceptable

---

## Architecture Principles

### Core Value Proposition

**Solving Manual Calculation Errors:**
- This feature addresses the primary problem: underproduction
- Automatic calculation eliminates math errors
- User makes strategic decisions with accurate information

**Why this matters:**
- Most important feature in planning module
- Direct impact on event success
- Solves real, validated user pain

### User Decision Philosophy

**Informed Choices:**
- System calculates options
- User sees real numbers and trade-offs
- User makes final decision based on context

**Why not auto-select:**
- Different recipes have different sensitivities
- User knows event context (better to have extras vs waste)
- Strategic balancing across recipes possible

### Validation Strategy

**Shortfall Protection:**
- Shortfalls explicitly flagged
- Confirmation required
- User can't accidentally create shortfall

**Completeness Validation:**
- All recipes must have decisions before proceeding
- Prevents incomplete plans
- Clear feedback on missing decisions

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Batch decisions validated before save
- Foreign key constraints enforced
- No orphaned decisions

✅ **Principle II: User Empowerment**
- User makes final decisions
- System provides information, not mandates
- Confirmation protects but doesn't prevent

✅ **Principle III: Calculation Accuracy**
- Math operations deterministic
- Rounding explicit and correct
- No approximations

✅ **Principle IV: Pattern Matching**
- Service methods match F068 patterns
- UI selection matches established patterns
- Confirmation dialogs match established patterns

✅ **Principle V: Core Value Delivery**
- Directly solves underproduction problem
- Replaces error-prone manual process
- Measurable impact on user success

---

## Risk Considerations

**Risk: User overwhelmed by options**
- **Context:** Multiple yield options per recipe creates many choices
- **Mitigation:** Clear presentation, highlight recommended option (exact match or ceil), allow progressive disclosure

**Risk: User ignores shortfall warnings**
- **Context:** Confirmation dialog could become click-through
- **Mitigation:** Make consequences explicit and specific, use strong visual warnings

**Risk: Batch decisions invalidated by upstream changes**
- **Context:** If user changes recipe selection or FG quantities, existing batch decisions may be wrong
- **Mitigation:** Detect staleness, warn user, offer recalculation

**Risk: Multiple yield options confusing**
- **Context:** "Small" vs "Large" yields for same recipe
- **Mitigation:** Show yield type clearly in option presentation, explain what it means

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study math.floor, math.ceil usage
- Study radio button selection patterns
- Study confirmation dialog patterns
- Study PlanningService (F068) for persistence patterns

**Key Patterns to Copy:**
- Service CRUD methods (F068) → Batch decision methods
- Radio button groups → Option selection UI
- Confirmation dialogs → Shortfall confirmation

**Focus Areas:**
- **Math accuracy:** Floor/ceil calculations must be correct
- **UX clarity:** Options must be immediately understandable
- **Warning visibility:** Shortfalls must be impossible to miss
- **Decision persistence:** Saves and loads must be reliable

**UI Considerations:**
- Display format determined in planning phase
- Shortfall warning style determined in planning
- Exact match highlight style determined in planning
- Overall layout determined in planning
- Focus on WHAT must be communicated, not HOW to present

**Example Scenarios to Support:**
```
Scenario 1: Exact Match
Recipe: Cookies (24/batch)
Need: 72
Options: 3 batches = 72 (exact match!) ← User likely chooses this

Scenario 2: Strategic Balancing
Recipe A: Cookies (24/batch), need 100
  - 4 batches = 96 (4 short)
  - 5 batches = 120 (20 extra) ← User might choose
  
Recipe B: Brownies (32/batch), need 100
  - 3 batches = 96 (4 short) ← User might choose
  - 4 batches = 128 (28 extra)
  
Strategy: Go high on A (popular item), low on B (reduces total waste)
Total: 216 vs 200 needed (8% overproduction acceptable)
```

---

**END OF SPECIFICATION**
