---
work_package_id: "WP04"
subtasks:
  - "T019"
  - "T020"
  - "T021"
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
title: "TypeAheadComboBox Widget"
phase: "Phase 1 - Widgets"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "33920"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-24T23:15:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – TypeAheadComboBox Widget

## Objectives & Success Criteria

**Goal**: Create reusable type-ahead filtering widget for Category/Ingredient/Product dropdowns.

**Success Criteria**:
- [ ] Typing "bak" filters dropdown to items containing "bak"
- [ ] Word boundary matches prioritized (e.g., "ap" matches "AP Flour" before "Maple")
- [ ] Case-insensitive matching
- [ ] min_chars parameter controls filter threshold
- [ ] reset_values() allows dynamic content updates
- [ ] Native CTk keyboard navigation preserved
- [ ] All unit tests pass

## Context & Constraints

**References**:
- Plan: `kitty-specs/029-streamlined-inventory-entry/plan.md` (PD-002: Type-Ahead Widget)
- Research: `kitty-specs/029-streamlined-inventory-entry/research.md` (RQ-002)
- Design: `docs/design/F029_streamlined_inventory_entry.md` (TypeAheadComboBox section)

**Constraints**:
- Subclass CTkFrame, wrap CTkComboBox (not subclass CTkComboBox directly)
- Do NOT override CTk's dropdown rendering
- Do NOT reimplement keyboard navigation
- Focus on filtering algorithm correctness

## Subtasks & Detailed Guidance

### Subtask T019 – Create widgets __init__.py

**Purpose**: Establish widgets package.

**Steps**:
1. Create `src/ui/widgets/__init__.py` if not exists
2. Add empty file or minimal docstring

**Files**: `src/ui/widgets/__init__.py` (NEW if not exists)

### Subtask T020 – Create type_ahead_combobox.py

**Purpose**: Establish module for type-ahead widget.

**Steps**:
1. Create `src/ui/widgets/type_ahead_combobox.py`
2. Add imports: customtkinter, List from typing

**Files**: `src/ui/widgets/type_ahead_combobox.py` (NEW)

### Subtask T021 – Subclass CTkFrame, embed CTkComboBox

**Purpose**: Create composite widget structure.

**Steps**:
1. Define `TypeAheadComboBox(ctk.CTkFrame)` class
2. Create embedded CTkComboBox in __init__
3. Store reference to internal entry widget for key binding

**Code Pattern**:
```python
class TypeAheadComboBox(ctk.CTkFrame):
    """
    Enhanced CTkComboBox with type-ahead filtering.

    Features:
    - Real-time filtering as user types
    - Minimum character threshold before filtering
    - Word boundary prioritization in matches
    - Preserves full values list for reset
    """

    def __init__(
        self,
        master,
        values: List[str] = None,
        min_chars: int = 2,
        command=None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent")

        self.full_values = values or []
        self.min_chars = min_chars
        self.filtered = False
        self._command = command

        # Create embedded combobox
        self._combobox = ctk.CTkComboBox(
            self,
            values=self.full_values,
            command=self._on_select,
            **kwargs
        )
        self._combobox.pack(fill="x", expand=True)

        # Get entry widget for key binding
        self._entry = self._combobox._entry

        # Bind events
        self._entry.bind('<KeyRelease>', self._on_key_release)
        self._entry.bind('<FocusOut>', self._on_focus_out)
```

### Subtask T022 – Implement filter algorithm

**Purpose**: Core filtering logic with word boundary prioritization.

**Steps**:
1. Implement `_filter_values(typed)` method
2. Split values into word_boundary and contains lists
3. Return word_boundary first, then contains

**Code**:
```python
def _filter_values(self, typed: str) -> List[str]:
    """
    Filter values list based on typed text.

    Prioritizes word boundary matches over contains matches.
    """
    typed_lower = typed.lower()

    word_boundary = []
    contains = []

    for value in self.full_values:
        value_lower = value.lower()

        # Check word boundaries (starts with or after space/punctuation)
        words = value_lower.split()
        is_word_boundary = any(word.startswith(typed_lower) for word in words)

        if is_word_boundary:
            word_boundary.append(value)
        elif typed_lower in value_lower:
            contains.append(value)

    return word_boundary + contains
```

### Subtask T023 – Bind KeyRelease event

**Purpose**: Trigger filtering on each keystroke.

**Steps**:
1. Implement `_on_key_release(event)` handler
2. Ignore navigation keys
3. Check min_chars threshold
4. Apply filter or reset

**Code**:
```python
def _on_key_release(self, event):
    """Handle key release for type-ahead filtering."""
    # Ignore navigation keys
    if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Tab', 'Escape'):
        return

    typed = self.get()

    # Reset filter if below threshold
    if len(typed) < self.min_chars:
        if self.filtered:
            self._combobox.configure(values=self.full_values)
            self.filtered = False
        return

    # Apply filter
    filtered = self._filter_values(typed)
    if filtered:
        self._combobox.configure(values=filtered)
        self.filtered = True
```

### Subtask T024 – Implement reset_values()

**Purpose**: Allow dynamic content updates when category/ingredient changes.

**Steps**:
1. Implement `reset_values(values)` method
2. Update both full_values and combobox values
3. Clear filtered state

**Code**:
```python
def reset_values(self, values: List[str]):
    """
    Update the full values list.

    Call this when underlying data changes (e.g., category selected).
    """
    self.full_values = values
    self._combobox.configure(values=values)
    self.filtered = False
```

### Subtask T025 – Add min_chars parameter

**Purpose**: Allow different thresholds for different dropdowns.

**Steps**:
1. Already in __init__ signature
2. Document: Category uses 1, Ingredient/Product use 2
3. Ensure threshold check works correctly

**Notes**:
- Category: min_chars=1 (filter on single character)
- Ingredient/Product: min_chars=2 (require 2 characters)

### Subtask T026 – Create unit tests [P]

**Purpose**: Verify widget behavior.

**Steps**:
1. Create `src/tests/ui/test_type_ahead_combobox.py`
2. Test filtering algorithm
3. Test word boundary prioritization

**Test Cases**:
```python
import pytest
from src.ui.widgets.type_ahead_combobox import TypeAheadComboBox

class TestFilterAlgorithm:
    """Test the filtering algorithm directly."""

    def test_word_boundary_priority(self):
        """Word boundary matches should come before contains matches."""
        widget = TypeAheadComboBox(None, values=[
            'All-Purpose Flour',
            'Maple Syrup',
            'Apple Cider'
        ])
        # Note: Can't fully test without Tk root, test _filter_values directly
        result = widget._filter_values('ap')
        # 'All-Purpose' and 'Apple' start with 'ap', 'Maple' contains 'ap'
        assert result.index('All-Purpose Flour') < result.index('Maple Syrup')
        assert result.index('Apple Cider') < result.index('Maple Syrup')

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        widget = TypeAheadComboBox(None, values=['FLOUR', 'flour', 'Flour'])
        result = widget._filter_values('flour')
        assert len(result) == 3

    def test_empty_typed_returns_empty(self):
        """Empty typed string returns empty list."""
        widget = TypeAheadComboBox(None, values=['Flour', 'Sugar'])
        result = widget._filter_values('')
        assert result == []

    def test_no_matches_returns_empty(self):
        """No matches returns empty list."""
        widget = TypeAheadComboBox(None, values=['Flour', 'Sugar'])
        result = widget._filter_values('xyz')
        assert result == []

    def test_reset_values(self):
        """reset_values should update full_values."""
        widget = TypeAheadComboBox(None, values=['A', 'B'])
        widget.reset_values(['X', 'Y', 'Z'])
        assert widget.full_values == ['X', 'Y', 'Z']
```

**Files**: `src/tests/ui/test_type_ahead_combobox.py` (NEW)

**Parallel?**: Yes, can be written alongside implementation

## Test Strategy

Run tests with:
```bash
pytest src/tests/ui/test_type_ahead_combobox.py -v
```

Note: Full widget tests may require Tk root. Focus on algorithm tests.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| CTk ComboBox internal structure changes | Pin customtkinter version |
| Focus management issues | Test tab navigation manually |
| Event binding conflicts | Review CTk source for conflicts |

## Definition of Done Checklist

- [ ] TypeAheadComboBox class implemented
- [ ] Filtering works with word boundary priority
- [ ] min_chars threshold respected
- [ ] reset_values() updates content
- [ ] All unit tests pass
- [ ] No linting errors

## Review Guidance

**Reviewers should verify**:
1. Word boundary prioritization works (test with "ap" on Flour/Maple)
2. Case insensitivity works
3. Reset clears filter state
4. Native navigation keys not intercepted

## Activity Log

- 2025-12-24T23:15:00Z – system – lane=planned – Prompt created.
- 2025-12-25T05:06:12Z – claude – shell_pid=33920 – lane=doing – Starting implementation
- 2025-12-25T05:09:18Z – claude – shell_pid=33920 – lane=for_review – All 16 tests pass. Widget ready.
- 2025-12-25T06:40:04Z – claude – shell_pid=33920 – lane=done – Moved to done
