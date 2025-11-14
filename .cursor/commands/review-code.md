---
description: Perform comprehensive code review for quality, standards, and best practices
---

# Code Review

You are performing a code review for the Seasonal Baking Tracker (`bake-tracker`) project.

## User Input

```text
$ARGUMENTS
```

If the user provides specific files or areas to review, focus on those. Otherwise, review recent changes or files currently open in the editor.

## Review Checklist

### 1. Code Quality
- [ ] **PEP 8 Compliance**: Max line length 100 characters, proper spacing
- [ ] **Type Hints**: All function parameters and return types annotated
- [ ] **Docstrings**: Google-style docstrings for all public classes and methods
- [ ] **Naming Conventions**: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE_CASE for constants
- [ ] **Error Handling**: Proper exception handling, no bare excepts
- [ ] **Code Duplication**: Check for repeated logic that should be extracted

### 2. Architecture & Design
- [ ] **Single Responsibility**: Each function/class has one clear purpose
- [ ] **Proper Layer Separation**: Models (data), Services (business logic), UI (presentation) are properly separated
- [ ] **Database Operations**: All database operations use SQLAlchemy ORM properly
- [ ] **Dependency Management**: No circular imports, clean dependency flow

### 3. Security
- [ ] **Input Validation**: All user inputs are validated
- [ ] **SQL Injection**: Using parameterized queries (SQLAlchemy handles this)
- [ ] **File Operations**: Safe file path handling, no path traversal vulnerabilities
- [ ] **Data Sanitization**: User data properly sanitized before display

### 4. Performance
- [ ] **Database Queries**: Efficient queries, proper use of joins, avoiding N+1 queries
- [ ] **Resource Management**: Proper closing of database sessions and file handles
- [ ] **Algorithm Efficiency**: No obvious performance bottlenecks
- [ ] **Memory Usage**: Large data sets handled efficiently (using Pandas appropriately)

### 5. Testing
- [ ] **Test Coverage**: New code has corresponding tests
- [ ] **Test Quality**: Tests are meaningful and test actual behavior
- [ ] **Edge Cases**: Tests cover error conditions and edge cases

### 6. Project-Specific Considerations
- [ ] **CustomTkinter Usage**: Proper widget usage and event handling
- [ ] **Data Export**: CSV export functionality follows Pandas best practices
- [ ] **Unit Conversions**: Ingredient unit conversions are accurate
- [ ] **Data Integrity**: Recipe calculations and cost tracking are correct

## Review Process

1. **Identify Files**: Determine which files to review based on user input or recent changes
2. **Read Code**: Examine the code systematically
3. **Document Findings**: Create a structured report with:
   - **Summary**: Overall code quality assessment
   - **Issues Found**: List of problems by severity (Critical, Major, Minor)
   - **Suggestions**: Specific improvements with code examples
   - **Positive Notes**: Highlight well-written code

4. **Prioritize**: Rank issues by:
   - **Critical**: Security issues, bugs, data corruption risks
   - **Major**: Code quality issues, significant technical debt
   - **Minor**: Style inconsistencies, minor improvements

## Output Format

```markdown
# Code Review Report

**Files Reviewed**: [list of files]
**Review Date**: [current date]
**Overall Assessment**: [Pass/Pass with Comments/Needs Work]

## Summary
[Brief overview of code quality]

## Critical Issues
[List critical issues with file:line references]

## Major Issues
[List major issues with file:line references]

## Minor Issues
[List minor issues]

## Suggestions for Improvement
[Specific actionable suggestions with code examples]

## Positive Aspects
[Things done well]

## Recommended Actions
1. [Prioritized list of fixes]
2. ...
```

## Notes
- Provide specific line numbers and file paths for all issues
- Include code snippets showing the problem and suggested fix
- Be constructive and educational in feedback
- Verify against project standards in `ai-agents/cursor-instructions.md`
