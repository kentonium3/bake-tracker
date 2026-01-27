# Tasks: Inventory Gap Analysis (F075)

**Feature**: 075-inventory-gap-analysis
**Created**: 2026-01-27
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Overview

This feature creates an inventory gap analysis service that compares F074's aggregated ingredient totals against current inventory to generate a shopping list.

**Total Subtasks**: 13
**Work Packages**: 2

## Work Packages

### WP01: Service Foundation & Gap Calculation

**Goal**: Create the inventory gap service with dataclasses and core gap calculation logic.

**Priority**: P1 (Foundation)
**Dependencies**: None (but requires F074 merged to main)
**Estimated Size**: ~350 lines

**Subtasks**:
- [x] T001: Create GapItem dataclass
- [x] T002: Create GapAnalysisResult dataclass
- [x] T003: Create inventory_gap_service.py skeleton with session pattern
- [x] T004: Implement inventory lookup helper (ingredient_id → slug → inventory)
- [x] T005: Implement gap calculation logic
- [x] T006: Implement analyze_inventory_gaps() main function
- [x] T007: Implement result partitioning (purchase vs sufficient)

**Implementation Notes**:
- Follow session=None pattern from CLAUDE.md
- Consume F074's aggregate_ingredients_for_event() output
- Query inventory via get_total_quantity(slug) after looking up slug from ingredient_id
- Match units exactly (no conversion)
- Treat missing inventory as zero

**Prompt File**: [tasks/WP01-service-foundation.md](tasks/WP01-service-foundation.md)

---

### WP02: Unit Tests

**Goal**: Write comprehensive unit tests for the gap analysis service.

**Priority**: P1 (Quality)
**Dependencies**: WP01
**Estimated Size**: ~300 lines

**Subtasks**:
- [x] T008: Write test: gap calculation with shortfall
- [x] T009: Write test: gap calculation with sufficient inventory
- [x] T010: Write test: missing inventory treated as zero
- [x] T011: Write test: all items categorized
- [ ] T012: Write test: empty event returns empty
- [ ] T013: Write test: unit mismatch treated as zero

**Implementation Notes**:
- Reuse F074 test fixtures (Event, Recipe, Ingredient, etc.)
- Add InventoryItem/Product fixtures for inventory levels
- Test edge cases explicitly
- Verify gap = max(0, needed - on_hand)

**Prompt File**: [tasks/WP02-unit-tests.md](tasks/WP02-unit-tests.md)

---

## Parallelization Opportunities

- WP01 and WP02 are sequential (WP02 depends on WP01)
- Within WP02, all tests are parallelizable (marked [P])

## MVP Scope

WP01 delivers the core service. WP02 adds test coverage for quality assurance.

Both WPs are required for feature completion.
