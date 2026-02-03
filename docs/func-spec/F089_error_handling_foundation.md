# F089: Error Handling Foundation

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Enhancement

---

## Executive Summary

Current gaps:
- ❌ 88 files catch generic `Exception` - hides error types and makes debugging difficult
- ❌ Mixed exception bases (`ServiceException` vs `ServiceError`) - inconsistent hierarchy
- ❌ No centralized error handling in UI layer - each file handles errors differently
- ❌ Technical error messages shown to users - not user-friendly

This spec establishes a three-tier exception strategy with centralized UI error handling, consolidates the exception hierarchy, and updates all 88 files to catch specific exceptions for better debugging and web migration readiness.

---

## Problem Statement

**Current State (BROKEN):**
```
Exception Handling
├─ ✅ Custom exceptions exist (ServiceError, domain exceptions)
├─ ❌ 88 files catch generic Exception
├─ ❌ Two exception bases (ServiceException vs ServiceError)
├─ ❌ No centralized UI error handler
├─ ❌ Mixed error messages (technical vs user-friendly)
└─ ❌ Won't map to HTTP status codes (blocks web migration)

UI Error Display
├─ ❌ Each UI file handles errors differently
├─ ❌ Technical errors shown directly to users
└─ ❌ Inconsistent error presentation
```

**Target State (COMPLETE):**
```
Exception Handling
├─ ✅ Consolidated exception hierarchy (ServiceError base)
├─ ✅ All files catch specific exceptions
├─ ✅ Centralized UI error handler
├─ ✅ User-friendly error messages
└─ ✅ Maps cleanly to HTTP status codes (web-ready)

UI Error Display
├─ ✅ All UI uses centralized error handler
├─ ✅ User-friendly messages consistently shown
└─ ✅ Technical details logged but not displayed
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Exception Hierarchy**
   - Find `src/services/exceptions.py` - current exception definitions
   - Study domain-specific exceptions (IngredientNotFoundBySlug, InsufficientInventoryError, ValidationError)
   - Note both `ServiceException` and `ServiceError` bases exist

2. **Current Exception Handling Patterns**
   - Find examples of generic `Exception` catches in UI files (src/ui/*)
   - Study how errors are currently displayed to users (messagebox.showerror)
   - Note technical error messages being shown directly

3. **Existing Error Context**
   - Find `src/services/batch_production_service.py` - good examples of domain exceptions with context
   - Study how context is included in exceptions (slugs, quantities, units)
   - Note structured error information

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.A**: Error Handling Standards
  - Exception hierarchy
  - Error propagation strategy
  - Validation strategy

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Consolidate Exception Hierarchy

**What it must do:**
- Consolidate to single base: `ServiceError` (deprecate `ServiceException`)
- All domain exceptions MUST inherit from `ServiceError`
- Maintain all existing domain exceptions (IngredientNotFoundBySlug, ValidationError, etc.)
- Add docstrings documenting when each exception should be raised

**Pattern reference:** Study existing domain exceptions in `src/services/exceptions.py`, ensure all follow same inheritance pattern

**Success criteria:**
- [ ] Single `ServiceError` base class exists
- [ ] All domain exceptions inherit from `ServiceError`
- [ ] Legacy `ServiceException` references updated or removed
- [ ] Each exception documented with usage examples

---

### FR-2: Create Centralized UI Error Handler

**What it must do:**
- Create central function to convert service exceptions to user-friendly messages
- Map each domain exception type to appropriate user message
- Log technical details separately (not shown to user)
- Support correlation IDs for tracing (even if not implemented yet)

**Pattern reference:** Study how UI currently displays errors (messagebox.showerror calls), create single point for all error display

**User-friendly message requirements:**
- IngredientNotFoundBySlug → "Ingredient 'X' not found"
- ValidationError → "Validation failed: [field-level errors]"
- InsufficientInventoryError → "Not enough X in inventory"
- Generic ServiceError → "Operation failed: [safe message]"
- Unexpected Exception → "An unexpected error occurred. Please contact support."

**Success criteria:**
- [ ] Central error handler function exists
- [ ] Handles all domain exception types
- [ ] Returns user-friendly messages (no technical details)
- [ ] Logs technical details for debugging
- [ ] Supports future correlation ID logging

---

### FR-3: Update UI Layer Exception Handling

**What it must do:**
- Update all 88 files catching generic `Exception`
- Use three-tier catch strategy:
  1. Catch specific domain exceptions (ServiceError subclasses)
  2. Use centralized error handler to convert to user message
  3. Catch generic Exception only for logging unexpected errors
- Never show raw exception messages to users

**Pattern reference:** Study current try/except blocks in UI files, establish single consistent pattern to apply across all files

**Success criteria:**
- [ ] All 88 files updated to catch specific exceptions
- [ ] All use centralized error handler
- [ ] No generic Exception catches without logging
- [ ] No raw technical errors shown to users
- [ ] Pattern consistent across all UI files

---

### FR-4: Add Exception Context Requirements

**What it must do:**
- All domain exceptions MUST include operation context
- Required context: entity identifiers (IDs, slugs), attempted operation, current state
- Support future correlation IDs (parameter exists even if not used yet)
- Structured exception data (not just string messages)

**Pattern reference:** Study `src/services/batch_production_service.py` InsufficientInventoryError - includes slug, needed, available, unit

**Exception context requirements:**
- Entity operations: include slug/ID of entity
- Validation errors: include field names and specific issues
- Business rule violations: include relevant quantities/states
- All exceptions: support optional correlation_id parameter

**Success criteria:**
- [ ] All domain exceptions include relevant context
- [ ] Context uses entity identifiers (slugs preferred over IDs)
- [ ] Correlation ID support exists in exception constructors
- [ ] Exception attributes accessible programmatically (not just string)

---

### FR-5: Document Exception Guidelines

**What it must do:**
- Create developer guide documenting when to raise each exception
- Document the three-tier catch pattern for UI layer
- Provide code examples for common scenarios
- Document mapping to future HTTP status codes

**Pattern reference:** Study existing CLAUDE.md pattern documentation style

**Documentation requirements:**
- When to raise which exception type
- How to include proper context
- UI layer exception handling pattern
- Examples of good vs bad exception handling
- HTTP status code mapping (404, 400, 500, etc.)

**Success criteria:**
- [ ] Developer guide exists in docs/
- [ ] All exception types documented with usage
- [ ] Three-tier pattern documented with examples
- [ ] HTTP status code mapping documented
- [ ] Code examples for common scenarios included

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Correlation ID implementation - F106 (just prepare exception constructors)
- ❌ Audit trail integration - F106 (separate observability feature)
- ❌ FastAPI error handlers - separate web migration feature
- ❌ Advanced error recovery/retry logic - not needed for desktop app
- ❌ User-configurable error verbosity - YAGNI for now

---

## Success Criteria

**Complete when:**

### Exception Hierarchy
- [ ] Single `ServiceError` base class (legacy bases removed/deprecated)
- [ ] All domain exceptions inherit from `ServiceError`
- [ ] All exceptions documented with docstrings
- [ ] Exception hierarchy ready for HTTP status code mapping

### Centralized Error Handler
- [ ] Central error handler function created
- [ ] Handles all current domain exception types
- [ ] Returns user-friendly messages consistently
- [ ] Logs technical details separately
- [ ] Supports future correlation ID parameter

### UI Layer Updates
- [ ] All 88 files updated to catch specific exceptions
- [ ] Three-tier catch pattern applied consistently
- [ ] No generic Exception catches without logging
- [ ] No raw technical errors displayed to users
- [ ] Centralized error handler used in all UI files

### Documentation
- [ ] Developer guide created documenting patterns
- [ ] All exception types documented
- [ ] Code examples provided for common scenarios
- [ ] HTTP status code mapping documented

### Quality
- [ ] Exception handling follows Code Quality Principle VI.A
- [ ] Pattern consistency verified across all UI files
- [ ] No reduction in error information (context preserved)
- [ ] Debugging improved (specific exceptions, better logging)

---

## Architecture Principles

### Three-Tier Exception Strategy

**Service Layer:**
- Raises domain exceptions with technical details
- Includes full operation context
- No user-facing message concerns

**UI Layer:**
- Catches specific exception types
- Uses centralized handler for user messages
- Logs technical details for debugging

**Unexpected Errors:**
- Generic Exception catch as last resort
- Always logs full stack trace
- Shows generic "contact support" message

### Exception Hierarchy Design

**Single Base:**
- All domain exceptions inherit from `ServiceError`
- Enables catching all service errors with single except clause
- Maps cleanly to HTTP 4xx/5xx status codes

**Domain-Specific:**
- Exceptions named for business domain (IngredientNotFoundBySlug)
- Not generic technical names (NotFoundException)
- Context included in exception attributes

### Pattern Matching

**All UI exception handling must match three-tier pattern:**
- Specific domain exception catches first
- ServiceError catch with centralized handler
- Generic Exception catch with logging last

---

## Constitutional Compliance

✅ **Principle VI.A: Error Handling Standards**
- Implements exception hierarchy requirement
- Implements error propagation strategy
- Implements validation strategy with consistent error patterns

✅ **Principle V: Layered Architecture Discipline**
- Service layer raises domain exceptions (business logic)
- UI layer presents user-friendly errors (presentation)
- Clear separation between technical and user concerns

✅ **Principle I.B: Data Integrity**
- Better error handling improves data integrity
- Clear validation errors prevent bad data entry
- Exception context aids debugging data issues

---

## Risk Considerations

**Risk: Breaking existing exception handling**
- 88 files being modified simultaneously
- Mitigation: Update files in batches, test after each batch
- Mitigation: Maintain backward compatibility during transition

**Risk: Loss of error information**
- Converting technical errors to user messages might hide details
- Mitigation: Always log technical details before converting
- Mitigation: Include correlation IDs for tracing (future)

**Risk: Inconsistent exception handling patterns**
- Multiple developers/AI agents might apply pattern differently
- Mitigation: Create clear code examples in documentation
- Mitigation: Code review phase verifies pattern consistency

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `src/services/exceptions.py` → understand current hierarchy
- Study UI files with exception handling → identify common patterns
- Study `batch_production_service.py` → learn context-rich exceptions

**Key Patterns to Copy:**
- InsufficientInventoryError structure → apply to all domain exceptions
- Current messagebox.showerror() calls → identify locations for centralized handler
- Existing domain exception types → preserve and consolidate

**Focus Areas:**
- Exception hierarchy consolidation is foundational
- Centralized error handler simplifies all future error handling
- Three-tier pattern must be applied consistently (not partially)
- Documentation critical for maintaining pattern long-term

**Implementation Note:**
This feature is the foundation for web migration error handling. The exception hierarchy and patterns established here will be used when implementing FastAPI error handlers that map exceptions to HTTP status codes.

---

**END OF SPECIFICATION**
