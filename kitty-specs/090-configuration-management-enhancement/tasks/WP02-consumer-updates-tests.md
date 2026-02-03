---
work_package_id: WP02
title: Consumer Updates & Tests
lane: "doing"
dependencies: [WP01]
base_branch: 090-configuration-management-enhancement-WP01
base_commit: 7b4a07e6ca24f8218f5697b1dca069c1a606d349
created_at: '2026-02-03T03:14:37.083472+00:00'
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 2 - Integration
assignee: ''
agent: ''
shell_pid: "8297"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T02:58:47Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Consumer Updates & Tests

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
spec-kitty implement WP02 --base WP01
```

**Important**: This WP depends on WP01. Use `--base WP01` to branch from the correct point.

---

## Objectives & Success Criteria

**Objective**: Update all consumer files (database.py, main.py, health_service.py) to use the new Config properties, and add comprehensive unit tests.

**Success Criteria**:
- [ ] database.py uses Config.db_connect_args (no hard-coded values)
- [ ] main.py uses Config.ui_theme and Config.ui_appearance
- [ ] health_service.py uses Config.health_check_interval as default
- [ ] All existing tests pass without modification
- [ ] New unit tests verify all Config property behaviors
- [ ] Application starts correctly with no environment variables set

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/090-configuration-management-enhancement/spec.md`
- Plan: `kitty-specs/090-configuration-management-enhancement/plan.md`
- Tasks: `kitty-specs/090-configuration-management-enhancement/tasks.md`

**Prerequisites**:
- WP01 complete (all Config properties exist)

**Key Constraints**:
- Maintain identical default behavior (backward compatibility)
- Use existing Config singleton via `get_config()`
- Tests must be isolated (use monkeypatch for env vars)

---

## Subtasks & Detailed Guidance

### Subtask T008 – Update database.py to Use Config

**Purpose**: Replace hard-coded database connection settings with Config properties.

**Current Code** (src/services/database.py, lines 121-132):
```python
# Test mode (in-memory)
if ":memory:" in database_url:
    _engine = create_engine(
        database_url,
        echo=echo,
        connect_args={"check_same_thread": False},  # ← HARD-CODED
        poolclass=StaticPool,
    )
else:
    # Normal mode (file-based)
    _engine = create_engine(
        database_url,
        echo=echo,
        connect_args={"check_same_thread": False, "timeout": 30},  # ← HARD-CODED
    )
```

**Steps**:
1. Import get_config at top of file:
   ```python
   from ..utils.config import get_config
   ```

2. Update the engine creation to use Config:
   ```python
   config = get_config()

   # Test mode (in-memory)
   if ":memory:" in database_url:
       _engine = create_engine(
           database_url,
           echo=echo,
           connect_args={"check_same_thread": False},  # Memory mode still needs this
           poolclass=StaticPool,
       )
   else:
       # Normal mode (file-based)
       _engine = create_engine(
           database_url,
           echo=echo,
           connect_args=config.db_connect_args,  # ← USE CONFIG
       )
   ```

**Files**: `src/services/database.py`

**Notes**:
- Keep in-memory mode's connect_args as-is (test isolation)
- Only change normal file-based mode
- Config.db_connect_args returns `{"check_same_thread": False, "timeout": 30}` by default

**Validation**:
- Application starts correctly
- Database connections work as before
- Run existing database tests

---

### Subtask T009 – Update main.py to Use Config

**Purpose**: Replace hard-coded UI settings with Config properties.

**Current Code** (src/main.py, lines 144-145):
```python
# Set CustomTkinter appearance
ctk.set_appearance_mode("system")  # ← HARD-CODED
ctk.set_default_color_theme("blue")  # ← HARD-CODED
```

**Steps**:
1. Import get_config (may already be imported):
   ```python
   from src.utils.config import get_config
   ```

2. Update the UI initialization:
   ```python
   # Get configuration
   config = get_config()

   # Set CustomTkinter appearance from config
   ctk.set_appearance_mode(config.ui_appearance)
   ctk.set_default_color_theme(config.ui_theme)
   ```

**Files**: `src/main.py`

**Notes**:
- Place after argument parsing but before window creation
- Config is already imported for database path - reuse that import

**Validation**:
- Application starts with default theme (blue) and appearance (system)
- Set BAKE_TRACKER_THEME=dark-blue and verify theme changes
- Set BAKE_TRACKER_APPEARANCE=dark and verify appearance changes

---

### Subtask T010 – Update health_service.py to Use Config

**Purpose**: Use Config for default health check interval instead of hard-coded value.

**Current Code** (src/services/health_service.py, line 51):
```python
def __init__(self, check_interval: int = 30, health_file: Optional[Path] = None):
```

**Steps**:
1. Import get_config and Optional:
   ```python
   from ..utils.config import get_config
   from typing import Optional
   ```

2. Update constructor to use Config as default:
   ```python
   def __init__(
       self,
       check_interval: Optional[int] = None,
       health_file: Optional[Path] = None
   ):
       """
       Initialize health check service.

       Args:
           check_interval: Seconds between health checks. If None, uses
                          Config.health_check_interval (default: 30).
           health_file: Optional path to health status file.
       """
       config = get_config()
       self._check_interval = check_interval if check_interval is not None else config.health_check_interval
       # ... rest of __init__
   ```

**Files**: `src/services/health_service.py`

**Notes**:
- Change parameter type to `Optional[int]` with default `None`
- Use Config value when not explicitly passed
- This allows tests to pass specific values while app uses Config

**Validation**:
- Health service starts with 30-second interval (default)
- Set BAKE_TRACKER_HEALTH_INTERVAL=60 and verify interval changes
- Existing tests pass (they pass explicit interval)

---

### Subtask T011 – Add Unit Tests for Config Properties

**Purpose**: Verify all new Config properties work correctly with defaults, overrides, and invalid values.

**Steps**:
1. Create or update test file `src/tests/unit/test_config.py`:

```python
"""Unit tests for Config class configuration properties."""

import pytest
from src.utils.config import Config, reset_config


class TestDatabaseConfigProperties:
    """Tests for database configuration properties."""

    def setup_method(self):
        """Reset config singleton before each test."""
        reset_config()

    def test_db_timeout_default(self):
        """Default db_timeout is 30."""
        config = Config()
        assert config.db_timeout == 30

    def test_db_timeout_env_override(self, monkeypatch):
        """db_timeout can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TIMEOUT", "60")
        config = Config()
        assert config.db_timeout == 60

    def test_db_timeout_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid db_timeout falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TIMEOUT", "invalid")
        config = Config()
        assert config.db_timeout == 30
        assert "Invalid BAKE_TRACKER_DB_TIMEOUT" in caplog.text

    def test_db_pool_size_default(self):
        """Default db_pool_size is 5."""
        config = Config()
        assert config.db_pool_size == 5

    def test_db_pool_recycle_default(self):
        """Default db_pool_recycle is 3600."""
        config = Config()
        assert config.db_pool_recycle == 3600

    def test_database_type_default(self):
        """Default database_type is sqlite."""
        config = Config()
        assert config.database_type == "sqlite"

    def test_database_type_postgresql(self, monkeypatch):
        """database_type can be set to postgresql."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        config = Config()
        assert config.database_type == "postgresql"

    def test_database_type_invalid_uses_sqlite(self, monkeypatch, caplog):
        """Invalid database_type falls back to sqlite with warning."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "mysql")
        config = Config()
        assert config.database_type == "sqlite"
        assert "Invalid BAKE_TRACKER_DB_TYPE" in caplog.text

    def test_database_url_sqlite_default(self):
        """SQLite database_url generated from path."""
        config = Config()
        assert config.database_url.startswith("sqlite:///")

    def test_database_url_postgresql(self, monkeypatch):
        """PostgreSQL database_url uses DATABASE_URL env var."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        config = Config()
        assert config.database_url == "postgresql://user:pass@localhost/db"

    def test_database_url_postgresql_missing_raises(self, monkeypatch):
        """PostgreSQL without DATABASE_URL raises ValueError."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        config = Config()
        with pytest.raises(ValueError, match="DATABASE_URL environment variable required"):
            _ = config.database_url

    def test_db_connect_args_sqlite(self):
        """SQLite db_connect_args includes timeout."""
        config = Config()
        args = config.db_connect_args
        assert args["check_same_thread"] is False
        assert args["timeout"] == 30

    def test_db_connect_args_postgresql(self, monkeypatch):
        """PostgreSQL db_connect_args is empty dict."""
        monkeypatch.setenv("BAKE_TRACKER_DB_TYPE", "postgresql")
        config = Config()
        assert config.db_connect_args == {}


class TestFeatureFlagsProperties:
    """Tests for feature flags properties."""

    def setup_method(self):
        reset_config()

    def test_feature_flags_defaults(self):
        """Default feature flags have expected values."""
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is False
        assert flags["enable_health_checks"] is True
        assert flags["enable_performance_monitoring"] is False

    def test_feature_flags_env_override(self, monkeypatch):
        """Feature flags can be enabled via env vars."""
        monkeypatch.setenv("ENABLE_AUDIT", "true")
        monkeypatch.setenv("ENABLE_HEALTH", "false")
        config = Config()
        flags = config.feature_flags
        assert flags["enable_audit_trail"] is True
        assert flags["enable_health_checks"] is False


class TestUIConfigProperties:
    """Tests for UI configuration properties."""

    def setup_method(self):
        reset_config()

    def test_ui_theme_default(self):
        """Default ui_theme is blue."""
        config = Config()
        assert config.ui_theme == "blue"

    def test_ui_theme_env_override(self, monkeypatch):
        """ui_theme can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_THEME", "dark-blue")
        config = Config()
        assert config.ui_theme == "dark-blue"

    def test_ui_theme_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid ui_theme falls back to blue with warning."""
        monkeypatch.setenv("BAKE_TRACKER_THEME", "red")
        config = Config()
        assert config.ui_theme == "blue"
        assert "Invalid BAKE_TRACKER_THEME" in caplog.text

    def test_ui_appearance_default(self):
        """Default ui_appearance is system."""
        config = Config()
        assert config.ui_appearance == "system"

    def test_ui_appearance_env_override(self, monkeypatch):
        """ui_appearance can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_APPEARANCE", "dark")
        config = Config()
        assert config.ui_appearance == "dark"

    def test_ui_appearance_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid ui_appearance falls back to system with warning."""
        monkeypatch.setenv("BAKE_TRACKER_APPEARANCE", "auto")
        config = Config()
        assert config.ui_appearance == "system"
        assert "Invalid BAKE_TRACKER_APPEARANCE" in caplog.text


class TestHealthCheckConfigProperties:
    """Tests for health check configuration properties."""

    def setup_method(self):
        reset_config()

    def test_health_check_interval_default(self):
        """Default health_check_interval is 30."""
        config = Config()
        assert config.health_check_interval == 30

    def test_health_check_interval_env_override(self, monkeypatch):
        """health_check_interval can be overridden via environment variable."""
        monkeypatch.setenv("BAKE_TRACKER_HEALTH_INTERVAL", "60")
        config = Config()
        assert config.health_check_interval == 60

    def test_health_check_interval_invalid_uses_default(self, monkeypatch, caplog):
        """Invalid health_check_interval falls back to default with warning."""
        monkeypatch.setenv("BAKE_TRACKER_HEALTH_INTERVAL", "invalid")
        config = Config()
        assert config.health_check_interval == 30
        assert "Invalid BAKE_TRACKER_HEALTH_INTERVAL" in caplog.text
```

**Files**: `src/tests/unit/test_config.py`

**Notes**:
- Use `monkeypatch` fixture to set/unset env vars (isolated per test)
- Use `caplog` fixture to verify warning messages
- Call `reset_config()` in setup to ensure clean state
- Group tests by functionality for clarity

**Validation**:
- Run `pytest src/tests/unit/test_config.py -v`
- All tests pass
- Run full test suite to verify no regressions

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking application startup | Maintain identical default values |
| Test environment pollution | Use monkeypatch for env var isolation |
| Health service constructor change | Make check_interval Optional with None default |

---

## Definition of Done Checklist

- [ ] database.py uses Config.db_connect_args
- [ ] main.py uses Config.ui_theme and ui_appearance
- [ ] health_service.py uses Config.health_check_interval as default
- [ ] No hard-coded configuration values remain in updated files
- [ ] All new unit tests pass
- [ ] All existing tests pass (no regressions)
- [ ] Application starts correctly with no environment variables
- [ ] Environment variable overrides work for all properties

---

## Review Guidance

**Reviewers should verify**:
1. Hard-coded values completely removed from consumer files
2. Default behavior identical to before (backward compatibility)
3. Config singleton used correctly (via get_config())
4. Tests cover defaults, overrides, and invalid values
5. Test isolation via monkeypatch (no env var leakage)
6. Health service constructor gracefully handles None vs explicit value

---

## Activity Log

- 2026-02-03T02:58:47Z – system – lane=planned – Prompt created.
