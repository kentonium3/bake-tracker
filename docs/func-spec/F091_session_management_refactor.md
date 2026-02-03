# F091: Session Management Refactor

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Enhancement

---

## Executive Summary

Current gaps:
- ❌ Session management desktop-focused (single `session_scope()` pattern)
- ❌ No request-scoped session support (needed for web concurrency)
- ❌ No session factory pattern (tight coupling to context manager)
- ❌ Global session state won't work for concurrent web requests

This spec implements a session factory pattern with context variable support for request-scoped sessions, enabling web migration while maintaining backward compatibility with desktop usage.

---

## Problem Statement

**Current State (DESKTOP-ONLY):**
```
Session Management
├─ ✅ session_scope() context manager works for desktop
├─ ✅ Session parameter pattern documented (CLAUDE.md)
├─ ❌ Desktop-focused (assumes single-threaded)
├─ ❌ No request-scoped session support
├─ ❌ No session factory abstraction
└─ ❌ Won't work for concurrent web requests

Web Migration Readiness
└─ ❌ BLOCKED: Cannot handle concurrent requests safely
```

**Target State (WEB-READY):**
```
Session Management
├─ ✅ SessionFactory class for session creation
├─ ✅ Context variable for request-scoped sessions
├─ ✅ Backward-compatible session_scope() for desktop
├─ ✅ Request-scoped session support for web
└─ ✅ Thread-safe session management

Web Migration Readiness
└─ ✅ READY: Can handle concurrent requests safely
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Current Session Management**
   - Find `src/services/database.py` - session_scope() implementation
   - Study context manager pattern
   - Note session lifecycle (create, commit, rollback, close)

2. **Session Parameter Pattern**
   - Find CLAUDE.md - documented session parameter pattern
   - Study `session: Optional[Session] = None` pattern
   - Note transactional composition pattern

3. **Service Functions Using Sessions**
   - Find examples in service files using session parameter
   - Study how sessions are passed between functions
   - Note transactional boundaries

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.C**: Dependency & State Management
  - Dependency injection
  - Transaction boundaries
- **Code Quality Principle VI.F**: Migration & Evolution Readiness
  - Database abstraction
  - Session factory pattern

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Implement SessionFactory Class

**What it must do:**
- Create SessionFactory class that manages session creation
- Accept engine as constructor parameter
- Provide `create_session()` method for creating new sessions
- Support both desktop and web usage patterns

**Pattern reference:** Study factory pattern in Python, apply to SQLAlchemy session creation

**Success criteria:**
- [ ] SessionFactory class exists in database.py
- [ ] Accepts engine in constructor
- [ ] create_session() method creates new Session
- [ ] Factory initialized at database init time
- [ ] Global factory accessor function exists

---

### FR-2: Add Context Variable for Request-Scoped Sessions

**What it must do:**
- Use Python contextvars for thread-safe request-scoped sessions
- Add methods to get/set current session in context
- Support web middleware pattern (future)
- Maintain None as default (desktop usage)

**Pattern reference:** Study Python contextvars module, apply to session management

**Context variable requirements:**
- Thread-safe storage of current session
- None default (no session by default)
- get_current_session() method
- set_current_session(session) method

**Success criteria:**
- [ ] Context variable defined for current session
- [ ] get_current_session() returns current session or None
- [ ] set_current_session() stores session in context
- [ ] Thread-safe (contextvars inherently thread-safe)
- [ ] No impact on desktop usage (None by default)

---

### FR-3: Maintain Backward-Compatible session_scope()

**What it must do:**
- Keep existing session_scope() context manager for desktop
- Use SessionFactory internally
- Maintain identical behavior (create, commit/rollback, close)
- No changes required to existing service code

**Pattern reference:** Study existing session_scope() implementation, refactor to use factory

**Success criteria:**
- [ ] session_scope() still works as context manager
- [ ] Uses SessionFactory.create_session() internally
- [ ] Identical behavior to current implementation
- [ ] Existing service code works without changes
- [ ] All tests pass without modification

---

### FR-4: Add Database Initialization Function

**What it must do:**
- Create `init_database(config)` function
- Initialize engine with Config settings
- Create and return SessionFactory instance
- Store global factory reference

**Pattern reference:** Study application initialization patterns, apply to database setup

**Initialization requirements:**
- Accept Config object as parameter
- Create engine with Config.database_url, Config.db_connect_args, etc.
- Initialize SessionFactory with engine
- Store factory in module-level variable
- Return factory for testing

**Success criteria:**
- [ ] init_database(config) function exists
- [ ] Creates engine with Config properties (from F090)
- [ ] Initializes global SessionFactory
- [ ] Returns factory instance
- [ ] Called during application startup

---

### FR-5: Add Web Middleware Pattern Support

**What it must do:**
- Document pattern for web middleware usage
- Show how to use context variables for request-scoped sessions
- Provide example of FastAPI middleware pattern
- Enable future web migration without code changes

**Pattern reference:** Study FastAPI middleware patterns, document for future use

**Documentation requirements:**
- Middleware pattern example (FastAPI)
- How to set/get request-scoped session
- Session lifecycle in web context
- Backward compatibility with desktop

**Success criteria:**
- [ ] Middleware pattern documented in code comments
- [ ] FastAPI example provided in docstrings
- [ ] Web usage pattern clear
- [ ] Desktop usage unchanged

---

### FR-6: Update Documentation

**What it must do:**
- Update CLAUDE.md with new session factory pattern
- Document context variable usage
- Provide examples for both desktop and web
- Document migration path from current to new pattern

**Pattern reference:** Study existing CLAUDE.md documentation style

**Documentation updates:**
- SessionFactory usage
- Context variable pattern
- Desktop vs web usage
- Migration examples

**Success criteria:**
- [ ] CLAUDE.md updated with new patterns
- [ ] Context variable usage documented
- [ ] Desktop/web usage examples provided
- [ ] Migration path documented

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ FastAPI implementation - separate web migration feature
- ❌ Actual web middleware - just prepare infrastructure
- ❌ Database connection pooling changes - F090 handles config
- ❌ Session lifecycle changes - maintain current behavior
- ❌ Service function refactoring - maintain session parameter pattern

---

## Success Criteria

**Complete when:**

### Session Factory
- [ ] SessionFactory class implemented
- [ ] Factory creates sessions correctly
- [ ] Global factory initialized at startup
- [ ] Factory accessible throughout application

### Context Variables
- [ ] Context variable for current session defined
- [ ] get_current_session() works correctly
- [ ] set_current_session() works correctly
- [ ] Thread-safe operation verified

### Backward Compatibility
- [ ] session_scope() works identically to before
- [ ] Existing service code unchanged
- [ ] All existing tests pass
- [ ] No breaking changes to desktop app

### Documentation
- [ ] CLAUDE.md updated with new patterns
- [ ] Web middleware pattern documented
- [ ] Context variable usage documented
- [ ] Migration examples provided

### Quality
- [ ] Follows Code Quality Principle VI.C (Dependency & State Management)
- [ ] Follows Code Quality Principle VI.F (Migration Readiness)
- [ ] Thread-safe session management
- [ ] Web-ready architecture

---

## Architecture Principles

### Factory Pattern

**SessionFactory centralizes session creation:**
- Encapsulates engine and session configuration
- Single point for session instantiation
- Testable (can inject mock factory)

### Context Variable Pattern

**Request-scoped sessions via contextvars:**
- Thread-safe storage (each thread/request has own context)
- No global state (context isolated per request)
- Backward compatible (None default for desktop)

### Backward Compatibility

**Maintain existing patterns:**
- session_scope() unchanged externally
- Session parameter pattern unchanged
- Service functions work identically

---

## Constitutional Compliance

✅ **Principle VI.C: Dependency & State Management**
- Implements dependency injection via factory
- Explicit session lifecycle
- Transaction boundaries maintained

✅ **Principle VI.F: Migration & Evolution Readiness**
- Session factory supports both SQLite and PostgreSQL
- Request-scoped sessions enable web concurrency
- Pattern prepared for web middleware

✅ **Principle V: Layered Architecture Discipline**
- Session management centralized in database layer
- Services use clean session interface
- Web concerns separated from business logic

---

## Risk Considerations

**Risk: Breaking existing session management**
- Refactoring core database infrastructure
- Mitigation: Maintain identical external behavior
- Mitigation: Comprehensive testing before merge

**Risk: Context variable complexity**
- New concept for team
- Mitigation: Clear documentation with examples
- Mitigation: Desktop usage unchanged (no learning curve)

**Risk: Performance impact**
- Factory adds indirection
- Mitigation: Minimal overhead (one additional function call)
- Mitigation: Measure performance before/after

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `src/services/database.py` → understand session_scope()
- Study Python contextvars documentation → learn context variable pattern
- Study FastAPI middleware examples → understand web pattern

**Key Patterns to Copy:**
- Existing session_scope() → maintain identical behavior
- Config property pattern (F090) → use for database settings
- Factory pattern → apply to session creation

**Focus Areas:**
- Backward compatibility is critical (desktop app must work identically)
- Context variables enable web without breaking desktop
- SessionFactory abstracts session creation for future flexibility
- Documentation critical for web migration team

**Implementation Note:**
This feature enables web migration without breaking desktop. The session factory and context variables are infrastructure that web middleware will use, but desktop continues using session_scope() unchanged.

---

**END OF SPECIFICATION**
