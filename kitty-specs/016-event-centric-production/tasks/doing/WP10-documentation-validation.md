---
work_package_id: "WP10"
subtasks:
  - "T054"
  - "T055"
  - "T056"
  - "T057"
  - "T058"
title: "Documentation & Validation"
phase: "Phase 8 - Documentation & Final"
lane: "doing"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-10T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP10 - Documentation & Validation

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Update documentation and verify all acceptance criteria met.

**Success Criteria**:
- CLAUDE.md updated with event-centric model description
- Feature roadmap updated to mark Feature 016 complete
- Migration dry-run test passes
- All acceptance criteria from spec verified
- Full workflow tested end-to-end

## Context & Constraints

**Reference Documents**:
- `kitty-specs/016-event-centric-production/spec.md` - User Stories, Success Criteria
- `CLAUDE.md` - Project documentation
- `docs/feature_roadmap.md` - Feature tracking

**Dependencies**: All previous work packages (WP01-WP09)

---

## Subtasks & Detailed Guidance

### Subtask T054 - Update CLAUDE.md with event-centric model description

**Purpose**: Document the event-production linkage for future reference.

**Steps**:
1. Open `CLAUDE.md`
2. Find "Key Design Decisions" section
3. Add new entry:
   ```markdown
   - **Event-Centric Production Model**: ProductionRun and AssemblyRun link to Events via optional `event_id` FK. This enables: (1) tracking which production is for which event, (2) explicit production targets per event via EventProductionTarget/EventAssemblyTarget, (3) progress tracking (produced vs target), (4) package fulfillment status workflow (pending/ready/delivered). See `docs/design/schema_v0.6_design.md`.
   ```
4. Verify formatting and placement

**Files**: `CLAUDE.md`
**Parallel?**: No
**Notes**: Keep description concise but complete.

---

### Subtask T055 - Update feature_roadmap.md

**Purpose**: Mark Feature 016 as complete.

**Steps**:
1. Open `docs/feature_roadmap.md`
2. Find Feature 016 entry (or add if missing)
3. Update status to COMPLETE:
   ```markdown
   ### Feature 016: Event-Centric Production Model
   **Status**: COMPLETE
   **Branch**: 016-event-centric-production
   **Completed**: 2025-12-XX

   Adds event-production linkage for progress tracking:
   - event_id FK on ProductionRun and AssemblyRun
   - EventProductionTarget and EventAssemblyTarget tables
   - Fulfillment status workflow on EventRecipientPackage
   - Targets tab in Event Detail window
   - Event selector in production/assembly dialogs
   ```

**Files**: `docs/feature_roadmap.md`
**Parallel?**: Yes (can proceed with T054)
**Notes**: Use actual completion date.

---

### Subtask T056 - Perform export/import migration dry-run test

**Purpose**: Verify data migration works correctly.

**Steps**:
1. Ensure test data exists:
   - At least one event
   - Production targets for that event
   - Production runs attributed to the event
   - Package assignments with various statuses
2. Export all data:
   ```python
   # Via app: Menu -> Data -> Export All
   # Or via service: import_export_service.export_all("backup.json")
   ```
3. Backup the export file
4. Delete the database file (`bake_tracker.db`)
5. Start the application (creates new schema)
6. Import the backup:
   ```python
   # Via app: Menu -> Data -> Import
   # Or via service: import_export_service.import_all("backup.json")
   ```
7. Verify all data:
   - [ ] Events restored
   - [ ] Production targets restored with correct event/recipe links
   - [ ] Assembly targets restored with correct event/finished_good links
   - [ ] Production runs have correct event_id
   - [ ] Assembly runs have correct event_id
   - [ ] Package fulfillment statuses preserved
8. Verify UI:
   - [ ] Targets tab shows correct progress
   - [ ] Assignments show correct fulfillment status

**Files**: N/A (testing procedure)
**Parallel?**: No
**Notes**: This is the critical migration safety test.

---

### Subtask T057 - Verify all acceptance criteria from spec.md

**Purpose**: Ensure feature meets all requirements.

**Verification Checklist** (from spec.md):

**User Story 1 - Link Production to Event**:
- [ ] Record Production dialog has "For Event" dropdown
- [ ] Events listed with "(None - standalone)" option
- [ ] Production run gets correct event_id when event selected
- [ ] Production run has event_id = NULL when standalone

**User Story 2 - Link Assembly to Event**:
- [ ] Record Assembly dialog has "For Event" dropdown
- [ ] Assembly run gets correct event_id when event selected
- [ ] Assembly run has event_id = NULL when standalone

**User Story 3 - Set Production Targets**:
- [ ] Targets tab visible in Event Detail
- [ ] "Add Production Target" button works
- [ ] Can select recipe and specify batch count
- [ ] Target persists to database
- [ ] Duplicate target for same recipe prevented

**User Story 4 - Set Assembly Targets**:
- [ ] "Add Assembly Target" button works
- [ ] Can select finished good and specify quantity
- [ ] Duplicate target for same finished good prevented

**User Story 5 - View Production Progress**:
- [ ] Progress shows: Recipe name, Target, Produced, Percentage, Progress bar
- [ ] 50% shows half-filled bar and "2/4 (50%)"
- [ ] 100%+ shows full bar, checkmark, actual percentage
- [ ] Only event-attributed runs counted (not standalone)

**User Story 6 - View Assembly Progress**:
- [ ] Progress shows for assembly targets
- [ ] Over-completion displayed correctly

**User Story 7 - Track Fulfillment Status**:
- [ ] Status column in assignments
- [ ] pending -> ready transition works
- [ ] ready -> delivered transition works
- [ ] delivered is terminal (no further changes)
- [ ] Changes persist immediately

**User Story 8 - Event Progress Summary**:
- [ ] Summary tab shows overall progress
- [ ] Production complete indicator
- [ ] Assembly complete indicator
- [ ] Package status counts

**Success Criteria** (from spec.md):
- [ ] SC-001: Production/assembly runs can link to events
- [ ] SC-002: Targets set in < 60 seconds
- [ ] SC-003: Progress viewable within 2 clicks
- [ ] SC-004: Progress percentages calculated correctly
- [ ] SC-005: Over-production displayed correctly
- [ ] SC-006: Fulfillment changes persist immediately
- [ ] SC-007: Sequential workflow enforced
- [ ] SC-008: Migration preserves existing data
- [ ] SC-009: Import/export round-trip works

**Files**: N/A (verification procedure)
**Parallel?**: No
**Notes**: Check off each item as verified.

---

### Subtask T058 - Final manual testing walkthrough

**Purpose**: Complete end-to-end workflow test.

**Steps**:
1. **Setup Test Event**:
   - Create or select event "Test Event 2025"
2. **Set Targets**:
   - Add production target: "Test Recipe" - 4 batches
   - Add assembly target: "Test Gift Box" - 10 units
3. **Record Production**:
   - Record 2 batches of Test Recipe for Test Event
   - Verify Targets tab shows 2/4 (50%)
4. **Record More Production**:
   - Record 3 more batches (total 5)
   - Verify Targets tab shows 5/4 (125%) with checkmark
5. **Record Assembly**:
   - Record 5 Test Gift Boxes for Test Event
   - Verify 5/10 (50%) progress
6. **Update Fulfillment Status**:
   - Find package assignment
   - Change status: pending -> ready
   - Change status: ready -> delivered
   - Verify delivered is terminal
7. **Check Summary**:
   - View Summary tab
   - Verify production complete indicator
   - Verify package status counts
8. **Export/Import Test**:
   - Export all data
   - Verify export includes all new fields
9. **Cleanup** (optional):
   - Delete test data or keep for reference

**Files**: N/A (testing procedure)
**Parallel?**: No
**Notes**: Document any issues found.

---

## Test Strategy

**Comprehensive Testing**:
- Migration dry-run (T056)
- Acceptance criteria verification (T057)
- End-to-end workflow (T058)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Missing acceptance criteria | Systematic checklist review |
| Migration issues | Backup before testing |
| Documentation outdated | Review all changed files |

---

## Definition of Done Checklist

- [ ] CLAUDE.md updated
- [ ] feature_roadmap.md updated
- [ ] Migration dry-run successful
- [ ] All acceptance criteria verified
- [ ] End-to-end testing complete
- [ ] All tests pass: `pytest src/tests -v`
- [ ] No regressions in existing functionality
- [ ] `tasks.md` updated with status change

---

## Review Guidance

**Reviewers should verify**:
1. Documentation accurately describes feature
2. All acceptance criteria have been tested
3. Migration test was performed and passed
4. No regression in existing features
5. Feature is ready for merge

---

## Activity Log

- 2025-12-10T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-11T17:42:00Z – system – shell_pid= – lane=doing – Started documentation and validation
