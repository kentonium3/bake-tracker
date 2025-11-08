---
work_package_id: WP08
title: Integration Test - Full Cycle
subtasks: [T052, T053, T054, T055, T056, T057, T058]
lane: planned
priority: P1
dependencies: [WP01, WP02, WP03, WP04, WP05]
---

# WP08: Integration Test

End-to-end test with real database:
- Start service
- Verify file created
- Wait for second cycle
- Disconnect DB, verify degraded
- Reconnect, verify online
- Stop service, verify cleanup
