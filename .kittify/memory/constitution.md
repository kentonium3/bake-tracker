<!--
Sync Impact Report:
- Version change: 1.3.0 → 1.4.0
- Modified principles: VII (Pragmatic Aspiration - timeline, AI integration, examples)
- Added sections: AI-Assisted Data Entry: Proof of Concept, BT Mobile integrations
- Removed sections: "2024-2025 Season" references, outdated timeline projections
- Rationale: 2025 holiday season complete; shift to event-centric generalization and AI-assisted data entry proof-of-concept
- Templates requiring updates:
  ✅ spec-template.md - No changes needed (references constitution dynamically)
  ✅ plan-template.md - No changes needed (Constitution Check gates are generic)
- Follow-up TODOs: None
-->

# Bake Tracker Constitution

## Core Principles

### I. User-Centric Design & Workflow Validation

**The application serves dual purposes: a practical tool for a real user AND a workflow validator for future AI-assisted SaaS evolution.**

#### Immediate User Value
- Features MUST solve actual user problems, not theoretical ones
- UI MUST be intuitive for non-technical users
- Workflows MUST match natural baking planning processes
- User testing with the primary user (wife) MUST validate major features before completion
- Complexity that doesn't serve the user MUST be rejected
- Mobile companion workflows MUST reduce friction for common tasks (shopping, inventory checks)

#### Prototype & Workflow Validation
- Data structures MUST support complete, real-world workflows that can be exercised manually
- Business logic MUST be explicit, testable, and separable from UI for future API/voice/chat wrapping
- Catalog creation workflows (Products, Bundles/Finished Goods, Recipe variations) MUST be fully functional before AI assistance layers are added
- Planning and purchasing workflows MUST be validated with real use before conversational interfaces wrap them

#### AI-Forward Foundation
- Application logic and data models will form RAG/RAGraph foundations for AI-assisted user interactions
- Voice and chat AI interactions for planning, purchasing, and catalog creation depend on proven manual workflows
- The principle "solve it manually first, then add AI" ensures AI assistance enhances rather than obscures validated processes

**Rationale:** This application is both a personal holiday baking tool AND a functional prototype for a multi-user, AI-forward SaaS platform. Features must work flawlessly for the current user while simultaneously validating the workflows, data structures, and business logic that will underpin future voice/chat AI interactions. If a workflow doesn't work well manually, wrapping AI around it will only amplify the friction. Proven manual workflows become the foundation for frictionless conversational experiences.

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

### VI. Schema Change Strategy (Desktop Phase)

**For single-user desktop apps, database migrations are unnecessary complexity.**

**Desktop Phase (Current):**
- Schema changes handled via export → reset → import cycle
- Export ALL data to JSON before schema change
- Delete database, update models, recreate empty database
- Programmatically transform JSON to match new schema if needed
- Import transformed data to restored database
- No migration scripts required or maintained

**Web Phase (Future):**
- Re-evaluate migration strategy when multi-user is implemented
- Consider Alembic or similar migration tooling
- Document migration requirements in web phase constitution amendment

**Rationale:** For a single-user desktop application with robust import/export capability, the export/reset/import cycle is simpler, more reliable, and eliminates an entire category of migration-related bugs. Migration tooling becomes necessary only when multiple users have independent databases that must be upgraded in place.

### VII. Pragmatic Aspiration

**Build for today's user while keeping tomorrow's platform in mind.**

#### Current Phase: Event-Centric Generalization (Q1-Q2 2025)
- **Shift from holiday baking to event baking** - Christmas is one of many event types
- **Shift from packaging to flexible output** - Support quantity goals, serving goals, or package goals
- **Single desktop user** validating workflows for family/friends
- **Manual + AI-assisted data entry** proving friction reduction is achievable
- **English-only** interface for non-technical user

#### Near-Term: Web Application (Q3-Q4 2025)
**Hobby-scale web app for 2025 holiday baking season**

Target: 10-15 users (family, friends, neighbors) using the web version for holiday 2025.

**Technical Goals:**
- **Architecture:** Desktop → Web migration (API design, state management, session handling)
- **Data Design:** Single-user → Multi-user schema (tenant isolation, data privacy)
- **UI Design:** Desktop native → Responsive web (browser compatibility, mobile-friendly)
- **Deployment:** Cloud hosting basics (containerization, CI/CD)
- **Security:** Authentication, authorization, HTTPS

**Scope Constraints:**
- Still **hobby tool scale** (10-15 users max)
- Now **event-focused** (not just baking - any food production event)
- Still **English-only**
- **AI-assisted data entry** validated and integrated

#### Full Platform Vision (2026+)
After validating web deployment and multi-user patterns:

**Platform Expansion:**
- **Any food type** (BBQ, catering, meal prep, weekly planning)
- **Any event type** (weddings, festivals, meal prep, restaurant prep)
- **Multi-language** support with full internationalization
- **Output flexibility** (packages, servings, quantities, catering orders)
- **Scalable infrastructure** for broader user base

**Intelligence & Enhancement:**
- AI-powered menu generation and optimization
- Fluid voice and chat interactions for planning and purchasing
- Nutritional analysis and dietary accommodation
- Recipe scaling and cost optimization
- Smart inventory predictions

#### AI-Assisted Data Entry: Proof of Concept

**The Core Insight:** Data entry friction causes most apps and spreadsheets in this space to fail. AI assistance can overcome this friction IF the underlying structure and workflows are sound.

**Proof-of-Concept Goals (Current Phase):**
- Demonstrate mobile AI-assisted user input for purchasing and inventory updates
- Validate with slow, batch, semi-automated JSON file creation and ingestion
- Show that fluid voice/chat interactions are achievable even if current implementation is clunky
- Prove the workflow structure supports AI wrapping before investing in real-time interfaces

**Current Integrations:**
- **BT Mobile Purchase Scanning:**
  - Gemini photo processing of barcodes, package images, and price tags
  - Results in JSON upload files merged via import service into Purchasing tables

- **BT Mobile Inventory Updates:**
  - Gemini image processing of products
  - Voice or text input for additions or percentage remaining
  - Results in JSON upload files merged via import service into Inventory tables

**Success Criteria:** If AI can create valid JSON that imports cleanly, real-time voice/chat is just an interface layer away.

#### Decision Framework

When making architectural choices, ask:

1. **Does this choice block web deployment (Q3 2025)?**
   - If YES → Find alternative that supports web migration
   - If NO → Proceed with simplest desktop implementation

2. **What's the migration cost for desktop → web?**
   - **High cost** (tightly coupled to desktop UI, local file assumptions) → Reconsider
   - **Medium cost** (clean service layer, just needs API wrapper) → Acceptable
   - **Low cost** (already stateless, testable) → Ideal

3. **Does this support AI-assisted data entry?**
   - If YES with minimal added complexity → Implement now
   - If YES but requires major refactoring → Document for near-term

4. **What's the cost of changing this decision later?**
   - **High cost** (database schema, core abstractions) → Invest extra care now
   - **Low cost** (UI layout, file formats) → Optimize for immediate needs

#### Examples of Pragmatic Aspiration in Practice

**Good Opportunistic Choices:**

- **BT Mobile purchase scanning with Gemini image processing**
  - *Desktop: Proves AI-assisted workflow; reduces data entry friction*
  - *Web: Same JSON import; mobile-first validated*
  - *Platform: Foundation for real-time voice/chat purchasing*

- **BT Mobile inventory updates with percentage input**
  - *Desktop: Validates FIFO + percentage calculation logic*
  - *Web: Same service layer; API-ready*
  - *Platform: Voice command "flour is half empty" → automatic adjustment*

- **Slug-based foreign keys instead of display names**
  - *Desktop: Clean references*
  - *Web: Enables future localization without breaking references*
  - *Platform: Multi-language ready*

- **Service layer separated from UI layer**
  - *Desktop: Easier testing*
  - *Web: Services become API endpoints with minimal refactoring*
  - *Platform: Mobile app and voice assistant use same API*

- **Import/Export v4.0 with atomic rollback**
  - *Desktop: Reliable data operations*
  - *Web: Same guarantees for multi-user*
  - *Platform: Foundation for real-time sync*

**Premature Optimization to Avoid:**

- Building real-time voice interface before batch JSON proves workflow
  - *Validate structure first; polish interface later*

- Implementing OAuth/SSO before web deployment
  - *Desktop doesn't need it; web phase determines auth strategy*

- Designing for 1000+ users before 15 users validated
  - *Prove hobby scale works; then scale*

- Building native mobile app before web + PWA validated
  - *BT Mobile JSON export proves the workflow; native can come later*

**Document for Later:**
- Maintain `/docs/web_migration_notes.md` - decisions that impact web transition
- Track "Web Migration Cost" in complexity justifications
- Note where desktop implementation makes web-hostile assumptions

#### Phase-Specific Constitution Checks

**Desktop Phase (Now - Q2 2025):**
- Does this design block web deployment? → Must be NO or have documented path
- Is the service layer UI-independent? → Must be YES
- Does this support AI-assisted JSON import? → Should be YES
- What's the web migration cost? → Must be documented

**Web Phase (Q3-Q4 2025):**
- Does this assume single-tenant database? → Should be NO
- Does this expose user data to other users? → Must be NO
- Can this scale to 15 users? → Must be YES
- What security vulnerabilities exist? → Must be assessed
- Is AI-assisted input working? → Must be validated

**Platform Phase (2026+):**
- Does this assume baking domain? → Should be NO
- Does this assume English? → Should be NO
- Can this scale to 100+ users? → Validate first
- Is real-time voice/chat feasible? → Must have proof-of-concept

**Rationale:** The 2025 holiday baking season is complete. Focus shifts to event-centric generalization and proving AI-assisted data entry reduces friction. The web app must be ready for 10-15 users by holiday 2025. Current development pace may accelerate these timelines. The key insight: if batch JSON import works with AI assistance, real-time voice/chat is achievable.

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

**Version**: 1.4.0 | **Ratified**: 2025-11-08 | **Last Amended**: 2026-01-07
