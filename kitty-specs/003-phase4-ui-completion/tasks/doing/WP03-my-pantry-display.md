---
id: WP03
title: My Pantry Tab - Inventory Display & Management
feature: 003-phase4-ui-completion
lane: planned
priority: P3
estimate: 12-15 hours
assignee: ""
agent: ""
shell_pid: ""
tags:
  - ui
  - pantry
  - customtkinter
dependencies:
  - WP02
history:
  - timestamp: "2025-11-10T18:01:00Z"
    lane: "planned"
    agent: ""
    shell_pid: ""
    action: "Work package created"
---

# WP03: My Pantry Tab - Inventory Display & Management

## Objective

Create My Pantry tab with inventory list view supporting aggregate and detail modes. Users can add, edit, delete pantry items and filter by location with expiration alerts.

## Tasks

- [ ] Create `src/ui/pantry_tab.py` with tab frame structure
- [ ] Implement view mode toggle (Aggregate vs Detail)
- [ ] Implement aggregate view (group by ingredient, show totals)
- [ ] Implement detail view (show individual pantry items)
- [ ] Add location filter dropdown
- [ ] Implement expiration alerts (yellow/red highlighting)
- [ ] Create "Add Pantry Item" form dialog
- [ ] Create "Edit Pantry Item" form dialog
- [ ] Implement delete with confirmation
- [ ] Add tab to main_window.py
- [ ] Test pantry CRUD through UI

## Acceptance Criteria

- [ ] User can view pantry in aggregate and detail modes
- [ ] Expiration alerts work (yellow < 14 days, red expired)
- [ ] Location filter works
- [ ] User can add/edit/delete pantry items
- [ ] FIFO ordering visible (oldest first)

## Estimated Effort

12-15 hours
