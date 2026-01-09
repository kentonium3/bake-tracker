# Requirements Checklist: Finished Units Yield Type Management

**Feature**: 044-finished-units-yield-type-management
**Created**: 2026-01-09

## Spec Quality Checklist

### Structure
- [x] Problem statement clearly defines the user pain point
- [x] User scenarios ordered by priority (P1, P2, P3)
- [x] Each user story has independent test criteria
- [x] Acceptance scenarios use Given/When/Then format
- [x] Edge cases documented
- [x] Functional requirements numbered (FR-001, etc.)
- [x] Success criteria are measurable (SC-001, etc.)

### Completeness
- [x] All UI entry points defined (Recipe Edit, Finished Units Tab)
- [x] CRUD operations specified (Create, Read, Update, Delete)
- [x] Validation rules explicit (empty name, zero/negative qty, duplicates)
- [x] Error message requirements defined
- [x] Navigation flows specified (double-click to parent)
- [x] Data persistence rules clear (save on recipe save)

### Dependencies & Assumptions
- [x] Dependencies on prior features listed (F037, F042)
- [x] Assumptions about existing models documented
- [x] Out of scope items explicitly listed

## Functional Requirements Traceability

### Recipe Edit Form - Yield Types Section
| Req ID | Description | Status |
|--------|-------------|--------|
| FR-001 | Recipe Edit includes Yield Types section | Specified |
| FR-002 | Display list with Name, Items Per Batch | Specified |
| FR-003 | Edit/Delete buttons per row | Specified |
| FR-004 | Inline entry row for adding | Specified |
| FR-005 | Entry row fields: Name, Items Per Batch, Add button | Specified |
| FR-006 | Add button adds to list (pending save) | Specified |
| FR-007 | Edit enables inline modification | Specified |
| FR-008 | Delete prompts confirmation | Specified |
| FR-009 | Recipe save persists all yield type changes | Specified |

### Finished Units Tab
| Req ID | Description | Status |
|--------|-------------|--------|
| FR-010 | Finished Units tab in CATALOG mode | Specified |
| FR-011 | Display all yield types from all recipes | Specified |
| FR-012 | Columns: Name, Recipe, Items Per Batch | Specified |
| FR-013 | Search field filters by name | Specified |
| FR-014 | Recipe dropdown filters by recipe | Specified |
| FR-015 | Double-click navigates to Recipe Edit | Specified |
| FR-016 | Tab is read-only (no CRUD buttons) | Specified |
| FR-017 | Message indicates edit via Recipe Edit | Specified |

### Validation
| Req ID | Description | Status |
|--------|-------------|--------|
| FR-018 | Name must not be empty | Specified |
| FR-019 | Name unique within recipe | Specified |
| FR-020 | Items Per Batch positive integer | Specified |
| FR-021 | Specific, actionable error messages | Specified |

### Service Layer
| Req ID | Description | Status |
|--------|-------------|--------|
| FR-022 | Create finished unit with name, qty, recipe | Specified |
| FR-023 | Update finished unit name and qty | Specified |
| FR-024 | Delete finished unit | Specified |
| FR-025 | Query finished units by recipe | Specified |
| FR-026 | Query all with optional filters | Specified |

## User Story Coverage

| Story | Priority | Acceptance Scenarios | Edge Cases |
|-------|----------|---------------------|------------|
| Define Yield Types | P1 | 5 scenarios | Yes |
| Browse Finished Units | P2 | 4 scenarios | Yes |
| Validation | P1 | 4 scenarios | Yes |

## Success Criteria Verification

| ID | Criterion | Measurable |
|----|-----------|------------|
| SC-001 | Define yield type in 3 clicks | Yes |
| SC-002 | Tab loads in <1 second | Yes |
| SC-003 | Search updates as user types | Yes |
| SC-004 | 100% validation errors have messages | Yes |
| SC-005 | Double-click navigation works | Yes |
| SC-006 | 10+ yield types remain responsive | Yes |
