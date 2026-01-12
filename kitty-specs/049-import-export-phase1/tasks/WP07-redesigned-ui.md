---
work_package_id: "WP07"
subtasks:
  - "T055"
  - "T056"
  - "T057"
  - "T058"
  - "T059"
  - "T060"
  - "T061"
  - "T062"
  - "T063"
  - "T064"
  - "T065"
  - "T066"
title: "Redesigned Import/Export UI"
phase: "Phase 2 - Wave 1"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "13882"
review_status: "approved"
reviewed_by: "claude"
history:
  - timestamp: "2026-01-12T16:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP07 - Redesigned Import/Export UI

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Redesign import/export dialogs to clearly distinguish export types and import purposes.

**Success Criteria**:
- SC-010: User can complete export workflow in under 30 seconds
- SC-011: User can complete import workflow in under 60 seconds
- FR-023: System MUST provide clear UI distinguishing 3 export types with purpose explanations
- FR-024: System MUST provide clear UI distinguishing 4 import purposes
- FR-025: System MUST display auto-detected format to user for confirmation

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 7)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Constitution: `.kittify/memory/constitution.md` (Principle V - Layered Architecture)

**Architectural Constraint**:
- UI layer must NOT contain business logic
- UI calls service layer methods only
- All validation happens in services

**Framework**: CustomTkinter (CTk*)

**Export Types**:
1. **Full Backup** - All 16 entities, no selection
2. **Catalog Export** - Select entities, choose format
3. **Context-Rich Export** - Select view type (ingredients, materials, recipes)

**Import Purposes**:
1. **Backup Restore** - Full restore, replace mode
2. **Catalog Import** - Add/augment entities
3. **Purchases Import** - Transaction import
4. **Adjustments Import** - Inventory adjustments

---

## Subtasks & Detailed Guidance

### Subtask T055 - Redesign export dialog with 3 tabs

**Purpose**: Clear separation of export types.

**Steps**:
1. Open `src/ui/dialogs/import_export_dialog.py`
2. Replace existing export dialog with tabbed interface:
```python
import customtkinter as ctk

class ExportDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Export Data")
        self.geometry("500x400")

        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add tabs
        self.tabview.add("Full Backup")
        self.tabview.add("Catalog")
        self.tabview.add("Context-Rich")

        # Populate each tab
        self._setup_full_backup_tab()
        self._setup_catalog_tab()
        self._setup_context_rich_tab()
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T056 - Full Backup tab: no entity selection

**Purpose**: Full backup exports everything - no choices needed.

**Steps**:
1. Create Full Backup tab content:
```python
def _setup_full_backup_tab(self):
    tab = self.tabview.tab("Full Backup")

    # Purpose explanation
    purpose = ctk.CTkLabel(
        tab,
        text="Create a complete backup of all data for disaster recovery or migration.",
        wraplength=400
    )
    purpose.pack(pady=10)

    # Info about what's included
    info = ctk.CTkLabel(
        tab,
        text="Includes: All 16 entity types (ingredients, products, recipes, etc.)\n"
             "Output: Folder with individual JSON files + manifest",
        justify="left"
    )
    info.pack(pady=10)

    # Export button
    export_btn = ctk.CTkButton(
        tab,
        text="Export Full Backup...",
        command=self._export_full_backup
    )
    export_btn.pack(pady=20)
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T057 - Catalog Export tab: entity and format selection

**Purpose**: Allow selective export of catalog entities.

**Steps**:
1. Create Catalog tab with checkboxes:
```python
def _setup_catalog_tab(self):
    tab = self.tabview.tab("Catalog")

    purpose = ctk.CTkLabel(
        tab,
        text="Export catalog data (ingredients, products, recipes) for sharing or backup.",
        wraplength=400
    )
    purpose.pack(pady=10)

    # Entity selection frame
    entity_frame = ctk.CTkFrame(tab)
    entity_frame.pack(fill="x", pady=10)

    ctk.CTkLabel(entity_frame, text="Select entities:").pack(anchor="w")

    self.entity_vars = {}
    for entity in ["ingredients", "products", "recipes", "materials", "material_products"]:
        var = ctk.BooleanVar(value=True)
        self.entity_vars[entity] = var
        cb = ctk.CTkCheckBox(entity_frame, text=entity.replace("_", " ").title(), variable=var)
        cb.pack(anchor="w", padx=20)

    # Format selection
    format_frame = ctk.CTkFrame(tab)
    format_frame.pack(fill="x", pady=10)

    ctk.CTkLabel(format_frame, text="Format:").pack(anchor="w")
    self.format_var = ctk.StringVar(value="normalized")
    ctk.CTkRadioButton(format_frame, text="Normalized (standard backup)", variable=self.format_var, value="normalized").pack(anchor="w", padx=20)

    # Export button
    export_btn = ctk.CTkButton(tab, text="Export Catalog...", command=self._export_catalog)
    export_btn.pack(pady=20)
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T058 - Context-Rich Export tab: entity selection for views

**Purpose**: Export context-rich views for AI augmentation.

**Steps**:
1. Create Context-Rich tab:
```python
def _setup_context_rich_tab(self):
    tab = self.tabview.tab("Context-Rich")

    purpose = ctk.CTkLabel(
        tab,
        text="Export data with full context (hierarchy paths, computed values) for AI tools.",
        wraplength=400
    )
    purpose.pack(pady=10)

    # View type selection
    view_frame = ctk.CTkFrame(tab)
    view_frame.pack(fill="x", pady=10)

    ctk.CTkLabel(view_frame, text="Select view to export:").pack(anchor="w")

    self.view_var = ctk.StringVar(value="ingredients")
    for view in ["ingredients", "materials", "recipes"]:
        rb = ctk.CTkRadioButton(
            view_frame,
            text=f"{view.title()} (with hierarchy, products, costs)",
            variable=self.view_var,
            value=view
        )
        rb.pack(anchor="w", padx=20)

    # Export button
    export_btn = ctk.CTkButton(tab, text="Export Context-Rich...", command=self._export_context_rich)
    export_btn.pack(pady=20)
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T059 - Add purpose explanations for each export type

**Purpose**: Help users understand when to use each type.

**Steps**:
1. Add clear explanations in each tab (done in T056-T058)
2. Consider adding tooltips or info icons:
```python
# Optional: Add info button with more detail
info_btn = ctk.CTkButton(
    tab,
    text="?",
    width=30,
    command=lambda: self._show_help("full_backup")
)
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T060 - Redesign import dialog with 4 purpose options

**Purpose**: Clear separation of import purposes.

**Steps**:
1. Create new import dialog:
```python
class ImportDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Import Data")
        self.geometry("500x500")

        # Purpose selection
        purpose_frame = ctk.CTkFrame(self)
        purpose_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(purpose_frame, text="What are you importing?", font=("", 14, "bold")).pack(anchor="w")

        self.purpose_var = ctk.StringVar(value="catalog")
        purposes = [
            ("backup", "Backup Restore", "Restore complete system from backup"),
            ("catalog", "Catalog Data", "Add/update ingredients, products, recipes"),
            ("purchases", "Purchases", "Import purchase transactions from BT Mobile"),
            ("adjustments", "Adjustments", "Import inventory adjustments (spoilage, waste)")
        ]

        for value, label, desc in purposes:
            frame = ctk.CTkFrame(purpose_frame)
            frame.pack(fill="x", pady=5)

            rb = ctk.CTkRadioButton(frame, text=label, variable=self.purpose_var, value=value)
            rb.pack(side="left")

            desc_label = ctk.CTkLabel(frame, text=desc, text_color="gray")
            desc_label.pack(side="left", padx=10)

        # File selection
        # ...
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T061 - Backup Restore option

**Purpose**: Full restore replaces all data.

**Steps**:
1. When "Backup Restore" selected:
   - Show warning about data replacement
   - No mode selection (always replace)
   - Call coordinated import service

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T062 - Catalog Import option with mode selection

**Purpose**: ADD_ONLY or AUGMENT mode for catalog data.

**Steps**:
1. When "Catalog" selected, show mode selection:
```python
def _show_catalog_options(self):
    # Mode selection
    self.mode_var = ctk.StringVar(value="add")

    modes = [
        ("add", "Add Only", "Create new records, skip existing"),
        ("augment", "Augment", "Create new + fill empty fields on existing")
    ]

    for value, label, desc in modes:
        # Create radio buttons with descriptions
        pass
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T063 - Purchases Import option

**Purpose**: Import purchase transactions.

**Steps**:
1. When "Purchases" selected:
   - File selection
   - Show validation preview (record count, any errors)
   - Call transaction_import_service.import_purchases()

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T064 - Adjustments Import option

**Purpose**: Import inventory adjustments.

**Steps**:
1. When "Adjustments" selected:
   - File selection
   - Show validation preview
   - Call transaction_import_service.import_adjustments()

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T065 - Integrate auto-detection with confirmation

**Purpose**: Show detected format before proceeding.

**Steps**:
1. After file selection, call detect_format():
```python
def _on_file_selected(self, file_path: str):
    from src.services.enhanced_import_service import detect_format

    format_type, data = detect_format(file_path)
    detection = FormatDetectionResult(format_type, ...)

    # Show confirmation
    self.detection_label.configure(
        text=f"Detected format: {detection.display_name}\n"
             f"Records: {detection.entity_count}"
    )

    # Auto-select matching purpose if clear
    if format_type == "purchases":
        self.purpose_var.set("purchases")
    elif format_type == "adjustments":
        self.purpose_var.set("adjustments")
```

**Files**: `src/ui/dialogs/import_export_dialog.py`

### Subtask T066 - Add progress indicator during import/export

**Purpose**: Show progress for long operations.

**Steps**:
1. Add progress bar:
```python
self.progress = ctk.CTkProgressBar(self)
self.progress.pack(fill="x", padx=10, pady=10)
self.progress.set(0)

# Update during operation
def _update_progress(self, current: int, total: int):
    self.progress.set(current / total)
    self.update()
```
2. Show status messages during operation

**Files**: `src/ui/dialogs/import_export_dialog.py`

---

## Test Strategy

**Manual Testing** (UI validation):
- Test export workflow completion < 30 seconds
- Test import workflow completion < 60 seconds
- Verify all labels and explanations clear
- Test auto-detection with different file types

**No automated UI tests required** - UI testing is manual per project conventions.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Complex UI overwhelms user | Clear labels, purpose explanations |
| Service integration issues | Mock services during UI development |
| Performance on large imports | Progress indicator shows activity |

---

## Definition of Done Checklist

- [ ] Export dialog has 3 tabs (Full Backup, Catalog, Context-Rich)
- [ ] Full Backup has no entity selection
- [ ] Catalog has entity checkboxes and format selection
- [ ] Context-Rich has view type selection
- [ ] Purpose explanations on each export type
- [ ] Import dialog has 4 purpose options
- [ ] Mode selection for Catalog import
- [ ] Auto-detection displays before import
- [ ] Progress indicator during operations
- [ ] Export workflow < 30 seconds (SC-010)
- [ ] Import workflow < 60 seconds (SC-011)

## Review Guidance

**Reviewers should verify**:
1. UI is intuitive for non-technical user
2. No business logic in UI layer
3. All operations call service layer
4. Purpose explanations are clear
5. Workflow timing meets success criteria

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T18:30:00Z – claude – lane=doing – Implemented UI redesign
- 2026-01-12T22:15:00Z – claude – shell_pid=13882 – lane=done – Approved: ExportDialog with 3 tabs (Full Backup, Catalog, Context-Rich). ImportDialog with 4 purposes. Auto-detection integrated. Progress indicators added.
