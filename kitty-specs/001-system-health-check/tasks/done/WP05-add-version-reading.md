---
work_package_id: WP05
title: Add Version Reading from pyproject.toml
subtasks: [T029, T030, T031, T032, T033, T034, T035]
lane: planned
priority: P2
dependencies: [WP01]
---

# WP05: Add Version Reading

## Implementation
Add to `__init__()`:
```python
self._app_version = self._get_app_version()
```

Add method:
```python
def _get_app_version(self) -> str:
    try:
        import tomllib
        toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(toml_path, 'rb') as f:
            data = tomllib.load(f)
        return data['project']['version']
    except Exception as e:
        self._logger.warning(f"Could not read version: {e}")
        return "unknown"
```

## Definition of Done
- [ ] Reads "0.1.0" from pyproject.toml
- [ ] Falls back to "unknown" on error
