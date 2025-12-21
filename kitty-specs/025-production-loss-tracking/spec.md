# Feature Specification: Production Loss Tracking

**Feature Branch**: `025-production-loss-tracking`
**Created**: 2025-12-21
**Status**: Draft
**Input**: User description: "Track production losses (burnt, broken, contaminated) with cost accounting and reporting"
**Design Reference**: `docs/design/F025_production_loss_tracking.md`

## Problem Statement

Baked goods production involves real-world failures: items burn in the oven, cookies break during handling, ingredients are contaminated or dropped, and wrong ingredients may require batch discard. Currently, the application cannot distinguish between successful production and losses. When recording production, users can enter `actual_yield < expected_yield`, but:

1. No explicit tracking of what happened to the "missing" units
2. No loss categorization (burnt vs broken vs contaminated)
3. No cost accounting for waste
4. No analytics on loss trends or patterns
5. No clear path to remake lost items to fulfill event requirements

**User Impact:**
- Cannot answer "How much did we lose to burnt cookies this season?"
- Cannot identify problematic recipes with high loss rates
- Cannot track improvement efforts (e.g., "oven temperature adjustment reduced burnt batches")
- Inventory consumed but no record of where finished goods went
- Lost batches create shortfalls against event targets with no visibility

## Solution Overview

Add explicit production loss tracking that:
1. Enforces accounting for every planned unit (produced or lost)
2. Categorizes loss reasons for trend analysis
3. Calculates waste costs for financial reporting
4. Enables process improvement analytics
5. Facilitates remake workflow by showing shortfall against event targets

**Core Principle:** Use terminology of "loss" rather than "failure" - acknowledges that losses are a normal part of production ("shit happens").

**Remake Workflow:** When production results in losses, the Event Production Dashboard shows the shortfall against targets. User can then record additional production runs to make up the deficit. The system tracks both the lost batch and the replacement batch separately for complete cost accounting.

## User Scenarios & Testing

### User Story 1 - Record Production with Losses (Priority: P1)

As a baker, when I complete a batch with some items lost (burnt, broken, etc.), I want to record both the good items and the losses so my inventory accurately reflects what I actually produced and I have a record of what was lost.

**Why this priority**: This is the core functionality - without loss recording, no other features work. Every subsequent feature depends on having loss data captured.

**Independent Test**: Can be fully tested by recording a production run with losses and verifying: (1) inventory only increased by actual yield, (2) loss record created with category and quantity, (3) cost breakdown shows good vs lost items.

**Acceptance Scenarios**:

1. **Given** a recipe with expected yield of 24, **When** I record production with actual yield of 18 and select "Burnt" as loss category, **Then** the system records 18 good units to inventory, creates a loss record for 6 units with "burnt" category, and shows cost breakdown for both.

2. **Given** a recipe with expected yield of 24, **When** I record production with actual yield of 0 (total loss), **Then** the system records 0 units to inventory, creates a loss record for 24 units, and marks production as "Total Loss".

3. **Given** a recipe with expected yield of 24, **When** I record production with actual yield of 24, **Then** the system records 24 good units to inventory, creates no loss record, and marks production as "Complete".

4. **Given** I am recording production with losses, **When** I enter actual yield of 30 (exceeds expected 24), **Then** the system prevents recording and shows validation error.

---

### User Story 2 - View Production History with Loss Information (Priority: P1)

As a baker, I want to see loss information in my production history so I can quickly identify which batches had problems and what type of problems occurred.

**Why this priority**: Essential for user awareness - without visibility into past losses, the user cannot learn from history or identify patterns.

**Independent Test**: Can be fully tested by viewing production history and verifying loss quantity and status columns display correctly with visual differentiation for partial/total loss entries.

**Acceptance Scenarios**:

1. **Given** production runs exist with various statuses (complete, partial loss, total loss), **When** I view production history, **Then** I see columns for loss quantity and status with clear visual indicators for each status type.

2. **Given** a production run with partial loss (6 of 24 lost), **When** I view production history, **Then** that row shows "6" in the loss column and "Partial Loss" status with visual indicator.

3. **Given** a production run with no losses, **When** I view production history, **Then** that row shows "-" in the loss column and "Complete" status.

---

### User Story 3 - Auto-Calculate Loss Quantity (Priority: P1)

As a baker, I want the system to automatically calculate how many items were lost based on my actual yield so I don't have to do mental math and can't make accounting errors.

**Why this priority**: Enforces data integrity and reduces user burden. The constraint that actual_yield + loss_quantity = expected_yield must be system-enforced.

**Independent Test**: Can be fully tested by changing batch count and actual yield values and verifying loss quantity updates automatically and correctly.

**Acceptance Scenarios**:

1. **Given** I'm recording production with expected yield of 48 (2 batches), **When** I enter actual yield of 40, **Then** the loss quantity field shows "8" and is read-only (auto-calculated).

2. **Given** I'm recording production, **When** I change batch count from 2 to 3, **Then** expected yield updates and loss quantity recalculates based on new expected vs actual.

---

### User Story 4 - Capture Loss Details (Priority: P2)

As a baker, I want to optionally record why items were lost (burnt, broken, contaminated, etc.) so I can later analyze what types of problems occur most often.

**Why this priority**: Enables analytics and process improvement, but the core recording works without detailed categorization (can default to "Other").

**Independent Test**: Can be fully tested by recording a loss with a specific category and notes, then verifying the data is stored and retrievable.

**Acceptance Scenarios**:

1. **Given** I'm recording production with losses, **When** I check "Record loss details", **Then** I see a dropdown for loss category (Burnt, Broken, Contaminated, Dropped, Wrong Ingredients, Other) and a notes field.

2. **Given** I'm recording production with losses, **When** I don't check "Record loss details", **Then** the loss is recorded with category "Other" and no notes.

3. **Given** I'm recording production with losses and have selected "Burnt" category, **When** I add notes "Oven temperature too high - check thermostat", **Then** both category and notes are saved with the loss record.

---

### User Story 5 - View Cost Breakdown (Priority: P2)

As a baker, I want to see the cost breakdown for good items vs lost items so I understand the financial impact of losses.

**Why this priority**: Provides immediate value visibility during recording, but core functionality works without it.

**Independent Test**: Can be fully tested by recording production with losses and verifying the cost summary shows accurate breakdown.

**Acceptance Scenarios**:

1. **Given** I'm recording production with 42 good units and 6 lost units at $0.30 per unit, **When** I view the cost summary, **Then** I see "Good units (42): $12.60" and "Lost units (6): $1.80" with total batch cost $14.40.

2. **Given** I'm recording production, **When** I change the actual yield, **Then** the cost breakdown updates in real-time.

---

### User Story 6 - Loss Summary Report (Priority: P3)

As a baker, I want to see a summary of all losses grouped by category so I can identify what types of problems occur most often.

**Why this priority**: Analytics feature - valuable for process improvement but not essential for core recording workflow.

**Independent Test**: Can be fully tested by recording multiple production runs with different loss categories, then viewing the loss summary report.

**Acceptance Scenarios**:

1. **Given** multiple production runs with losses across categories, **When** I view the loss summary, **Then** I see each category with total quantity lost, total cost of losses, and number of occurrences.

2. **Given** I want to analyze losses for a specific time period, **When** I filter by date range, **Then** the summary reflects only losses within that period.

---

### User Story 7 - Recipe Loss Rate Analysis (Priority: P3)

As a baker, I want to see which recipes have the highest loss rates so I can identify recipes that need process improvements.

**Why this priority**: Analytics feature - builds on core loss data to provide insights.

**Independent Test**: Can be fully tested by recording multiple production runs for the same recipe, then viewing recipe loss rate.

**Acceptance Scenarios**:

1. **Given** a recipe with multiple production runs totaling 72 expected and 60 actual, **When** I view recipe loss rate, **Then** I see loss rate of approximately 16.7% with total expected, actual, and loss quantities.

---

### Edge Cases

- What happens when user enters actual yield equal to expected yield? Loss quantity is 0, no loss record created, status is "Complete".
- What happens when user enters actual yield of 0? Total loss recorded, status is "Total Loss", inventory not increased.
- What happens when user enters actual yield greater than expected? Validation error prevents recording (yield cannot exceed expected).
- How are costs calculated for losses? Per-unit cost snapshot at production time, same as good units (ingredients consumed regardless of outcome).
- What happens to existing production data during migration? All historical records set to "Complete" status with 0 losses (historical loss data unavailable).

## Requirements

### Functional Requirements

**Recording:**
- **FR-001**: System MUST enforce that actual_yield + loss_quantity = expected_yield for every production run
- **FR-002**: System MUST auto-calculate loss_quantity as expected_yield - actual_yield
- **FR-003**: System MUST prevent recording when actual_yield exceeds expected_yield
- **FR-004**: System MUST determine production status automatically: COMPLETE (no loss), PARTIAL_LOSS (some loss), TOTAL_LOSS (all lost)
- **FR-005**: System MUST update finished unit inventory by actual_yield only (not expected_yield)
- **FR-006**: System MUST create a loss record when loss_quantity > 0
- **FR-007**: System MUST require loss category when loss_quantity > 0 (default to "Other" if not specified)

**Loss Categories:**
- **FR-008**: System MUST support fixed loss categories: Burnt, Broken, Contaminated, Dropped, Wrong Ingredients, Other
- **FR-009**: System MUST allow optional free-text notes for loss details

**Cost Accounting:**
- **FR-010**: System MUST snapshot per-unit cost at production time for loss records
- **FR-011**: System MUST calculate total_loss_cost as loss_quantity * per_unit_cost
- **FR-012**: System MUST display cost breakdown (good vs lost) during production recording

**History & Reporting:**
- **FR-013**: Production history MUST display loss quantity and production status columns
- **FR-014**: Production history MUST visually differentiate complete, partial loss, and total loss entries
- **FR-015**: System MUST provide loss summary grouped by category with quantity, cost, and occurrence count
- **FR-016**: System MUST provide recipe-level loss rate analysis

**Data Integrity:**
- **FR-017**: System MUST preserve loss records when production run is deleted (audit trail)
- **FR-018**: System MUST migrate existing production data to COMPLETE status with 0 losses

### Key Entities

- **ProductionRun (Enhanced)**: Existing entity with added loss tracking fields - production status, loss quantity, loss notes
- **ProductionLoss**: New entity recording detailed loss information - links to production run and finished unit, captures quantity, category, per-unit cost snapshot, total loss cost, and optional notes

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can record production with losses in under 30 seconds additional time compared to current workflow
- **SC-002**: 100% of production runs have complete accounting (actual_yield + loss_quantity = expected_yield)
- **SC-003**: Users can identify their top 3 loss categories within 10 seconds of viewing the loss summary
- **SC-004**: Users can see recipe loss rates to identify high-loss recipes for process improvement
- **SC-005**: Event production shortfalls (caused by losses) are visible in existing Event Dashboard
- **SC-006**: Loss data enables answering "How much did we lose to burnt cookies this season?" with a single report view

## Scope

### In Scope

- Schema changes to ProductionRun for loss tracking fields
- New ProductionLoss entity for detailed loss records
- Service layer updates to accept and validate loss parameters
- UI updates to RecordProductionDialog for loss input and cost display
- Production history table updates for loss visibility
- Loss summary and recipe loss rate reporting
- Data migration for existing production records

### Out of Scope

- Assembly loss tracking (future feature - same pattern applies)
- Predictive loss warnings based on historical patterns
- Loss recovery tracking (e.g., burnt cookies become crumbs for crust)
- Partial ingredient consumption tracking (assumes proportional loss)
- Automatic remake scheduling (system shows shortfall, user decides when to remake)
- Custom user-defined loss categories (fixed enum with "Other" handles edge cases)
- Historical loss backfilling (migration sets all historical to COMPLETE/0 loss)
- Per-batch granularity for multi-batch runs (aggregate loss per production run)

## Assumptions

- Users will accept that historical production data will be migrated as "Complete" with no losses (historical loss data unavailable)
- The fixed set of loss categories (Burnt, Broken, Contaminated, Dropped, Wrong Ingredients, Other) is sufficient; "Other" with notes handles edge cases
- Loss tracking adds minimal friction to the production recording workflow (optional details section)
- Per-unit cost at production time is the appropriate basis for loss cost calculation (same as good units)
- Aggregate loss tracking per production run is sufficient (no need for per-batch granularity within a multi-batch run)

## Dependencies

- **Feature 013**: Production & Inventory Tracking (FIFO consumption, cost calculation) - foundational
- **Feature 014**: Production UI (RecordProductionDialog foundation) - UI to enhance
- **Feature 016**: Event-Centric Production Model (event linkage, targets) - remake workflow visibility
