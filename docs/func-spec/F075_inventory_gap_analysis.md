# F075: Inventory Gap Analysis

**Version**: 1.0  
**Priority**: HIGH  
**Type**: Service Integration + UI

---

## Executive Summary

User has ingredient totals but no shopping list:
- ❌ No comparison against current inventory
- ❌ No gap calculation (what to purchase)
- ❌ No shopping list display

This spec integrates with InventoryService to generate shopping list.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Ingredient Totals
└─ ✅ System knows total ingredients needed (F074)

Inventory Comparison
└─ ❌ No check against current inventory

Shopping List
└─ ❌ Doesn't exist
```

**Target State (COMPLETE):**
```
Inventory Gap Analysis
├─ ✅ Query current inventory per ingredient
├─ ✅ Calculate gaps (need - have)
└─ ✅ Flag items requiring purchase

Shopping List Display
├─ ✅ Show ingredients to purchase with quantities
└─ ✅ Show sufficient ingredients separately
```

---

## CRITICAL: Study These Files FIRST

1. **InventoryService**
   - Find inventory query methods
   - Understand how to get current quantities
   - Note unit handling

2. **Ingredient totals (F074)**
   - Find output structure
   - Understand how to iterate
   - Note unit information

---

## Requirements Reference

Implements:
- **REQ-PLAN-047** through **REQ-PLAN-052**: Inventory gap requirements
- Section 7.6 from req_planning.md (v0.4)

---

## Functional Requirements

### FR-1: Query Current Inventory

**What it must do:**
- For each ingredient in totals, query current inventory
- Handle missing inventory (treat as zero)
- Use same units as ingredient totals

**Success criteria:**
- [ ] Inventory queries work
- [ ] Missing inventory handled
- [ ] Unit consistency maintained

---

### FR-2: Calculate Gaps

**What it must do:**
- For each ingredient: gap = max(0, needed - on_hand)
- Flag ANY shortfall for purchasing
- Identify sufficient ingredients

**Success criteria:**
- [ ] Gap calculation correct
- [ ] Shortfall flagging works
- [ ] Sufficient identification works

---

### FR-3: Display Shopping List

**What it must do:**
- Show ingredients requiring purchase with quantities
- Show sufficient ingredients separately
- Format clearly for user

**Success criteria:**
- [ ] Purchase list clear
- [ ] Sufficient list shown
- [ ] Formatting readable

---

## Out of Scope

- ❌ Shopping list export (future)
- ❌ Store assignment (future)
- ❌ Price estimation (future)

---

## Success Criteria

### Gap Analysis
- [ ] Queries work correctly
- [ ] Calculations accurate
- [ ] Gaps identified

### Shopping List
- [ ] Purchase items displayed
- [ ] Sufficient items displayed
- [ ] User can take action

### Quality
- [ ] Integration works
- [ ] Error handling robust
- [ ] Performance acceptable

---

## Constitutional Compliance

✅ **Service Integration**
✅ **Data Accuracy**
✅ **User-Facing Output**

---

## Notes for Implementation

Study InventoryService interface, integrate with F074 output.

---

**END OF SPECIFICATION**
