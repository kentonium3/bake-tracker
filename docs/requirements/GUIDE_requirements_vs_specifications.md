# Requirements vs. Specifications - Documentation Guide

**Purpose:** Clarify the distinction between Requirements Documents and Specification Documents  
**Audience:** All contributors (humans and AI systems)  
**Last Updated:** 2025-12-30

---

## Document Types Overview

### Requirements Documents (WHAT)

**Purpose:** Define what the system must do from a user/business perspective

**Characteristics:**
- User-focused language
- Business justification for features
- Technology-agnostic where possible
- Stable over time (represents enduring needs)
- Examples: User stories, acceptance criteria, validation rules

**File Pattern:** `requirements_[component].md`  
**Template:** `/docs/design/TEMPLATE_requirements.md`

**Example Topics:**
- What problem does this solve?
- Who uses this feature and why?
- What are the boundaries (in scope / out of scope)?
- What must the system do (functional requirements)?
- What quality attributes must it have (non-functional requirements)?

---

### Specification Documents (HOW)

**Purpose:** Define how requirements are implemented technically

**Characteristics:**
- Developer-focused language
- Technical design decisions
- Technology-specific (Python, SQLite, CustomTkinter, etc.)
- May change across implementations
- Examples: Database schemas, API contracts, UI wireframes

**File Pattern:** `F0XX_[feature_name].md` or `spec_[component].md`  
**No Template:** Each spec is unique to its implementation approach

**Example Topics:**
- What data model implements this requirement?
- What service layer methods are needed?
- What UI components display this information?
- What algorithms solve this problem?
- What migration strategy preserves data?

---

## When to Use Each

### Use Requirements Document When:

✅ Defining a **major component** of the system (Ingredients, Recipes, Products, Inventory, Planning)  
✅ Documenting **enduring business rules** that won't change with implementation  
✅ Communicating **scope and boundaries** to all stakeholders  
✅ Creating **acceptance criteria** for testing  
✅ Establishing **validation rules** for data integrity

**Lifecycle:** Long-lived, updated quarterly or when business needs change

---

### Use Specification Document When:

✅ Designing a **specific feature** (F031: Ingredient Hierarchy backend)  
✅ Planning **implementation details** for developers/AI agents  
✅ Documenting **technical decisions** (export-transform-import strategy)  
✅ Creating **gap analysis** between current and desired state  
✅ Estimating **implementation complexity** and effort

**Lifecycle:** Created per feature, may become obsolete after implementation

---

## Relationship Between Requirements and Specs

```
Requirements Document (ingredients)
    ↓
    Describes WHAT the ingredient system must do
    ↓
    ├─ F031 Specification (Ingredient Hierarchy - Backend)
    │  └─ HOW to implement schema, services, import/export
    │
    ├─ F032 Specification (Ingredient Hierarchy - UI)
    │  └─ HOW to implement tabs, forms, cascading selectors
    │
    └─ BUG_F032 Specification (Fix Conceptual Errors)
       └─ HOW to correct wrong mental model in implementation
```

**Key Insight:** One requirements document can spawn multiple specification documents over time.

---

## bake-tracker Documentation Structure

### Requirements Layer (Long-Lived)

```
/docs/design/
├─ requirements_ingredients.md     ← What ingredients must do
├─ requirements_recipes.md         ← What recipes must do
├─ requirements_products.md        ← What products must do
├─ requirements_inventory.md       ← What inventory must do
└─ requirements_planning.md        ← What planning must do
```

**Characteristics:**
- Reviewed quarterly
- Updated when business needs change
- Stable reference for all implementations

---

### Specification Layer (Per-Feature)

```
/docs/design/
├─ F031_ingredient_hierarchy.md        ← Backend implementation
├─ F032_ingredient_hierarchy_ui.md     ← UI implementation (was BUG spec)
├─ F033_recipe_redesign.md             ← Recipe snapshots/variants
├─ F034_ui_mode_restructure.md         ← 5-mode workflow
└─ ...

/docs/bugs/
├─ BUG_F032_hierarchy_conceptual_errors.md  ← Fix specification
└─ ...
```

**Characteristics:**
- Created per feature
- May become obsolete after implementation
- References requirements document for business context

---

## Template Usage

### For New Requirements Document:

1. Copy `TEMPLATE_requirements.md` to `requirements_[component].md`
2. Replace all `[placeholders]` with actual content
3. Delete sections that don't apply
4. Add component-specific sections as needed
5. Review with stakeholders before marking APPROVED

### For New Specification Document:

1. Create `F0XX_[feature_name].md` (no template - custom per feature)
2. Include these standard sections:
   - Executive Summary
   - Problem Statement
   - Proposed Solution
   - Data Model (if schema changes)
   - Service Layer Design
   - UI Design (if applicable)
   - Gap Analysis
   - Constitutional Compliance
   - Implementation Complexity
   - Success Criteria
3. Reference related requirements document(s)

---

## Example: Ingredients Documentation

### requirements_ingredients.md (WHAT)

**Content:**
- Ingredients are a foundational ontology entity
- Three-tier hierarchy: L0 → L1 → L2
- Only L2 can have products
- Users create/edit L2 ingredients in-app
- L0/L1 managed externally via OPML

**Stability:** Enduring business rules, reviewed quarterly

---

### F031_ingredient_hierarchy.md (HOW - Backend)

**Content:**
- Schema: `parent_ingredient_id` FK, `hierarchy_level` field
- Service: `ingredient_hierarchy_service.py` methods
- Migration: Export → transform → import strategy
- No Alembic (per Constitution Principle VI)

**Lifecycle:** Created for F031 feature, archived after implementation

---

### BUG_F032_hierarchy_conceptual_errors.md (HOW - Fix)

**Content:**
- Wrong: "Set ingredient level" dropdown
- Right: Radio buttons + cascading L0/L1 selectors
- Level is computed from parent, not assigned
- Validation rules for hierarchy changes

**Lifecycle:** Created to fix F032 error, archived after fix

---

## AI System Guidelines

### When Reading Requirements:

✅ Use as **authoritative source** for business rules  
✅ Validate your specification against requirements  
✅ Flag any spec that contradicts requirements  
✅ Don't invent requirements - ask human if unclear

### When Reading Specifications:

✅ Treat as **implementation guidance** (may be outdated)  
✅ Check if specification has been superseded  
✅ Verify constitutional compliance  
✅ Look for "Status: MERGED" to see if implemented

### When Creating Documentation:

**Ask yourself:**
- Am I defining WHAT (→ requirements) or HOW (→ specification)?
- Is this enduring business logic (→ requirements) or specific implementation (→ specification)?
- Will this change if we switch databases/frameworks (→ specification) or stay stable (→ requirements)?

---

## Maintenance Schedule

### Requirements Documents

**Review Frequency:** Quarterly  
**Update Triggers:**
- Business process changes
- User feedback reveals misaligned assumptions
- New regulatory/industry standards
- Phase transitions (desktop → web → platform)

**Ownership:** Kent Gale (Product Owner)

---

### Specification Documents

**Review Frequency:** Per feature implementation  
**Update Triggers:**
- Feature status changes (Draft → In Progress → Merged)
- Implementation reveals design flaws
- Constitutional principles updated

**Ownership:** Feature implementer (Claude Code, Gemini, Cursor, Kent)

---

## Summary

| Aspect | Requirements | Specifications |
|--------|-------------|----------------|
| **Focus** | WHAT (user needs) | HOW (implementation) |
| **Language** | Business/user terms | Technical terms |
| **Stability** | Long-lived | Per-feature lifecycle |
| **Audience** | All stakeholders | Developers/AI agents |
| **Template** | Yes (TEMPLATE_requirements.md) | No (custom per feature) |
| **Pattern** | requirements_[component].md | F0XX_[feature].md |
| **Review** | Quarterly | Per implementation |
| **Examples** | User stories, validation rules | Schemas, APIs, algorithms |

---

**Key Takeaway:**

> Requirements tell you **WHAT to build and WHY**.  
> Specifications tell you **HOW to build it**.  
> Both are essential, but serve different purposes.

---

**END OF GUIDE**
