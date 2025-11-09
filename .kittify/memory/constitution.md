<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles: N/A
- Added sections: Principle VII (Pragmatic Aspiration)
- Removed sections: N/A
- Templates requiring updates:
  ✅ plan-template.md - Constitution Check section needs phase-specific questions
  ⏳ web_migration_notes.md - new document to be created
- Follow-up TODOs:
  - Update plan-template.md Constitution Check section
  - Create /docs/web_migration_notes.md
-->

# Bake Tracker Constitution

## Core Principles

### I. User-Centric Design

**The application serves a real user with real needs - all features must deliver practical value.**

- Features MUST solve actual user problems, not theoretical ones
- UI MUST be intuitive for non-technical users
- Workflows MUST match natural baking planning processes
- User testing with the primary user (wife) MUST validate major features before completion
- Complexity that doesn't serve the user MUST be rejected

**Rationale:** This is a personal tool for managing holiday baking operations. Features exist to make the user's life easier, not to demonstrate technical sophistication. If the user can't understand or use it, it fails.

### II. Data Integrity & FIFO Accuracy (NON-NEGOTIABLE)

**Cost calculations and inventory tracking must be accurate and trustworthy.**

- FIFO (First In, First Out) consumption MUST be enforced for pantry items
- Unit conversions MUST be ingredient-specific where density/volume matters
- Cost calculations MUST reflect actual pantry consumption or preferred variant pricing
- Database migrations MUST preserve all existing data with validation
- Data import/export MUST be lossless and version-controlled

**Rationale:** The user relies on this application for expense tracking and shopping planning. Incorrect costs or lost data breaks trust and renders the application useless. FIFO matches physical reality (using oldest ingredients first) and provides accurate historical costing.

### III. Future-Proof Schema, Present-Simple Implementation

**Database schema supports future enhancements, but only required fields are populated initially.**

- Schema MUST include industry standard fields (FoodOn, GTIN, etc.) as nullable
- Implementation MUST populate only essential fields initially
- Features MUST be added incrementally without schema breaking changes
- User MUST NOT be burdened with unnecessary data entry upfront
- Optional enhancements MUST be clearly documented for future phases

**Rationale:** The schema is designed to support potential commercial product evolution, but the immediate need is a working personal tool. This principle allows the application to grow without disruptive migrations while keeping the MVP simple and usable.

### IV. Test-Driven Development

**Service layer logic must be tested before implementation is considered complete.**

- Unit tests MUST be written for all service layer methods
- Tests MUST cover happy path, edge cases, and error conditions
- Integration tests MUST validate database operations
- Test coverage MUST exceed 70% for services layer
- Failing tests MUST block feature completion

**Rationale:** The application involves complex calculations (FIFO costing, unit conversions, event planning aggregations). Manual testing cannot reliably catch regressions. Automated tests provide confidence during refactoring and feature additions.

### V. Layered Architecture Discipline

**Clear separation between UI, business logic, and data access layers.**

- UI layer (`src/ui/`) MUST NOT contain business logic
- Services layer (`src/services/`) MUST NOT import UI components
- Models layer (`src/models/`) MUST define schema and relationships only
- Cross-layer dependencies MUST flow downward only (UI → Services → Models → Database)
- Each layer MUST have a single, well-defined responsibility

**Rationale:** Layered architecture enables independent testing, easier refactoring, and potential future UI alternatives (web, mobile). Violations create tight coupling and make the codebase unmaintainable.

### VI. Migration Safety & Validation

**Database migrations must be reversible and thoroughly validated before execution.**

- Migration scripts MUST support dry-run mode for preview
- Dry-run MUST be executed and reviewed before actual migration
- Migration MUST preserve all data with validation queries
- Rollback plan MUST be documented before migration
- Schema changes MUST be backward-compatible during transition periods

**Rationale:** The database contains the user's planning data for important holiday events. Data loss or corruption is unacceptable. Gradual migration strategies (dual foreign keys, parallel models) provide safety nets during major refactors.

### VII. Pragmatic Aspiration

**Build for today's user while keeping tomorrow's platform in mind.**

#### Immediate Reality (2024-2025 Season)
- **Single desktop user** managing holiday baking for family/friends
- **Manual data entry** for ingredients, recipes, and planning
- **English-only** interface for non-technical user
- **Holiday-focused** workflow (Christmas, Thanksgiving, etc.)
- **Gift packages** as primary output unit

#### Near-Term Evolution (6-18 Months)
**Web Application for Friends & Family - Learning Phase**

The first major pivot serves as a **learning laboratory** for cloud application development:

**Technical Learning Goals:**
- **Architecture:** Desktop → Web migration patterns (API design, state management, session handling)
- **Data Design:** Single-user → Multi-user schema evolution (tenant isolation, data privacy)
- **UI Design:** Desktop native → Responsive web interface (browser compatibility, mobile-friendly)
- **Technologies:** Evaluate web frameworks (FastAPI/Flask + React/Vue vs. Django)
- **Deployment:** Cloud hosting basics (AWS/GCP/Azure, containerization, CI/CD)
- **Security:** Authentication, authorization, data encryption, HTTPS, vulnerability management
- **Costs:** Infrastructure monitoring, database hosting, bandwidth, scaling implications
- **Workflows:** Web development lifecycle, staging environments, blue-green deployments

**Scope Constraints for Learning Phase:**
- Still **hobby tool scale** (10-50 users max: family, friends, neighbors)
- Still **baking-focused** (validate core use case before generalizing)
- Still **English-only** (i18n is separate learning curve)
- Still **manual data entry** (focus on multi-user before automation)
- **New capability:** User accounts, data isolation, shared recipes (opt-in)

**Questions This Phase Answers:**
- What does multi-tenancy actually cost in complexity?
- How do users actually collaborate on recipes/events?
- What are real security concerns vs. theoretical ones?
- What cloud costs look like for hobby-scale application?
- Which frameworks/tools were good choices vs. regrets?

#### Full Aspirational Vision (1-3+ Years)
After validating web deployment and multi-user patterns:

**Platform Expansion:**
- **Any food type** (BBQ, catering, meal prep, weekly planning)
- **Any event type** (weddings, festivals, meal prep, restaurant prep)
- **Multi-language** support with full internationalization
- **Output flexibility** (packages, people served, dishes, portions, catering orders)

**Data Integration & Automation:**
- Programmatic ingredient/recipe ingestion (reduce friction)
- Supplier API connections (pricing, availability, ordering)
- Mobile companion app (shopping, inventory, notifications)
- Accounting system integrations
- Recipe sharing platforms and import tools

**Intelligence & Enhancement:**
- AI-powered menu generation and optimization
- Nutritional analysis and dietary accommodation
- Recipe scaling and cost optimization
- Smart inventory predictions
- Social features and community recipe sharing

#### Decision Framework

When making architectural choices, ask:

1. **Does this choice block web deployment (6-18 months)?**
   - If YES → Find alternative that supports web migration
   - If NO → Proceed with simplest desktop implementation

2. **What's the migration cost for desktop → web?**
   - **High cost** (tightly coupled to desktop UI, local file assumptions) → Reconsider
   - **Medium cost** (clean service layer, just needs API wrapper) → Acceptable
   - **Low cost** (already stateless, testable) → Ideal

3. **Does this naturally enable future multi-user features?**
   - If YES with minimal added complexity → Consider implementing
   - If YES but adds significant desktop complexity → Document for web phase

4. **What's the cost of changing this decision later?**
   - **High cost** (database schema, core abstractions) → Invest extra care now
   - **Low cost** (UI layout, file formats) → Optimize for immediate needs

#### Examples of Pragmatic Aspiration in Practice

**✅ Good Opportunistic Choices:**
- **Ingredient/Variant architecture with industry standard fields (FoodOn, GTIN, etc.)**
  - *Desktop: Nullable fields, no burden*
  - *Web: Enables supplier integrations*
  - *Platform: Ready for API connections*

- **Slug-based foreign keys instead of display names**
  - *Desktop: Clean references*
  - *Web: Enables future localization without breaking references*
  - *Platform: Multi-language ready*

- **Recipe references generic Ingredients, not specific Variants**
  - *Desktop: Brand flexibility*
  - *Web: Recipe sharing across users with different suppliers*
  - *Platform: Community recipe marketplace*

- **Service layer separated from UI layer**
  - *Desktop: Easier testing*
  - *Web: Services become API endpoints with minimal refactoring*
  - *Platform: Mobile app can use same API*

- **UUID support in BaseModel**
  - *Desktop: No impact*
  - *Web: Distributed user IDs, no conflicts*
  - *Platform: Mobile sync, distributed systems*

- **SQLAlchemy ORM (not raw SQL)**
  - *Desktop: Easier migrations*
  - *Web: Can switch to PostgreSQL/MySQL if needed*
  - *Platform: Read replicas, sharding options*

**❌ Premature Optimization to Avoid:**
- Building multi-tenancy support in desktop app
  - *Wait for web phase to learn actual requirements*

- Implementing OAuth/SSO before web deployment
  - *Desktop doesn't need it; web phase determines auth strategy*

- Creating supplier API abstraction layer before first integration
  - *Learn from real integration before generalizing*

- Designing for 10,000+ users
  - *Validate 10-50 users first, learn scaling needs*

**📋 Document for Later:**
- Maintain `/docs/web_migration_notes.md` - decisions that impact web transition
- Track "Web Migration Cost" in complexity justifications
- Note where desktop implementation makes web-hostile assumptions

#### Phase-Specific Constitution Checks

**Desktop Phase (Now):**
- Does this design block web deployment? → Must be NO or have documented path
- Is the service layer UI-independent? → Must be YES
- Are business rules in services, not UI? → Must be YES
- What's the web migration cost? → Must be documented

**Web Phase (6-18 months):**
- Does this assume single-tenant database? → Should be NO
- Does this expose user data to other users? → Must be NO
- Can this scale to 50 users? → Must be YES
- What security vulnerabilities exist? → Must be assessed
- What are monthly infrastructure costs? → Must be monitored

**Platform Phase (1-3+ years):**
- Does this assume baking domain? → Should be NO
- Does this assume English? → Should be NO
- Can this scale to 1000+ users? → Validate first
- What's the API rate limit strategy? → Must exist

**Rationale:** The user needs a working desktop tool this holiday season, but the **web migration is a deliberate learning exercise** in building cloud applications. This principle creates three distinct evaluation frames: "Does this work for my wife today?" (YES required), "Does this make web migration harder?" (document the cost), "Does this foreclose platform options?" (avoid if possible, but platform can wait).

## Technology Stack Constraints

**Fixed technology choices for consistency and compatibility.**

- **Language:** Python 3.10+ (minimum version for type hints and syntax features)
- **UI Framework:** CustomTkinter (modern appearance, cross-platform, desktop-native)
- **Database:** SQLite with WAL mode (portable, no server, excellent Python integration)
- **ORM:** SQLAlchemy 2.x (type safety, relationship management, migration support)
- **Testing:** pytest (de facto standard for Python, excellent fixtures and plugins)
- **Packaging:** PyInstaller (single executable for Windows distribution)

**Rationale:** These technologies are mature, well-documented, and meet the requirements for a desktop application. Changes require strong justification (e.g., fundamental limitation discovered) and full migration plan.

## Development Workflow

**Spec-Kitty driven development with documentation-first approach.**

- Feature specifications MUST be created in `/kitty-specs/` before implementation
- Implementation plans MUST define technical approach and complexity justifications
- Tasks MUST be tracked in `/tasks/` directory with clear status (backlog/doing/done)
- Documentation MUST be updated before feature is marked complete
- Git commits MUST reference feature numbers and follow conventional commit format

**Workflow Steps:**
1. `/spec-kitty.specify` - Create feature specification with user stories
2. `/spec-kitty.plan` - Research and plan technical implementation
3. `/spec-kitty.tasks` - Generate atomic, testable task prompts
4. `/spec-kitty.implement` - Execute tasks with TDD approach
5. `/spec-kitty.review` - Validate implementation against acceptance criteria
6. `/spec-kitty.accept` - Run full acceptance checks and user testing
7. `/spec-kitty.merge` - Merge feature branch and cleanup

**Rationale:** Spec-Kitty enforces a disciplined approach that prevents scope creep, ensures testability, and maintains comprehensive documentation. The workflow matches software engineering best practices while providing AI-assisted automation.

## Governance

**The constitution guides all development decisions and must be respected.**

### Amendment Process

- Constitution amendments MUST be proposed with clear rationale
- Version MUST be incremented according to semantic versioning:
  - **MAJOR:** Backward incompatible principle removals or redefinitions
  - **MINOR:** New principles added or material guidance expansions
  - **PATCH:** Clarifications, wording improvements, typo fixes
- Sync Impact Report MUST be generated showing affected templates
- All dependent templates and documentation MUST be updated

### Compliance Review

- Feature plans MUST pass Constitution Check gate before implementation
- Principle violations MUST be explicitly justified in Complexity Tracking table
- "Simpler alternative rejected because" MUST be documented for violations
- Unjustified complexity MUST be rejected and simplified

### Living Documentation

- This constitution supersedes ad-hoc decisions and undocumented practices
- Questions about architecture or approach MUST consult constitution first
- Conflicts between constitution and existing code MUST be resolved in favor of constitution
- Runtime guidance for AI agents found in `.kittify/AGENTS.md`

**Version**: 1.1.0 | **Ratified**: 2025-11-08 | **Last Amended**: 2025-11-08
