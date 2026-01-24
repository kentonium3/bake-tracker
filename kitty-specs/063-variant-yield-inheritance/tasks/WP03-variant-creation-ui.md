---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Variant Creation UI"
phase: "Phase 1 - Core"
lane: "done"
assignee: ""
agent: "claude-opus"
shell_pid: "30126"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: ["WP02"]
history:
  - timestamp: "2025-01-24T07:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Variant Creation UI

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP03 --base WP02
```

This work package depends on WP02 (variant creation service extension).

---

## Objectives & Success Criteria

Create UI for variant recipe creation with inline FinishedUnit display_name input, allowing users to create variants and specify FinishedUnit names in a single workflow.

**Success Criteria**:
- [ ] User can initiate variant creation from recipe detail view
- [ ] Dialog/form shows base recipe's FinishedUnits as reference
- [ ] User can enter display_name for each variant FinishedUnit
- [ ] Inline validation shows error if display_name matches base
- [ ] Save button calls `create_recipe_variant()` with `finished_unit_names`
- [ ] Handles base recipes with no FinishedUnits gracefully

---

## Context & Constraints

**References**:
- Plan: `kitty-specs/063-variant-yield-inheritance/plan.md` (UI integration)
- Spec: `kitty-specs/063-variant-yield-inheritance/spec.md` (User Story 2, Clarifications)
- Clarification: FinishedUnit display_name input integrated inline in variant creation dialog

**Architectural Constraints**:
- Use CustomTkinter for UI components
- Follow existing form patterns in `src/ui/forms/`
- UI layer calls service layer (never accesses models directly)
- Validation on save (per clarification)

**Existing UI Patterns**:
- Recipe detail/edit forms in `src/ui/forms/recipe_detail.py` or similar
- CTkEntry for text input with validation
- CTkLabel for display
- CTkButton for actions

---

## Subtasks & Detailed Guidance

### Subtask T012 – Create variant creation dialog/method

**Purpose**: Add UI entry point for creating a variant from an existing recipe.

**Steps**:
1. **Research existing recipe forms**:
   - Check `src/ui/forms/` for recipe-related forms
   - Look for existing "Create Variant" or "Copy Recipe" functionality
   - Identify where to add variant creation button/menu

2. **Add variant creation trigger** (if not exists):
   - In recipe detail view, add "Create Variant" button
   - Or add to context menu / actions dropdown

3. **Create variant dialog class**:
   ```python
   # src/ui/forms/variant_creation_form.py (new file) or extend existing

   import customtkinter as ctk
   from typing import Optional, List, Dict

   class VariantCreationDialog(ctk.CTkToplevel):
       """Dialog for creating a variant of an existing recipe."""

       def __init__(
           self,
           parent,
           base_recipe_id: int,
           base_recipe_name: str,
           base_finished_units: List[Dict],
           on_save_callback=None,
       ):
           super().__init__(parent)
           self.base_recipe_id = base_recipe_id
           self.base_recipe_name = base_recipe_name
           self.base_finished_units = base_finished_units
           self.on_save_callback = on_save_callback

           self.title(f"Create Variant of {base_recipe_name}")
           self.geometry("500x400")

           self._create_widgets()

       def _create_widgets(self):
           # Variant name input
           # FinishedUnit display_name inputs
           # Save/Cancel buttons
           pass
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (new, ~50 lines structure)
- Or extend existing recipe form

**Validation**:
- [ ] Dialog opens when "Create Variant" is triggered
- [ ] Dialog receives base recipe info

---

### Subtask T013 – Query and display base recipe's FinishedUnits

**Purpose**: Show base recipe's FinishedUnits as reference so user knows what to name.

**Steps**:
1. **Before opening dialog, query base FinishedUnits**:
   ```python
   from src.services import recipe_service

   def open_variant_dialog(self, base_recipe_id: int, base_recipe_name: str):
       # Get base recipe's FinishedUnits
       with ui_session() as session:
           base_fus = recipe_service.get_finished_units(base_recipe_id, session=session)

       # Open dialog with base FU info
       dialog = VariantCreationDialog(
           parent=self,
           base_recipe_id=base_recipe_id,
           base_recipe_name=base_recipe_name,
           base_finished_units=base_fus,
           on_save_callback=self._on_variant_created,
       )
   ```

2. **Display base FUs in dialog**:
   ```python
   def _create_widgets(self):
       # ... variant name section ...

       # FinishedUnit section
       if self.base_finished_units:
           fu_label = ctk.CTkLabel(self, text="Finished Unit Names:")
           fu_label.pack(pady=(10, 5))

           # Create frame for FU entries
           self.fu_frame = ctk.CTkFrame(self)
           self.fu_frame.pack(fill="x", padx=20, pady=5)

           self.fu_entries = {}
           for fu in self.base_finished_units:
               self._create_fu_row(fu)
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (modify ~30 lines)

**Validation**:
- [ ] Base FinishedUnits displayed in dialog
- [ ] Each FU shows base display_name as reference

---

### Subtask T014 – Add CTkEntry fields for variant FinishedUnit display_names

**Purpose**: Provide input fields for user to enter variant display_names.

**Steps**:
1. **Create row for each base FinishedUnit**:
   ```python
   def _create_fu_row(self, base_fu: Dict):
       """Create input row for one FinishedUnit."""
       row = ctk.CTkFrame(self.fu_frame)
       row.pack(fill="x", pady=2)

       # Label showing base FU name
       base_label = ctk.CTkLabel(
           row,
           text=f"Base: {base_fu['display_name']}",
           width=150,
       )
       base_label.pack(side="left", padx=5)

       # Entry for variant display_name
       entry = ctk.CTkEntry(row, width=200)
       entry.pack(side="left", padx=5)

       # Pre-populate with suggestion
       variant_name = self.variant_name_entry.get() if hasattr(self, 'variant_name_entry') else ""
       suggested_name = f"{variant_name} {base_fu['display_name']}"
       entry.insert(0, suggested_name.strip())

       # Store for later retrieval
       self.fu_entries[base_fu['slug']] = {
           'entry': entry,
           'base_display_name': base_fu['display_name'],
       }
   ```

2. **Update suggestions when variant name changes**:
   ```python
   def _on_variant_name_changed(self, *args):
       """Update FU name suggestions when variant name changes."""
       variant_name = self.variant_name_var.get()
       for slug, data in self.fu_entries.items():
           entry = data['entry']
           base_name = data['base_display_name']
           # Only update if user hasn't modified
           current = entry.get()
           if not current or current.endswith(base_name):
               entry.delete(0, 'end')
               entry.insert(0, f"{variant_name} {base_name}".strip())
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (modify ~50 lines)

**Validation**:
- [ ] Entry field for each base FinishedUnit
- [ ] Pre-populated with suggested name
- [ ] Updates when variant name changes

---

### Subtask T015 – Add inline validation feedback

**Purpose**: Show error if variant display_name matches base display_name.

**Steps**:
1. **Add validation on entry change or on save**:
   ```python
   def _validate_fu_names(self) -> List[str]:
       """Validate FinishedUnit display_names. Returns list of errors."""
       errors = []
       for slug, data in self.fu_entries.items():
           new_name = data['entry'].get().strip()
           base_name = data['base_display_name']

           if not new_name:
               errors.append(f"Display name for '{base_name}' cannot be empty")
           elif new_name == base_name:
               errors.append(f"'{new_name}' must differ from base name '{base_name}'")

       return errors
   ```

2. **Show inline error feedback**:
   ```python
   def _show_validation_errors(self, errors: List[str]):
       """Display validation errors in the dialog."""
       if hasattr(self, 'error_label'):
           self.error_label.destroy()

       if errors:
           error_text = "\n".join(errors)
           self.error_label = ctk.CTkLabel(
               self,
               text=error_text,
               text_color="red",
           )
           self.error_label.pack(pady=5)
   ```

3. **Validate on save button click**:
   ```python
   def _on_save(self):
       errors = self._validate_fu_names()
       if errors:
           self._show_validation_errors(errors)
           return
       # Proceed with save
       self._save_variant()
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (modify ~40 lines)

**Validation**:
- [ ] Error shown if display_name matches base
- [ ] Error shown if display_name is empty
- [ ] Error message is clear and user-friendly

---

### Subtask T016 – Wire save to call `create_recipe_variant()` with `finished_unit_names`

**Purpose**: Connect the UI to the service layer to create the variant.

**Steps**:
1. **Collect data and call service**:
   ```python
   def _save_variant(self):
       """Save the variant recipe."""
       variant_name = self.variant_name_var.get().strip()

       # Collect finished_unit_names
       finished_unit_names = None
       if self.fu_entries:
           finished_unit_names = [
               {
                   "base_slug": slug,
                   "display_name": data['entry'].get().strip(),
               }
               for slug, data in self.fu_entries.items()
           ]

       try:
           from src.ui.utils import ui_session
           from src.services import recipe_service

           with ui_session() as session:
               result = recipe_service.create_recipe_variant(
                   base_recipe_id=self.base_recipe_id,
                   variant_name=variant_name,
                   finished_unit_names=finished_unit_names,
                   session=session,
               )

           # Success - close dialog and notify parent
           if self.on_save_callback:
               self.on_save_callback(result)
           self.destroy()

       except ValidationError as e:
           self._show_validation_errors(e.errors if hasattr(e, 'errors') else [str(e)])
       except Exception as e:
           self._show_validation_errors([f"Error creating variant: {str(e)}"])
   ```

2. **Add save and cancel buttons**:
   ```python
   def _create_buttons(self):
       button_frame = ctk.CTkFrame(self)
       button_frame.pack(fill="x", pady=20, padx=20)

       cancel_btn = ctk.CTkButton(
           button_frame,
           text="Cancel",
           command=self.destroy,
       )
       cancel_btn.pack(side="left", padx=5)

       save_btn = ctk.CTkButton(
           button_frame,
           text="Create Variant",
           command=self._on_save,
       )
       save_btn.pack(side="right", padx=5)
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (modify ~50 lines)

**Validation**:
- [ ] Save calls service with correct parameters
- [ ] Errors from service displayed to user
- [ ] Success closes dialog and triggers callback

---

### Subtask T017 – Handle base recipes with no FinishedUnits

**Purpose**: Gracefully handle the case where base recipe has no FinishedUnits.

**Steps**:
1. **Check for empty FinishedUnits and skip FU section**:
   ```python
   def _create_widgets(self):
       # ... variant name section ...

       # FinishedUnit section - only if base has FUs
       if self.base_finished_units:
           fu_label = ctk.CTkLabel(self, text="Finished Unit Names:")
           fu_label.pack(pady=(10, 5))
           # ... create FU entries ...
       else:
           # No FUs - show informational message
           no_fu_label = ctk.CTkLabel(
               self,
               text="Base recipe has no yield types defined.\nVariant will also have no yield types.",
               text_color="gray",
           )
           no_fu_label.pack(pady=10)
   ```

2. **Ensure save works without FU names**:
   ```python
   def _save_variant(self):
       # ...
       # finished_unit_names will be None if no FU entries
       finished_unit_names = None
       if self.fu_entries:
           finished_unit_names = [...]

       # Service accepts None for finished_unit_names
   ```

**Files**:
- `src/ui/forms/variant_creation_form.py` (modify ~15 lines)

**Validation**:
- [ ] Dialog works when base has no FinishedUnits
- [ ] Informational message displayed
- [ ] Variant created successfully without FinishedUnits

---

## Definition of Done

- [ ] Variant creation dialog implemented
- [ ] Base FinishedUnits displayed as reference
- [ ] Display_name entry fields functional
- [ ] Inline validation shows duplicate name errors
- [ ] Save creates variant with FinishedUnits
- [ ] Empty FinishedUnit case handled gracefully
- [ ] Dialog integrates with existing recipe UI

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| No existing variant UI | Research existing forms; create minimal dialog |
| Complex dialog state | Keep state minimal; validate on save only |
| CustomTkinter learning curve | Follow existing patterns in `src/ui/forms/` |

---

## Reviewer Guidance

When reviewing this work package, verify:

1. **User Flow**: User can create variant from recipe detail view in single session
2. **Base FU Display**: Base FinishedUnit names shown as reference
3. **Validation**: Duplicate display_name blocked with clear error
4. **Service Integration**: Correctly calls `create_recipe_variant` with `finished_unit_names`
5. **Edge Case**: No FinishedUnits case handled gracefully
6. **UI Consistency**: Follows existing CustomTkinter patterns in codebase

## Activity Log

- 2026-01-24T07:57:46Z – claude-opus – shell_pid=28526 – lane=doing – Started implementation via workflow command
- 2026-01-24T08:03:26Z – claude-opus – shell_pid=28526 – lane=for_review – Ready for review: Created VariantCreationDialog with inline FU display_name input, validation, and Create Variant button in recipes tab
- 2026-01-24T08:05:32Z – claude-opus – shell_pid=30126 – lane=doing – Started review via workflow command
- 2026-01-24T08:06:24Z – claude-opus – shell_pid=30126 – lane=done – Review passed: Dialog shows base FUs, entry fields with auto-suggestions, inline validation, correct service integration, and no-FU edge case handled
