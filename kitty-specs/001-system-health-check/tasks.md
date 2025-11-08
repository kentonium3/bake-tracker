# Tasks: System Health Check

**Feature**: 001-system-health-check
**Branch**: `001-system-health-check`
**Created**: 2025-11-08
**Status**: Ready for implementation

## Overview

Implement a background health monitoring service that periodically writes system status to `data/health.json`. This provides monitoring tools with visibility into application health, database connectivity, and version information without requiring HTTP endpoints.

**Total Work Packages**: 9 (3 core, 2 integration, 3 testing, 1 documentation)
**Estimated Effort**: 6-8 hours
**Dependencies**: Sequential implementation recommended (core → integration → testing → docs)

## Work Package Summary

| ID | Title | Priority | Est. Time | Dependencies |
|----|-------|----------|-----------|--------------|
| WP01 | Create health service module structure | P1 | 45min | None |
| WP02 | Implement database connectivity testing | P1 | 1h | WP01 |
| WP03 | Implement atomic file writing | P1 | 1h | WP01 |
| WP04 | Integrate with main application | P1 | 45min | WP01-03 |
| WP05 | Add version reading from pyproject.toml | P2 | 30min | WP01 |
| WP06 | Unit tests for health check logic | P1 | 1h | WP01-03 |
| WP07 | Unit tests for file I/O operations | P1 | 45min | WP03 |
| WP08 | Integration test for full cycle | P1 | 1h | WP01-05 |
| WP09 | Documentation and docstrings | P2 | 30min | WP01-05 |

---

## Setup & Foundation

### WP01: Create Health Service Module Structure

**Priority**: P1 (Critical path)
**Prompt File**: [`tasks/planned/WP01-create-health-service-module.md`](tasks/planned/WP01-create-health-service-module.md)
**Estimated Time**: 45 minutes
**Dependencies**: None
**Parallelizable**: No (foundation for all other work)

**Objective**: Create the basic `HealthCheckService` class structure with threading infrastructure, initialization, and cleanup methods.

**Included Subtasks**:
- [ ] T001: Create `src/services/health_service.py` file
- [ ] T002: Implement `HealthCheckService` class skeleton
- [ ] T003: Add `__init__()` method with instance variables
- [ ] T004: Add `start()` method to launch background thread
- [ ] T005: Add `stop()` method with graceful shutdown
- [ ] T006: Add `_health_check_loop()` thread main loop with 30-second interval
- [ ] T007: Add threading.Event for shutdown signaling

**Implementation Sketch**:
1. Create file with module docstring and imports
2. Define class with type hints
3. Implement initialization (create data dir, set up threading)
4. Implement start/stop methods with daemon thread
5. Implement loop method with event.wait(timeout=30) pattern
6. Add error handling for thread safety

**Success Criteria**:
- File exists at `src/services/health_service.py`
- Class can be instantiated
- start() launches thread without blocking
- stop() terminates thread within 1 second
- Thread loops every 30 seconds
- No exceptions on startup or shutdown

**Risks**:
- Thread cleanup issues (mitigated by daemon thread + Event)
- Race conditions (mitigated by proper event signaling)

---

### WP02: Implement Database Connectivity Testing

**Priority**: P1 (Critical path)
**Prompt File**: [`tasks/planned/WP02-implement-database-testing.md`](tasks/planned/WP02-implement-database-testing.md)
**Estimated Time**: 1 hour
**Dependencies**: WP01 (requires HealthCheckService class)
**Parallelizable**: No (core health check logic)

**Objective**: Add database connection testing using existing `session_scope()` context manager with timeout handling.

**Included Subtasks**:
- [ ] T008: Import `session_scope` from `src.services.database`
- [ ] T009: Add `_check_database()` method
- [ ] T010: Implement connection test with `SELECT 1` query
- [ ] T011: Add 3-second timeout handling
- [ ] T012: Return status: "connected", "disconnected", or "timeout"
- [ ] T013: Handle SQLAlchemyError exceptions
- [ ] T014: Log connection failures (non-blocking)

**Implementation Sketch**:
1. Import database service dependencies
2. Create private method `_check_database() -> str`
3. Wrap `SELECT 1` in try/except with timeout
4. Use existing session_scope context manager
5. Map exceptions to status strings
6. Add logging for troubleshooting
7. Call from `_health_check_loop()`

**Success Criteria**:
- Returns "connected" when database is available
- Returns "disconnected" on connection failure
- Returns "timeout" after 3 seconds
- Catches and logs SQLAlchemyError
- Does not crash on database errors
- Completes in <3.5 seconds worst case

**Risks**:
- Timeout not properly enforced (mitigation: test with killed database)
- Session leaks (mitigation: use session_scope context manager)

---

### WP03: Implement Atomic File Writing

**Priority**: P1 (Critical path)
**Prompt File**: [`tasks/planned/WP03-implement-atomic-file-writing.md`](tasks/planned/WP03-implement-atomic-file-writing.md)
**Estimated Time**: 1 hour
**Dependencies**: WP01 (requires HealthCheckService class)
**Parallelizable**: Can work in parallel with WP02

**Objective**: Add atomic file writing using write-to-temp-and-rename pattern to prevent partial reads by monitoring tools.

**Included Subtasks**:
- [ ] T015: Add `_write_health_status(status_dict)` method
- [ ] T016: Implement JSON serialization with proper formatting
- [ ] T017: Write to temporary file `data/health.json.tmp`
- [ ] T018: Use `pathlib.Path.rename()` for atomic move
- [ ] T019: Add error handling for file write failures
- [ ] T020: Ensure `data/` directory exists (create if missing)
- [ ] T021: Log write errors without crashing application
- [ ] T022: Add ISO 8601 timestamp generation

**Implementation Sketch**:
1. Create private method `_write_health_status(data: dict) -> bool`
2. Ensure `data/` directory exists
3. Serialize dict to JSON with indent=2
4. Write to `data/health.json.tmp`
5. Rename to `data/health.json` (atomic operation)
6. Handle IOError, OSError gracefully
7. Return success/failure boolean
8. Log all errors

**Success Criteria**:
- Writes valid JSON to `data/health.json`
- Uses atomic write-and-rename pattern
- Creates `data/` directory if missing
- Handles write failures gracefully
- Logs errors appropriately
- Does not crash application on file errors
- JSON is properly formatted (indented)

**Risks**:
- File permissions issues (mitigation: catch and log OSError)
- Partial writes (mitigation: write-and-rename pattern)
- Disk full (mitigation: catch IOError, log, continue)

---

## Integration

### WP04: Integrate Health Service with Main Application

**Priority**: P1 (Critical path)
**Prompt File**: [`tasks/planned/WP04-integrate-with-main.md`](tasks/planned/WP04-integrate-with-main.md)
**Estimated Time**: 45 minutes
**Dependencies**: WP01-03 (requires complete health service)
**Parallelizable**: No (integration work)

**Objective**: Initialize and start health service in `src/main.py` with proper lifecycle management.

**Included Subtasks**:
- [ ] T023: Import `HealthCheckService` in `src/main.py`
- [ ] T024: Instantiate service in `initialize_application()`
- [ ] T025: Call `service.start()` after database initialization
- [ ] T026: Add cleanup: call `service.stop()` on application exit
- [ ] T027: Handle service initialization errors gracefully
- [ ] T028: Add logging for service lifecycle events

**Implementation Sketch**:
1. Import HealthCheckService at top of main.py
2. Create global or module-level service instance
3. In initialize_application(), create service after DB init
4. Call start() before returning from initialization
5. In main(), add try/finally to call stop() on exit
6. Add error handling for service startup failures
7. Log "Health service started" message

**Success Criteria**:
- Service starts automatically with application
- Service stops cleanly on application exit
- Startup failures don't crash application
- `data/health.json` exists after application starts
- File updates every ~30 seconds
- No resource leaks on application restart

**Risks**:
- Service not stopped on crash (mitigation: daemon thread auto-terminates)
- Initialization order issues (mitigation: start after DB ready)

---

### WP05: Add Version Reading from pyproject.toml

**Priority**: P2 (Enhancement)
**Prompt File**: [`tasks/planned/WP05-add-version-reading.md`](tasks/planned/WP05-add-version-reading.md)
**Estimated Time**: 30 minutes
**Dependencies**: WP01 (requires HealthCheckService class)
**Parallelizable**: Can work in parallel with WP02-04

**Objective**: Read application version from `pyproject.toml` and cache it for health status reporting.

**Included Subtasks**:
- [ ] T029: Import `tomllib` (Python 3.11+) or `toml` package
- [ ] T030: Add `_get_app_version()` method
- [ ] T031: Read `pyproject.toml` from project root
- [ ] T032: Extract `project.version` from TOML
- [ ] T033: Cache version in instance variable
- [ ] T034: Implement fallback to "unknown" on read failure
- [ ] T035: Call once during `__init__()`

**Implementation Sketch**:
1. Try importing tomllib, fall back to toml package
2. Create method to read pyproject.toml
3. Parse TOML and extract ['project']['version']
4. Cache in self._app_version
5. Handle FileNotFoundError, KeyError gracefully
6. Return cached value in health status
7. Add static `api_version = "v1"`

**Success Criteria**:
- Reads version "0.1.0" from pyproject.toml
- Caches version (doesn't re-read every health check)
- Falls back to "unknown" if file missing
- Falls back to "unknown" if version key missing
- Works with both tomllib and toml packages
- Health status includes both app_version and api_version

**Risks**:
- pyproject.toml location varies (mitigation: use pathlib from __file__)
- toml package not installed (mitigation: graceful fallback)

---

## Testing

### WP06: Unit Tests for Health Check Logic

**Priority**: P1 (Quality gate)
**Prompt File**: [`tasks/planned/WP06-unit-tests-health-logic.md`](tasks/planned/WP06-unit-tests-health-logic.md)
**Estimated Time**: 1 hour
**Dependencies**: WP01-03 (requires implementation)
**Parallelizable**: Can start after WP01-03 complete

**Objective**: Test health service initialization, threading, database checking, and error handling with mocked dependencies.

**Included Subtasks**:
- [ ] T036: Create `src/tests/services/test_health_service.py`
- [ ] T037: Test service initialization
- [ ] T038: Test start() launches thread
- [ ] T039: Test stop() terminates thread
- [ ] T040: Test database check returns "connected"
- [ ] T041: Test database check returns "disconnected" on error
- [ ] T042: Test database check returns "timeout" after 3 seconds
- [ ] T043: Test version reading success and fallback
- [ ] T044: Mock session_scope and file I/O

**Implementation Sketch**:
1. Create test file with fixtures
2. Mock database session_scope
3. Mock file I/O operations
4. Test initialization sets up instance variables
5. Test threading lifecycle (start/stop)
6. Test database connectivity states
7. Test version reading with various scenarios
8. Aim for 90%+ coverage

**Success Criteria**:
- All tests pass
- Coverage >90% for health_service.py
- Tests run in <5 seconds
- No actual database or file operations
- Thread cleanup verified in tests
- Mocks properly configured

**Risks**:
- Threading tests can be flaky (mitigation: use proper wait/join)
- Mock complexity (mitigation: use pytest fixtures)

---

### WP07: Unit Tests for File I/O Operations

**Priority**: P1 (Quality gate)
**Prompt File**: [`tasks/planned/WP07-unit-tests-file-io.md`](tasks/planned/WP07-unit-tests-file-io.md)
**Estimated Time**: 45 minutes
**Dependencies**: WP03 (requires file writing implementation)
**Parallelizable**: Can work in parallel with WP06

**Objective**: Test atomic file writing, JSON serialization, directory creation, and error handling.

**Included Subtasks**:
- [ ] T045: Test successful file write creates `data/health.json`
- [ ] T046: Test write-and-rename atomicity
- [ ] T047: Test directory creation when `data/` missing
- [ ] T048: Test JSON format and structure
- [ ] T049: Test file write error handling (permissions)
- [ ] T050: Test disk full scenario
- [ ] T051: Use tmpdir fixture for isolation

**Implementation Sketch**:
1. Use pytest tmpdir fixture
2. Test normal write operation
3. Verify .tmp file → .json rename
4. Test directory auto-creation
5. Validate JSON structure matches spec
6. Simulate permission errors with mocks
7. Verify error logging without crashes

**Success Criteria**:
- All file I/O paths tested
- Atomic write pattern verified
- Error cases handled gracefully
- No actual writes to project data/
- Tests use isolated temp directories
- JSON validation passes

**Risks**:
- Filesystem test flakiness (mitigation: use tmpdir)
- Permission simulation complexity (mitigation: mock pathlib)

---

### WP08: Integration Test for Full Health Check Cycle

**Priority**: P1 (Quality gate)
**Prompt File**: [`tasks/planned/WP08-integration-test-full-cycle.md`](tasks/planned/WP08-integration-test-full-cycle.md)
**Estimated Time**: 1 hour
**Dependencies**: WP01-05 (requires complete implementation)
**Parallelizable**: No (integration test)

**Objective**: Test complete end-to-end health check cycle with real database and file system.

**Included Subtasks**:
- [ ] T052: Create integration test with real database connection
- [ ] T053: Test service starts and writes initial health file
- [ ] T054: Test periodic updates (wait for second cycle)
- [ ] T055: Test database status changes (disconnect DB, verify status)
- [ ] T056: Test health file structure and content
- [ ] T057: Test service cleanup on stop
- [ ] T058: Verify no resource leaks

**Implementation Sketch**:
1. Create integration test file
2. Use real database (test DB or temp SQLite)
3. Start service and wait for first write
4. Verify file contents match spec
5. Disconnect database, verify degraded status
6. Reconnect, verify online status
7. Stop service, verify cleanup
8. Check for thread leaks

**Success Criteria**:
- Full health check cycle completes
- File written with correct structure
- Database status accurately reflects connectivity
- Version information correct
- Timestamps in ISO 8601 format
- Service stops cleanly
- No resource leaks detected

**Risks**:
- Timing-dependent tests (mitigation: use reasonable wait times)
- Database setup complexity (mitigation: use SQLite in-memory)

---

## Documentation & Polish

### WP09: Add Module Docstrings and Inline Comments

**Priority**: P2 (Quality enhancement)
**Prompt File**: [`tasks/planned/WP09-add-documentation.md`](tasks/planned/WP09-add-documentation.md)
**Estimated Time**: 30 minutes
**Dependencies**: WP01-05 (requires implementation complete)
**Parallelizable**: Can work in parallel with testing

**Objective**: Add comprehensive docstrings and inline comments following Google-style documentation.

**Included Subtasks**:
- [ ] T059: Add module-level docstring to health_service.py
- [ ] T060: Add class docstring with usage example
- [ ] T061: Add docstrings to all public methods
- [ ] T062: Add docstrings to private methods
- [ ] T063: Add inline comments for complex threading logic
- [ ] T064: Document error handling strategy
- [ ] T065: Add type hints to all methods

**Implementation Sketch**:
1. Write module docstring explaining purpose
2. Document class with overview and example
3. Document each method with Args/Returns/Raises
4. Add inline comments for non-obvious code
5. Ensure type hints on all signatures
6. Run mypy to verify type correctness
7. Review against constitution docstring standards

**Success Criteria**:
- All public APIs documented
- Private methods have brief docstrings
- Complex logic has inline comments
- Type hints complete and correct
- Passes mypy type checking
- Follows Google docstring style
- Examples in docstrings are accurate

**Risks**:
- None (documentation only)

---

## Implementation Order

**Recommended sequence**:

**Phase 1: Foundation** (2-2.5 hours)
1. WP01: Module structure (45min)
2. WP02: Database testing (1h)
3. WP03: File writing (1h)

**Phase 2: Integration** (1.25 hours)
4. WP04: Main.py integration (45min)
5. WP05: Version reading (30min)

**Phase 3: Testing** (2.75 hours)
6. WP06: Unit tests - health logic (1h)
7. WP07: Unit tests - file I/O (45min)
8. WP08: Integration test (1h)

**Phase 4: Polish** (30 minutes)
9. WP09: Documentation (30min)

**Total**: ~6.5 hours

---

## Notes

- All work packages follow constitutional requirements
- Test coverage target: 90%+ (exceeds 80% requirement)
- Type hints required throughout (constitution compliance)
- Black formatting will be applied (100 char line length)
- No implementation details in this file (referenced in prompts)

**Next Step**: Run `/spec-kitty.implement` to begin execution from `tasks/planned/`
