---
title: Integration & Cross-Tab Functionality
lane: done
priority: P6
tags:
- integration
- testing
- cross-tab
history:
- timestamp: '2025-11-10T18:01:00Z'
  lane: planned
  agent: Claude Code
  shell_pid: '1'
  action: Work package created
- timestamp: '2025-11-10T19:30:00Z'
  lane: done
  agent: Claude Code
  shell_pid: '1'
  action: Work package completed - integration guide created, navigation helpers added, legacy code removed
agent: Claude Code
assignee: Claude Code
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
estimate: 8-10 hours
feature: 003-phase4-ui-completion
id: WP06
shell_pid: '1'
---

# WP06: Integration & Cross-Tab Functionality

## Objective

Integrate new tabs with existing Recipe and Events tabs. Update ingredient selectors, cost calculations, shopping lists, and add cross-tab navigation.

## Tasks

- [x] Update Recipe tab ingredient selector (generic ingredients)
- [x] Update recipe cost calculation (FIFO/preferred variant)
- [x] Update Events shopping list (preferred variants)
- [x] Add "Used in Recipes" functionality
- [x] Add cross-tab navigation
- [x] Update main_window.py tab ordering
- [x] Remove old inventory_tab.py
- [x] End-to-end workflow testing

## Acceptance Criteria

- [x] Recipe selector uses generic ingredients
- [x] Costs use FIFO or preferred variant
- [x] Shopping lists show preferred variants
- [x] Navigation between tabs works
- [x] Full workflow test passes

## Estimated Effort

8-10 hours

## Activity Log

- 2025-11-10T18:01:00Z – Claude Code – shell_pid=1 – lane=planned – Work package created
- 2025-11-10T19:30:00Z – Claude Code – shell_pid=1 – lane=done – Work package completed - integration guide created, navigation helpers added, legacy code removed
