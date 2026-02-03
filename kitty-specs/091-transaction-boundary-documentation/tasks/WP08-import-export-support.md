---
work_package_id: WP08
title: Import/Export & Support Services
lane: "doing"
dependencies: [WP01]
base_branch: 091-transaction-boundary-documentation-WP01
base_commit: ea54478c184557f13c16ab46b637a8903d9343c6
created_at: '2026-02-03T05:56:20.220188+00:00'
subtasks:
- T029
- T030
- T031
- T032
- T033
- T034
phase: Phase 2 - Documentation
assignee: ''
agent: ''
shell_pid: "38175"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Import/Export & Support Services

## Objectives & Success Criteria

**Goal**: Add transaction boundary documentation to import/export and remaining support services.

**Success Criteria**:
- [ ] All public functions in import services have "Transaction boundary:" section
- [ ] All public functions in export services have "Transaction boundary:" section

**Implementation Command**:
```bash
spec-kitty implement WP08 --base WP01
```

**Parallel-Safe**: Yes - assign to Codex

## Context & Constraints

**References**:
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`

**Key Constraints**:
- Import services are complex multi-step operations
- Export services are typically read-only
- Focus on public API functions, not internal helpers

## Subtasks & Detailed Guidance

### Subtask T029 – Document import_export_service.py

**Purpose**: Add transaction boundary documentation to main import/export service.

**Files**:
- Edit: `src/services/import_export_service.py`

**Typical functions**:

| Function | Type | Template |
|----------|------|----------|
| `export_all_data` | READ | Pattern A |
| `export_table` | READ | Pattern A |
| `import_all_data` | MULTI | Pattern C (complex) |
| `import_table` | MULTI | Pattern C |
| `validate_import_data` | READ | Pattern A |

**For import operations**:
```python
def import_all_data(data: dict, session: Optional[Session] = None) -> ImportResult:
    """
    Import complete data set from JSON.

    Transaction boundary: ALL operations in single session (atomic).
    Atomicity guarantee: Either ALL tables import successfully OR entire import rolls back.
    Steps executed atomically:
    1. Validate import data structure and version
    2. Clear existing data (if replace mode)
    3. Import each table in dependency order
    4. Resolve foreign key references
    5. Validate referential integrity

    CRITICAL: All nested service calls receive session parameter to ensure
    atomicity. Never create new session_scope() within this function.
    Any validation failure in step 5 triggers complete rollback of all imports.

    Args:
        data: Complete JSON data structure to import
        session: Optional session for transactional composition

    Returns:
        ImportResult with counts and any warnings

    Raises:
        ValidationError: If data structure invalid
        ImportError: If referential integrity check fails
    """
```

**Validation**:
- [ ] All public functions documented

---

### Subtask T030 – Document enhanced_import_service.py

**Purpose**: Add transaction boundary documentation to enhanced import operations.

**Files**:
- Edit: `src/services/enhanced_import_service.py`

**Typical functions**:
- Enhanced validation functions: READ (Pattern A)
- Enhanced import functions: MULTI (Pattern C)
- Merge/update functions: MULTI (Pattern C)

**Validation**:
- [ ] All public functions documented

---

### Subtask T031 – Document transaction_import_service.py

**Purpose**: Add transaction boundary documentation to transactional import operations.

**Files**:
- Edit: `src/services/transaction_import_service.py`

**Note**: This service specifically handles transaction-aware imports.

**Key documentation elements**:
- Atomic batch import semantics
- Partial failure handling
- Rollback scope

**Validation**:
- [ ] All public functions documented

---

### Subtask T032 – Document catalog_import_service.py

**Purpose**: Add transaction boundary documentation to catalog import operations.

**Files**:
- Edit: `src/services/catalog_import_service.py`

**Typical functions**:
- Import catalog items: MULTI (Pattern C)
- Validate catalog data: READ (Pattern A)

**Validation**:
- [ ] All public functions documented

---

### Subtask T033 – Document coordinated_export_service.py

**Purpose**: Add transaction boundary documentation to coordinated export operations.

**Files**:
- Edit: `src/services/coordinated_export_service.py`

**Note**: Export services are typically READ but may use transactions for consistency.

**Example**:
```python
def export_coordinated_data(tables: List[str], session: Optional[Session] = None) -> dict:
    """
    Export multiple tables with referential consistency.

    Transaction boundary: Read-only snapshot within single session.
    Uses consistent read to ensure exported data has referential integrity.
    All tables read within same session see consistent state.

    Args:
        tables: List of table names to export
        session: Optional session (for composition with other operations)

    Returns:
        Dictionary with table names as keys and data as values

    Raises:
        ExportError: If table name invalid
    """
```

**Validation**:
- [ ] All public functions documented

---

### Subtask T034 – Document denormalized_export_service.py

**Purpose**: Add transaction boundary documentation to denormalized export operations.

**Files**:
- Edit: `src/services/denormalized_export_service.py`

**Typical functions**:
- All export functions: READ (Pattern A)
- May join across tables: document read consistency

**Validation**:
- [ ] All public functions documented

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Large import files | Focus on public API, not internal helpers |
| Complex transaction semantics | Document rollback scope clearly |

## Definition of Done Checklist

- [ ] import_export_service.py: All public functions documented
- [ ] enhanced_import_service.py: All public functions documented
- [ ] transaction_import_service.py: All public functions documented
- [ ] catalog_import_service.py: All public functions documented
- [ ] coordinated_export_service.py: All public functions documented
- [ ] denormalized_export_service.py: All public functions documented
- [ ] Tests still pass: `pytest src/tests -v -k "import or export"`

## Review Guidance

**Reviewers should verify**:
1. Import atomicity clearly documented
2. Export consistency documented
3. Rollback scope specified for imports

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
