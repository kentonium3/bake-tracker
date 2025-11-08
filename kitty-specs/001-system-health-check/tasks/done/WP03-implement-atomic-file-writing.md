---
work_package_id: WP03
title: Implement Atomic File Writing
subtasks: [T015, T016, T017, T018, T019, T020, T021, T022]
lane: planned
priority: P1
dependencies: [WP01]
---

# WP03: Implement Atomic File Writing

## Objective
Add atomic file writing using write-to-temp-and-rename pattern.

## Implementation
Add `_write_health_status()` to health_service.py:

```python
def _write_health_status(self, status_data: Dict) -> bool:
    try:
        tmp_file = self._health_file.with_suffix('.json.tmp')
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)
        tmp_file.rename(self._health_file)  # Atomic on most systems
        return True
    except (IOError, OSError) as e:
        self._logger.error(f"Failed to write health file: {e}")
        return False
```

Call from `_health_check_loop()`:
```python
self._write_health_status(status_data)
```

## Definition of Done
- [ ] Writes to data/health.json
- [ ] Uses atomic write-and-rename
- [ ] Handles write errors gracefully
- [ ] Unit tests pass (WP07)
