---
work_package_id: "WP11"
subtasks:
  - "T047"
  - "T048"
  - "T049"
  - "T050"
title: "Code Review Checklist Update"
phase: "Phase 4 - Finalization"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP10"]
history:
  - timestamp: "2026-02-03T04:37:19Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP11 – Code Review Checklist Update

## Objectives & Success Criteria

**Goal**: Update code review checklist with transaction boundary verification.

**Success Criteria**:
- [ ] Constitution code review checklist updated
- [ ] New Service Function Checklist updated
- [ ] CLAUDE.md references transaction patterns guide
- [ ] PR template updated (if exists)

**Implementation Command**:
```bash
spec-kitty implement WP11 --base WP10
```

## Context & Constraints

**References**:
- Constitution: `.kittify/memory/constitution.md`
- CLAUDE.md: Project root
- Transaction guide: `docs/design/transaction_patterns_guide.md`

**Key Constraints**:
- Constitution changes require version bump
- Follow amendment process from constitution Governance section

## Subtasks & Detailed Guidance

### Subtask T047 – Add transaction check to Code Review Checklist

**Purpose**: Ensure reviewers verify transaction boundary documentation.

**Files**:
- Edit: `.kittify/memory/constitution.md`

**Location**: Find the "Code Review Checklist (AI Agents)" section in constitution.

**Add these items**:
- `- [ ] No multi-step operations without transaction documentation`
- `- [ ] Transaction boundary matches implementation`

**Version bump**: Update version in constitution footer from 1.6.0 to 1.6.1 (patch)

**Update Sync Impact Report** at top of file.

**Validation**:
- [ ] Two new checklist items added
- [ ] Version bumped to 1.6.1
- [ ] Sync Impact Report updated

---

### Subtask T048 – Update New Service Function Checklist

**Purpose**: Ensure new functions include transaction docs from start.

**Files**:
- Edit: `.kittify/memory/constitution.md`

**Location**: Find "New Service Function Checklist" in constitution appendix.

**Add/verify this item**:
- `- [ ] **Transaction boundary section in docstring** (Pattern A, B, or C)`

**Validation**:
- [ ] Transaction boundary explicitly in checklist

---

### Subtask T049 – Update PR template (if exists)

**Purpose**: Remind contributors to update transaction documentation.

**Files**:
- Check for: `.github/PULL_REQUEST_TEMPLATE.md`
- If exists, add transaction check

**If no template exists**: Skip this task, note in activity log.

**Validation**:
- [ ] PR template checked
- [ ] Updated if exists, or noted as N/A

---

### Subtask T050 – Update CLAUDE.md session management section

**Purpose**: Reference the new transaction patterns guide.

**Files**:
- Edit: `CLAUDE.md`

**Location**: Find "Session Management (CRITICAL - Read Before Modifying Services)" section.

**Add reference to guide**:
```markdown
### Transaction Patterns Guide

For comprehensive documentation of transaction patterns, including code examples
and common pitfalls, see:

**`docs/design/transaction_patterns_guide.md`**
```

**Validation**:
- [ ] CLAUDE.md references transaction_patterns_guide.md
- [ ] Reference is in Session Management section

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Constitution version conflict | Check current version before editing |
| PR template doesn't exist | Skip T049 if not found |

## Definition of Done Checklist

- [ ] Constitution Code Review Checklist: 2 items added
- [ ] Constitution New Service Function Checklist: transaction item explicit
- [ ] Constitution version bumped to 1.6.1
- [ ] CLAUDE.md references transaction guide
- [ ] PR template updated OR noted as N/A

## Review Guidance

**Reviewers should verify**:
1. Constitution amendment follows governance process
2. Version bump is appropriate (patch for clarification)
3. CLAUDE.md reference is discoverable

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
