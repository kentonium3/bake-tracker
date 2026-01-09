---
description: Perform structured code review and kanban transitions for completed task prompt files.
scripts:
  sh: spec-kitty agent check-prerequisites --json --include-tasks
  ps: spec-kitty agent -Json -IncludeTasks
---
*Path: [templates/commands/review.md](templates/commands/review.md)*


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with review, verify you are in the correct working directory by running the shared pre-flight validation:

```python
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

This is intentional - worktrees provide isolation for parallel feature development.

## Outline

1. Run `{SCRIPT}` from repo root; capture `FEATURE_DIR`, `AVAILABLE_DOCS`, and `tasks.md` path.

2. Determine the review target:
   - If user input specifies a filename, validate it exists under `tasks/` (flat structure, check `lane: "for_review"` in frontmatter).
   - Otherwise, select the oldest file in `tasks/` (lexical order is sufficient because filenames retain task ordering).
   - Abort with instructional message if no files are waiting for review.

3. Load context for the selected task:
   - Read the prompt file frontmatter (lane MUST be `for_review`); note `task_id`, `phase`, `agent`, `shell_pid`.
   - Read the body sections (Objective, Context, Implementation Guidance, etc.).
   - Consult supporting documents as referenced: constitution, plan, spec, data-model, contracts, research, quickstart, code changes.
   - Review the associated code in the repository (diffs, tests, docs) to validate the implementation.

4. **PRE-CHECK: Verify subtask completion (CRITICAL - NEW STEP):**

   Before proceeding with code review, verify that all subtasks for this WP are marked complete:

   a. Read `tasks.md` and find the section for this work package
   b. Identify all subtasks (T###) listed under this WP
   c. Check that each subtask shows `[x]` (completed), not `[ ]` (incomplete)

   **If any subtasks are unchecked:**
   - **STOP the review immediately**
   - Do NOT proceed to code review
   - Document which subtasks are incomplete:
     ```
     REVIEW BLOCKED: Incomplete subtasks detected for <WPID>

     The following subtasks are not marked complete in tasks.md:
     - [ ] T001 <description>
     - [ ] T003 <description>

     Action required:
     1. Return WP to 'doing' lane
     2. Implementer must mark subtasks complete:
        spec-kitty agent mark-status --task-id T001 --status done
        spec-kitty agent mark-status --task-id T003 --status done
     3. Re-submit for review
     ```
   - Run: `spec-kitty agent move-task <FEATURE> <WP_ID> doing --note "Review blocked: incomplete subtask markers"`
   - **Reviewer should NOT mark subtasks on behalf of implementer** - this masks workflow compliance issues

   **If all subtasks are checked:** Proceed to step 5.

5. Conduct the review:
   - Verify implementation against the prompt's Definition of Done and Review Guidance.
   - Run required tests or commands; capture results.
   - Document findings explicitly: bugs, regressions, missing tests, risks, or validation notes.

6. Decide outcome:
  - **Needs changes**:
     * **CRITICAL**: Insert detailed feedback in the `## Review Feedback` section (located immediately after the frontmatter, before Objectives). This is the FIRST thing implementers will see when they re-read the prompt.
     * Use a clear structure:
       ```markdown
       ## Review Feedback

       **Status**: :x: **Needs Changes**

       **Key Issues**:
       1. [Issue 1] - Why it's a problem and what to do about it
       2. [Issue 2] - Why it's a problem and what to do about it

       **What Was Done Well**:
       - [Positive note 1]
       - [Positive note 2]

       **Action Items** (must complete before re-review):
       - [ ] Fix [specific thing 1]
       - [ ] Add [missing thing 2]
       - [ ] Verify [validation point 3]
       ```
     * Update frontmatter:
       - Set `lane: "planned"`
       - Set `review_status: "has_feedback"`
       - Set `reviewed_by: <YOUR_AGENT_ID>`
       - Clear `assignee` if needed
     * Append a new entry in the prompt's **Activity Log** with timestamp, reviewer agent, shell PID, and summary of feedback.
     * Run `spec-kitty agent move-task <FEATURE> <TASK_ID> planned --note "Code review complete: [brief summary of issues]"` (use the PowerShell equivalent on Windows) so the move and history update are staged consistently.
  - **Approved**:
     * Append Activity Log entry capturing approval details (capture shell PID via `echo $$` or helper script, e.g., `2025-11-11T13:45:00Z – claude – shell_pid=1234 – lane=done – Approved without changes`).
     * Update frontmatter:
       - Sets `lane: "done"`
       - Sets `review_status: "approved without changes"` (or your custom status)
       - Sets `reviewed_by: <YOUR_AGENT_ID>`
       - Updates `agent: <YOUR_AGENT_ID>` and `shell_pid: <YOUR_SHELL_PID>`
       - Appends Activity Log entry with reviewer's info (NOT implementer's)
       - Handles git operations (add new location, remove old location)
     * **Alternative:** For custom review statuses, use `--review-status "approved with minor notes"` or `--target-lane "planned"` for rejected tasks.
     * Use helper script to mark the task complete in `tasks.md` (see Step 7).

7. Update `tasks.md` automatically:
   - Run `spec-kitty agent mark-status --task-id <TASK_ID> --status done` (POSIX) or `spec-kitty agent -TaskId <TASK_ID> -Status done` (PowerShell) from repo root.
   - Confirm the task entry now shows `[X]` and includes a reference to the prompt file in its notes.
   - **Note:** If the pre-check in step 4 passed, subtasks should already be marked. This step marks the WP itself as complete.

8. Produce a review report summarizing:
   - Task ID and filename reviewed.
   - Approval status and key findings.
   - Tests executed and their results.
   - Follow-up actions (if any) for other team members.
   - Reminder to push changes or notify teammates as per project conventions.

Context for review: {ARGS} (resolve this to the prompt's relative path, e.g., `kitty-specs/<feature>/tasks/WPXX.md`)

All review feedback must live inside the prompt file, ensuring future implementers understand historical decisions before revisiting the task.

---

## Review Checklist Summary

Before approving a WP, verify:

- [ ] **Pre-check passed:** All subtasks (T###) are marked `[x]` in tasks.md
- [ ] **Assignee set:** WP frontmatter has `assignee:` populated (not empty)
- [ ] **Code quality:** Implementation meets Definition of Done
- [ ] **Tests pass:** Required validation commands succeed
- [ ] **No regressions:** Existing functionality unaffected

If pre-check fails, return WP to implementer - do not fix tracking issues on their behalf.
