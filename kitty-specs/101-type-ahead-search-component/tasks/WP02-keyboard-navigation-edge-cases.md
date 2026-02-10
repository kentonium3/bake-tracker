---
work_package_id: WP02
title: Keyboard Navigation & Edge Cases
lane: "for_review"
dependencies: [WP01]
base_branch: 101-type-ahead-search-component-WP01
base_commit: 0e019b4b9408cb10a77bbdfd504c4ad55fe90cfb
created_at: '2026-02-10T22:13:06.679255+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 0 - Foundation
assignee: ''
agent: "claude-opus"
shell_pid: "88543"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-10T21:59:40Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 -- Keyboard Navigation & Edge Cases

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
spec-kitty implement WP02 --base WP01
```

Depends on WP01 - branches from WP01's completed work.

---

## Objectives & Success Criteria

Add keyboard navigation and edge case handling to the `TypeAheadEntry` widget created in WP01:

1. Down/Up Arrow keys navigate dropdown items with visual highlighting
2. Enter key selects the highlighted item (no-op if nothing highlighted)
3. Click-outside detection closes dropdown
4. Screen edge clamping prevents dropdown going off-screen
5. Edge cases: special characters, rapid typing, exact match, multiple instances

**Success Criteria:**
- Full ingredient selection possible using only keyboard (type, arrow, Enter) without mouse (US2)
- Arrow Down at last item stays on last item (no wrap) (FR-009)
- Arrow Up at first item stays on first item (no wrap) (FR-009)
- Enter with no item highlighted does nothing (FR-009)
- Highlighted item has visually distinct background (US2-AS2)
- Clicking outside dropdown area closes it (edge case: focus loss)
- Dropdown doesn't go off-screen when entry is near screen edge
- Two TypeAheadEntry widgets on same form maintain independent state
- Queries with `&`, `/`, `-`, `()` work correctly (edge case: special characters)
- Rapid typing only fires one search per pause (edge case: rapid typing / debounce)

## Context & Constraints

- **Spec**: `kitty-specs/101-type-ahead-search-component/spec.md` (US2, FR-004, FR-008, FR-009, edge cases)
- **Plan**: `kitty-specs/101-type-ahead-search-component/plan.md` (D4: no wrap, D1: dropdown positioning)
- **Data Model**: `kitty-specs/101-type-ahead-search-component/data-model.md` (event flow for keyboard nav)
- **Contract**: `kitty-specs/101-type-ahead-search-component/contracts/type_ahead_entry_contract.md` (keyboard bindings, invariants)
- **Constitution**: `.kittify/memory/constitution.md`

**Key Constraints:**
- Keyboard navigation operates on `self._result_labels` created in WP01
- Highlight index tracking uses `self._highlight_index` initialized in WP01 (starts at -1)
- Arrow key bindings must be on `self._entry` (not the dropdown) since entry keeps focus
- Click-outside must NOT interfere with dropdown item clicks (coordinate check required)
- Widget must remain under 500 lines total (including WP01 code)

## Subtasks & Detailed Guidance

### Subtask T006 -- Down Arrow Key Navigation

- **Purpose**: Allow keyboard-only navigation to the next item in the dropdown.
- **Steps**:
  1. Bind `<Down>` on `self._entry`:
     ```python
     self._entry.bind("<Down>", self._on_arrow_down)
     ```
  2. Implement `_on_arrow_down(self, event)`:
     - If dropdown not visible or no results: return
     - Increment `self._highlight_index`
     - Clamp at `len(self._results) - 1` (no wrap per FR-009):
       ```python
       self._highlight_index = min(self._highlight_index + 1, len(self._results) - 1)
       ```
     - Call `self._update_highlight()`
     - Return `"break"` to prevent default cursor movement in entry

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**: The `"break"` return is important -- without it, the cursor would move to the end of the entry text.

### Subtask T007 -- Up Arrow Key Navigation

- **Purpose**: Allow keyboard-only navigation to the previous item in the dropdown.
- **Steps**:
  1. Bind `<Up>` on `self._entry`:
     ```python
     self._entry.bind("<Up>", self._on_arrow_up)
     ```
  2. Implement `_on_arrow_up(self, event)`:
     - If dropdown not visible or no results: return
     - Decrement `self._highlight_index`
     - Clamp at 0 (no wrap per FR-009):
       ```python
       self._highlight_index = max(self._highlight_index - 1, 0)
       ```
     - If `_highlight_index` was already 0 before decrement: stay at 0
     - Call `self._update_highlight()`
     - Return `"break"`

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**: Consider whether Up from index 0 should go to -1 (deselect) or stay at 0. Per US2-AS6, "highlight stays on the first item" → clamp at 0, do not deselect.

### Subtask T008 -- Visual Highlight Styling

- **Purpose**: Provide clear visual feedback for which item is selected via keyboard.
- **Steps**:
  1. Implement `_update_highlight(self)`:
     - Iterate over `self._result_labels`:
       ```python
       for i, label in enumerate(self._result_labels):
           if i == self._highlight_index:
               label.configure(
                   fg_color=("gray78", "gray30"),  # Highlighted
                   text_color=("gray10", "gray90"),
               )
           else:
               label.configure(
                   fg_color="transparent",  # Normal
                   text_color=("gray10", "gray90"),
               )
       ```
  2. The highlight colors should be distinct but fit the CustomTkinter theme
     - Use tuple `(light_mode, dark_mode)` for both appearance modes
     - Test that highlighted item is clearly distinguishable from non-highlighted

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - The highlight must reset when new search results arrive (already handled by `_highlight_index = -1` in `_execute_search`)
  - Consider adding hover effect on mouse (`<Enter>`/`<Leave>` events) for visual consistency, but this is optional -- mouse hover highlighting is nice-to-have, keyboard highlight is required.

### Subtask T009 -- Enter Key Selection

- **Purpose**: Allow keyboard-only item selection without requiring mouse click.
- **Steps**:
  1. Bind `<Return>` on `self._entry`:
     ```python
     self._entry.bind("<Return>", self._on_enter)
     ```
  2. Implement `_on_enter(self, event)`:
     - If dropdown not visible: return (do nothing)
     - If `self._highlight_index == -1`: return (no-op per FR-009)
     - If `self._highlight_index >= len(self._results)`: return (safety check)
     - Get selected item: `item = self._results[self._highlight_index]`
     - Call `self._on_item_click(item)` (reuse the mouse click handler from WP01)
     - Return `"break"` to prevent form submission

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - CRITICAL: Return `"break"` to prevent the Enter key from triggering form submission or other default behaviors.
  - The spec explicitly says "Given dropdown open with no item highlighted, When user presses Enter, Then nothing happens" (US2-AS7).

### Subtask T010 -- Click-Outside Detection

- **Purpose**: Close the dropdown when user clicks anywhere outside it (FR-008).
- **Steps**:
  1. When dropdown is shown, bind click detection on the root window:
     ```python
     self._root_click_id = self.winfo_toplevel().bind("<Button-1>", self._on_root_click, add="+")
     ```
  2. When dropdown is hidden, unbind:
     ```python
     self.winfo_toplevel().unbind("<Button-1>", self._root_click_id)
     ```
  3. Implement `_on_root_click(self, event)`:
     - Get click coordinates: `event.x_root`, `event.y_root`
     - Get dropdown bounds:
       ```python
       dx = self._dropdown.winfo_rootx()
       dy = self._dropdown.winfo_rooty()
       dw = self._dropdown.winfo_width()
       dh = self._dropdown.winfo_height()
       ```
     - Also get entry bounds (clicks on entry should NOT close dropdown):
       ```python
       ex = self._entry.winfo_rootx()
       ey = self._entry.winfo_rooty()
       ew = self._entry.winfo_width()
       eh = self._entry.winfo_height()
       ```
     - If click is outside BOTH entry and dropdown: `self._hide_dropdown()`
  4. Use `add="+"` to avoid removing other bindings on the root window

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - CRITICAL: Must check both entry AND dropdown bounds. Clicking the entry itself should NOT close the dropdown.
  - CRITICAL: Must use `add="+"` with `bind` to avoid removing other handlers.
  - The bind/unbind lifecycle must be robust: don't unbind if never bound, handle widget destruction gracefully.
  - Store `self._root_click_id` for proper unbinding.

### Subtask T011 -- Screen Edge Clamping & Multiple Instances

- **Purpose**: Ensure dropdown is always visible and multiple widgets don't interfere.
- **Steps**:
  1. In `_position_dropdown()`, add screen edge clamping:
     ```python
     screen_width = self.winfo_screenwidth()
     screen_height = self.winfo_screenheight()

     # Clamp horizontal
     if x + width > screen_width:
         x = screen_width - width

     # Clamp vertical - if dropdown would go below screen, show above entry
     if y + height > screen_height:
         y = self._entry.winfo_rooty() - height

     # Ensure not negative
     x = max(0, x)
     y = max(0, y)
     ```
  2. For multiple instances, verify independent state:
     - Each widget has its own `_dropdown`, `_results`, `_highlight_index`, `_debounce_id`
     - Each widget's `_on_root_click` only checks its own dropdown bounds
     - When one widget's dropdown opens, other widgets' dropdowns should remain unaffected (they close on their own focus-out)

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**:
  - The "show above" fallback when below-screen is a nice touch but not required. At minimum, clamp to screen bounds.
  - Multiple instances should "just work" since all state is instance-based. No class-level state.
  - Test scenario: two TypeAheadEntry widgets side by side on the same form.

### Subtask T012 -- Edge Case Hardening

- **Purpose**: Handle special characters, rapid typing, and exact match scenarios per spec edge cases.
- **Steps**:
  1. **Special characters** (`&`, `/`, `-`, `()`):
     - The widget passes the raw query to the callback unchanged. No escaping or sanitization.
     - Verify that typing `salt & pepper` or `(baking)` doesn't crash the widget.
     - This is primarily the callback's responsibility, but the widget must not break.
  2. **Rapid typing / debounce cancellation**:
     - Already handled by T002's debounce pattern. Verify:
       - Typing 10 characters rapidly results in only 1 search call (the last one after debounce_ms pause)
       - Intermediate debounce timers are properly cancelled
  3. **Exact match** (user types full name like "Chocolate Chips"):
     - Widget still shows dropdown with matching results (no auto-select per spec decision)
     - User must explicitly click or press Enter to select
  4. **Rapid tab-through**:
     - If user tabs into and out of field without typing: no dropdown appears, no search fires
     - Verify `<FocusOut>` handler doesn't crash when there's no dropdown to hide
  5. **Empty/whitespace-only input**:
     - `query.strip()` in `_on_key_release` handles this -- results in length check failure → no search

- **Files**: `src/ui/widgets/type_ahead_entry.py`
- **Notes**: Most edge cases are "verify existing behavior" rather than new code. Focus on ensuring the debounce and focus handlers don't have unexpected interactions.

## Test Strategy

Write unit tests in `src/tests/test_type_ahead_entry.py`:

1. **Test keyboard navigation bounds**:
   - Arrow Down at last item stays at last item
   - Arrow Up at first item stays at first item
   - Enter with no highlight does nothing
   - Enter with highlight calls on_select_callback
2. **Test click-outside detection**:
   - Click inside dropdown doesn't close it
   - Click on entry doesn't close dropdown
   - Click outside both closes dropdown
3. **Test highlight visual state**:
   - Highlight resets on new search results
   - Only one item highlighted at a time

Note: Testing tkinter widgets requires careful setup. If direct widget testing is impractical, document manual test scenarios instead.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Click-outside binding interferes with dropdown clicks | Check coordinates against both entry and dropdown bounds |
| Root window binding not properly unbound | Track bind ID; unbind in both `_hide_dropdown` and `destroy` |
| Arrow key events propagate to parent | Return `"break"` from all arrow/enter handlers |
| Highlight index out of sync with results | Reset to -1 on every new search; bounds-check before access |
| Multiple instances' root bindings conflict | Each instance binds with `add="+"` and only checks its own dropdown |

## Definition of Done Checklist

- [ ] Down/Up Arrow keys navigate dropdown items with clamping at boundaries
- [ ] Highlighted item has visually distinct background
- [ ] Enter selects highlighted item; no-op when nothing highlighted
- [ ] Click outside dropdown and entry closes dropdown
- [ ] Click on entry or dropdown does NOT close dropdown
- [ ] Dropdown stays within screen bounds
- [ ] Two widgets on same form maintain independent state
- [ ] Special characters in queries don't crash widget
- [ ] Rapid typing fires only one search per pause
- [ ] Exact match still shows dropdown (no auto-select)
- [ ] Tests written for keyboard navigation

## Review Guidance

- Manually test full keyboard-only workflow: Tab to field → type → Arrow Down → Arrow Down → Enter → verify selection
- Test boundary behavior: Arrow Down past last item, Arrow Up past first item
- Test Enter with no highlight -- should do absolutely nothing
- Test click-outside: click different areas (entry, dropdown, outside both)
- Verify no `TclError` exceptions when navigating with empty results

## Activity Log

- 2026-02-10T21:59:40Z -- system -- lane=planned -- Prompt created.
- 2026-02-10T22:13:07Z – claude-opus – shell_pid=88543 – lane=doing – Assigned agent via workflow command
- 2026-02-10T22:17:31Z – claude-opus – shell_pid=88543 – lane=for_review – All WP02 subtasks complete. Widget code from WP01 already implemented all keyboard nav, click-outside, screen edge clamping. WP02 added 11 new tests (51 total) covering click-outside detection, multiple instances, full keyboard workflow. All 51 tests pass.
