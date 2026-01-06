Files in the ./docs/code-review dir are for tracking prompts and reports of independent code reviews that augment the spec-kitty.review process. Evidence shows that independent reviews often find issues spec-kitty reviews miss so getting input from a different system makes for better code quality and more successful user testing.

**Claude Code code review prompt instructions for Cursor**
Create a prompt for Cursor to perform an independent code review as a senior software engineer discovering this feature for the first time. Follow the prompt/report pattern of docs/code-reviews/cursor-F035*.md.

**Context to provide:**
- Feature number, title, and high-level user goal
- Key files modified (full paths)
- Any spec files that define requirements
- Commands to verify environment (imports/greps/pytest) - run outside sandbox

**Review approach - tell Cursor to:**
1. Read the spec to understand intended behavior BEFORE looking at implementation
2. Form independent expectations about how the feature SHOULD work
3. Compare implementation against those expectations, noting:
   - Logic gaps or edge cases the spec didn't anticipate
   - Code patterns that differ from rest of codebase
   - User workflow friction points
   - Data integrity risks
   - Performance or maintainability concerns
4. Run verification commands - if ANY fail, STOP and report blocker before fixing
5. Write report to docs/code-reviews/ (not worktree)

**What NOT to include:**
- Detailed test cases (let Cursor devise its own)
- Specific code locations to examine (beyond listing modified files)
- Expected findings or known issues
- Implementation approach guidance

The goal is for Cursor to approach this as a fresh reviewer with different assumptions and priorities than the original implementer.
