# Code Review Report: [Feature Number] - [Feature Title]

**Reviewer:** Cursor (Independent Review)
**Date:** [YYYY-MM-DD]
**Feature Spec:** [path to spec file]

## Executive Summary
[2-3 sentences: What this feature does, overall assessment, key concerns if any]

## Review Scope

**Primary Files Modified:**
- [list full paths to modified files]

**Additional Code Examined:**
- [any dependencies, callers, related systems you reviewed beyond the modified files]

## Environment Verification

**Setup Process:**
```bash
[commands used to verify environment]
```

**Results:**
[Document what you verified and whether environment is functional]

**STOP HERE if verification failed - report blocker before proceeding**

---

## Findings

### Critical Issues
[Issues that could cause data loss, corruption, crashes, or security problems]

**[Issue Title]**
- **Location:** [file:line or general area]
- **Problem:** [what's wrong]
- **Impact:** [what could happen]
- **Recommendation:** [how to fix]

### Major Concerns
[Issues affecting core functionality, user workflows, or maintainability]

[Same format as Critical]

### Minor Issues
[Code quality, style inconsistencies, optimization opportunities]

[Same format as Critical]

### Positive Observations
[What was done well - good patterns, clever solutions, solid error handling]

## Spec Compliance Analysis

Review how implementation matches spec requirements. Form your own approach to verification - consider what matters most for this feature type. Document your findings:

[Your analysis of how well implementation matches spec, including:]
- Core functionality delivery
- Edge case handling
- Error handling approach
- User workflow experience
- Anything the spec didn't anticipate

## Code Quality Assessment

**Consistency with Codebase:**
[Does this follow established patterns? Any deviations and why they matter?]

**Maintainability:**
[How easy will this be for future developers to understand and modify?]

**Test Coverage:**
[Are the right things tested? Any obvious gaps?]

**Dependencies & Integration:**
[How does this interact with other systems? Any coupling concerns?]

## Recommendations Priority

**Must Fix Before Merge:**
1. [Critical/blocking items]

**Should Fix Soon:**
1. [Important but not blocking]

**Consider for Future:**
1. [Nice-to-haves, refactoring opportunities]

## Overall Assessment
[Pass/Pass with minor fixes/Needs revision/Major rework needed]

[Final paragraph: Would you ship this to users? Why or why not? What gives you confidence or concerns?]
