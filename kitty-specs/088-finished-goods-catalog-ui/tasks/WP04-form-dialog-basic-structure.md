---
work_package_id: "WP04"
title: "Form Dialog - Basic Structure"
lane: "done"
dependencies: []
subtasks: ["T021", "T022", "T023", "T024", "T025", "T026", "T027"]
priority: "P1"
estimated_lines: 380
agent: "gemini-wp04"
shell_pid: "21873"
reviewed_by: "Kent Gale"
review_status: "approved"
history:
  - date: "2026-01-30"
    action: "created"
    agent: "claude"
---

# WP04: Form Dialog - Basic Structure

## Objective

Create the create/edit form dialog with basic info section. The dialog opens modally, displays fields for Name, Assembly Type, Packaging Instructions, and Notes, with Save/Cancel buttons and validation.

## Context

- **Feature**: 088-finished-goods-catalog-ui
- **Priority**: P1 (form is required for CRUD operations)
- **Dependencies**: None (form is independent of tab)
- **Estimated Size**: ~380 lines

### Reference Files

- `src/ui/forms/recipe_form.py` - Pattern for modal form dialogs
- `src/models/assembly_type.py` - AssemblyType enum values
- `src/models/finished_good.py` - FinishedGood model fields

### Form Result Structure

```python
{
    "display_name": str,
    "assembly_type": str,  # Enum value string
    "packaging_instructions": str,
    "notes": str,
    "components": []  # Empty in WP04, populated in WP05/WP06
}
```

### Assembly Type Options

- CUSTOM_ORDER → "Custom Order"
- GIFT_BOX → "Gift Box"
- VARIETY_PACK → "Variety Pack"
- SEASONAL_BOX → "Seasonal Box"
- EVENT_PACKAGE → "Event Package"

## Implementation Command

```bash
spec-kitty implement WP04
```

---

## Subtasks

### T021: Create `src/ui/forms/finished_good_form.py` dialog shell (CTkToplevel modal)

**Purpose**: Create the base dialog structure following RecipeFormDialog pattern.

**Steps**:
1. Create new file `src/ui/forms/finished_good_form.py`
2. Add imports:
   ```python
   import customtkinter as ctk
   from typing import Optional, Dict, List
   from src.models.finished_good import FinishedGood
   from src.models.assembly_type import AssemblyType
   ```
3. Create `FinishedGoodFormDialog` class:
   ```python
   class FinishedGoodFormDialog(ctk.CTkToplevel):
       """Modal dialog for creating/editing FinishedGoods."""

       def __init__(
           self,
           parent,
           finished_good: Optional[FinishedGood] = None,
           title: str = "Create Finished Good"
       ):
           super().__init__(parent)

           self.finished_good = finished_good
           self.result: Optional[Dict] = None

           # Window configuration
           self.title(title if not finished_good else f"Edit: {finished_good.display_name}")
           self.geometry("600x700")
           self.resizable(True, True)
           self.minsize(500, 500)

           # Modal behavior
           self.transient(parent)
           self.grab_set()

           # Build UI
           self._create_widgets()
           self._populate_form()

           # Center on parent
           self._center_on_parent(parent)
   ```
4. Add centering helper:
   ```python
   def _center_on_parent(self, parent):
       self.update_idletasks()
       parent_x = parent.winfo_rootx()
       parent_y = parent.winfo_rooty()
       parent_w = parent.winfo_width()
       parent_h = parent.winfo_height()
       dialog_w = self.winfo_width()
       dialog_h = self.winfo_height()
       x = parent_x + (parent_w - dialog_w) // 2
       y = parent_y + (parent_h - dialog_h) // 2
       self.geometry(f"+{x}+{y}")
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (new file, ~60 lines for shell)

**Validation**:
- [ ] Dialog opens as modal window
- [ ] Window is centered on parent
- [ ] Cannot interact with parent while dialog is open
- [ ] Window has appropriate minimum size

---

### T022: Add scrollable form container for sections

**Purpose**: Create scrollable container to hold all form sections.

**Steps**:
1. In `_create_widgets()`, create main container:
   ```python
   def _create_widgets(self):
       # Main container
       self.main_frame = ctk.CTkFrame(self)
       self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

       # Scrollable form area
       self.form_scroll = ctk.CTkScrollableFrame(
           self.main_frame,
           label_text="",
           label_anchor="nw"
       )
       self.form_scroll.pack(fill="both", expand=True, pady=(0, 10))

       # Button frame at bottom (not scrollable)
       self.button_frame = ctk.CTkFrame(self.main_frame)
       self.button_frame.pack(fill="x", pady=(10, 0))
   ```
2. Configure scroll frame for consistent widget sizing:
   ```python
   self.form_scroll.grid_columnconfigure(0, weight=0)  # Labels
   self.form_scroll.grid_columnconfigure(1, weight=1)  # Inputs
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~25 lines added)

**Validation**:
- [ ] Scroll frame fills available space
- [ ] Button frame stays at bottom (not scrolled)
- [ ] Long forms can be scrolled

---

### T023: Add Basic Info section (Name entry with validation, Assembly Type dropdown) [P]

**Purpose**: Implement the primary required fields.

**Steps**:
1. Create section header:
   ```python
   def _create_basic_info_section(self):
       # Section header
       header = ctk.CTkLabel(
           self.form_scroll,
           text="Basic Information",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(10, 5))
   ```
2. Add Name field (required):
   ```python
   # Name label
   name_label = ctk.CTkLabel(self.form_scroll, text="Name *")
   name_label.grid(row=1, column=0, sticky="w", pady=5, padx=(0, 10))

   # Name entry
   self.name_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="Enter name")
   self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)
   ```
3. Add Assembly Type dropdown:
   ```python
   # Assembly Type label
   type_label = ctk.CTkLabel(self.form_scroll, text="Assembly Type *")
   type_label.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 10))

   # Assembly Type dropdown
   type_values = [
       "Custom Order", "Gift Box", "Variety Pack",
       "Seasonal Box", "Event Package"
   ]
   self.type_dropdown = ctk.CTkComboBox(
       self.form_scroll,
       values=type_values,
       state="readonly"
   )
   self.type_dropdown.set("Custom Order")  # Default
   self.type_dropdown.grid(row=2, column=1, sticky="ew", pady=5)
   ```
4. Store mapping for enum conversion:
   ```python
   self._type_to_enum = {
       "Custom Order": AssemblyType.CUSTOM_ORDER,
       "Gift Box": AssemblyType.GIFT_BOX,
       "Variety Pack": AssemblyType.VARIETY_PACK,
       "Seasonal Box": AssemblyType.SEASONAL_BOX,
       "Event Package": AssemblyType.EVENT_PACKAGE,
   }
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~45 lines added)

**Validation**:
- [ ] Name field accepts text input
- [ ] Assembly Type dropdown shows all options
- [ ] Default assembly type is "Custom Order"
- [ ] Required fields marked with asterisk

---

### T024: Add Packaging Instructions textarea [P]

**Purpose**: Add optional field for packaging instructions.

**Steps**:
1. Add after Basic Info section:
   ```python
   def _create_packaging_section(self):
       # Section header
       header = ctk.CTkLabel(
           self.form_scroll,
           text="Packaging Instructions",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       header.grid(row=3, column=0, columnspan=2, sticky="w", pady=(15, 5))

       # Textarea
       self.packaging_text = ctk.CTkTextbox(
           self.form_scroll,
           height=100,
           wrap="word"
       )
       self.packaging_text.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~20 lines added)

**Validation**:
- [ ] Textarea renders with appropriate height
- [ ] Text wraps at word boundaries
- [ ] Can enter multi-line text

---

### T025: Add Notes textarea [P]

**Purpose**: Add optional field for additional notes.

**Steps**:
1. Add after Packaging section:
   ```python
   def _create_notes_section(self):
       # Section header
       header = ctk.CTkLabel(
           self.form_scroll,
           text="Notes",
           font=ctk.CTkFont(size=14, weight="bold")
       )
       header.grid(row=5, column=0, columnspan=2, sticky="w", pady=(15, 5))

       # Textarea
       self.notes_text = ctk.CTkTextbox(
           self.form_scroll,
           height=80,
           wrap="word"
       )
       self.notes_text.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~18 lines added)

**Validation**:
- [ ] Notes textarea renders correctly
- [ ] Independent of packaging instructions

---

### T026: Add Save/Cancel buttons with basic validation (name required)

**Purpose**: Implement form submission and cancellation.

**Steps**:
1. Add buttons to button frame:
   ```python
   def _create_buttons(self):
       # Cancel button
       self.cancel_btn = ctk.CTkButton(
           self.button_frame,
           text="Cancel",
           command=self._on_cancel,
           fg_color="gray"
       )
       self.cancel_btn.pack(side="right", padx=5)

       # Save button
       self.save_btn = ctk.CTkButton(
           self.button_frame,
           text="Save",
           command=self._on_save
       )
       self.save_btn.pack(side="right", padx=5)
   ```
2. Implement cancel handler:
   ```python
   def _on_cancel(self):
       self.result = None
       self.destroy()
   ```
3. Implement save handler with validation:
   ```python
   def _on_save(self):
       # Validate required fields
       name = self.name_entry.get().strip()
       if not name:
           self._show_error("Name is required")
           return

       # Build result
       self.result = {
           "display_name": name,
           "assembly_type": self._get_assembly_type(),
           "packaging_instructions": self.packaging_text.get("1.0", "end-1c").strip(),
           "notes": self.notes_text.get("1.0", "end-1c").strip(),
           "components": []  # WP05/WP06 will populate this
       }
       self.destroy()

   def _get_assembly_type(self) -> str:
       selected = self.type_dropdown.get()
       return self._type_to_enum.get(selected, AssemblyType.CUSTOM_ORDER).value
   ```
4. Add error display:
   ```python
   def _show_error(self, message: str):
       # Simple error: highlight the name field
       self.name_entry.configure(border_color="red")
       # Could also use a toast/popup - keeping simple for now
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~50 lines added)

**Validation**:
- [ ] Cancel closes dialog with None result
- [ ] Save validates name is not empty
- [ ] Save builds result dictionary correctly
- [ ] Empty name shows error indication

---

### T027: Implement form population for edit mode (load existing FinishedGood data)

**Purpose**: Pre-fill form fields when editing an existing FinishedGood.

**Steps**:
1. Implement `_populate_form()`:
   ```python
   def _populate_form(self):
       """Populate form fields from existing FinishedGood."""
       if not self.finished_good:
           return

       # Name
       self.name_entry.insert(0, self.finished_good.display_name)

       # Assembly Type
       type_display = self._enum_to_type.get(
           self.finished_good.assembly_type,
           "Custom Order"
       )
       self.type_dropdown.set(type_display)

       # Packaging Instructions
       if self.finished_good.packaging_instructions:
           self.packaging_text.insert("1.0", self.finished_good.packaging_instructions)

       # Notes
       if self.finished_good.notes:
           self.notes_text.insert("1.0", self.finished_good.notes)
   ```
2. Add reverse mapping:
   ```python
   self._enum_to_type = {
       AssemblyType.CUSTOM_ORDER: "Custom Order",
       AssemblyType.GIFT_BOX: "Gift Box",
       AssemblyType.VARIETY_PACK: "Variety Pack",
       AssemblyType.SEASONAL_BOX: "Seasonal Box",
       AssemblyType.EVENT_PACKAGE: "Event Package",
   }
   ```
3. Update title in edit mode:
   ```python
   # In __init__
   if finished_good:
       self.title(f"Edit: {finished_good.display_name}")
   else:
       self.title("Create Finished Good")
   ```

**Files**:
- `src/ui/forms/finished_good_form.py` (~35 lines added)

**Validation**:
- [ ] Edit mode pre-fills all fields
- [ ] Name field shows existing name
- [ ] Assembly Type dropdown shows correct selection
- [ ] Packaging and Notes show existing content

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] `src/ui/forms/finished_good_form.py` created
- [ ] Dialog opens modally and centers on parent
- [ ] All form fields work (Name, Assembly Type, Packaging, Notes)
- [ ] Validation prevents empty name submission
- [ ] Edit mode correctly populates fields
- [ ] Cancel returns None, Save returns result dict

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Form layout complexity | Use grid layout with consistent padding; test at different sizes |
| CTkTextbox quirks | Test multi-line input; use get("1.0", "end-1c") pattern |
| Modal behavior issues | Use transient() and grab_set() as shown in pattern |

## Reviewer Guidance

1. Verify modal behavior (can't click parent while open)
2. Check form validation (empty name should fail)
3. Test edit mode with existing FinishedGood
4. Verify scrolling works when form content exceeds window
5. Check that result dict has correct structure

## Activity Log

- 2026-01-31T04:32:19Z – gemini-wp04 – shell_pid=21873 – lane=doing – Started implementation via workflow command
- 2026-01-31T04:34:57Z – gemini-wp04 – shell_pid=21873 – lane=for_review – Ready for review: All subtasks implemented. Dialog supports create/edit with Name, Assembly Type dropdown, Packaging Instructions textarea, Notes textarea, and Save/Cancel validation.
- 2026-01-31T04:42:44Z – gemini-wp04 – shell_pid=21873 – lane=done – Review passed: Form dialog properly implements modal behavior, all 5 AssemblyType options, validation, and edit mode population.
