# Requirements Directory Migration Plan

**Date:** 2025-12-30  
**Purpose:** Consolidate all requirements documents into `/docs/requirements/`

---

## Overview

Creating a dedicated requirements directory to separate business requirements (WHAT) from technical specifications (HOW). This improves organization and makes it clear to all contributors where to find authoritative requirements.

---

## Directory Structure

```
/docs/
├── requirements/              ← NEW - All requirements documents
│   ├── GUIDE_requirements_vs_specifications.md
│   ├── TEMPLATE_req.md
│   ├── req_application.md     (was: requirements.md)
│   ├── req_ingredients.md     (was: design/requirements_ingredients.md)
│   ├── req_recipes.md         (future)
│   ├── req_products.md        (future)
│   ├── req_inventory.md       (future)
│   ├── req_planning.md        (future)
│   └── user_stories.md        (from design/)
│
├── design/                    ← Specifications only (HOW)
│   ├── F0XX_*.md             (feature specs)
│   ├── architecture.md
│   ├── schema_*.md
│   ├── import_export_specification.md
│   └── ...
│
├── bugs/                      ← Bug fix specifications
│   └── BUG_*.md
│
└── archive/                   ← Historical/superseded docs
    └── export_import_enhancement_requirements.md
```

---

## Files to Move

### 1. Core Requirements Documents

| Current Location | New Location | Rationale |
|------------------|--------------|-----------|
| `/docs/requirements.md` | `/docs/requirements/req_application.md` | Top-level application requirements - rename for consistency |
| `/docs/design/requirements_ingredients.md` | `/docs/requirements/req_ingredients.md` | Component requirements - consolidate with others |
| `/docs/design/GUIDE_requirements_vs_specifications.md` | `/docs/requirements/GUIDE_requirements_vs_specifications.md` | Documentation guide belongs with requirements |
| `/docs/design/TEMPLATE_requirements.md` | `/docs/requirements/TEMPLATE_req.md` | Template belongs with requirements, rename for brevity |
| `/docs/design/user_stories.md` | `/docs/requirements/user_stories.md` | User stories are requirements artifacts |

### 2. Historical/Archive Documents

| Current Location | Action | Rationale |
|------------------|--------|-----------|
| `/docs/archive/export_import_enhancement_requirements.md` | KEEP in archive | Already archived, superseded by F030 |

### 3. Documents to Keep in Place

| Location | Why Not Moving |
|----------|----------------|
| `/docs/design/F0XX_*.md` | Feature specifications (HOW), belong in design/ |
| `/docs/design/architecture.md` | System architecture (HOW), belongs in design/ |
| `/docs/design/schema_*.md` | Schema specs (HOW), belong in design/ |
| `/docs/design/PHASE2_workflow_ux_redesign.md` | Design spec, not requirements |
| `/docs/design/import_export_specification.md` | Technical spec (HOW), belongs in design/ |

---

## Recommended Actions

### Phase 1: Move Core Documents (Do This Now)

```bash
# Create requirements directory (DONE)
mkdir -p /Users/kentgale/Vaults-repos/bake-tracker/docs/requirements

# Move and rename files
mv /docs/requirements.md /docs/requirements/req_application.md
mv /docs/design/requirements_ingredients.md /docs/requirements/req_ingredients.md
mv /docs/design/GUIDE_requirements_vs_specifications.md /docs/requirements/GUIDE_requirements_vs_specifications.md
mv /docs/design/TEMPLATE_requirements.md /docs/requirements/TEMPLATE_req.md
mv /docs/design/user_stories.md /docs/requirements/user_stories.md
```

### Phase 2: Update References (Do After Move)

Files that reference moved documents need path updates:

**Update these files:**
1. `/docs/requirements/req_ingredients.md`
   - Section 17 "Related Documents"
   - Change paths from `docs/design/` to `docs/requirements/` or `../design/`

2. `/docs/requirements/GUIDE_requirements_vs_specifications.md`
   - Update all example paths
   - Change `requirements_*.md` → `req_*.md`
   - Update directory references

3. `/docs/design/F031_ingredient_hierarchy.md`
   - If it references requirements, update path to `../requirements/req_ingredients.md`

4. `/docs/design/F033_recipe_redesign.md`
   - Will need to reference `../requirements/req_recipes.md` when created

5. Any other design specs that reference requirements docs

### Phase 3: Create Future Requirements Docs

When ready to document other components:

```bash
# Copy template
cp /docs/requirements/TEMPLATE_req.md /docs/requirements/req_recipes.md
cp /docs/requirements/TEMPLATE_req.md /docs/requirements/req_products.md
cp /docs/requirements/TEMPLATE_req.md /docs/requirements/req_inventory.md
cp /docs/requirements/TEMPLATE_req.md /docs/requirements/req_planning.md

# Edit each file following the template structure
```

---

## Document Classification Guide

### Move to `/docs/requirements/` if:

✅ Defines WHAT the system must do  
✅ Contains user stories or acceptance criteria  
✅ Describes business rules and validation  
✅ Technology-agnostic (could work with any tech stack)  
✅ Stable over time (doesn't change with implementation)

**Examples:**
- req_application.md (overall app requirements)
- req_ingredients.md (what ingredients must do)
- user_stories.md (business needs)

### Keep in `/docs/design/` if:

✅ Defines HOW requirements are implemented  
✅ Contains data models, APIs, algorithms  
✅ Technology-specific (Python, SQLite, etc.)  
✅ May change across implementations  
✅ Feature-specific specifications

**Examples:**
- F031_ingredient_hierarchy.md (backend implementation)
- architecture.md (system design)
- schema_v0.6_design.md (database structure)

### Keep in `/docs/archive/` if:

✅ Historical document superseded by newer work  
✅ Reference material no longer actively used  
✅ Worth keeping for historical context

---

## Benefits of This Organization

### For Humans:
1. **Clear mental model:** Requirements = WHAT, Design = HOW
2. **Easy onboarding:** New contributors know where to start
3. **Stable reference:** Requirements don't churn with implementation
4. **Better reviews:** Can review requirements independent of implementation

### For AI Agents:
1. **Authoritative source:** Clear where to find business rules
2. **Validation anchor:** Can check specs against requirements
3. **Context building:** Know what to read first (requirements) vs. second (specs)
4. **Conflict detection:** Can flag when spec contradicts requirement

### For Project Management:
1. **Traceability:** Feature specs reference component requirements
2. **Scope management:** Requirements define boundaries clearly
3. **Change control:** Separate requirements changes from implementation changes
4. **Documentation debt:** Easy to see what's documented vs. not

---

## Post-Migration Checklist

After moving files, verify:

- [ ] All moved files exist in new location
- [ ] Old locations no longer have files (or have symlinks)
- [ ] No broken links in moved documents
- [ ] Feature specs updated to reference new requirement paths
- [ ] GUIDE updated with new directory structure
- [ ] TEMPLATE renamed to TEMPLATE_req.md
- [ ] README.md (if exists) updated with new structure

---

## Notes

**Backward Compatibility:**

Some external systems (bookmarks, AI agents, documentation) may reference old paths. Consider:
- Adding a note in old location pointing to new location
- Creating symlinks (if needed temporarily)
- Updating any external documentation

**Git History:**

Using `git mv` instead of `mv` preserves file history:
```bash
git mv /docs/requirements.md /docs/requirements/req_application.md
```

---

**END OF MIGRATION PLAN**
