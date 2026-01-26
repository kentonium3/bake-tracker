# F071: Quantity Specification

**Version**: 1.0  
**Priority**: HIGH  
**Type**: UI Enhancement + Service Integration

---

## Executive Summary

User can see available finished goods but cannot specify how many of each to make:
- ❌ No quantity input for selected finished goods
- ❌ No validation of quantity values
- ❌ No persistence of quantities with event
- ❌ No modification support after initial entry

This spec implements quantity specification UI allowing user to specify positive integer quantities for each FG, completing the basic event definition workflow.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Finished Goods Filtering
└─ ✅ User sees available FGs (F070)

Quantity Specification
└─ ❌ No way to specify how many of each FG

Event-FG Associations
└─ ❌ event_finished_goods table unused (exists from F068)
```

**Target State (COMPLETE):**
```
Quantity Specification
├─ ✅ Quantity input per selected FG
├─ ✅ Validation (positive integers only)
├─ ✅ Modification support
└─ ✅ Persistence to event_finished_goods table

User Workflow Complete
└─ ✅ User can fully define event: recipes + FGs + quantities
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **event_finished_goods model (F068)**
   - Find table structure (event_id, finished_good_id, quantity)
   - Understand primary key constraints
   - Note validation requirements

2. **PlanningService (F068)**
   - Study existing CRUD patterns
   - Understand session management
   - Note validation approach

3. **FG selection UI (F070)**
   - Find how FG list rendered
   - Understand how to add quantity inputs
   - Note layout and spacing patterns

4. **Quantity input patterns**
   - Find existing numeric input components
   - Study validation and error display
   - Note user feedback patterns

---

## Requirements Reference

This specification implements:
- **REQ-PLAN-018**: User shall specify quantity for each selected finished good
- **REQ-PLAN-019**: Quantities must be positive integers
- **REQ-PLAN-020**: System shall allow quantities to be modified after initial entry
- **REQ-PLAN-021**: System shall validate quantities reference valid finished goods
- **VAL-PLAN-005**: Quantity must be greater than zero

From: `docs/requirements/req_planning.md` (v0.4)

---

## Functional Requirements

### FR-1: Add Quantity Input to FG List

**What it must do:**
- Display numeric input field next to each available FG
- Accept positive integers only
- Default value: empty or 1 (planning phase decides)
- Validate on entry (reject negative, zero, non-integer)
- Show validation feedback inline

**UI Requirements:**
- Input field sized appropriately for typical values
- Validation errors clear and immediate
- Tab order logical for data entry

**Pattern reference:** Study existing numeric input components, copy validation patterns

**Success criteria:**
- [ ] Input field displays per FG
- [ ] Accepts integers only
- [ ] Rejects invalid values
- [ ] Validation feedback works
- [ ] Tab order logical

---

### FR-2: Persist FG Quantities

**What it must do:**
- Save FG + quantity pairs to event_finished_goods table
- Create record: (event_id, finished_good_id, quantity)
- Replace existing quantities on save (not append)
- Only save FGs with quantities > 0
- Validate FG still available before saving

**Service operations needed:**
```
set_event_fg_quantity(event_id, fg_id, quantity) → bool
remove_event_fg(event_id, fg_id) → bool
get_event_fg_quantities(event_id) → List[(FG, quantity)]
```

**Pattern reference:** PlanningService (F068) CRUD patterns

**Success criteria:**
- [ ] Quantities save to database
- [ ] Quantities load correctly
- [ ] Replace (not append) works
- [ ] Only non-zero quantities saved
- [ ] Validation prevents invalid FG IDs

---

### FR-3: Load and Display Existing Quantities

**What it must do:**
- When event opened, load existing quantities from event_finished_goods
- Pre-populate input fields with saved quantities
- Handle missing quantities (FG available but not selected)

**Loading behavior:**
- Query event_finished_goods for event_id
- Match FGs to input fields
- Display quantity or empty

**Pattern reference:** Standard form loading patterns

**Success criteria:**
- [ ] Existing quantities load correctly
- [ ] Input fields pre-populated
- [ ] Empty fields for unselected FGs
- [ ] Load performance acceptable

---

### FR-4: Quantity Modification Support

**What it must do:**
- Allow user to change quantities after initial entry
- Save updates same as initial save
- Clear quantity removes FG from event

**Modification scenarios:**
- Change existing quantity: update record
- Clear quantity (empty or 0): delete record
- Add new quantity: insert record

**Success criteria:**
- [ ] User can modify quantities
- [ ] Changes save correctly
- [ ] Clearing quantity removes FG
- [ ] Database updates work

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Bulk quantity entry (copy/paste lists)
- ❌ Quantity suggestions based on attendees
- ❌ Historical quantity defaults
- ❌ Batch calculation (F073 - happens after quantities set)
- ❌ Assembly feasibility (F076)

---

## Success Criteria

**Complete when:**

### UI Components
- [ ] Quantity input per available FG
- [ ] Validation works (positive integers)
- [ ] Error feedback clear
- [ ] Tab order logical

### Persistence
- [ ] Quantities save to database
- [ ] Quantities load on event open
- [ ] Pre-population works
- [ ] Replace behavior correct

### Modification
- [ ] User can change quantities
- [ ] Changes persist
- [ ] Clearing quantity works
- [ ] Database operations correct

### Validation
- [ ] Positive integers only
- [ ] Zero/negative rejected
- [ ] Non-integers rejected
- [ ] Error messages clear

### Quality
- [ ] Code follows patterns
- [ ] Service operations match F068
- [ ] Error handling robust
- [ ] Performance acceptable

---

## Architecture Principles

### Data Validation

**Client-Side First:**
- Validate in UI before submission
- Prevent invalid values early
- Provide immediate feedback

**Server-Side Always:**
- Service layer validates all inputs
- Never trust client validation alone
- Return validation errors clearly

### Zero vs Empty Distinction

**Business Rule:**
- Empty quantity = not selected (no record)
- Zero quantity = invalid (validation error)
- Only positive integers stored

### Atomic Operations

**Per-FG Granularity:**
- Each FG quantity is independent record
- Can update single FG without affecting others
- Enables fine-grained modifications

---

## Constitutional Compliance

✅ **Principle I: Data Integrity**
- Only valid quantities stored
- Validation prevents bad data
- Database constraints enforced

✅ **Principle II: Layered Architecture**
- UI handles input and validation
- Service handles persistence
- Clear separation maintained

✅ **Principle III: Service Primitives**
- Each operation atomic
- Set, get, remove operations independent
- Composable for higher-level features

✅ **Principle IV: User Intent Respected**
- Empty field = user hasn't decided
- Zero/negative = validation error
- Clear distinction maintained

✅ **Principle V: Pattern Matching**
- Quantity inputs match existing numeric input patterns
- Service methods match F068 PlanningService patterns
- Validation matches established validation patterns

---

## Risk Considerations

**Risk: User enters large quantities accidentally**
- **Context:** Typo could result in 1000 instead of 100
- **Mitigation:** Consider reasonable max value validation or confirmation for unusually large quantities

**Risk: Validation too strict**
- **Context:** User might need to save work-in-progress with missing quantities
- **Mitigation:** Allow saving with empty quantities, validate completeness at higher level (before batch calculation)

**Risk: Lost quantities when FG becomes unavailable**
- **Context:** User deselects recipe, FG auto-removed (F070), quantity lost
- **Mitigation:** Acceptable - F070 already notifies user of removal

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study numeric input components → apply to quantity fields
- Study PlanningService (F068) → add FG quantity methods
- Study validation patterns → apply to quantity validation
- Study form loading → apply to quantity pre-population

**Key Patterns to Copy:**
- Numeric input validation → Quantity validation
- Service CRUD methods (F068) → FG quantity methods
- Form field patterns → Quantity input fields

**Focus Areas:**
- **Validation clarity:** User understands why input rejected
- **Persistence reliability:** Quantities save and load correctly
- **Modification support:** Changes work smoothly
- **Performance:** Input responsive, save fast

---

**END OF SPECIFICATION**
