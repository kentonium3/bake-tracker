---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "Production Dashboard Event Progress"
phase: "Phase 3 - Production Dashboard Enhancement"
lane: "for_review"
assignee: ""
agent: "system"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-11T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Production Dashboard Event Progress

## Objectives & Success Criteria

**Objective**: Add event selector and progress tracking to Production Dashboard (User Stories 1 & 2). This is the **MVP** work package.

**Success Criteria**:
- Event selector dropdown populated with available events (FR-003)
- Production progress bars show batches produced vs target (FR-004)
- Assembly progress bars show quantity assembled vs target (FR-005)
- "No targets set" message with link when event has no targets (FR-006)
- Progress displays within 2 seconds of event selection (SC-001)
- User can answer "Where do I stand for [Event]?" within 5 seconds (SC-007)

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md`
- Plan: `kitty-specs/017-event-reporting-production/plan.md`
- Spec: `kitty-specs/017-event-reporting-production/spec.md`
- Research: `kitty-specs/017-event-reporting-production/research.md` (Decision D2)

**Architectural Constraints**:
- UI layer only displays data; all calculations in services
- Use existing service methods: `get_production_progress()`, `get_assembly_progress()`
- Follow CustomTkinter patterns from existing code
- Navigation link must work with main_window's `switch_to_tab()` pattern

**Existing Service Methods to Use**:
- `get_all_events()` - for event selector
- `get_production_progress(event_id)` - returns list of {recipe_name, target_batches, produced_batches, progress_pct}
- `get_assembly_progress(event_id)` - returns list of {finished_good_name, target_quantity, assembled_quantity, progress_pct}

## Subtasks & Detailed Guidance

### Subtask T011 - Add event selector dropdown

**Purpose**: Allow user to select which event's progress to view.

**Steps**:
1. Open `src/ui/production_dashboard_tab.py`
2. Add imports if needed:
   ```python
   from src.services import event_service
   ```

3. In `__init__()`, add event selector at the top of the tab (before existing content):
   ```python
   # Event Progress Section (Feature 017)
   self.progress_frame = ctk.CTkFrame(self)
   self.progress_frame.pack(fill="x", padx=10, pady=(10, 5))

   # Event selector row
   selector_row = ctk.CTkFrame(self.progress_frame)
   selector_row.pack(fill="x", padx=10, pady=5)

   ctk.CTkLabel(selector_row, text="Event Progress:", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

   self.event_var = ctk.StringVar(value="Select Event")
   self.event_selector = ctk.CTkComboBox(
       selector_row,
       variable=self.event_var,
       values=["Select Event"],
       command=self._on_event_selected,
       width=250
   )
   self.event_selector.pack(side="left", padx=(10, 0))
   ```

4. Add method to populate events:
   ```python
   def _populate_event_selector(self):
       """Populate event selector with available events."""
       try:
           events = event_service.get_all_events()
           self.events_map = {event.name: event.id for event in events}
           event_names = ["Select Event"] + list(self.events_map.keys())
           self.event_selector.configure(values=event_names)
       except Exception as e:
           print(f"Error loading events: {e}")
           self.events_map = {}
   ```

5. Call `_populate_event_selector()` in `__init__()` and `refresh()`.

6. Add event selection handler:
   ```python
   def _on_event_selected(self, event_name: str):
       """Handle event selection from dropdown."""
       if event_name == "Select Event":
           self._clear_progress_display()
           return

       event_id = self.events_map.get(event_name)
       if event_id:
           self._load_event_progress(event_id)
   ```

**Files**: `src/ui/production_dashboard_tab.py`
**Parallel?**: No (foundation for T012-T015)

---

### Subtask T012 - Add production progress section with progress bars

**Purpose**: Show recipe production progress (batches produced vs target).

**Steps**:
1. Create production progress frame:
   ```python
   # Production Progress Section
   self.production_progress_frame = ctk.CTkFrame(self.progress_frame)
   self.production_progress_frame.pack(fill="x", padx=10, pady=5)

   ctk.CTkLabel(
       self.production_progress_frame,
       text="Recipe Production:",
       font=ctk.CTkFont(size=14, weight="bold")
   ).pack(anchor="w", padx=5)

   # Container for progress bars (will be populated dynamically)
   self.production_bars_frame = ctk.CTkScrollableFrame(
       self.production_progress_frame,
       height=150
   )
   self.production_bars_frame.pack(fill="x", padx=5, pady=5)
   ```

2. Add method to display production progress:
   ```python
   def _display_production_progress(self, progress_data: list):
       """Display production progress bars."""
       # Clear existing
       for widget in self.production_bars_frame.winfo_children():
           widget.destroy()

       if not progress_data:
           ctk.CTkLabel(
               self.production_bars_frame,
               text="No production targets for this event",
               text_color="gray"
           ).pack(pady=10)
           return

       for item in progress_data:
           row = ctk.CTkFrame(self.production_bars_frame)
           row.pack(fill="x", pady=2)

           # Recipe name
           ctk.CTkLabel(
               row,
               text=item["recipe_name"],
               width=150,
               anchor="w"
           ).pack(side="left", padx=5)

           # Progress bar
           progress_pct = min(item["progress_pct"], 100) / 100  # Cap at 1.0 for bar
           progress_bar = ctk.CTkProgressBar(row, width=200)
           progress_bar.set(progress_pct)
           progress_bar.pack(side="left", padx=5)

           # Text label: "2/4 (50%)"
           pct_display = item["progress_pct"]
           label_text = f"{item['produced_batches']}/{item['target_batches']} ({pct_display:.0f}%)"

           # Color code: green if complete, default otherwise
           label_color = "green" if item["is_complete"] else None

           ctk.CTkLabel(
               row,
               text=label_text,
               text_color=label_color
           ).pack(side="left", padx=5)
   ```

**Files**: `src/ui/production_dashboard_tab.py`
**Parallel?**: No (builds on T011)

---

### Subtask T013 - Add assembly progress section with progress bars

**Purpose**: Show finished good assembly progress (quantity assembled vs target).

**Steps**:
1. Create assembly progress frame (similar to production):
   ```python
   # Assembly Progress Section
   self.assembly_progress_frame = ctk.CTkFrame(self.progress_frame)
   self.assembly_progress_frame.pack(fill="x", padx=10, pady=5)

   ctk.CTkLabel(
       self.assembly_progress_frame,
       text="Finished Good Assembly:",
       font=ctk.CTkFont(size=14, weight="bold")
   ).pack(anchor="w", padx=5)

   self.assembly_bars_frame = ctk.CTkScrollableFrame(
       self.assembly_progress_frame,
       height=150
   )
   self.assembly_bars_frame.pack(fill="x", padx=5, pady=5)
   ```

2. Add method to display assembly progress:
   ```python
   def _display_assembly_progress(self, progress_data: list):
       """Display assembly progress bars."""
       for widget in self.assembly_bars_frame.winfo_children():
           widget.destroy()

       if not progress_data:
           ctk.CTkLabel(
               self.assembly_bars_frame,
               text="No assembly targets for this event",
               text_color="gray"
           ).pack(pady=10)
           return

       for item in progress_data:
           row = ctk.CTkFrame(self.assembly_bars_frame)
           row.pack(fill="x", pady=2)

           # Finished good name
           ctk.CTkLabel(
               row,
               text=item["finished_good_name"],
               width=150,
               anchor="w"
           ).pack(side="left", padx=5)

           # Progress bar
           progress_pct = min(item["progress_pct"], 100) / 100
           progress_bar = ctk.CTkProgressBar(row, width=200)
           progress_bar.set(progress_pct)
           progress_bar.pack(side="left", padx=5)

           # Text label
           pct_display = item["progress_pct"]
           label_text = f"{item['assembled_quantity']}/{item['target_quantity']} ({pct_display:.0f}%)"
           label_color = "green" if item["is_complete"] else None

           ctk.CTkLabel(
               row,
               text=label_text,
               text_color=label_color
           ).pack(side="left", padx=5)
   ```

**Files**: `src/ui/production_dashboard_tab.py`
**Parallel?**: No (builds on T012)

---

### Subtask T014 - Handle "no targets" case with message and link

**Purpose**: Show helpful message when event has no targets set.

**Steps**:
1. Add no-targets display method:
   ```python
   def _display_no_targets(self, event_id: int):
       """Display message when event has no targets."""
       # Clear progress sections
       for widget in self.production_bars_frame.winfo_children():
           widget.destroy()
       for widget in self.assembly_bars_frame.winfo_children():
           widget.destroy()

       # Create centered message frame
       no_targets_frame = ctk.CTkFrame(self.production_bars_frame)
       no_targets_frame.pack(expand=True, fill="both", pady=20)

       ctk.CTkLabel(
           no_targets_frame,
           text="No production targets set for this event",
           font=ctk.CTkFont(size=14),
           text_color="gray"
       ).pack(pady=10)

       # Store event_id for button callback
       self._current_event_id = event_id
   ```

2. Update `_load_event_progress()` to check for empty targets:
   ```python
   def _load_event_progress(self, event_id: int):
       """Load and display progress for selected event."""
       try:
           prod_progress = event_service.get_production_progress(event_id)
           asm_progress = event_service.get_assembly_progress(event_id)

           # Check if any targets exist
           if not prod_progress and not asm_progress:
               self._display_no_targets(event_id)
               return

           self._display_production_progress(prod_progress)
           self._display_assembly_progress(asm_progress)

       except Exception as e:
           print(f"Error loading event progress: {e}")
   ```

**Files**: `src/ui/production_dashboard_tab.py`
**Parallel?**: No (builds on T012, T013)

---

### Subtask T015 - Add navigation link to Event Detail

**Purpose**: Allow user to navigate to Event Detail to add/edit targets.

**Steps**:
1. Add button in no-targets display:
   ```python
   def _display_no_targets(self, event_id: int):
       """Display message when event has no targets."""
       # ... existing code ...

       ctk.CTkButton(
           no_targets_frame,
           text="Set Targets in Event Detail",
           command=lambda: self._navigate_to_event_detail(event_id)
       ).pack(pady=10)
   ```

2. Add navigation method:
   ```python
   def _navigate_to_event_detail(self, event_id: int):
       """Navigate to Event Detail window for target management."""
       # Get main window reference
       main_window = self.winfo_toplevel()

       # Switch to Events tab
       if hasattr(main_window, 'switch_to_tab'):
           main_window.switch_to_tab("Events")

       # Open event detail (if events tab has this method)
       if hasattr(main_window, 'events_tab') and hasattr(main_window.events_tab, 'open_event_detail'):
           main_window.events_tab.open_event_detail(event_id)
   ```

3. Alternative: Just switch to Events tab with message:
   ```python
   def _navigate_to_event_detail(self, event_id: int):
       """Navigate to Events tab."""
       from tkinter import messagebox

       main_window = self.winfo_toplevel()
       if hasattr(main_window, 'switch_to_tab'):
           main_window.switch_to_tab("Events")
           messagebox.showinfo(
               "Set Targets",
               "Select the event and click 'View Details' to set production targets."
           )
   ```

**Files**: `src/ui/production_dashboard_tab.py`
**Parallel?**: No (builds on T014)

---

## Test Strategy

**Manual Testing** (UI changes):
1. Launch app: `python src/main.py`
2. Verify Production Dashboard loads by default
3. Click event selector - verify events are listed
4. Select event with targets - verify progress bars appear
5. Verify progress percentages match: produced/target * 100
6. Select event without targets - verify message and link appear
7. Click "Set Targets" link - verify navigation works
8. Test refresh: record production elsewhere, return to dashboard, verify update

**Timing Test**:
1. Select event with targets
2. Count time until progress displays (should be < 2 seconds)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Progress >100% breaks bar | Cap bar at 1.0, display actual % in label |
| Empty event list | Show "No events available" in selector |
| Navigation fails | Fallback to simple tab switch with message |
| Layout issues | Use CTkScrollableFrame for progress lists |

## Definition of Done Checklist

- [ ] T011: Event selector dropdown working
- [ ] T012: Production progress bars display correctly
- [ ] T013: Assembly progress bars display correctly
- [ ] T014: "No targets" message appears when appropriate
- [ ] T015: Navigation link works
- [ ] Progress loads in < 2 seconds
- [ ] Manual testing confirms accuracy
- [ ] `tasks.md` updated with completion status

## Review Guidance

**Key Checkpoints**:
1. Event selector populates with all events
2. Progress percentages match manual calculation
3. Green highlighting for completed targets
4. "No targets" case handled gracefully
5. Over-production (>100%) displays correctly (bar full, % shows actual)

## Activity Log

- 2025-12-11T00:00:00Z - system - lane=planned - Prompt created.
- 2025-12-12T03:16:55Z – system – shell_pid= – lane=doing – Moved to doing
- 2025-12-12T03:29:52Z – system – shell_pid= – lane=for_review – Moved to for_review
