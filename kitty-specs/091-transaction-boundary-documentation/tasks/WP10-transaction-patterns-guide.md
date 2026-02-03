---
work_package_id: WP10
title: Transaction Patterns Guide
lane: "doing"
dependencies: [WP09]
base_branch: 091-transaction-boundary-documentation-WP09
base_commit: 67d28002b977b447089b6f9dd881bf2ddb4b9264
created_at: '2026-02-03T07:06:09.532366+00:00'
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 3 - Guide
assignee: ''
agent: ''
shell_pid: "65219"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T04:37:19Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP10 – Transaction Patterns Guide

## Objectives & Success Criteria

**Goal**: Create comprehensive transaction patterns guide in docs/design/.

**Success Criteria**:
- [ ] Guide exists at `docs/design/transaction_patterns_guide.md`
- [ ] All three patterns documented with code examples
- [ ] At least 3 common pitfalls documented with fixes
- [ ] Session parameter pattern explained

**Implementation Command**:
```bash
spec-kitty implement WP10 --base WP09
```

## Context & Constraints

**References**:
- Func-spec FR-3: `docs/func-spec/F091_transaction_boundary_documentation.md`
- Templates: `kitty-specs/091-transaction-boundary-documentation/research/docstring_templates.md`
- Audit results: `kitty-specs/091-transaction-boundary-documentation/research/atomicity_audit.md`
- Constitution: `.kittify/memory/constitution.md` (Principle VI.C.2)

**Key Constraints**:
- Use REAL code examples from the codebase
- Include anti-patterns discovered during audit
- Reference from CLAUDE.md

## Subtasks & Detailed Guidance

### Subtask T041 – Create docs/design/transaction_patterns_guide.md

**Purpose**: Create the guide file with initial structure.

**Files**:
- Create: `docs/design/transaction_patterns_guide.md`

**Initial structure**: See func-spec FR-3 for complete content structure including:
- Purpose section
- Quick Reference table
- Pattern Catalog
- Session Parameter Pattern
- Common Pitfalls
- Code Review Checklist

**Validation**:
- [ ] File created at correct location
- [ ] Structure matches func-spec FR-3

---

### Subtask T042 – Document Pattern A (Read-Only)

**Purpose**: Document read-only transaction pattern with code examples.

**Content**: Include description, when to use, template, and real example from codebase (e.g., get_ingredient).

**Validation**:
- [ ] Pattern A fully documented
- [ ] Real code example included

---

### Subtask T043 – Document Pattern B (Single-Step Write)

**Purpose**: Document single-step write pattern with code examples.

**Content**: Include description, when to use, template, and real example from codebase.

**Validation**:
- [ ] Pattern B fully documented
- [ ] Real code example included

---

### Subtask T044 – Document Pattern C (Multi-Step Atomic)

**Purpose**: Document multi-step atomic pattern with code examples.

**Content**: Include description, when to use, template, critical rules, and real example (e.g., record_batch_production).

**Validation**:
- [ ] Pattern C fully documented
- [ ] Real code example included
- [ ] Critical rules emphasized

---

### Subtask T045 – Document common pitfalls

**Purpose**: Document anti-patterns and how to fix them.

**Content**: Document at least 3 pitfalls:
1. Multiple session_scope() calls
2. Forgetting to pass session
3. Assuming implicit transactions
4. Detached object modification (optional 4th)

Each pitfall needs WRONG and CORRECT examples.

**Validation**:
- [ ] At least 3 pitfalls documented
- [ ] Each has WRONG and CORRECT examples

---

### Subtask T046 – Document session parameter pattern

**Purpose**: Explain when and how to use the session parameter.

**Content**:
- Why every service function accepts `session=None`
- When to pass session (composing operations)
- When to omit session (standalone calls)
- Desktop vs web usage
- The implementation pattern
- Benefits

**Validation**:
- [ ] Session pattern fully explained
- [ ] Desktop vs web usage documented
- [ ] Benefits listed

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Examples outdated | Reference actual code, not paraphrased |
| Guide too long | Use collapsible sections if needed |

## Definition of Done Checklist

- [ ] Guide created at `docs/design/transaction_patterns_guide.md`
- [ ] Pattern A documented with example
- [ ] Pattern B documented with example
- [ ] Pattern C documented with example
- [ ] At least 3 pitfalls documented with WRONG/CORRECT examples
- [ ] Session parameter pattern explained
- [ ] Guide referenced from constitution (if appropriate)

## Review Guidance

**Reviewers should verify**:
1. Examples compile/make sense
2. Pitfalls match actual issues found in audit
3. Guide is discoverable (linked from CLAUDE.md)

## Activity Log

- 2026-02-03T04:37:19Z – system – lane=planned – Prompt created.
