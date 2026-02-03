# Implementation Plan: Configuration Management Enhancement

**Branch**: `090-configuration-management-enhancement` | **Date**: 2026-02-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/090-configuration-management-enhancement/spec.md`

## Summary

Extend the existing `Config` class in `src/utils/config.py` to centralize all configuration values currently scattered as hard-coded values across the codebase. This enables environment-specific configuration, PostgreSQL support for web migration testing, feature flags for gradual rollout, and UI customization via environment variables.

## Technical Context

**Language/Version**: Python 3.10+ (existing project requirement)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (existing dependencies)
**Storage**: SQLite (desktop default), PostgreSQL (web migration via DATABASE_URL)
**Testing**: pytest (existing test framework)
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single project with layered architecture
**Performance Goals**: N/A (configuration access is not performance-critical)
**Constraints**: Backward compatibility - identical behavior with no env vars set
**Scale/Scope**: ~4 files modified, ~100 lines added to Config class

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| **VI.B Configuration & Environment Management** | ✅ ALIGNS | This feature directly implements Section VI.B requirements: no hard-coded values, settings pattern, environment-specific configuration |
| **VI.F Migration & Evolution Readiness** | ✅ ALIGNS | PostgreSQL URL support enables web migration testing per constitution guidance |
| **V. Layered Architecture Discipline** | ✅ ALIGNS | Configuration centralized in utils layer, accessed by services and UI |
| **I. User-Centric Design** | ✅ ALIGNS | Defaults maintain current behavior; configuration is for developers/admins |

### Constitution Requirements Addressed

From Section VI.B (Configuration & Environment Management):

1. **No Hard-Coded Values** (REQUIRED):
   - Currently violated: `database.py` has `timeout: 30`, `main.py` has theme/appearance
   - Fix: Move to Config properties with environment variable overrides

2. **Settings Pattern** (REQUIRED):
   - Pattern to follow: `@property` methods with `os.environ.get()` defaults
   - Already demonstrated in existing `Config.database_url` property

3. **Feature Flags Dictionary** (RECOMMENDED):
   - Constitution example: `config.feature_flags['enable_audit_trail']`
   - Implement as Config property returning dictionary

4. **Support Both SQLite and PostgreSQL** (RECOMMENDED):
   - Constitution example shows `database_type` and `database_url` properties
   - Critical for web migration readiness

## Project Structure

### Documentation (this feature)

```
kitty-specs/090-configuration-management-enhancement/
├── spec.md              # Feature specification
├── plan.md              # This file
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality validation
└── tasks/               # Work packages (after /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── utils/
│   └── config.py        # PRIMARY: Add new Config properties
├── services/
│   ├── database.py      # UPDATE: Use Config for connection settings
│   └── health_service.py # UPDATE: Use Config for check_interval
└── main.py              # UPDATE: Use Config for UI settings
```

**Structure Decision**: No new files needed. Extend existing Config class and update consumers.

## Complexity Tracking

*No constitution violations - this feature directly implements constitution requirements.*

## Hard-Coded Values Inventory

### database.py (Lines 123, 131)
```python
# Current (hard-coded)
connect_args={"check_same_thread": False, "timeout": 30}

# Target (from Config)
connect_args=config.db_connect_args  # Returns appropriate dict for db_type
```

### main.py (Lines 144-145)
```python
# Current (hard-coded)
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

# Target (from Config)
ctk.set_appearance_mode(config.ui_appearance)
ctk.set_default_color_theme(config.ui_theme)
```

### health_service.py (Line 51)
```python
# Current (default in constructor)
def __init__(self, check_interval: int = 30, ...):

# Target (from Config)
def __init__(self, check_interval: Optional[int] = None, ...):
    self._check_interval = check_interval or config.health_check_interval
```

## New Config Properties

### Database Configuration

| Property | Type | Env Var | Default | Notes |
|----------|------|---------|---------|-------|
| `db_timeout` | int | `BAKE_TRACKER_DB_TIMEOUT` | 30 | Connection timeout seconds |
| `db_pool_size` | int | `BAKE_TRACKER_DB_POOL_SIZE` | 5 | Connection pool size (future) |
| `db_pool_recycle` | int | `BAKE_TRACKER_DB_POOL_RECYCLE` | 3600 | Connection recycle time |
| `database_type` | str | `BAKE_TRACKER_DB_TYPE` | "sqlite" | "sqlite" or "postgresql" |
| `db_connect_args` | dict | N/A | (computed) | Returns appropriate connect_args for db_type |

### PostgreSQL Support

| Property | Type | Env Var | Default | Notes |
|----------|------|---------|---------|-------|
| `database_url` | str | `DATABASE_URL` (postgres) | SQLite path | Updated to support both |

**Logic**:
- If `database_type == "postgresql"`: Use `DATABASE_URL` env var
- If `database_type == "sqlite"`: Use existing SQLite path logic
- Raise clear error if postgresql selected but `DATABASE_URL` missing

### Feature Flags

| Property | Type | Env Var | Default | Notes |
|----------|------|---------|---------|-------|
| `feature_flags` | dict | Multiple | (see below) | Dictionary of boolean flags |

**Flags**:
- `enable_audit_trail`: `ENABLE_AUDIT` → False (future observability)
- `enable_health_checks`: `ENABLE_HEALTH` → True (existing feature)
- `enable_performance_monitoring`: `ENABLE_PERF_MON` → False (future)

### UI Configuration

| Property | Type | Env Var | Default | Notes |
|----------|------|---------|---------|-------|
| `ui_theme` | str | `BAKE_TRACKER_THEME` | "blue" | CustomTkinter theme |
| `ui_appearance` | str | `BAKE_TRACKER_APPEARANCE` | "system" | Appearance mode |

**Validation**:
- `ui_theme`: Valid values are "blue", "dark-blue", "green"
- `ui_appearance`: Valid values are "system", "light", "dark"
- Invalid values: Use default with warning logged

### Health Service Configuration

| Property | Type | Env Var | Default | Notes |
|----------|------|---------|---------|-------|
| `health_check_interval` | int | `BAKE_TRACKER_HEALTH_INTERVAL` | 30 | Seconds between checks |

## Implementation Approach

### Phase 1: Config Class Extension (~50 lines)

Add new properties to `src/utils/config.py`:
1. Database connection properties (db_timeout, db_pool_size, db_pool_recycle)
2. Database type and URL properties (support PostgreSQL)
3. Feature flags dictionary property
4. UI configuration properties
5. Health check configuration property

### Phase 2: Consumer Updates (~30 lines changed)

Update files to use Config:
1. `database.py`: Use `config.db_connect_args`, `config.database_url`
2. `main.py`: Use `config.ui_theme`, `config.ui_appearance`
3. `health_service.py`: Use `config.health_check_interval`

### Phase 3: Documentation

1. Docstrings for all new Config properties
2. Environment variable reference (can be in Config class docstring)

## Testing Strategy

### Unit Tests for Config Properties

- Test default values when env vars not set
- Test env var override for each property
- Test type conversion (string → int, string → bool)
- Test invalid value handling (use default, log warning)
- Test PostgreSQL URL logic (with/without DATABASE_URL)

### Integration Tests

- Verify application starts correctly with no env vars (backward compatibility)
- Verify database connection with custom timeout
- Verify UI appearance/theme application

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing database connections | HIGH | Maintain identical default values |
| PostgreSQL connection string errors | MEDIUM | Validate format, clear error message |
| Environment variable confusion | LOW | Comprehensive documentation |

## Success Metrics

1. Zero hard-coded configuration values in database.py, main.py, health_service.py
2. All configuration properties support environment variable overrides
3. PostgreSQL database URL can be configured without code changes
4. Application behavior identical with no environment variables set
5. All existing tests pass without modification

---

## ⛔ MANDATORY STOP POINT

**Planning phase complete. Artifacts generated:**

- ✅ `plan.md` - This file
- ⏭️ `research.md` - Not needed (patterns already established in codebase)
- ⏭️ `data-model.md` - Not needed (no new data entities)
- ⏭️ `contracts/` - Not needed (no API contracts)

**Next step**: User must run `/spec-kitty.tasks` to generate work packages.
