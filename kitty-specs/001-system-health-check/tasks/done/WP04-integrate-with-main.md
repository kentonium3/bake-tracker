---
work_package_id: WP04
title: Integrate with Main Application
subtasks: [T023, T024, T025, T026, T027, T028]
lane: planned
priority: P1
dependencies: [WP01, WP02, WP03]
---

# WP04: Integrate Health Service with Main Application

## Objective
Initialize and start health service in src/main.py.

## Implementation
1. Import: `from src.services.health_service import HealthCheckService`
2. In `initialize_application()`, after database init:
   ```python
   # Initialize health check service
   global _health_service
   _health_service = HealthCheckService()
   _health_service.start()
   print("Health check service started")
   ```
3. In `main()`, add cleanup:
   ```python
   finally:
       if '_health_service' in globals():
           _health_service.stop()
   ```

## Definition of Done
- [ ] Service starts with application
- [ ] Service stops on exit
- [ ] data/health.json created on startup
- [ ] File updates every 30 seconds
