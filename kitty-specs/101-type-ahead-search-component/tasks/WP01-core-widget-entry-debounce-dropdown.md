---
work_package_id: WP01
title: Core Widget - Entry, Debounce & Dropdown
lane: "planned"
dependencies: []
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
phase: "Phase 0 - Foundation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-02-10T21:59:40Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 -- Core Widget - Entry, Debounce & Dropdown

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - branches from main.

---

## Objectives & Success Criteria

Create the complete `TypeAheadEntry` widget in `src/ui/widgets/type_ahead_entry.py` with:

1. A `CTkEntry` text field with configurable placeholder text
2. Debounce-based search triggering via caller-provided `items_callback`
3. A floating `CTkToplevel` dropdown displaying search results
4. Mouse-click selection with `on_select_callback` firing
5. Basic dismissal (Escape, focus-out, tab-away) and cleanup

**Success Criteria:**
- Widget instantiates with mock callbacks without errors
- Typing >= `min_chars` characters triggers `items_callback` after `debounce_ms` delay
- Results appear in a floating dropdown positioned below the entry field
- Clicking a result fires `on_select_callback` with the full item dict
- `clear_on_select=True` clears entry text after selection
- Dropdown closes on Escape, focus-out, and tab-away
- "No items match" message appears for empty results
- Truncation message appears when results exceed `max_results`
- `destroy()` cleanly removes all bindings and toplevel windows

## Context & Constraints

- **Spec**: `kitty-specs/101-type-ahead-search-component/spec.md` (FR-001 through FR-008, FR-010)
- **Plan**: `kitty-specs/101-type-ahead-search-component/plan.md` (D1: floating CTkToplevel, D2: callback architecture, D3: debounce pattern)
- **Data Model**: `kitty-specs/101-type-ahead-search-component/data-model.md` (constructor params, event flow)
- **Contract**: `kitty-specs/101-type-ahead-search-component/contracts/type_ahead_entry_contract.md`
- **Research**: `kitty-specs/101-type-ahead-search-component/research.md` (existing patterns, debounce, CTkToplevel considerations)
- **Constitution**: `.kittify/memory/constitution.md` - Layered architecture (V), Code organization (VI.G)

**Key Constraints:**
- Widget imports ZERO service modules. All data comes through injected callbacks.
- Follow `TypeAheadComboBox` pattern: `ctk.CTkFrame` base, `fg_color="transparent"`, `**kwargs` passthrough
- Follow `IngredientTreeWidget` debounce pattern: `self._debounce_id` + `self.after()` / `self.after_cancel()`
- Module must stay under 500 lines (constitution VI.G)
- Case-insensitive search is the callback's responsibility, not the widget's (FR-010)
- The widget trims whitespace from queries before passing to callback (FR-010)

## Subtasks & Detailed Guidance

### Subtask T001 -- Create TypeAheadEntry Class Skeleton

- **Purpose**: Establish the module file and class structure with all constructor parameters.
- **Steps**:
  1. Create `src/ui/widgets/type_ahead_entry.py` with module docstring:
     ```python
     """
     Type-ahead search entry widget with floating dropdown.

     Reusable component that provides instant filtered search with
     service-backed data fetching via caller-provided callbacks.

     Usage:
         from src.ui.widgets.type_ahead_entry import TypeAheadEntry

         entry = TypeAheadEntry(
             master=frame,
             items_callback=my_search_func,
             on_select_callback=my_select_handler,
         )
     """
     ```
  2. Define `TypeAheadEntry(ctk.CTkFrame)` with `__init__` accepting:
     - `master: Any`
     - `items_callback: Callable[[str], List[Dict[str, Any]]]` (required)
     - `on_select_callback: Callable[[Dict[str, Any]], None]` (required)
     - `min_chars: int = 3`
     - `debounce_ms: int = 300`
     - `max_results: int = 10`
     - `placeholder_text: str = "Type at least 3 characters to search..."`
     - `clear_on_select: bool = True`
     - `display_key: str = "display_name"`
     - `**kwargs` passed to `CTkFrame.__init__`
  3. Call `super().__init__(master, fg_color="transparent")` (not passing `**kwargs` to avoid CTkFrame parameter conflicts -- only pass known CTkFrame kwargs)
  4. Store all parameters as instance attributes
  5. Initialize internal state:
     ```python
     self._debounce_id: Optional[str] = None
     self._dropdown: Optional[ctk.CTkToplevel] = None
     self._results: List[Dict[str, Any]] = []
     self._highlight_index: int = -1
     self._result_labels: List[ctk.CTkLabel] = []
     ```
  6. Create `CTkEntry` widget:
     ```python
     self._entry = ctk.CTkEntry(
         self,
         placeholder_text=placeholder_text,
     )
     self._entry.pack(fill="x", expand=True)
     ```
  7. Bind `<KeyRelease>` on `self._entry` to `self._on_key_release`
  8. Add public methods as stubs: `clear()`, `get_text()`, `set_focus()`, `destroy()`

- **Files**: `src/ui/widgets/type_ahead_entry.py` (new file)
- **Notes**: Do NOT add `__init__.py` exports yet -- widget is imported directly by path.

### Subtask T002 -- Implement Debounce Search Trigger

- **Purpose**: Ensure search only fires after user pauses typing, preventing excessive callback invocations.
- **Steps**:
  1. Implement `_on_key_release(self, event)`:
     - Ignore navigation keys: `Up`, `Down`, `Return`, `Tab`, `Escape` (these are handled separately)
     - Get current text: `query = self._entry.get().strip()`
     - If `len(query) < self.min_chars`: call `self._hide_dropdown()` and return
     - Cancel any pending debounce: `if self._debounce_id: self.after_cancel(self._debounce_id)`
     - Schedule new search: `self._debounce_id = self.after(self.debounce_ms, lambda: self._execute_search(query))`
  2. Implement `_execute_search(self, query: str)`:
     - Reset debounce ID: `self._debounce_id = None`
     - Call callback with try/except:
       ```python
       try:
           results = self._items_callback(query)
       except Exception:
           results = []
       ```
     - Store results: `self._results = results`
     - Reset highlight: `self._highlight_index = -1`
     - If no results: call `self._show_no_results(query)`
     - If results: call `self._show_results(results)`

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**: The lambda captures `query` at schedule time, not at execution time. This is important -- if the user keeps typing, the old query is stale but gets cancelled by `after_cancel`. Only the latest query survives.

### Subtask T003 -- Create Floating CTkToplevel Dropdown

- **Purpose**: Display search results in a positioned overlay window that doesn't disrupt parent layout.
- **Steps**:
  1. Implement `_create_dropdown(self)`:
     - If `self._dropdown` exists and is still valid (use `winfo_exists()`), reuse it
     - Otherwise create new:
       ```python
       self._dropdown = ctk.CTkToplevel(self)
       self._dropdown.overrideredirect(True)
       self._dropdown.wm_attributes("-topmost", True)
       self._dropdown.configure(fg_color=("gray92", "gray14"))
       ```
     - Create a scrollable frame or simple frame inside for result items
     - Do NOT call `self._dropdown.focus_set()` -- keep focus on the entry
  2. Implement `_position_dropdown(self)`:
     - Calculate position from entry widget:
       ```python
       x = self._entry.winfo_rootx()
       y = self._entry.winfo_rooty() + self._entry.winfo_height()
       width = self._entry.winfo_width()
       ```
     - Apply geometry: `self._dropdown.geometry(f"{width}x{height}+{x}+{y}")`
     - Height is dynamic based on number of items (each item ~30px)
  3. Implement `_hide_dropdown(self)`:
     - If `self._dropdown` exists: `self._dropdown.withdraw()` (hide, don't destroy -- reuse)
     - Clear result labels list
     - Reset `self._highlight_index = -1`
  4. Implement `_show_results(self, results: List[Dict])`:
     - Call `_create_dropdown()`
     - Clear any existing children in dropdown frame
     - Populate with result items (see T004)
     - Call `_position_dropdown()`
     - Show: `self._dropdown.deiconify()`

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - Use `withdraw()`/`deiconify()` instead of repeated `destroy()`/create for performance
  - `overrideredirect(True)` removes title bar (critical for dropdown feel)
  - The dropdown MUST NOT steal focus from the entry. User continues typing while dropdown is visible.
  - Consider using `wm_transient(self.winfo_toplevel())` to associate the dropdown with the main window

### Subtask T004 -- Render Search Results with Messages

- **Purpose**: Display search results as clickable items, plus "no match" and truncation messages.
- **Steps**:
  1. In `_show_results(self, results)`:
     - Determine display count: `display_results = results[:self.max_results]`
     - Clear `self._result_labels`
     - For each result, create a `CTkLabel`:
       ```python
       text = result.get(self._display_key, str(result))
       label = ctk.CTkLabel(
           self._dropdown_frame,
           text=text,
           anchor="w",
           padx=8,
           pady=4,
           cursor="hand2",
       )
       label.pack(fill="x")
       label.bind("<Button-1>", lambda e, item=result: self._on_item_click(item))
       self._result_labels.append(label)
       ```
     - If `len(results) > self.max_results`: add truncation label:
       ```python
       msg = f"Showing {self.max_results} of {len(results)}+ results. Refine search for more."
       trunc_label = ctk.CTkLabel(
           self._dropdown_frame,
           text=msg,
           text_color="gray50",
           anchor="w",
           padx=8,
           pady=4,
       )
       trunc_label.pack(fill="x")
       ```
  2. Implement `_show_no_results(self, query: str)`:
     - Create/show dropdown with single message label:
       ```python
       msg = f"No items match '{query}'"
       ```
     - Style as italic/gray to distinguish from selectable items

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - Labels use `anchor="w"` for left-aligned text
  - `cursor="hand2"` gives pointer cursor on hover (visual affordance for clickability)
  - The truncation message is NOT clickable (no `<Button-1>` binding, no cursor change)
  - Dropdown height = (number of visible items + optional message) * item_height

### Subtask T005 -- Selection, Dismissal, and Cleanup

- **Purpose**: Complete the selection flow and ensure clean widget lifecycle.
- **Steps**:
  1. Implement `_on_item_click(self, item: Dict)`:
     - Call `self._on_select_callback(item)` with try/except (catch and log errors)
     - If `self.clear_on_select`: `self._entry.delete(0, "end")`
     - Call `self._hide_dropdown()`
  2. Implement Escape dismissal:
     - Bind `<Escape>` on `self._entry`:
       ```python
       self._entry.bind("<Escape>", self._on_escape)
       ```
     - `_on_escape`: call `_hide_dropdown()`, return `"break"` to prevent propagation
  3. Implement focus-out dismissal:
     - Bind `<FocusOut>` on `self._entry`:
       ```python
       self._entry.bind("<FocusOut>", self._on_focus_out)
       ```
     - `_on_focus_out`: schedule `self.after(150, self._check_focus_and_hide)` to allow dropdown clicks to process first
     - `_check_focus_and_hide`: check if focus moved to dropdown → if not, hide dropdown
  4. Implement public methods:
     - `clear()`: `self._entry.delete(0, "end")` + `self._hide_dropdown()`
     - `get_text()`: `return self._entry.get()`
     - `set_focus()`: `self._entry.focus_set()`
  5. Override `destroy()`:
     ```python
     def destroy(self):
         if self._debounce_id:
             self.after_cancel(self._debounce_id)
         if self._dropdown and self._dropdown.winfo_exists():
             self._dropdown.destroy()
         super().destroy()
     ```

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - The 150ms delay in focus-out is CRITICAL. Without it, clicking a dropdown item triggers `FocusOut` before `Button-1`, causing the dropdown to close before the click registers.
  - `return "break"` on Escape prevents the event from propagating to parent widgets.
  - `_on_select_callback` errors should not crash the widget -- catch and continue.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CTkToplevel focus stealing on macOS | Never call `focus_set()` on dropdown; keep focus on entry |
| FocusOut fires before dropdown click | 150ms delay before hiding; check actual focus target |
| Stale debounce callbacks after widget destroyed | Cancel in `destroy()`; check `winfo_exists()` |
| Memory leak from unreleased toplevel | Explicit `destroy()` in cleanup; `withdraw()` for reuse |

## Definition of Done Checklist

- [ ] `src/ui/widgets/type_ahead_entry.py` created with all constructor parameters
- [ ] Debounce fires after configurable delay, cancels on continued typing
- [ ] Floating dropdown appears below entry with correct positioning
- [ ] Results render with display_key text, clickable
- [ ] "No items match" message shows for empty results
- [ ] Truncation message shows when results > max_results
- [ ] Click selection fires callback and optionally clears entry
- [ ] Escape, focus-out, tab-away close dropdown
- [ ] destroy() cleans up debounce and toplevel
- [ ] Module is under 500 lines

## Review Guidance

- Verify no service imports in the widget module (constitution V)
- Verify debounce pattern matches codebase standard (after/after_cancel)
- Test focus-out timing: click a dropdown item, verify it doesn't dismiss before selection
- Test with empty callback results and with callback that raises exception
- Check CTkToplevel behavior on macOS: no title bar, stays above parent

## Activity Log

- 2026-02-10T21:59:40Z -- system -- lane=planned -- Prompt created.
