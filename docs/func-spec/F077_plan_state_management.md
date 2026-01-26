# F077: Plan State Management

**Version**: 1.0  
**Priority**: MEDIUM (Phase 3)  
**Type**: Service Layer + UI Enhancement

---

## Executive Summary

Plans need lifecycle state management for production workflow:
- ❌ No state transitions (DRAFT → LOCKED → IN_PRODUCTION → COMPLETED)
- ❌ No plan locking mechanism
- ❌ No prevention of modifications during production

This spec implements plan state machine enabling Phase 3 dynamic planning.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Plan State
└─ ✅ plan_state field exists (F068) but unused

State Transitions
└─ ❌ No enforcement or validation

Plan Locking
└─ ❌ Plans remain mutable always
```

**Target State (COMPLETE):**
```
State Machine
├─ ✅ DRAFT → LOCKED
├─ ✅ LOCKED → IN_PRODUCTION
├─ ✅ IN_PRODUCTION → COMPLETED
└─ ✅ Invalid transitions prevented

Plan Locking
├─ ✅ Lock plan before production
└─ ✅ Prevent most modifications when locked

UI Indicators
└─ ✅ Current state visible and clear
```

---

## CRITICAL: Study These Files FIRST

1. **Event model (F068)**
   - Find plan_state field
   - Understand allowed values
   - Note constraints

2. **State machine patterns**
   - Find existing state management code
   - Study transition validation
   - Note event/callback patterns

---

## Requirements Reference

Implements Phase 3 preparation from req_planning.md (v0.4) Section 3.2

---

## Functional Requirements

### FR-1: State Transition Service Methods

**What it must do:**
- lock_plan(event_id) → DRAFT to LOCKED
- start_production(event_id) → LOCKED to IN_PRODUCTION
- complete_production(event_id) → IN_PRODUCTION to COMPLETED
- Validate transitions, raise errors if invalid

**Success criteria:**
- [ ] Transitions work correctly
- [ ] Invalid transitions prevented
- [ ] State persists

---

### FR-2: Modification Rules by State

**What it must do:**
- DRAFT: All modifications allowed
- LOCKED: Recipe/FG changes prevented, batch decision changes allowed
- IN_PRODUCTION: Most changes prevented (amendments only - F078)
- COMPLETED: Read-only

**Success criteria:**
- [ ] Rules enforced
- [ ] Clear error messages
- [ ] UI respects rules

---

### FR-3: State Display and Controls

**What it must do:**
- Show current state prominently
- Provide state transition buttons (Lock, Start Production, Complete)
- Disable invalid transitions

**Success criteria:**
- [ ] State visible
- [ ] Controls work
- [ ] Invalid actions disabled

---

## Out of Scope

- ❌ Amendments (F078)
- ❌ Snapshots (F078)
- ❌ Production-aware calculations (F079)

---

## Success Criteria

### State Machine
- [ ] All transitions work
- [ ] Invalid transitions blocked
- [ ] State persists correctly

### Modification Rules
- [ ] Rules enforced by state
- [ ] Errors clear
- [ ] UI respects state

### UI Integration
- [ ] State visible
- [ ] Transition controls work
- [ ] Clear feedback

### Quality
- [ ] Code follows patterns
- [ ] Error handling robust
- [ ] State consistency maintained

---

## Constitutional Compliance

✅ **State Management**
✅ **Data Integrity**
✅ **User Control**

---

## Notes for Implementation

Study state machine patterns, implement transitions with validation.

---

**END OF SPECIFICATION**
