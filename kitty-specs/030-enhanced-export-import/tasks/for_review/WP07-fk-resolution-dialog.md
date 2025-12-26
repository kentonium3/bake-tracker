---
work_package_id: "WP07"
subtasks:
  - "T033"
  - "T034"
  - "T035"
  - "T036"
title: "FK Resolution Dialog"
phase: "Phase 3 - UI Integration"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-25T14:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - FK Resolution Dialog

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create UI dialog for interactive FK resolution during import.

**Success Criteria**:
1. FKResolutionDialog shows missing FK info with create/map/skip options
2. "Map to existing" shows fuzzy search dropdown
3. "Create new" shows entity-specific form
4. User cancellation prompts keep/rollback choice
5. Dialog follows existing CustomTkinter patterns

## Context & Constraints

**Owner**: Claude (Track B - Import)

**References**:
- `kitty-specs/030-enhanced-export-import/spec.md`: FR-016, FR-018, FR-019, FR-032, FR-033
- `src/ui/import_export_dialog.py`: Existing dialog patterns
- `src/ui/catalog_import_dialog.py`: Additional dialog examples
- WP04: fk_resolver_service.py for FKResolverCallback protocol

**Constraints**:
- MUST follow modal dialog patterns from existing dialogs
- MUST use CustomTkinter widgets
- MUST implement FKResolverCallback protocol

**Dependencies**: WP04 (FK Resolver Service)

## Subtasks & Detailed Guidance

### Subtask T033 - Create FKResolutionDialog

**Purpose**: Main dialog for FK resolution with three options.

**Steps**:
1. Create `src/ui/fk_resolution_dialog.py`
2. Implement FKResolutionDialog class:
   ```python
   class FKResolutionDialog(ctk.CTkToplevel):
       def __init__(self, parent, missing: MissingFK):
           super().__init__(parent)
           self.title("Resolve Missing Reference")
           self.missing = missing
           self.result: Optional[Resolution] = None

           self._setup_ui()

           # Modal behavior
           self.transient(parent)
           self.grab_set()
           self._center_on_parent(parent)

       def _setup_ui(self):
           # Info section
           info_label = ctk.CTkLabel(
               self,
               text=f"Missing {self.missing.entity_type}: '{self.missing.missing_value}'"
           )
           info_label.pack(pady=10)

           affected_label = ctk.CTkLabel(
               self,
               text=f"Affects {self.missing.affected_record_count} records"
           )
           affected_label.pack()

           # Option buttons
           btn_frame = ctk.CTkFrame(self)
           btn_frame.pack(pady=20)

           create_btn = ctk.CTkButton(btn_frame, text="Create New", command=self._on_create)
           create_btn.pack(side="left", padx=5)

           map_btn = ctk.CTkButton(btn_frame, text="Map to Existing", command=self._on_map)
           map_btn.pack(side="left", padx=5)

           skip_btn = ctk.CTkButton(btn_frame, text="Skip Records", command=self._on_skip)
           skip_btn.pack(side="left", padx=5)

           # Cancel button
           cancel_btn = ctk.CTkButton(self, text="Cancel Import", command=self._on_cancel)
           cancel_btn.pack(pady=10)
   ```

**Files**: `src/ui/fk_resolution_dialog.py`
**Parallel?**: No (foundation)

### Subtask T034 - Implement fuzzy search dropdown

**Purpose**: Show similar entities for "map to existing" option.

**Steps**:
1. Implement `_on_map()` method:
   ```python
   def _on_map(self):
       # Open map selection dialog
       map_dialog = MapEntityDialog(self, self.missing)
       self.wait_window(map_dialog)

       if map_dialog.selected_id:
           self.result = Resolution(
               choice=ResolutionChoice.MAP,
               entity_type=self.missing.entity_type,
               missing_value=self.missing.missing_value,
               mapped_id=map_dialog.selected_id
           )
           self.destroy()
   ```
2. Create MapEntityDialog:
   ```python
   class MapEntityDialog(ctk.CTkToplevel):
       def __init__(self, parent, missing: MissingFK):
           super().__init__(parent)
           self.title("Select Existing Entity")
           self.selected_id: Optional[int] = None

           # Search entry
           self.search_var = ctk.StringVar(value=missing.missing_value)
           search_entry = ctk.CTkEntry(self, textvariable=self.search_var)
           search_entry.pack(pady=10)
           search_entry.bind("<KeyRelease>", self._on_search)

           # Results listbox
           self.results_frame = ctk.CTkScrollableFrame(self)
           self.results_frame.pack(fill="both", expand=True)

           # Initial search
           self._do_search()
   ```
3. Use find_similar_entities from fk_resolver_service

**Files**: `src/ui/fk_resolution_dialog.py`
**Parallel?**: No

### Subtask T035 - Implement entity creation form

**Purpose**: Show form for creating new entity.

**Steps**:
1. Implement `_on_create()` method:
   ```python
   def _on_create(self):
       create_dialog = CreateEntityDialog(self, self.missing.entity_type, self.missing.missing_value)
       self.wait_window(create_dialog)

       if create_dialog.entity_data:
           self.result = Resolution(
               choice=ResolutionChoice.CREATE,
               entity_type=self.missing.entity_type,
               missing_value=self.missing.missing_value,
               created_entity=create_dialog.entity_data
           )
           self.destroy()
   ```
2. Create CreateEntityDialog with entity-specific forms:
   ```python
   class CreateEntityDialog(ctk.CTkToplevel):
       def __init__(self, parent, entity_type: str, default_value: str):
           super().__init__(parent)
           self.title(f"Create New {entity_type.title()}")
           self.entity_data: Optional[Dict] = None

           if entity_type == "supplier":
               self._setup_supplier_form(default_value)
           elif entity_type == "ingredient":
               self._setup_ingredient_form(default_value)
           elif entity_type == "product":
               self._setup_product_form(default_value)

       def _setup_supplier_form(self, default_name: str):
           # Name (pre-filled)
           ctk.CTkLabel(self, text="Name:").pack()
           self.name_var = ctk.StringVar(value=default_name)
           ctk.CTkEntry(self, textvariable=self.name_var).pack()

           # City, State, ZIP
           ctk.CTkLabel(self, text="City:").pack()
           self.city_var = ctk.StringVar()
           ctk.CTkEntry(self, textvariable=self.city_var).pack()
           # ... similar for state, zip

           # Create button
           ctk.CTkButton(self, text="Create", command=self._on_submit).pack(pady=10)
   ```

**Files**: `src/ui/fk_resolution_dialog.py`
**Parallel?**: No

### Subtask T036 - Handle user cancellation

**Purpose**: Prompt user about keeping or rolling back on cancel.

**Steps**:
1. Implement `_on_cancel()` method:
   ```python
   def _on_cancel(self):
       # Show confirmation dialog per spec clarification
       if self._records_already_imported > 0:
           response = messagebox.askyesnocancel(
               "Cancel Import",
               f"{self._records_already_imported} records have already been imported.\n\n"
               "Yes = Keep imported records, cancel remaining\n"
               "No = Rollback all changes\n"
               "Cancel = Continue import",
               icon="warning"
           )
           if response is True:  # Yes
               self.result = Resolution(
                   choice=ResolutionChoice.SKIP,
                   entity_type="__cancel_keep__",
                   missing_value=""
               )
               self.destroy()
           elif response is False:  # No
               self.result = Resolution(
                   choice=ResolutionChoice.SKIP,
                   entity_type="__cancel_rollback__",
                   missing_value=""
               )
               self.destroy()
           # else Cancel - do nothing, continue
       else:
           self.destroy()
   ```
2. Parent import service handles special __cancel_* entity types

**Files**: `src/ui/fk_resolution_dialog.py`
**Parallel?**: No

## Test Strategy

- Manual testing of dialog flows
- Verify modal behavior
- Verify all three resolution paths
- Verify cancellation handling

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| UI complexity | Follow existing dialog patterns exactly |
| Modal issues | Use transient() and grab_set() |

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] FKResolutionDialog shows with create/map/skip options
- [ ] Map to existing shows fuzzy search results
- [ ] Create new shows entity-specific form
- [ ] Cancellation prompts keep/rollback per spec
- [ ] Manual UI testing complete
- [ ] tasks.md updated with status change

## Review Guidance

- Verify dialog follows existing CustomTkinter patterns
- Verify modal behavior works correctly
- Verify all entity types have creation forms
- Verify cancellation handling per spec clarification

## Activity Log

- 2025-12-25T14:00:00Z - system - lane=planned - Prompt created.
- 2025-12-26T02:57:09Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-26T02:59:35Z – system – shell_pid= – lane=for_review – Moved to for_review
