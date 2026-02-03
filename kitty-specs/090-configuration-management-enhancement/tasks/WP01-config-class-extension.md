---
work_package_id: WP01
title: Config Class Extension
lane: "done"
dependencies: []
base_branch: main
base_commit: 6f1def0ba0a8662ee167d9031b07e806e4bc9778
created_at: '2026-02-03T03:02:42.328311+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
assignee: ''
agent: "claude"
shell_pid: "9583"
review_status: "approved"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-03T02:58:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Config Class Extension

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

---

## Objectives & Success Criteria

**Objective**: Extend the existing `Config` class in `src/utils/config.py` with all new configuration properties needed for F090.

**Success Criteria**:
- [ ] All new properties return correct default values when no env vars set
- [ ] Environment variable overrides work for all properties
- [ ] Invalid values fall back to defaults with warning logged
- [ ] PostgreSQL URL support works when DATABASE_URL is set
- [ ] All properties have comprehensive docstrings
- [ ] Existing Config functionality unchanged

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/090-configuration-management-enhancement/spec.md`
- Plan: `kitty-specs/090-configuration-management-enhancement/plan.md`
- Constitution: `.kittify/memory/constitution.md` (Section VI.B)

**Key Constraints**:
- Follow existing `@property` pattern in Config class
- Maintain backward compatibility (defaults match current hard-coded values)
- Use `os.environ.get()` with sensible defaults
- Log warnings for invalid values, don't crash

**Current Config Pattern** (from existing code):
```python
@property
def database_url(self) -> str:
    db_path_str = str(self._database_path).replace("\\", "/")
    return f"sqlite:///{db_path_str}"
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Add Database Connection Properties

**Purpose**: Centralize database connection settings that are currently hard-coded in `database.py`.

**Steps**:
1. Add `db_timeout` property:
   ```python
   @property
   def db_timeout(self) -> int:
       """Database connection timeout in seconds.

       Environment variable: BAKE_TRACKER_DB_TIMEOUT
       Default: 30
       """
       try:
           return int(os.environ.get("BAKE_TRACKER_DB_TIMEOUT", "30"))
       except ValueError:
           logger.warning("Invalid BAKE_TRACKER_DB_TIMEOUT, using default 30")
           return 30
   ```

2. Add `db_pool_size` property:
   - Env var: `BAKE_TRACKER_DB_POOL_SIZE`
   - Default: 5
   - Type: int

3. Add `db_pool_recycle` property:
   - Env var: `BAKE_TRACKER_DB_POOL_RECYCLE`
   - Default: 3600 (1 hour)
   - Type: int

**Files**: `src/utils/config.py`

**Notes**:
- Add `import logging` at top if not present
- Create logger: `logger = logging.getLogger(__name__)`

---

### Subtask T002 – Add database_type and Update database_url for PostgreSQL

**Purpose**: Enable PostgreSQL support for web migration testing via environment variable.

**Steps**:
1. Add `database_type` property:
   ```python
   @property
   def database_type(self) -> str:
       """Database type: 'sqlite' (default) or 'postgresql'.

       Environment variable: BAKE_TRACKER_DB_TYPE
       Default: sqlite
       """
       db_type = os.environ.get("BAKE_TRACKER_DB_TYPE", "sqlite").lower()
       if db_type not in ("sqlite", "postgresql"):
           logger.warning(f"Invalid BAKE_TRACKER_DB_TYPE '{db_type}', using sqlite")
           return "sqlite"
       return db_type
   ```

2. Update `database_url` property to support PostgreSQL:
   ```python
   @property
   def database_url(self) -> str:
       """SQLAlchemy database URL.

       For PostgreSQL: Uses DATABASE_URL environment variable.
       For SQLite: Generates path-based URL (current behavior).

       Raises:
           ValueError: If postgresql selected but DATABASE_URL not set.
       """
       if self.database_type == "postgresql":
           url = os.environ.get("DATABASE_URL")
           if not url:
               raise ValueError(
                   "DATABASE_URL environment variable required when "
                   "BAKE_TRACKER_DB_TYPE=postgresql"
               )
           return url

       # SQLite (default) - existing logic
       db_path_str = str(self._database_path).replace("\\", "/")
       return f"sqlite:///{db_path_str}"
   ```

**Files**: `src/utils/config.py`

**Notes**:
- PostgreSQL URL format: `postgresql://user:password@host:port/dbname`
- Keep existing SQLite behavior as default

---

### Subtask T003 – Add db_connect_args Computed Property

**Purpose**: Provide database-specific connection arguments that database.py can use directly.

**Steps**:
1. Add `db_connect_args` property:
   ```python
   @property
   def db_connect_args(self) -> dict:
       """Database connection arguments for SQLAlchemy.

       Returns appropriate connect_args based on database_type:
       - SQLite: check_same_thread, timeout
       - PostgreSQL: (empty dict, connection params in URL)
       """
       if self.database_type == "postgresql":
           return {}

       # SQLite
       return {
           "check_same_thread": False,
           "timeout": self.db_timeout,
       }
   ```

**Files**: `src/utils/config.py`

**Notes**:
- This replaces the hard-coded dict in `database.py`
- PostgreSQL connection params go in the URL, not connect_args

---

### Subtask T004 – Add Feature Flags Dictionary Property

**Purpose**: Enable gradual rollout of observability features via environment variables.

**Steps**:
1. Add helper method for boolean parsing:
   ```python
   def _parse_bool_env(self, var_name: str, default: bool) -> bool:
       """Parse boolean from environment variable."""
       value = os.environ.get(var_name, str(default).lower())
       return value.lower() in ("true", "1", "yes")
   ```

2. Add `feature_flags` property:
   ```python
   @property
   def feature_flags(self) -> dict:
       """Feature flags for gradual rollout of optional features.

       Flags:
           enable_audit_trail: Future observability (default: False)
               Env: ENABLE_AUDIT
           enable_health_checks: Current health service (default: True)
               Env: ENABLE_HEALTH
           enable_performance_monitoring: Future metrics (default: False)
               Env: ENABLE_PERF_MON
       """
       return {
           "enable_audit_trail": self._parse_bool_env("ENABLE_AUDIT", False),
           "enable_health_checks": self._parse_bool_env("ENABLE_HEALTH", True),
           "enable_performance_monitoring": self._parse_bool_env("ENABLE_PERF_MON", False),
       }
   ```

**Files**: `src/utils/config.py`

**Notes**:
- Health checks default to True (existing feature)
- Audit trail and performance monitoring default to False (future features)

---

### Subtask T005 – Add UI Configuration Properties

**Purpose**: Allow UI customization via environment variables instead of hard-coded values.

**Steps**:
1. Add `ui_theme` property with validation:
   ```python
   @property
   def ui_theme(self) -> str:
       """CustomTkinter color theme.

       Environment variable: BAKE_TRACKER_THEME
       Default: blue
       Valid values: blue, dark-blue, green
       """
       valid_themes = ("blue", "dark-blue", "green")
       theme = os.environ.get("BAKE_TRACKER_THEME", "blue")
       if theme not in valid_themes:
           logger.warning(f"Invalid BAKE_TRACKER_THEME '{theme}', using blue")
           return "blue"
       return theme
   ```

2. Add `ui_appearance` property with validation:
   ```python
   @property
   def ui_appearance(self) -> str:
       """CustomTkinter appearance mode.

       Environment variable: BAKE_TRACKER_APPEARANCE
       Default: system
       Valid values: system, light, dark
       """
       valid_modes = ("system", "light", "dark")
       mode = os.environ.get("BAKE_TRACKER_APPEARANCE", "system")
       if mode not in valid_modes:
           logger.warning(f"Invalid BAKE_TRACKER_APPEARANCE '{mode}', using system")
           return "system"
       return mode
   ```

**Files**: `src/utils/config.py`

**Notes**:
- These match CustomTkinter's supported values
- Invalid values fall back gracefully with warning

---

### Subtask T006 – Add Health Check Interval Property

**Purpose**: Centralize health service configuration.

**Steps**:
1. Add `health_check_interval` property:
   ```python
   @property
   def health_check_interval(self) -> int:
       """Health check interval in seconds.

       Environment variable: BAKE_TRACKER_HEALTH_INTERVAL
       Default: 30
       """
       try:
           return int(os.environ.get("BAKE_TRACKER_HEALTH_INTERVAL", "30"))
       except ValueError:
           logger.warning("Invalid BAKE_TRACKER_HEALTH_INTERVAL, using default 30")
           return 30
   ```

**Files**: `src/utils/config.py`

**Notes**:
- Default matches current hard-coded value in health_service.py

---

### Subtask T007 – Add Comprehensive Docstrings

**Purpose**: Document all new properties per constitution requirements (VI.D: docstrings REQUIRED).

**Steps**:
1. Update Config class docstring to describe new capabilities:
   ```python
   class Config:
       """Application configuration manager.

       Handles all configuration settings including:
       - Database paths and connection settings
       - PostgreSQL/SQLite database URL abstraction
       - Environment settings (development/production)
       - Feature flags for gradual rollout
       - UI appearance and theme settings
       - Health check configuration

       All properties support environment variable overrides with sensible defaults.
       Invalid values fall back to defaults with warning logged.

       Environment Variables:
           BAKE_TRACKER_ENV: Environment mode (production/development)
           BAKE_TRACKER_DB_TYPE: Database type (sqlite/postgresql)
           BAKE_TRACKER_DB_TIMEOUT: Connection timeout (default: 30)
           BAKE_TRACKER_DB_POOL_SIZE: Connection pool size (default: 5)
           BAKE_TRACKER_DB_POOL_RECYCLE: Connection recycle time (default: 3600)
           DATABASE_URL: PostgreSQL connection URL (required if DB_TYPE=postgresql)
           ENABLE_AUDIT: Enable audit trail (default: false)
           ENABLE_HEALTH: Enable health checks (default: true)
           ENABLE_PERF_MON: Enable performance monitoring (default: false)
           BAKE_TRACKER_THEME: UI color theme (default: blue)
           BAKE_TRACKER_APPEARANCE: UI appearance mode (default: system)
           BAKE_TRACKER_HEALTH_INTERVAL: Health check interval (default: 30)
       """
   ```

2. Verify each property added in T001-T006 has a docstring (already included in examples above)

**Files**: `src/utils/config.py`

**Notes**:
- Environment variable reference in class docstring provides quick overview
- Individual property docstrings provide detail

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing database_url behavior | Only change when database_type is "postgresql" |
| Invalid env values causing crashes | Graceful fallback to defaults with warning |
| Missing logger import | Add `import logging` and create module logger |

---

## Definition of Done Checklist

- [ ] All 7 new properties added to Config class
- [ ] All properties return correct defaults when no env vars set
- [ ] Environment variable overrides work correctly
- [ ] Invalid values log warning and use defaults
- [ ] PostgreSQL URL support implemented
- [ ] Feature flags dictionary returns expected values
- [ ] UI properties validate against allowed values
- [ ] All properties have comprehensive docstrings
- [ ] Config class docstring updated with environment variable reference
- [ ] No existing Config functionality broken

---

## Review Guidance

**Reviewers should verify**:
1. Property naming follows existing pattern (snake_case, no get_ prefix)
2. Environment variable names are consistent (BAKE_TRACKER_* prefix)
3. Default values match current hard-coded values (30 for timeout, etc.)
4. Docstrings are comprehensive and accurate
5. Invalid value handling is graceful (warning + default, not exception)
6. PostgreSQL URL requirement raises clear error if DATABASE_URL missing

---

## Activity Log

- 2026-02-03T02:58:47Z – system – lane=planned – Prompt created.
- 2026-02-03T03:14:23Z – unknown – shell_pid=2687 – lane=for_review – WP01 Config class extension complete. All 7 subtasks implemented. All tests pass (3416 passed).
- 2026-02-03T03:17:25Z – claude – shell_pid=9583 – lane=doing – Started review via workflow command
- 2026-02-03T03:18:11Z – claude – shell_pid=9583 – lane=done – Review passed: All 9 new properties implemented with correct defaults, env var overrides, invalid value handling, PostgreSQL support, and comprehensive docstrings.
