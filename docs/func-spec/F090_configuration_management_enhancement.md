# F090: Configuration Management Enhancement

**Version**: 1.0
**Priority**: HIGH
**Type**: Architecture Enhancement

---

## Executive Summary

Current gaps:
- ❌ Hard-coded database connection settings (timeout: 30, no pool configuration)
- ❌ Hard-coded UI settings (theme, appearance mode)
- ❌ No feature flags system for gradual rollout
- ❌ No PostgreSQL connection string support (blocks web migration testing)

This spec extends the existing Config class to support database connection settings, PostgreSQL URLs, feature flags, and UI configuration, enabling environment-specific configuration and web migration readiness.

---

## Problem Statement

**Current State (INCOMPLETE):**
```
Configuration System
├─ ✅ Config class exists (src/utils/config.py)
├─ ✅ Environment-based paths (development vs production)
├─ ✅ Environment variable support (BAKING_TRACKER_ENV)
├─ ❌ Hard-coded database settings (timeout, pool size)
├─ ❌ Hard-coded UI settings (theme, appearance)
├─ ❌ No feature flags support
└─ ❌ No PostgreSQL URL support (SQLite only)

Hard-Coded Values
├─ ❌ database.py: timeout=30, check_same_thread=False
├─ ❌ main.py: appearance_mode="system", theme="blue"
├─ ❌ health_service.py: check_interval=30
└─ ❌ Multiple other scattered hard-coded values
```

**Target State (COMPLETE):**
```
Configuration System
├─ ✅ Extended Config class with all settings
├─ ✅ Database connection configuration
├─ ✅ PostgreSQL and SQLite URL support
├─ ✅ Feature flags dictionary
├─ ✅ UI settings configurable
└─ ✅ Environment variable overrides

Configuration Values
├─ ✅ All database settings in Config
├─ ✅ All UI settings in Config
├─ ✅ Feature flags for gradual rollout
└─ ✅ No hard-coded values in code
```

---

## CRITICAL: Study These Files FIRST

**Before implementation, spec-kitty planning phase MUST read and understand:**

1. **Existing Configuration System**
   - Find `src/utils/config.py` - current Config class implementation
   - Study property-based configuration pattern (@property decorators)
   - Note environment variable usage and default values

2. **Hard-Coded Database Settings**
   - Find `src/services/database.py` - connection configuration
   - Study SQLite-specific connect_args: check_same_thread, timeout
   - Note engine creation pattern

3. **Hard-Coded UI Settings**
   - Find `src/main.py` - UI initialization
   - Study ctk.set_appearance_mode() and set_default_color_theme() calls
   - Note current hard-coded values

4. **Other Configuration Needs**
   - Find `src/services/health_service.py` - check_interval parameter
   - Search for other hard-coded configuration values
   - Note patterns for configuration needs

---

## Requirements Reference

This specification implements:
- **Code Quality Principle VI.B**: Configuration & Environment Management
  - No hard-coded values
  - Settings pattern
  - Environment-specific configuration

From: `docs/design/code_quality_principles_revised.md` (v1.0)

---

## Functional Requirements

### FR-1: Add Database Connection Configuration

**What it must do:**
- Add database timeout setting (configurable via environment variable)
- Add database pool size setting (for web migration readiness)
- Add database pool recycle time setting (connection lifetime)
- Support both SQLite and PostgreSQL connection arguments

**Pattern reference:** Study existing Config properties (@property decorators with os.environ.get)

**Configuration properties needed:**
- `db_timeout` - connection timeout in seconds (default 30)
- `db_pool_size` - connection pool size (default 5)
- `db_pool_recycle` - connection recycle time in seconds (default 3600)
- `db_connect_args` - database-specific connection arguments (varies by database_type)

**Success criteria:**
- [ ] Config.db_timeout property exists with environment variable support
- [ ] Config.db_pool_size property exists with environment variable support
- [ ] Config.db_pool_recycle property exists with environment variable support
- [ ] Config.db_connect_args property returns appropriate args for database type
- [ ] All properties have sensible defaults
- [ ] All properties support integer type enforcement

---

### FR-2: Add PostgreSQL Connection String Support

**What it must do:**
- Add database_type property (sqlite or postgresql)
- Modify database_url property to support PostgreSQL URLs
- Handle environment-based database URL configuration
- Maintain backward compatibility with existing SQLite usage

**Pattern reference:** Study Config.database_path property, extend database_url logic

**Database URL requirements:**
- SQLite (desktop): `sqlite:///path/to/database.db`
- PostgreSQL (web): `postgresql://user:pass@host:port/dbname`
- Environment variable: DATABASE_URL for PostgreSQL
- Default to SQLite for desktop app

**Success criteria:**
- [ ] Config.database_type property exists (default: "sqlite")
- [ ] Config.database_url supports both SQLite and PostgreSQL formats
- [ ] PostgreSQL URL read from DATABASE_URL environment variable
- [ ] SQLite URL generation unchanged from current behavior
- [ ] Raises clear error if PostgreSQL selected but DATABASE_URL missing

---

### FR-3: Add Feature Flags System

**What it must do:**
- Create feature_flags property returning dictionary of flags
- Support environment variable configuration for each flag
- Provide clear naming convention for feature flag variables
- Include flags for observability features (audit trail, performance monitoring)

**Pattern reference:** Study Config property pattern, return dictionary with boolean values

**Initial feature flags:**
- `enable_audit_trail` - future observability feature (default: false)
- `enable_health_checks` - current health check service (default: true)
- `enable_performance_monitoring` - future performance tracking (default: false)

**Environment variable naming:**
- `ENABLE_AUDIT` → feature_flags['enable_audit_trail']
- `ENABLE_HEALTH` → feature_flags['enable_health_checks']
- `ENABLE_PERF_MON` → feature_flags['enable_performance_monitoring']

**Success criteria:**
- [ ] Config.feature_flags property returns dictionary
- [ ] All flags have boolean values (true/false)
- [ ] All flags support environment variable override
- [ ] All flags have sensible defaults
- [ ] Flag naming convention documented

---

### FR-4: Add UI Configuration Settings

**What it must do:**
- Add ui_theme property (color theme: "blue", "green", "dark-blue")
- Add ui_appearance property (appearance mode: "system", "dark", "light")
- Support environment variable configuration
- Maintain current defaults as fallbacks

**Pattern reference:** Study Config string property pattern with environment variables

**UI configuration properties:**
- `ui_theme` - color theme (default: "blue")
- `ui_appearance` - appearance mode (default: "system")

**Environment variables:**
- `BAKE_TRACKER_THEME` → Config.ui_theme
- `BAKE_TRACKER_APPEARANCE` → Config.ui_appearance

**Success criteria:**
- [ ] Config.ui_theme property exists
- [ ] Config.ui_appearance property exists
- [ ] Both support environment variable overrides
- [ ] Current defaults maintained ("blue", "system")
- [ ] Values validated against allowed options

---

### FR-5: Update Code to Use Configuration

**What it must do:**
- Update database.py to use Config for all connection settings
- Update main.py to use Config for UI settings
- Update health_service.py to use Config for check interval
- Remove all hard-coded configuration values

**Pattern reference:** Study how Config is currently used, apply consistently

**Files requiring updates:**
- `src/services/database.py` - use Config properties for engine creation
- `src/main.py` - use Config properties for UI initialization
- `src/services/health_service.py` - use Config for check_interval
- Any other files with hard-coded configuration

**Success criteria:**
- [ ] database.py uses Config.db_timeout, db_pool_size, db_pool_recycle
- [ ] database.py uses Config.db_connect_args
- [ ] main.py uses Config.ui_theme and Config.ui_appearance
- [ ] health_service.py uses Config for check_interval
- [ ] No hard-coded configuration values remain in code
- [ ] All configuration centralized in Config class

---

### FR-6: Document Configuration System

**What it must do:**
- Document all configuration properties in Config class docstrings
- Create environment variable reference documentation
- Provide examples for common configuration scenarios
- Document PostgreSQL connection string format

**Pattern reference:** Study existing docstring patterns in codebase

**Documentation requirements:**
- Config class docstring with overview
- Each property documented with purpose, default, environment variable
- Environment variable reference table
- PostgreSQL connection examples
- Feature flag usage examples

**Success criteria:**
- [ ] Config class has comprehensive docstring
- [ ] All properties documented with docstrings
- [ ] Environment variable reference exists in docs/
- [ ] PostgreSQL configuration examples provided
- [ ] Feature flag usage documented

---

## Out of Scope

**Explicitly NOT included in this feature:**
- ❌ Configuration file support (YAML/JSON) - environment variables sufficient
- ❌ Dynamic configuration reloading - requires app restart
- ❌ Configuration validation at startup - defer to separate feature
- ❌ User-editable configuration UI - desktop app uses defaults
- ❌ Cloud-based configuration - not needed for desktop

---

## Success Criteria

**Complete when:**

### Configuration Properties
- [ ] All database connection settings in Config
- [ ] PostgreSQL URL support implemented
- [ ] Feature flags system implemented
- [ ] UI settings in Config
- [ ] All properties have environment variable support
- [ ] All properties have sensible defaults

### Code Updates
- [ ] database.py uses Config for all settings
- [ ] main.py uses Config for UI settings
- [ ] health_service.py uses Config for check_interval
- [ ] No hard-coded configuration values remain
- [ ] Configuration pattern applied consistently

### Documentation
- [ ] Config class comprehensively documented
- [ ] Environment variable reference exists
- [ ] PostgreSQL configuration examples provided
- [ ] Feature flag usage documented
- [ ] Configuration pattern documented for future additions

### Quality
- [ ] Configuration follows Code Quality Principle VI.B
- [ ] Type safety maintained (int, bool, str conversions)
- [ ] Backward compatibility preserved (existing defaults)
- [ ] Environment variable naming consistent

---

## Architecture Principles

### Configuration Centralization

**All configuration through Config class:**
- No hard-coded values scattered in code
- Single source of truth for all settings
- Environment variable overrides consistently supported

### Property-Based Pattern

**Use @property decorators:**
- Clean interface: `config.db_timeout` not `config.get_db_timeout()`
- Lazy evaluation (computed when accessed)
- Easy to extend with new properties

### Environment Variable Convention

**Consistent naming:**
- Prefix: `BAKE_TRACKER_*` for app-specific settings
- Format: UPPERCASE_WITH_UNDERSCORES
- Boolean: "true"/"false" strings converted to bool

### Pattern Matching

**All new configuration properties must follow existing pattern:**
- @property decorator
- os.environ.get() with default
- Type conversion (int(), bool via string check)
- Docstring with purpose, default, environment variable

---

## Constitutional Compliance

✅ **Principle VI.B: Configuration & Environment Management**
- Implements no hard-coded values requirement
- Implements settings pattern requirement
- Implements environment-specific configuration

✅ **Principle VI.F: Migration & Evolution Readiness**
- PostgreSQL support enables web migration testing
- Database abstraction supports both SQLite and PostgreSQL
- Configuration pattern scales to web deployment

✅ **Principle V: Layered Architecture Discipline**
- Configuration centralized in utils layer
- Services access configuration through clean interface
- No configuration logic scattered in business logic

---

## Risk Considerations

**Risk: Breaking existing database connections**
- Changing connection configuration might cause failures
- Mitigation: Maintain identical default values to current hard-coded values
- Mitigation: Test with existing database before committing

**Risk: PostgreSQL connection string errors**
- Invalid DATABASE_URL format could cause startup failure
- Mitigation: Validate format and provide clear error message
- Mitigation: Document expected format with examples

**Risk: Environment variable confusion**
- Users might not know which variables are available
- Mitigation: Create comprehensive environment variable reference
- Mitigation: Document defaults clearly in Config class

---

## Notes for Implementation

**Pattern Discovery (Planning Phase):**
- Study `src/utils/config.py` → understand property pattern
- Study `src/services/database.py` → identify hard-coded values to extract
- Study `src/main.py` → identify UI settings to extract

**Key Patterns to Copy:**
- Existing Config properties → apply same pattern to new properties
- os.environ.get() usage → consistent default value handling
- Type conversion patterns → apply to integer and boolean properties

**Focus Areas:**
- Maintain exact default values from current hard-coded values
- PostgreSQL URL support is critical for web migration testing
- Feature flags enable gradual rollout of observability features
- Documentation prevents future hard-coding of new configuration

**Implementation Note:**
This feature is a quick win (small effort, high value) that unblocks PostgreSQL testing and provides infrastructure for future feature flags. The configuration pattern established here should be used for all future configuration needs.

---

**END OF SPECIFICATION**
