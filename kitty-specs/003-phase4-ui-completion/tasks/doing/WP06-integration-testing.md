---
id: WP06
title: Integration & Cross-Tab Functionality
feature: 003-phase4-ui-completion
lane: planned
priority: P6
estimate: 8-10 hours
assignee: ""
agent: ""
shell_pid: ""
tags:
  - integration
  - testing
  - cross-tab
dependencies:
  - WP01
  - WP02
  - WP03
  - WP04
  - WP05
history:
  - timestamp: "2025-11-10T18:01:00Z"
    lane: "planned"
    agent: ""
    shell_pid: ""
    action: "Work package created"
---

# WP06: Integration & Cross-Tab Functionality

## Objective

Integrate new tabs with existing Recipe and Events tabs. Update ingredient selectors, cost calculations, shopping lists, and add cross-tab navigation.

## Tasks

- [ ] Update Recipe tab ingredient selector (generic ingredients)
- [ ] Update recipe cost calculation (FIFO/preferred variant)
- [ ] Update Events shopping list (preferred variants)
- [ ] Add "Used in Recipes" functionality
- [ ] Add cross-tab navigation
- [ ] Update main_window.py tab ordering
- [ ] Remove old inventory_tab.py
- [ ] End-to-end workflow testing

## Acceptance Criteria

- [ ] Recipe selector uses generic ingredients
- [ ] Costs use FIFO or preferred variant
- [ ] Shopping lists show preferred variants
- [ ] Navigation between tabs works
- [ ] Full workflow test passes

## Estimated Effort

8-10 hours
