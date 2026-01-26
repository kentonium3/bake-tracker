# F079: Production-Aware Calculations

**Version**: 1.0  
**Priority**: MEDIUM (Phase 3)  
**Type**: Service Integration (Production Service)

---

## Executive Summary

Planning calculations don't consider actual production progress:
- ❌ No production status integration
- ❌ No remaining needs calculation
- ❌ No real-time assembly feasibility

This spec completes Phase 3 by making planning production-aware.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Planning Calculations
└─ ✅ Based on batch decisions (Phase 2)

Production Integration
└─ ❌ Doesn't account for what's actually produced

Real-Time Feasibility
└─ ❌ Shows planned, not actual production state
```

**Target State (COMPLETE):**
```
Production Service Integration
├─ ✅ Query batch completion status
└─ ✅ Query finished goods produced

Production-Aware Calculations
├─ ✅ Remaining needs (not total needs)
├─ ✅ Real-time assembly feasibility
└─ ✅ Ingredient gaps for remaining work

UI Display
└─ ✅ Show actual vs planned production
```

---

## CRITICAL: Study These Files FIRST

1. **ProductionService**
   - Find production status queries
   - Understand batch tracking
   - Note FG production tracking

2. **Planning calculations (F072-F076)**
   - Find existing calculation methods
   - Understand how to modify for production
   - Note data structures

---

## Requirements Reference

Implements Phase 3 production-aware planning from req_planning.md (v0.4) Sections 3.2 and 14.2

---

## Functional Requirements

### FR-1: Query Production Status

**What it must do:**
- Query ProductionService for batch completion
- Get batches completed, in-progress, pending per recipe
- Get FG units produced

**Success criteria:**
- [ ] Queries work
- [ ] Status accurate
- [ ] Performance acceptable

---

### FR-2: Calculate Remaining Needs

**What it must do:**
- Original batch decisions - completed batches = remaining
- Ingredient needs for remaining work only
- Assembly feasibility based on: produced + remaining production

**Success criteria:**
- [ ] Remaining calculation correct
- [ ] Ingredient gaps adjusted
- [ ] Assembly uses actual + planned

---

### FR-3: Validate Amendments Against Production

**What it must do:**
- Check if batch in-progress before allowing amendment
- Prevent changes to active batches
- Allow changes to pending batches

**Success criteria:**
- [ ] In-progress batches protected
- [ ] Pending batches modifiable
- [ ] Validation clear

---

### FR-4: Display Production Progress

**What it must do:**
- Show completed vs planned per recipe
- Show FG produced vs needed
- Update assembly feasibility in real-time

**Success criteria:**
- [ ] Progress displays
- [ ] Numbers accurate
- [ ] Updates work

---

## Out of Scope

- ❌ Production scheduling (separate system)
- ❌ Production cost tracking (separate system)
- ❌ Production quality tracking (future)

---

## Success Criteria

### Production Integration
- [ ] Queries work
- [ ] Status accurate
- [ ] Integration stable

### Calculations
- [ ] Remaining needs correct
- [ ] Assembly feasibility accurate
- [ ] Ingredient gaps adjusted

### Validation
- [ ] In-progress protection works
- [ ] Amendment validation correct
- [ ] Error messages clear

### UI
- [ ] Progress displays
- [ ] Real-time updates work
- [ ] User understands state

### Quality
- [ ] Integration reliable
- [ ] Performance acceptable
- [ ] Error handling robust

---

## Constitutional Compliance

✅ **Service Integration**
✅ **Real-Time Accuracy**
✅ **Production Coordination**

---

## Notes for Implementation

Study ProductionService interface, integrate with planning calculations (F072-F076).

**Most Complex Phase 3 Feature:**
Integrates external dependency, modifies multiple calculation paths, requires careful testing.

---

**END OF SPECIFICATION**
