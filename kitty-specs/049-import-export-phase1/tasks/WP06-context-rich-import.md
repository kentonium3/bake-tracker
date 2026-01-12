---
work_package_id: "WP06"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
  - "T051"
  - "T052"
  - "T053"
  - "T054"
title: "Context-Rich Import with Auto-Detection"
phase: "Phase 3 - Wave 2"
lane: "done"
assignee: ""
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

# Work Package Prompt: WP06 - Context-Rich Import with Auto-Detection

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Extend `enhanced_import_service.py` with format auto-detection and context-rich import handling.

**Success Criteria**:
- SC-009: Format auto-detection correctly identifies normalized vs context-rich in 100% of test cases
- FR-013: System MUST auto-detect import format (normalized vs context-rich)
- FR-014: System MUST extract only editable fields from context-rich imports (ignore computed fields)

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/049-import-export-phase1/spec.md` (User Story 6)
- Plan: `kitty-specs/049-import-export-phase1/plan.md`
- Research: `kitty-specs/049-import-export-phase1/research.md` (Section 6)

**Detection Algorithm**:
```python
def detect_format(data: dict) -> str:
    if "_meta" in data and "editable_fields" in data.get("_meta", {}):
        return "context_rich"
    if "version" in data and "application" in data:
        return "normalized"
    if "import_type" in data:
        if data["import_type"] == "purchases":
            return "purchases"
        if data["import_type"] in ("adjustments", "inventory_updates"):
            return "adjustments"
    return "unknown"
```

**Dependency**: WP03 (Context-Rich Export) must be complete to have `_meta` sections to detect.

---

## Subtasks & Detailed Guidance

### Subtask T047 - Add `detect_format()` function

**Purpose**: Identify import file format automatically.

**Steps**:
1. Open `src/services/enhanced_import_service.py`
2. Add detection function:
```python
from typing import Literal

FormatType = Literal["context_rich", "normalized", "purchases", "adjustments", "unknown"]

def detect_format(file_path: str) -> tuple[FormatType, dict]:
    """
    Detect the format of an import file.

    Args:
        file_path: Path to JSON file

    Returns:
        Tuple of (format_type, parsed_data)
    """
    with open(file_path) as f:
        data = json.load(f)

    format_type = _detect_format_from_data(data)
    return format_type, data


def _detect_format_from_data(data: dict) -> FormatType:
    """Detect format from parsed JSON data."""
    # Check for context-rich view format
    if "_meta" in data and "editable_fields" in data.get("_meta", {}):
        return "context_rich"

    # Check for transaction imports
    import_type = data.get("import_type")
    if import_type == "purchases":
        return "purchases"
    if import_type in ("adjustments", "inventory_updates"):
        return "adjustments"

    # Check for normalized backup/catalog format
    if "version" in data and data.get("application") == "bake-tracker":
        return "normalized"

    return "unknown"
```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T048 - Detect context-rich by `_meta` field

**Purpose**: Context-rich exports have `_meta.editable_fields`.

**Steps**:
1. Context-rich format has:
```json
{
  "view_type": "ingredients",
  "_meta": {
    "editable_fields": ["description", "notes", ...],
    "readonly_fields": ["id", "slug", ...]
  },
  "records": [...]
}
```
2. Check for nested structure:
```python
if "_meta" in data:
    meta = data["_meta"]
    if isinstance(meta, dict) and "editable_fields" in meta:
        return "context_rich"
```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T049 - Detect normalized by `version` + `application`

**Purpose**: Normalized backup/catalog format has version header.

**Steps**:
1. Normalized format has:
```json
{
  "version": "4.0",
  "application": "bake-tracker",
  "exported_at": "...",
  "ingredients": [...],
  "products": [...]
}
```
2. Check for both fields:
```python
if data.get("version") and data.get("application") == "bake-tracker":
    return "normalized"
```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T050 - Extract editable fields only from context-rich

**Purpose**: When importing context-rich, only use editable fields.

**Steps**:
1. Create extraction function:
```python
def extract_editable_fields(record: dict, meta: dict) -> dict:
    """
    Extract only editable fields from a context-rich record.

    Args:
        record: Full record with all fields
        meta: _meta section with editable_fields list

    Returns:
        Dict containing only editable fields
    """
    editable_fields = set(meta.get("editable_fields", []))
    return {k: v for k, v in record.items() if k in editable_fields}
```
2. Use during import:
```python
for record in data.get("records", []):
    editable_data = extract_editable_fields(record, data["_meta"])
    # Use editable_data for update, ignore other fields
```

**Files**: `src/services/enhanced_import_service.py`

### Subtask T051 - Ignore readonly/computed fields during import

**Purpose**: Computed values in context-rich should not be imported.

**Steps**:
1. Readonly fields are explicitly ignored:
```python
def import_context_rich_view(file_path: str, dry_run: bool = False) -> ImportResult:
    """Import context-rich view file, merging editable fields."""
    result = ImportResult()

    format_type, data = detect_format(file_path)
    if format_type != "context_rich":
        result.add_error("file", file_path, f"Expected context-rich format, got {format_type}")
        return result

    meta = data["_meta"]
    view_type = data.get("view_type")  # "ingredients", "materials", "recipes"

    with session_scope() as session:
        for record in data.get("records", []):
            # Extract only editable fields
            editable_data = extract_editable_fields(record, meta)

            # Find existing record by slug (always in readonly)
            slug = record.get("slug")
            existing = find_by_slug(view_type, slug, session)

            if existing:
                # Merge editable fields
                merge_fields(existing, editable_data)
                result.add_success(view_type)
            else:
                result.add_skip(view_type, slug, "Record not found for merge")
```
2. Computed fields (inventory_total, average_cost, etc.) silently ignored

**Files**: `src/services/enhanced_import_service.py`

### Subtask T052 - Merge editable fields with existing records

**Purpose**: Update existing records with augmented editable data.

**Steps**:
1. Create merge function:
```python
def merge_fields(entity, editable_data: dict):
    """
    Update entity with editable field values.

    Only updates fields that are present in editable_data.
    Does not clear fields not present in the update.
    """
    for field, value in editable_data.items():
        if hasattr(entity, field):
            setattr(entity, field, value)
```
2. This is a merge, not a replace - missing fields keep current value

**Files**: `src/services/enhanced_import_service.py`

### Subtask T053 - Return detection result for UI confirmation

**Purpose**: UI needs to display detected format before import.

**Steps**:
1. Create data class for detection result:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FormatDetectionResult:
    """Result of format auto-detection."""
    format_type: FormatType
    view_type: Optional[str] = None  # For context-rich: "ingredients", etc.
    entity_count: int = 0
    editable_fields: list = None
    version: Optional[str] = None  # For normalized

    @property
    def display_name(self) -> str:
        """Human-readable format name for UI."""
        names = {
            "context_rich": f"Context-Rich View ({self.view_type})",
            "normalized": f"Normalized Backup (v{self.version})",
            "purchases": "Purchase Transactions",
            "adjustments": "Inventory Adjustments",
            "unknown": "Unknown Format"
        }
        return names.get(self.format_type, "Unknown")
```
2. UI will call `detect_format()` and show confirmation dialog

**Files**: `src/services/enhanced_import_service.py`

### Subtask T054 - Add unit tests

**Purpose**: Test format detection and context-rich import.

**Steps**:
1. Open `src/tests/services/test_enhanced_import_service.py`
2. Add tests:
   - `test_detect_format_context_rich()`
   - `test_detect_format_normalized()`
   - `test_detect_format_purchases()`
   - `test_detect_format_adjustments()`
   - `test_detect_format_unknown()`
   - `test_extract_editable_fields_only()`
   - `test_import_context_rich_ignores_computed()`
   - `test_import_context_rich_merges_existing()`
   - `test_detection_result_display_name()`

**Files**: `src/tests/services/test_enhanced_import_service.py`

---

## Test Strategy

**Unit Tests** (required):
- Test each format detection case
- Test editable field extraction
- Test merge behavior
- Test 100% detection accuracy (SC-009)

**Run Tests**:
```bash
./run-tests.sh src/tests/services/test_enhanced_import_service.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Detection ambiguity | Test with all known file formats |
| Missing view_type handling | Support all view types from WP03 |
| Merge conflicts | Only update present fields |

---

## Definition of Done Checklist

- [ ] `detect_format()` function implemented
- [ ] Context-rich detected by `_meta` presence
- [ ] Normalized detected by `version` + `application`
- [ ] Transaction types detected by `import_type`
- [ ] Editable field extraction working
- [ ] Computed fields ignored on import
- [ ] Merge updates existing records
- [ ] FormatDetectionResult for UI display
- [ ] All unit tests pass (100% detection accuracy)

## Review Guidance

**Reviewers should verify**:
1. Detection is 100% accurate across all formats
2. Editable fields match WP03 `_meta` definitions
3. Computed fields never imported
4. UI display names clear and accurate

---

## Activity Log

- 2026-01-12T16:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-12T17:29:12Z – claude – lane=doing – Starting context-rich import implementation
- 2026-01-12T17:33:39Z – claude – lane=for_review – All 82 tests passing. Format auto-detection and context-rich import complete.
- 2026-01-12T22:10:00Z – claude – shell_pid=13882 – lane=done – Approved: All 82 tests pass. Format detection accurate for all types. Editable fields extracted correctly, computed fields ignored (fix applied for readonly override issue).
