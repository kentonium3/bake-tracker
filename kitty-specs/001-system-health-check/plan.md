# Implementation Plan: System Health Check

**Branch**: `001-system-health-check` | **Date**: 2025-11-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/001-system-health-check/spec.md`

## Summary

Implement a background health monitoring service that periodically writes system status to `data/health.json`. The health check includes application operational status, database connectivity, current timestamp, application version from `pyproject.toml`, and static API version. This enables external monitoring tools to track application health without requiring HTTP endpoints or direct application interaction.

**Technical Approach**: Create a health service module in `src/services/health_service.py` that runs a background thread, performs periodic health checks (every 30 seconds), and writes JSON status to `data/health.json`. Uses existing database session management for connectivity testing and Python standard library for threading and file I/O.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- SQLAlchemy (existing - for database connection testing)
- CustomTkinter (existing - desktop UI framework)
- Python standard library: json, pathlib, threading, datetime, tomllib (or toml for Python <3.11)

**Storage**:
- SQLite database (existing - for data persistence)
- File system (new - for health status file at `data/health.json`)

**Testing**: pytest (existing test framework)
**Target Platform**: Windows/Linux/Mac desktop (Python desktop application)
**Project Type**: Single project (desktop application)
**Performance Goals**:
- Health check completes in <500ms (non-blocking)
- File write operations <100ms
- No UI thread blocking

**Constraints**:
- Must not block main UI thread
- Must handle database connection failures gracefully
- File write failures must not crash application
- Must work with existing service layer architecture

**Scale/Scope**: Single-user desktop application, minimal performance impact on UI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Standards ✅
- **Type safety**: Will use Python type hints throughout health service
- **Linting**: Will follow existing black formatting (100 char line length)
- **Code review**: Required before merge (constitution requirement)
- **Docstrings**: Will document public health service API with Google-style docstrings
- **Complexity**: Health check logic is simple (cyclomatic complexity <10)

**Status**: PASS - No conflicts

### Testing Standards ✅
- **80% coverage**: Will exceed (targeting 90%+ for health service module)
- **Unit tests**: Required for health check logic, file I/O, version reading
- **Integration tests**: Required for database connectivity testing
- **Test isolation**: Will use fixtures for file system and database mocking

**Status**: PASS - All requirements met

### Performance Requirements ✅
- **Database queries**: Single connection test query, no N+1 issues
- **Service operations**: Health check completes in <500ms (meets <200ms critical path requirement)
- **UI responsiveness**: Background thread ensures zero UI blocking
- **Progress indicators**: Not applicable (background operation)

**Status**: PASS - Meets all performance targets

### Security Principles ✅
- **Input validation**: No user input (reads config files only)
- **SQL injection**: Uses existing session_scope context manager (safe)
- **File paths**: Uses pathlib with fixed path (no user-provided paths)
- **Error messages**: Logs errors internally, no sensitive data exposure

**Status**: PASS - No security concerns

### User Experience Standards ⚠️
- **Accessibility**: Not applicable (no UI components)
- **Error handling**: File write failures logged, app continues (non-blocking)
- **User feedback**: No user-facing feedback (background operation)

**Status**: PASS - UX standards not applicable to background service

### Development Workflow ✅
- **Spec-Kitty worktree**: Using worktree `001-system-health-check`
- **Specification**: Complete and validated
- **Implementation matches plan**: Required
- **Conventional commits**: Will use `feat:` prefix

**Status**: PASS - Following workflow

**Overall Constitution Compliance**: ✅ PASS

## Project Structure

### Documentation (this feature)

```
kitty-specs/001-system-health-check/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (in progress)
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── [Phase outputs to be added]
    ├── research.md      # Phase 0 output
    ├── data-model.md    # Phase 1 output
    ├── quickstart.md    # Phase 1 output
    └── contracts/       # Phase 1 output (API contracts if needed)
```

### Source Code (repository root)

```
src/
├── models/              # Existing - no changes needed
├── services/
│   ├── database.py      # Existing - will use for connection testing
│   ├── health_service.py # NEW - health check service
│   └── ...
├── utils/
│   ├── config.py        # Existing - will read app version
│   └── ...
└── main.py              # Existing - will initialize health service

tests/
└── unit/
    └── services/
        └── test_health_service.py  # NEW - health service tests

data/
└── health.json          # NEW - generated at runtime (gitignored)
```

## Phase 0: Outline & Research

### Research Topics

1. **Threading Patterns in Python Desktop Apps**
   - Daemon threads vs. regular threads
   - Thread cleanup on application shutdown
   - Thread-safe file writing

2. **File I/O Safety**
   - Atomic file writes (write to temp, then rename)
   - Handling concurrent read/write access
   - File system error handling

3. **Database Connection Testing**
   - Using existing `session_scope()` context manager
   - Quick connection validation queries
   - Timeout handling for connection tests

4. **Version Reading from pyproject.toml**
   - Using `tomllib` (Python 3.11+) or `toml` package
   - Fallback handling if file not found
   - Caching version information

### Research Findings

**Threading Pattern Decision**: Use daemon thread with proper cleanup
- Daemon thread terminates automatically when main application exits
- Use `threading.Event` for clean shutdown signaling
- Periodic execution via `event.wait(timeout=30)` pattern

**File I/O Pattern Decision**: Write-and-rename for atomicity
- Write to `data/health.json.tmp`
- Rename to `data/health.json` (atomic on most file systems)
- Prevents partial reads by monitoring tools

**Database Testing Pattern**: Use existing infrastructure
- Import `session_scope` from `src.services.database`
- Simple `SELECT 1` query with 3-second timeout
- Catch SQLAlchemyError for connection failures

**Version Reading Pattern**: Use tomllib with fallback
- Try `tomllib` (Python 3.11+), fall back to `toml` package
- Read once at service initialization, cache value
- Graceful degradation to `"unknown"` on read failure

## Phase 1: Design

### Data Model

See [data-model.md](./data-model.md) for complete data structures.

**Health Status Data Structure:**
```python
{
    "status": str,        # "online" | "degraded" | "starting"
    "database": str,      # "connected" | "disconnected" | "timeout"
    "timestamp": str,     # ISO 8601 format: "2025-11-08T12:34:56Z"
    "app_version": str,   # From pyproject.toml: "0.1.0"
    "api_version": str    # Static: "v1"
}
```

### Module Design: health_service.py

**Classes:**
- `HealthCheckService`: Main service class managing health checks

**Key Methods:**
- `__init__()`: Initialize service, read app version, create data directory
- `start()`: Start background health check thread
- `stop()`: Signal thread to stop and wait for cleanup
- `_health_check_loop()`: Background thread main loop
- `_check_database()`: Test database connectivity
- `_get_app_version()`: Read version from pyproject.toml (cached)
- `_write_health_status()`: Write JSON to file atomically

**Error Handling:**
- Database connection errors: Log and continue
- File write errors: Log and continue
- Version read errors: Use fallback value

### Integration Points

1. **Main Application (src/main.py)**
   - Import `HealthCheckService`
   - Initialize after database setup
   - Start service before UI launch
   - Stop service on application exit

2. **Database Service (src/services/database.py)**
   - Use existing `session_scope()` for connection testing
   - Use existing exception types

3. **Configuration (src/utils/config.py)**
   - May leverage existing config for health check interval (optional)

### API Contracts

See [contracts/health-status-schema.json](./contracts/health-status-schema.json) for JSON schema definition.

**Health Status File Contract:**
- Location: `data/health.json`
- Format: JSON
- Update frequency: Every 30 seconds
- Encoding: UTF-8
- Max size: <1KB

## Phase 2: Tasks Breakdown Planning

*Note: Detailed tasks will be generated in `/spec-kitty.tasks` command*

### Task Categories

1. **Core Implementation (WP01-WP03)**
   - WP01: Create health_service.py module structure
   - WP02: Implement database connectivity testing
   - WP03: Implement file writing with atomic operations

2. **Integration (WP04-WP05)**
   - WP04: Integrate health service with main.py
   - WP05: Add version reading from pyproject.toml

3. **Testing (WP06-WP08)**
   - WP06: Unit tests for health check logic
   - WP07: Unit tests for file I/O operations
   - WP08: Integration test for full health check cycle

4. **Documentation (WP09)**
   - WP09: Add module docstrings and inline comments

### Estimated Complexity

- **Core implementation**: 3-4 hours
- **Integration**: 1 hour
- **Testing**: 2-3 hours
- **Documentation**: 30 minutes

**Total estimate**: 6-8 hours

## Constitution Re-Check (Post-Design)

*Re-evaluating against constitution after design phase*

### Code Quality ✅
- Module structure follows existing patterns in src/services/
- Type hints throughout design
- Single responsibility (health checking only)

### Testing ✅
- 8 test scenarios identified (3 core, 2 integration, 3 edge cases)
- Estimated coverage: 92%+

### Performance ✅
- Background thread prevents UI blocking
- File I/O <100ms
- Database check with 3-second timeout

### Security ✅
- No user input processing
- No new attack surface
- Uses existing safe database patterns

**Overall**: ✅ PASS - Design meets all constitutional requirements

## Next Steps

1. Run `/spec-kitty.tasks` to generate detailed task breakdown
2. Review generated task files in `kitty-specs/001-system-health-check/tasks/`
3. Begin implementation with `/spec-kitty.implement`

## Artifacts Generated

- ✅ plan.md (this file)
- ⏳ research.md (Phase 0 output)
- ⏳ data-model.md (Phase 1 output)
- ⏳ quickstart.md (Phase 1 output)
- ⏳ contracts/ (Phase 1 output)

**Planning Status**: Phase 0-1 complete, ready for Phase 2 (tasks)
