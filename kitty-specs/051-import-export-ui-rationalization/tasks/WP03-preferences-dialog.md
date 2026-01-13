---
work_package_id: "WP03"
subtasks:
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Preferences Dialog"
phase: "Phase 1 - Dependent Services"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-13T12:55:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Preferences Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create a UI dialog for configuring directory preferences, accessible via File > Preferences menu.

**Success Criteria**:
- `preferences_dialog.py` exists with directory picker UI
- Dialog accessible from File > Preferences menu
- Changes persist to app_config via preferences_service
- Restore Defaults button works correctly

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/051-import-export-ui-rationalization/spec.md` (US6 - Configurable Directories)
- Plan: `kitty-specs/051-import-export-ui-rationalization/plan.md`

**Dependencies**:
- WP02 (preferences_service) must be complete

**Architecture Constraints**:
- Use CustomTkinter for UI
- Follow existing dialog patterns (ImportDialog, ExportDialog)
- Modal behavior (transient, grab_set)

**Existing Patterns**:
- `src/ui/import_export_dialog.py` - dialog structure, button layout
- `src/ui/main_window.py` - menu setup (verify location)

## Subtasks & Detailed Guidance

### Subtask T015 - Create preferences_dialog.py with dialog structure
- **Purpose**: Establish dialog class with CustomTkinter
- **Steps**:
  1. Create `src/ui/preferences_dialog.py`
  2. Import `customtkinter as ctk`, `filedialog`, `messagebox`
  3. Import `preferences_service`
  4. Create `PreferencesDialog(ctk.CTkToplevel)` class
  5. Initialize with parent, title "Preferences", geometry ~500x400
  6. Set modal behavior: `self.transient(parent)`, `self.grab_set()`
  7. Center on parent
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: No (establishes structure)
- **Notes**: Follow ImportDialog pattern in `import_export_dialog.py`

### Subtask T016 - Add Import directory picker
- **Purpose**: UI for configuring import directory
- **Steps**:
  1. Add labeled frame "Import Directory"
  2. Add entry field (readonly) showing current path
  3. Add "Browse..." button that opens `filedialog.askdirectory()`
  4. Initialize entry with `preferences_service.get_import_directory()`
  5. Store selected path in instance variable for save
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: No (establishes pattern)
- **Notes**: Use CTkEntry with state="readonly"

### Subtask T017 - Add Export directory picker
- **Purpose**: UI for configuring export directory
- **Steps**:
  1. Add labeled frame "Export Directory"
  2. Add entry field and Browse button (same pattern as T016)
  3. Initialize with `preferences_service.get_export_directory()`
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: Yes (once T016 pattern exists)
- **Notes**: Copy/adapt T016 implementation

### Subtask T018 - Add Logs directory picker
- **Purpose**: UI for configuring logs directory
- **Steps**:
  1. Add labeled frame "Logs Directory"
  2. Add entry field and Browse button (same pattern as T016)
  3. Initialize with `preferences_service.get_logs_directory()`
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: Yes (once T016 pattern exists)
- **Notes**: May want to add note about write permission requirement

### Subtask T019 - Add Restore Defaults button
- **Purpose**: Allow user to reset all preferences
- **Steps**:
  1. Add "Restore Defaults" button (left side of button bar)
  2. On click, show confirmation dialog
  3. If confirmed, call `preferences_service.reset_all_preferences()`
  4. Refresh all entry fields with new defaults
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: No (after directory pickers)
- **Notes**: Confirmation prevents accidental reset

### Subtask T020 - Add Save/Cancel buttons with validation
- **Purpose**: Persist changes or cancel dialog
- **Steps**:
  1. Add button frame at bottom (right side)
  2. Add "Cancel" button that destroys dialog
  3. Add "Save" button that:
     - Validates all directories exist
     - Shows warning if any directory missing/invalid
     - Calls set_*() for each preference
     - Destroys dialog on success
  4. Bind Escape key to cancel
- **Files**: `src/ui/preferences_dialog.py`
- **Parallel?**: No (after pickers)
- **Notes**: Validate before save; show specific error if directory invalid

### Subtask T021 - Add Preferences menu item to File menu
- **Purpose**: Make dialog accessible from main menu
- **Steps**:
  1. Find menu setup (likely `src/ui/main_window.py`)
  2. Add "Preferences..." item to File menu
  3. Position after existing items, before "Exit" if present
  4. Handler opens PreferencesDialog(self)
  5. Import preferences_dialog module
- **Files**: `src/ui/main_window.py` (or equivalent)
- **Parallel?**: No (after dialog complete)
- **Notes**: Use ellipsis in menu item name per UI convention

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Menu file location unclear | Search for "Import Data" menu item to find pattern |
| Dialog doesn't refresh after reset | Explicitly update entry fields after reset |
| Directory validation race condition | Validate at save time, not browse time |

## Definition of Done Checklist

- [ ] `src/ui/preferences_dialog.py` created
- [ ] Three directory pickers (Import, Export, Logs) functional
- [ ] Browse buttons open directory picker and update display
- [ ] Restore Defaults button resets all preferences
- [ ] Save validates and persists preferences
- [ ] Cancel closes without saving
- [ ] File > Preferences menu item opens dialog
- [ ] Manual test: set preferences, close app, reopen, verify persisted

## Review Guidance

**Key checkpoints**:
1. Open File > Preferences and verify dialog appears
2. Browse to new directory, verify entry updates
3. Save, close app, reopen - preferences should persist
4. Test Restore Defaults returns to system defaults
5. Test Cancel doesn't save partial changes

## Activity Log

- 2026-01-13T12:55:00Z - system - lane=planned - Prompt created.
- 2026-01-13T18:50:46Z – claude – lane=doing – Starting implementation of Preferences Dialog
- 2026-01-13T18:54:08Z – claude – lane=for_review – Implemented Preferences dialog with directory pickers and File > Preferences menu item
- 2026-01-13T20:57:03Z – claude – lane=done – Code review APPROVED by claude - Preferences dialog accessible via File > Preferences, directory pickers work, Restore Defaults implemented
