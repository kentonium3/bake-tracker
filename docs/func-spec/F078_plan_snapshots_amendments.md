# F078: Plan Snapshots & Amendments

**Version**: 1.0  
**Priority**: MEDIUM (Phase 3)  
**Type**: Service Layer + UI

---

## Executive Summary

Plans need to track changes during production:
- ❌ No snapshot of original plan
- ❌ No amendment tracking
- ❌ No current vs original comparison

This spec implements plan versioning and amendment logging for mid-production changes.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Plan History
└─ ❌ No record of original plan

Amendments
└─ ❌ No tracking of mid-production changes

Plan Versions
└─ ❌ Can't compare current vs original
```

**Target State (COMPLETE):**
```
Plan Snapshots
├─ ✅ Original plan captured at production start
└─ ✅ Snapshots stored in plan_snapshots table

Amendment Tracking
├─ ✅ Drop FG amendments
├─ ✅ Add FG amendments
├─ ✅ Modify batch amendments
└─ ✅ Reason capture

Plan Comparison
└─ ✅ View original vs current plan
```

---

## CRITICAL: Study These Files FIRST

1. **plan_snapshots and plan_amendments models (F068)**
   - Find table structures
   - Understand JSON storage
   - Note relationships

2. **Plan state management (F077)**
   - Understand when snapshots created
   - Note state transition triggers
   - Study validation rules

---

## Requirements Reference

Implements Phase 3 dynamic planning from req_planning.md (v0.4) Section 14.2

---

## Functional Requirements

### FR-1: Capture Plan Snapshot

**What it must do:**
- When production starts (F077), capture complete plan state
- Store as JSON in plan_snapshots
- Include: recipes, FGs, quantities, batch decisions

**Success criteria:**
- [ ] Snapshot triggered on state transition
- [ ] Complete data captured
- [ ] JSON storage works

---

### FR-2: Record Amendments

**What it must do:**
- Support 3 amendment types: DROP_FG, ADD_FG, MODIFY_BATCH
- Store amendment data, reason, timestamp
- Append-only (never delete amendments)

**Amendment types:**
```
DROP_FG: {fg_id, original_quantity, reason}
ADD_FG: {fg_id, new_quantity, reason}
MODIFY_BATCH: {recipe_id, old_batches, new_batches, reason}
```

**Success criteria:**
- [ ] All types supported
- [ ] Data stored correctly
- [ ] Reasons captured

---

### FR-3: Amendment UI

**What it must do:**
- Show amendment history for event
- Provide controls to add amendments
- Require reason entry
- Validate amendments allowed (not batch in-progress)

**Success criteria:**
- [ ] History displays
- [ ] Amendment controls work
- [ ] Reason required
- [ ] Validation works

---

### FR-4: Plan Comparison View

**What it must do:**
- Display original plan (from snapshot)
- Display current plan (with amendments)
- Highlight differences

**Success criteria:**
- [ ] Original plan displays
- [ ] Current plan displays
- [ ] Differences clear

---

## Out of Scope

- ❌ Production-aware calculations (F079)
- ❌ Amendment undo (future)
- ❌ Amendment approval workflow (future)

---

## Success Criteria

### Snapshots
- [ ] Created at production start
- [ ] Complete data captured
- [ ] Retrieval works

### Amendments
- [ ] All types work
- [ ] Reasons required
- [ ] History tracked

### UI
- [ ] Amendment controls work
- [ ] History displays
- [ ] Comparison view clear

### Quality
- [ ] Code follows patterns
- [ ] JSON handling robust
- [ ] Append-only enforced

---

## Constitutional Compliance

✅ **Immutability of Historical Records**
✅ **Audit Trail**
✅ **Data Integrity**

---

## Notes for Implementation

Study JSON storage patterns, implement amendment types with validation.

---

**END OF SPECIFICATION**
