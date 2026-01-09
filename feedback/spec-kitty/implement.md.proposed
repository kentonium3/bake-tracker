---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## Work Package Selection

**User specified**: `$ARGUMENTS`

**Your task**: Determine which WP to implement:
- If `$ARGUMENTS` is empty → Find first WP file with `lane: "planned"` in `tasks/` directory
- If `$ARGUMENTS` provided → Normalize it:
  - `wp01` → `WP01`
  - `WP01` → `WP01`
  - `WP01-foo-bar` → `WP01`
  - Then find: `tasks/WP01*.md`

**Once you know which WP**, proceed to setup.

---

## Setup (Do This First)

**1. Move WP to doing lane (with assignee):**
```bash
spec-kitty agent tasks move-task <WPID> --to doing --assignee "<YOUR_AGENT_ID>" --note "Started implementation"
```
This updates frontmatter, captures shell PID, sets assignee, adds activity log, and creates a commit.

**IMPORTANT:** Always include `--assignee` to track who is working on this WP.

**2. Get the prompt file path:**
The WP file is at: `kitty-specs/<feature>/tasks/<WPID>-<slug>.md`
Find the full absolute path.

**3. Verify the move worked:**
```bash
git log -1  # Should show "Start <WPID>: Move to doing lane"
```

---

## Implementation (Do This Second)

**1. READ THE PROMPT FILE** (`tasks/<WPID>-slug.md`)
   - This is your complete implementation guide
   - Check `review_status` in frontmatter:
     - If `has_feedback` → Read `## Review Feedback` section first
     - Treat action items as your TODO list

**2. Read supporting docs:**
   - `tasks.md` - Full task breakdown
   - `plan.md` - Tech stack and architecture
   - `spec.md` - Requirements
   - `data-model.md`, `contracts/`, `research.md`, `quickstart.md` (if exist)

**3. Implement following the prompt's guidance:**
   - Follow subtask order
   - Respect dependencies (sequential vs parallel `[P]`)
   - Run tests if required
   - Commit as you complete major milestones

**4. Mark subtasks complete AS YOU GO (CRITICAL):**

After completing each subtask (T001, T002, etc.), IMMEDIATELY run:
```bash
spec-kitty agent mark-status --task-id <TASK_ID> --status done
```

Example workflow:
```bash
# Complete T001 implementation...
spec-kitty agent mark-status --task-id T001 --status done

# Complete T002 implementation...
spec-kitty agent mark-status --task-id T002 --status done

# Continue for each subtask...
```

**DO NOT batch these at the end.** Mark each subtask done right after completing it.
This updates the `[ ]` → `[x]` checkboxes in `tasks.md`.

**5. Verify completion before moving to for_review:**

Before proceeding, check that ALL subtasks for this WP are marked complete:
```bash
# View tasks.md and verify all subtasks for this WP show [x]
cat kitty-specs/<feature>/tasks.md | grep -A1 "## Work Package <WPID>"
```

If any subtasks show `[ ]` instead of `[x]`, mark them now:
```bash
spec-kitty agent mark-status --task-id <MISSING_TASK_ID> --status done
```

**6. When complete:**
```bash
spec-kitty agent tasks move-task <WPID> --to for_review --note "Ready for review"
git add <your-changes>
git commit -m "Complete <WPID>: <description>"
```

---

## Two-Tier Tracking System (Important!)

Spec-kitty tracks progress at TWO levels:

| Level | Location | Marker | Command |
|-------|----------|--------|---------|
| Work Package | `tasks/WP##-*.md` frontmatter | `lane: doing/for_review/done` | `move-task` |
| Subtask | `tasks.md` checkboxes | `- [ ]` / `- [x]` | `mark-status` |

**Both must be updated.** Moving a WP to `done` does NOT automatically check off its subtasks.

---

## Checklist Before Moving to for_review

- [ ] All subtasks (T###) for this WP are marked `[x]` in `tasks.md`
- [ ] WP frontmatter shows `assignee:` is set (not empty)
- [ ] All code changes are committed
- [ ] Tests pass (if applicable)

---

## That's It

**Simple workflow:**
1. Find which WP (from `$ARGUMENTS` or first planned)
2. Move it to doing **with assignee**
3. Read the prompt file
4. Do the work, **marking each subtask done as you complete it**
5. Verify all subtasks checked in tasks.md
6. Move to for_review

**Track as you go, not at the end.**
