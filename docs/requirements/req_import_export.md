# Import / Export - Requirements Document

**Component:** Import / Export (Backups + Test Data + External Sharing)
**Version:** 1.0
**Last Updated:** 2026-01-07
**Status:** Active
**Owner:** Kent Gale

---

## 1. Purpose & Function

### 1.1 Overview

Import/Export provides a **current-schema** JSON pathway for:

- exporting user data for backup and diagnostics
- re-importing that data into a fresh local database (restore / testing)
- keeping `test_data/` fixtures aligned with evolving schema requirements

### 1.2 Business Purpose

1. **Backup & Restore:** enable the user to preserve and restore a growing database during user testing.
2. **Repeatable Testing:** enable reliable creation of local test fixtures in `test_data/` that match the current schema.
3. **Controlled Data Evolution:** ensure schema changes are reflected by updating JSON fixtures externally (manual/spec-driven), not by adding runtime compatibility layers.

### 1.3 Policy (Critical)

**Import files MUST be current-spec compliant.**

- **No backward compatibility import functions.**
- **No programmatic transforms** between historical formats.
- **No version-based branching or gating.**
- If a file fails to import, **the file is fixed externally** (manual edit / Claude instruction / spec-driven update to `test_data/`).

---

## 2. Core Concepts

### 2.1 Import Modes

- **merge**: add new records; skip duplicates (matching strategy is schema/entity-specific)
- **replace**: clear tables first, then import from scratch

### 2.2 Canonical Interfaces

- **Primary full-database importer:** `import_all_from_json_v4(file_path, mode)`
- **Primary exporter:** `export_all_to_json(file_path)`

### 2.3 Schema is the Contract (not Version)

- A `version` field may exist in files for informational purposes, but **must not** drive import logic.
- Import correctness is determined by:
  - required fields present
  - FK references resolvable
  - SQLAlchemy model validation/constraints

---

## 3. Scope & Boundaries

### 3.1 In Scope

- ✅ Export a complete database dataset to JSON
- ✅ Import a complete database dataset from JSON in `merge` and `replace` modes
- ✅ Strict “current schema only” behavior (no hidden transforms)
- ✅ Clear, actionable errors for invalid schema / missing references
- ✅ Support test fixture generation/update workflows via `test_data/`

### 3.2 Out of Scope

- ❌ Importing older schemas “as-is”
- ❌ Automatically transforming old JSON formats into current format
- ❌ Maintaining multiple importers per historical version

---

## 4. User Stories & Use Cases

### 4.1 Primary User Stories

**As a baker, I want to:**
1. export my database to a JSON file so I can back it up and share it for debugging
2. import a JSON backup into a clean database so I can restore my work

**As the developer, I want to:**
1. update JSON fixtures in `test_data/` to match schema changes so tests remain stable
2. reject invalid import files so schema drift is caught early

### 4.2 Use Case: Restore from Backup (Replace Mode)

**Actor:** user/developer
**Preconditions:** app can access the JSON file and the DB is reachable
**Main Flow:**
1. user selects Import and chooses `replace`
2. app clears existing data
3. app imports all entities in dependency order
4. app reports summary counts + any warnings

**Postconditions:** database reflects the imported dataset.

---

## 5. Functional Requirements

### 5.1 Export

**REQ-IE-001:** Export MUST produce a valid JSON document.
**REQ-IE-002:** Export MUST include all required entity collections for a full restore.
**REQ-IE-003:** Export MUST include F037 recipe fields (`base_recipe_slug`, `variant_name`, `is_production_ready`).
**REQ-IE-004:** Export MUST include F039 event `output_mode`.

### 5.2 Import (Current Schema Only)

**REQ-IE-010:** Import MUST assume current-spec schema compliance; non-compliant files MUST fail with actionable errors.
**REQ-IE-011:** Import MUST NOT attempt to transform historical formats.
**REQ-IE-012:** Import MUST NOT branch/gate behavior based on `version`.
**REQ-IE-013:** Import MUST support `merge` and `replace` modes.
**REQ-IE-014:** Import MUST validate required FK references before creating dependent records (or fail with clear error).
**REQ-IE-015:** Import MUST provide per-entity success/skip/error counts and error details.

### 5.3 BT Mobile JSON Imports (Feature 040)

**REQ-IE-020:** Purchase import MUST validate `schema_version == "4.0"` and `import_type == "purchases"`.
**REQ-IE-021:** Purchase import MUST match UPCs against `Product.upc_code`.
**REQ-IE-022:** Unknown UPCs MUST be surfaced for explicit user resolution (map/create/skip).
**REQ-IE-023:** Inventory update import MUST validate `schema_version == "4.0"` and `import_type == "inventory_updates"`.
**REQ-IE-024:** Inventory update import MUST validate percentage range 0–100 and apply FIFO item selection.

---

## 6. Non-Functional Requirements

### 6.1 Data Integrity

**REQ-IE-NFR-001:** Imports MUST not silently mutate files (no in-app transforms).
**REQ-IE-NFR-002:** Error messages MUST identify the record and field (or entity) that caused the failure.

### 6.2 Maintainability

**REQ-IE-NFR-010:** There MUST be a single “current importer” API to reduce drift and complexity.
**REQ-IE-NFR-011:** Tests MUST align with policy (no legacy importer tests).

---

## 7. Development & Maintenance Workflow

### 7.1 Updating Test Data After Schema Changes

**When schema changes require JSON updates:**

```
1. Export from the current app (or assemble a minimal JSON fixture).
   └─ Save/adjust files under test_data/

2. If import fails, fix the JSON externally.
   └─ Manual edit or Claude instructions to update fields/structure

3. Re-run focused tests + full suite.
```

---

## 8. Testing Requirements

### 8.1 Test Coverage

**Unit Tests:**
- Result accounting (success/skip/error)
- Required-field/FK validation failures

**Integration Tests:**
- Full export → delete → import (replace)
- Full export → import (merge)
- F037 recipe variants round-trip
- F039 event output_mode round-trip

### 8.2 Test Data

- `test_data/sample_data.json` should remain current-spec compliant and updated as the schema evolves.

---

## 9. Related Documents

- **Feature 040 spec:** `kitty-specs/040-import-export-v4/spec.md`
- **F040 review:** `docs/code-reviews/cursor-F040-review.md`
- **Bug fix spec:** `docs/bugs/_BUG_import-export-backcompat-importer.md`

---

**END OF REQUIREMENTS DOCUMENT**


