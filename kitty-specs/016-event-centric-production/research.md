# Research: Event-Centric Production Model

**Feature**: 016-event-centric-production
**Date**: 2025-12-10
**Status**: Complete

## Research Summary

This document captures research findings for implementing event-production linkage in the bake-tracker application.

---

## 1. Existing Codebase Analysis

### 1.1 Models Requiring Modification

| Model | File | Changes Required |
|-------|------|------------------|
| ProductionRun | `src/models/production_run.py` | Add `event_id` FK (nullable), add `event` relationship |
| AssemblyRun | `src/models/assembly_run.py` | Add `event_id` FK (nullable), add `event` relationship |
| Event | `src/models/event.py` | Add relationships: `production_runs`, `assembly_runs`, `production_targets`, `assembly_targets` |
| EventRecipientPackage | `src/models/event.py` | Add `fulfillment_status` column |

### 1.2 New Models Required

| Model | Location | Purpose |
|-------|----------|---------|
| EventProductionTarget | `src/models/event.py` | Store recipe batch targets for events |
| EventAssemblyTarget | `src/models/event.py` | Store finished good quantity targets for events |
| FulfillmentStatus | `src/models/event.py` | Enum for package workflow states |

### 1.3 Services Requiring Modification

| Service | File | Changes Required |
|---------|------|------------------|
| BatchProductionService | `src/services/batch_production_service.py` | Add `event_id` parameter to `record_batch_production()` |
| AssemblyService | `src/services/assembly_service.py` | Add `event_id` parameter to `record_assembly()` |
| EventService | `src/services/event_service.py` | Add 12 new methods for targets, progress, fulfillment |
| ImportExportService | `src/services/import_export_service.py` | Add new entities and fields to export/import |

### 1.4 UI Components Requiring Modification

| Component | File | Changes Required |
|-----------|------|------------------|
| RecordProductionDialog | `src/ui/forms/record_production_dialog.py` | Add event selector dropdown |
| RecordAssemblyDialog | `src/ui/forms/record_assembly_dialog.py` | Add event selector dropdown |
| EventDetailWindow | `src/ui/event_detail_window.py` | Add Targets tab with progress display |

---

## 2. Design Decisions

### 2.1 Schema Design Simplification

**Decision**: Follow `docs/design/schema_v0.6_design.md` with minor adjustments from planning.

**Adjustments**:
1. Event deletion cascade behavior changed from SET NULL to RESTRICT per user decision
2. No auto-suggestion of targets from packages (manual-only per user decision)
3. Sequential fulfillment workflow enforced (pending → ready → delivered)

### 2.2 Event Selector Ordering

**Decision**: Events ordered by `event_date` ascending (nearest upcoming first)

**Rationale**: Users recording production for an event will most likely be working on the nearest upcoming event. This reduces clicks and cognitive load.

### 2.3 Progress Display

**Decision**: CTkProgressBar + adjacent text label showing "X/Y (Z%)"

**Rationale**: Visual progress bar provides quick scanning, text label provides exact numbers. CustomTkinter's built-in CTkProgressBar is sufficient without custom widget.

**Implementation**:
```python
# Progress row in Targets tab
progress_frame = ctk.CTkFrame(parent)
progress_bar = ctk.CTkProgressBar(progress_frame, width=100)
progress_bar.set(0.5)  # 50%
progress_label = ctk.CTkLabel(progress_frame, text="2/4 (50%)")
```

### 2.4 Target Table Location

**Decision**: Define EventProductionTarget and EventAssemblyTarget in `src/models/event.py` alongside Event model.

**Rationale**: These are tightly coupled to Event with cascade delete behavior. Keeping them together improves code organization and makes relationships clearer.

### 2.5 Fulfillment Status Implementation

**Decision**: Add FulfillmentStatus enum and `fulfillment_status` column to EventRecipientPackage.

**Note**: This is separate from the existing `status` column which uses PackageStatus enum. The new field tracks the workflow state for this feature specifically.

**Sequential Workflow Enforcement**:
- pending → ready (only valid next state)
- ready → delivered (only valid next state)
- delivered → (terminal, no more transitions)

---

## 3. Migration Strategy

### 3.1 Approach

**Decision**: Export/recreate/import (established pattern)

**Steps**:
1. Export all data using existing `import_export_service.export_all()`
2. Update models with new columns/tables
3. Delete SQLite database file
4. Restart app (SQLAlchemy creates new schema)
5. Import data (new columns get defaults)

### 3.2 Default Values for Existing Data

| Column | Default Value |
|--------|---------------|
| ProductionRun.event_id | NULL (standalone) |
| AssemblyRun.event_id | NULL (standalone) |
| EventRecipientPackage.fulfillment_status | 'pending' |

### 3.3 Cascade/Restrict Behavior

| Parent Delete | Child Behavior |
|---------------|----------------|
| Event deleted | EventProductionTarget CASCADE deleted |
| Event deleted | EventAssemblyTarget CASCADE deleted |
| Event deleted | ProductionRun/AssemblyRun RESTRICT (block delete) |
| Recipe deleted | EventProductionTarget RESTRICT (block delete) |
| FinishedGood deleted | EventAssemblyTarget RESTRICT (block delete) |

---

## 4. Technical Findings

### 4.1 Existing Event Detail Window Structure

The current EventDetailWindow has 4 tabs:
1. Assignments
2. Recipe Needs
3. Shopping List
4. Summary

New "Targets" tab should be inserted as position 2 (after Assignments, before Recipe Needs).

### 4.2 Service Method Signatures

**BatchProductionService.record_batch_production()** (lines 176-318):
- Current params: recipe_id, num_batches, actual_yield, notes, session
- Add: event_id: Optional[int] = None

**AssemblyService.record_assembly()** (lines 205-396):
- Current params: finished_good_id, quantity, assembled_at, notes, session
- Add: event_id: Optional[int] = None

### 4.3 Import/Export Considerations

Current import/export handles:
- Events, EventRecipientPackages (partial - no fulfillment_status yet)
- Does NOT handle ProductionRun/AssemblyRun

Feature 016 must add:
- ProductionRun with event_name (nullable)
- AssemblyRun with event_name (nullable)
- EventProductionTarget with event_name, recipe_name
- EventAssemblyTarget with event_name, finished_good_name
- fulfillment_status field in EventRecipientPackage

---

## 5. Constitution Compliance

### 5.1 Desktop Phase Checks

| Check | Status |
|-------|--------|
| Does this design block web deployment? | NO - Standard FK relationships |
| Is the service layer UI-independent? | YES - Services have no UI imports |
| Are business rules in services, not UI? | YES - Progress calc, status workflow in EventService |
| What's the web migration cost? | LOW - Services become API endpoints |

### 5.2 Principle Compliance

| Principle | Compliance |
|-----------|------------|
| I. User-Centric Design | YES - Solves real progress tracking need |
| II. Data Integrity | YES - Explicit targets, FK constraints |
| III. Future-Proof Schema | YES - Standard patterns, UUID support |
| IV. TDD | REQUIRED - Service tests before implementation |
| V. Layered Architecture | YES - Strict layer separation maintained |
| VI. Migration Safety | YES - Export/import with validation |

---

## 6. Risk Assessment

### 6.1 Low Risk Items
- Adding nullable FK to existing tables (no data loss)
- New target tables (clean addition)
- Service parameter additions (backward compatible with default None)

### 6.2 Medium Risk Items
- Event Detail Window tabbed structure may need refactoring if tabs not already using CTkTabview

### 6.3 Mitigations
- Verify Event Detail Window structure before UI implementation
- Write comprehensive service tests before UI integration
- Use export/import cycle to validate data preservation
