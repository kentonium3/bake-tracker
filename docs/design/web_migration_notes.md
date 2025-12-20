# Web Migration Notes

**Purpose:** Track architectural decisions and their impact on future web deployment

**Last Updated:** 2025-11-08
**Target Timeline:** 6-18 months (Web deployment for friends & family)

---

## Overview

This document tracks decisions made during desktop development that will impact the web migration. The goal is to identify potential migration pain points early and document the rationale for desktop-specific choices.

### Migration Philosophy

**Near-term goal:** Convert desktop app to web application for 10-50 users (friends, family, neighbors)

**Learning objectives:**
- Desktop → Web architecture patterns
- Single-user → Multi-user data isolation
- Local SQLite → Cloud database (PostgreSQL/MySQL)
- Desktop UI → Responsive web interface
- Local file system → Cloud storage
- No auth → User authentication & authorization
- Single instance → Deployment/hosting/CI-CD

---

## Decision Log

Track all architectural decisions with their web migration implications.

### Template Entry

```markdown
#### [YYYY-MM-DD] Decision Name

**Context:** Why this decision was made for desktop

**Desktop Choice:** What was implemented

**Web Migration Impact:** 
- **Cost:** Low | Medium | High
- **Changes Needed:** What needs to change for web
- **Risks:** Potential issues during migration
- **Alternatives Considered:** Other options and why rejected

**Status:** ✅ Web-friendly | ⚠️ Needs migration work | 🚫 Blocks web deployment
```

---

## Architecture Decisions

### [2025-12-20] Inventory Management via API for Multiple Input Modes

**Context:** Desktop app uses manual UI for inventory entry. Web version needs to support multiple inventory input methods beyond just UI forms.

**Desktop Choice:** Direct UI input only - CustomTkinter forms for adding inventory items manually

**Web Migration Impact:**
- **Cost:** Medium
- **Changes Needed:**
  - Implement REST API endpoints for inventory management (CRUD operations)
  - Support multiple input modes:
    - Manual UI entry (web forms)
    - Mobile barcode scanning workflow (GTIN lookup → confirm/edit → add to inventory)
    - Bulk CSV import (purchase data from retailers)
    - Future: Receipt photo OCR, smart home integrations
  - API design should be input-agnostic:
    - `POST /api/inventory` - Create inventory item
    - `GET /api/inventory` - List user's inventory
    - `PUT /api/inventory/{id}` - Update inventory item
    - `DELETE /api/inventory/{id}` - Remove inventory item
  - Mobile barcode workflow needs:
    - `GET /api/products/lookup?gtin={barcode}` - Product lookup by GTIN
    - Return product details for user confirmation
    - Allow editing product_name, package_size before creating inventory
- **Risks:**
  - API security critical (ensure user can only access their own inventory)
  - Concurrent updates from multiple devices/input methods
  - Barcode lookup failures need graceful degradation (manual entry fallback)
- **Alternatives Considered:**
  - Keep UI-only approach → Rejected (limits mobile/automation use cases)
  - Separate APIs per input mode → Rejected (increases complexity, harder to maintain)

**Status:** ⚠️ Needs migration work (API layer + mobile workflow design)

**Related Features:**
- Feature 023 (Product Name Differentiation) enables GTIN → readable product identification for mobile
- Background density enrichment service (documented above) complements inventory API

---

### [2025-11-08] Service Layer Separation

**Context:** Need testable business logic independent of UI framework

**Desktop Choice:** Clean service layer with no UI imports, stateless methods accepting explicit parameters

**Web Migration Impact:**
- **Cost:** Low
- **Changes Needed:** 
  - Wrap service methods in REST API endpoints (FastAPI/Flask)
  - Add request/response serialization
  - Add authentication middleware to check user permissions
- **Risks:** Minimal - services are already UI-independent
- **Alternatives Considered:** 
  - Tight coupling to CustomTkinter → Rejected (can't reuse for web)

**Status:** ✅ Web-friendly

---

### [2025-11-08] SQLite Database with SQLAlchemy ORM

**Context:** Need simple, portable database for single desktop user

**Desktop Choice:** SQLite with WAL mode, SQLAlchemy 2.x ORM

**Web Migration Impact:**
- **Cost:** Medium
- **Changes Needed:**
  - Switch to PostgreSQL or MySQL for production (SQLAlchemy makes this easier)
  - Add connection pooling
  - Update database URL configuration
  - Test all queries on target database (some SQLite-specific quirks may exist)
  - Set up database migrations (Alembic)
- **Risks:** 
  - SQLite-specific features may not translate perfectly
  - Concurrent user access patterns differ from single-user
- **Alternatives Considered:**
  - Start with PostgreSQL → Rejected (overkill for desktop, adds complexity)
  - Use raw SQL → Rejected (ORM provides database portability)

**Status:** ✅ Web-friendly (ORM provides abstraction, but database switch required)

---

### [2025-11-08] Ingredient/Variant Architecture

**Context:** Need to support multiple brands, FIFO costing, future supplier integrations

**Desktop Choice:** Separated Ingredient (generic) from Variant (brand-specific), UUID support, industry standard fields (FoodOn, GTIN)

**Web Migration Impact:**
- **Cost:** Low
- **Changes Needed:**
  - Add user_id or tenant_id to isolate data between users
  - Decide on tenant isolation strategy (row-level vs. schema-level)
  - UUIDs already support distributed ID generation (good for web)
- **Risks:** Minimal - architecture is already multi-tenant friendly
- **Alternatives Considered:**
  - Keep conflated Ingredient model → Rejected (limits future features, requires refactor later anyway)

**Status:** ✅ Web-friendly (UUIDs and clean separation support multi-tenancy)

---

### [2025-11-08] Local File System for Database

**Context:** Desktop app stores database in user's Documents folder

**Desktop Choice:** `C:\Users\[Username]\Documents\BakeTracker\bake_tracker.db`

**Web Migration Impact:**
- **Cost:** High
- **Changes Needed:**
  - Migrate to cloud-hosted database (AWS RDS, Google Cloud SQL, etc.)
  - Set up database backups and disaster recovery
  - Implement user authentication to associate data with accounts
  - Decide on data migration strategy (import existing data to web)
  - Handle multi-tenancy (user data isolation)
- **Risks:**
  - Data migration from desktop → web could be error-prone
  - Users may want to keep desktop version and sync
- **Alternatives Considered:**
  - Cloud sync for desktop → Deferred (web migration is separate learning phase)

**Status:** ⚠️ Needs significant migration work (expected for desktop → web)

---

### [2025-11-08] No Authentication/Authorization

**Context:** Single desktop user doesn't need authentication

**Desktop Choice:** No login, no user accounts, open access to all data

**Web Migration Impact:**
- **Cost:** High
- **Changes Needed:**
  - Implement user registration and login
  - Add session management
  - Implement authorization (users can only see their own data)
  - Add password hashing (bcrypt, argon2)
  - Decide on auth strategy (sessions vs. JWT)
  - Consider OAuth/social login for ease of use
  - Add "forgot password" flow
- **Risks:**
  - Security vulnerabilities if implemented incorrectly
  - Privacy concerns if data isolation has bugs
- **Alternatives Considered:**
  - Add user accounts to desktop → Rejected (unnecessary complexity for single user)

**Status:** 🚫 Blocks web deployment (must be implemented for web)

---

### [2025-11-08] CustomTkinter Desktop UI

**Context:** Need modern desktop UI for Windows

**Desktop Choice:** CustomTkinter with tabbed interface, dialogs, forms

**Web Migration Impact:**
- **Cost:** High
- **Changes Needed:**
  - Complete UI rewrite for web (HTML/CSS/JavaScript)
  - Choose web framework (React, Vue, Svelte, or server-rendered)
  - Responsive design for mobile/tablet
  - Replicate UX patterns from desktop
  - Consider component library (Material-UI, shadcn/ui, Bootstrap)
- **Risks:**
  - UI/UX may need redesign for web paradigms
  - Users familiar with desktop may need onboarding for web
- **Alternatives Considered:**
  - Web framework for desktop (Electron, Tauri) → Rejected (heavier than CustomTkinter, less native feel)

**Status:** 🚫 Blocks web deployment (UI must be rewritten, but expected)

---

## Data Model Considerations

### Multi-Tenancy Strategy

**Decision Needed:** How to isolate user data in web version?

**Options:**
1. **Row-level tenancy** (add `user_id` to all tables)
   - ✅ Simpler database structure
   - ✅ Easier backups (single database)
   - ❌ Risk of data leakage if queries miss `user_id` filter
   
2. **Schema-level tenancy** (separate schema per user)
   - ✅ Strong data isolation
   - ❌ More complex migrations and backups
   - ❌ Harder to implement shared features (recipe sharing)

3. **Database-level tenancy** (separate database per user)
   - ✅ Strongest data isolation
   - ❌ Much more complex to manage
   - ❌ Cost prohibitive for hobby-scale

**Preliminary Choice:** Row-level tenancy with careful query auditing

**Implementation Notes:**
- Add `user_id` UUID to: Ingredient, Variant, Purchase, PantryItem, Recipe, FinishedGood, Bundle, Package, Recipient, Event
- Use SQLAlchemy query filters to enforce user_id automatically
- Add database-level row-level security (RLS) for defense in depth (PostgreSQL supports this)

---

### Shared vs. Private Recipes

**Decision Needed:** Should users be able to share recipes?

**Options:**
1. **All recipes private** (simplest for learning phase)
2. **Opt-in sharing** (user can mark recipe as "public")
3. **Full recipe marketplace** (search, ratings, forking)

**Preliminary Choice:** All private for learning phase, opt-in sharing in later iteration

**Implementation Notes:**
- Schema already supports this (just need `is_public` flag + `creator_user_id`)
- Web UI needs "share recipe" button
- Shared recipes reference generic Ingredients (already designed this way!)

---

## Service Layer Considerations

### Current Service Methods

Most service methods are already web-friendly:

✅ **IngredientService**
- Methods accept explicit parameters (no global state)
- Return data objects (no UI coupling)
- **Web change needed:** Add user_id parameter to all methods

✅ **RecipeService**
- Stateless cost calculations
- **Web change needed:** Add user_id parameter, filter by user

✅ **EventService**
- Complex aggregations are pure functions
- **Web change needed:** Add user_id parameter

⚠️ **Import/Export Service**
- Currently reads/writes local files
- **Web change needed:** Accept/return JSON data directly, let API handle file upload/download

---

## Security Considerations

### Desktop Security Model
- **No authentication:** Anyone with access to computer can use app
- **No authorization:** Full access to all data
- **No encryption:** Database file is unencrypted SQLite
- **No network:** Offline app, no remote attack surface

### Web Security Requirements
- **Authentication:** User login required (username/password + optional OAuth)
- **Authorization:** Users can only access their own data
- **Encryption:** HTTPS for data in transit, encrypted database backups
- **Network security:** Rate limiting, CSRF protection, SQL injection prevention
- **Session management:** Secure session cookies, expiration, logout
- **Password security:** Strong hashing (bcrypt/argon2), complexity requirements
- **Privacy:** GDPR/CCPA considerations for user data

**Learning Areas:**
- OWASP Top 10 vulnerabilities
- Secure session management
- Database connection security
- API authentication patterns (JWT vs. sessions)
- Input validation and sanitization

---

## Technology Stack Evolution

### Desktop Stack
```
CustomTkinter → SQLAlchemy → SQLite → Local Files
```

### Proposed Web Stack (To Be Decided)

**Backend Options:**
1. **FastAPI + SQLAlchemy + PostgreSQL**
   - ✅ Async support, modern Python
   - ✅ Reuse SQLAlchemy models (minimal changes)
   - ✅ Auto-generated OpenAPI docs
   - ✅ Fast development

2. **Django + Django ORM + PostgreSQL**
   - ✅ Batteries included (auth, admin, ORM)
   - ❌ Different ORM (would need to port models)
   - ✅ Mature ecosystem

**Frontend Options:**
1. **React + TypeScript**
   - ✅ Most popular, lots of libraries
   - ❌ Steeper learning curve

2. **Vue + TypeScript**
   - ✅ Easier learning curve
   - ✅ Good balance of features/simplicity

3. **Svelte + TypeScript**
   - ✅ Smallest bundle size
   - ❌ Smaller ecosystem

4. **Server-side rendered (Jinja2/Django templates)**
   - ✅ Simpler architecture
   - ❌ Less interactive UX

**Preliminary Preference:** FastAPI backend + Vue frontend (balance of learning and productivity)

---

## Cost Estimates

### Desktop Hosting
- **Cost:** $0/month (local app)
- **Infrastructure:** User's computer

### Web Hosting (Hobby Scale: 10-50 users)

**Option 1: Cloud Platform (AWS/GCP/Azure)**
- Database (RDS/Cloud SQL): $15-30/month
- Compute (small instance): $10-20/month
- Storage: $2-5/month
- **Total:** ~$30-60/month

**Option 2: Platform-as-a-Service (Heroku, Railway, Render)**
- All-in-one platform: $10-25/month
- Database: $10-20/month
- **Total:** ~$20-45/month

**Option 3: Serverless (AWS Lambda/Cloud Functions + managed DB)**
- Compute: ~$0-10/month (low traffic)
- Database: $15-30/month
- **Total:** ~$15-40/month

**Learning Goal:** Understand real-world hosting costs and tradeoffs

---

## Migration Milestones

### Phase 1: Service Layer API-ification (Months 1-2)
- [ ] Add user_id to all service methods
- [ ] Create REST API endpoints wrapping services
- [ ] Add request/response serialization
- [ ] Write API integration tests
- [ ] Document API (OpenAPI/Swagger)

### Phase 2: Authentication & Authorization (Months 2-3)
- [ ] Implement user registration/login
- [ ] Add session management
- [ ] Implement authorization middleware
- [ ] Add password security
- [ ] Test security thoroughly

### Phase 3: Database Migration (Months 3-4)
- [ ] Set up PostgreSQL instance
- [ ] Migrate schema (add user_id, tenant isolation)
- [ ] Test all queries on PostgreSQL
- [ ] Set up database migrations (Alembic)
- [ ] Import existing desktop data

### Phase 4: Frontend Development (Months 4-6)
- [ ] Choose frontend framework
- [ ] Set up frontend project
- [ ] Replicate desktop UI screens
- [ ] Add responsive design
- [ ] Connect to backend API

### Phase 5: Deployment & Testing (Months 6-7)
- [ ] Choose hosting platform
- [ ] Set up CI/CD pipeline
- [ ] Deploy to staging environment
- [ ] User testing with family/friends
- [ ] Fix bugs and iterate

### Phase 6: Production Launch (Month 7-8)
- [ ] Production deployment
- [ ] Monitor costs and performance
- [ ] Gather user feedback
- [ ] Document lessons learned

---

## Web Phase Enhancements

### Automated Ingredient Density Enrichment

**Feature:** Background service to lookup and populate missing density values for ingredients

**Desktop Approach:**
- Manual batch export of ingredients missing density factors
- Upload to AI tool for research and data fill
- Import completed density data back to app
- **Rationale:** Desktop phase avoids network dependencies and infrastructure complexity

**Web Phase Implementation:**
- **Service:** Background task queue (Celery, Bull, or cloud native)
- **Data Sources:** 
  - USDA FoodData Central API (free, 1000 req/hr, portions with gram equivalents)
  - Edamam/FatSecret/Spoonacular (commercial, better coverage)
  - Custom density database from desktop phase accumulated data
- **Confidence Scoring:**
  - High: Direct API match with verified source
  - Medium: Calculated from similar foods or nutritional data
  - Low: Estimated from food category averages
  - Store confidence level with density data for user transparency
- **User Control:**
  - Admin-initiated batch processing
  - Review queue for low-confidence matches
  - User can override auto-populated values
  - Audit trail for data provenance

**Architecture Benefits:**
- Cloud infrastructure supports async processing
- Multiple users = better ROI on API costs
- Learned density patterns improve over time
- Failed lookups don't block user workflow

**Implementation Priority:** Medium (after core multi-user features stable)

**Estimated Effort:** 2-3 weeks
- Background task infrastructure: 1 week
- API integration and confidence scoring: 1 week  
- Admin UI and review queue: 1 week

---

## Open Questions

**To be answered during desktop development:**

1. **Should we add web-friendly abstractions now or later?**
   - Example: Abstract file operations to support cloud storage?
   - **Preliminary answer:** Wait until web phase - don't prematurely optimize

2. **How much desktop data will users want to migrate to web?**
   - All historical data? Just active recipes?
   - **Action:** Survey users during web phase planning

3. **Will users want to use both desktop and web versions simultaneously?**
   - Need sync? Or one-way migration?
   - **Action:** Decide during web phase planning

4. **What's the authentication strategy?**
   - Email/password? OAuth (Google, GitHub)? Both?
   - **Action:** Research user preferences during web phase

5. **Which cloud provider should we use?**
   - AWS vs. GCP vs. Azure vs. PaaS?
   - **Action:** Evaluate during web phase based on learning goals and costs

---

## Document Maintenance

**When to update:**
- After making any architectural decision
- When discovering web-unfriendly pattern in desktop code
- After researching web technologies or costs
- When answering open questions

**Review schedule:**
- Monthly during desktop phase (note decisions)
- Weekly during web migration planning
- Daily during web implementation

**Status tracking:**
- ✅ Web-friendly (no migration work needed)
- ⚠️ Needs migration work (expected, planned)
- 🚫 Blocks web deployment (must be resolved)

---

**Document Status:** Living document
**Next Review:** When desktop v0.4.0 complete (Ingredient/Variant refactor)
