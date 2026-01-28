# BakeTracker Cloud Migration: Project Management Plan

**Document Purpose**: Define resources, timelines, dependencies, and execution order for migrating BakeTracker from desktop to cloud multi-tenant SaaS.

**Audience**: Project managers, senior developers, technical advisors coordinating the cloud migration effort.

**Last Updated**: January 2026

---

## Executive Summary

**Total Timeline**: 24-32 weeks from start to beta launch
- **Phase 0** (Parallel with Desktop): Preparation & POC (12 weeks)
- **Phase 1** (Post-Desktop): Cloud Migration (12-16 weeks)

**Team Structure**: 
- Primary developer (you) + Senior developer/architect (50-80 hours)
- Claude Code for implementation assistance
- Former colleagues for AWS/architecture advice

**Budget**: $10-20K one-time + $125-310/month ongoing

---

## Phase 0: Preparation & Proof of Concept (Weeks 1-12)
**Timing**: Parallel with desktop MVP completion
**Goal**: De-risk cloud migration with architecture validation and resource alignment

### Week 1-2: Foundation Setup

**Deliverables**:
1. **Multi-Tenant Schema Design Document**
   - List all tables requiring `tenant_id` column
   - Define composite index strategy: `(tenant_id, id)` on all tenant-scoped tables
   - Document PostgreSQL Row-Level Security (RLS) policy approach
   - Plan SQLite → PostgreSQL data transformation logic
   - Estimated effort: 8-12 hours

2. **API Endpoint Mapping Specification**
   - Map each desktop service method to REST endpoint
   - Define request/response schemas (Pydantic models)
   - Document authentication flow (JWT with `tenant_id` claim)
   - Plan error handling and status codes
   - Estimated effort: 12-16 hours

3. **Technology Selection Finalized**
   - Auth provider: Firebase Auth vs. Supabase vs. Auth0 (comparison matrix)
   - Hosting: Render vs. Railway vs. Fly.io (pricing + features)
   - UI component library: DaisyUI vs. shadcn-svelte
   - Decision deadline: End of Week 2

**Resources**:
- Primary developer: 20-28 hours
- No external resources needed

**Dependencies**:
- None (independent work)

**Risks**:
- Technology selection paralysis → Mitigation: Use decision matrix, timebox to 2 weeks

---

### Week 3-4: Senior Developer Engagement

**Deliverables**:
1. **Senior Developer/Architect Identified**
   - Reach out to former colleagues
   - Define scope of engagement:
     - Architecture review (8-12 hours)
     - AWS/hosting setup (20-30 hours)
     - Security review (4-8 hours)
     - Code review (4 hours/week during migration)
   - Negotiate terms: Hourly rate vs. equity arrangement
   - Estimated effort: 4-8 hours (your time for outreach/negotiation)

2. **Engagement Agreement Finalized**
   - SOW (Statement of Work) or contract
   - Timeline alignment
   - Communication cadence (weekly sync calls?)
   - Estimated effort: 2-4 hours

**Resources**:
- Primary developer: 6-12 hours
- Senior developer: 2-4 hours (initial scoping calls)

**Dependencies**:
- Week 1-2 documents (needed for scoping discussion)

**Risks**:
- Senior developer unavailable in timeline → Mitigation: Identify 2-3 options, pursue in parallel
- Budget misalignment → Mitigation: Consider equity arrangement or deferred payment

---

### Week 5-8: Proof of Concept Build

**Goal**: Validate migration pattern end-to-end with minimal scope

**Deliverables**:
1. **Local PostgreSQL Setup (Docker)**
   - PostgreSQL 15+ container running locally
   - Database created with RLS enabled
   - Sample tenant data loaded
   - Estimated effort: 4-6 hours

2. **Multi-Tenant Service Layer POC**
   - Select 1-2 service methods (e.g., `IngredientService.create`, `IngredientService.get_all`)
   - Refactor to accept `tenant_id` parameter
   - Implement RLS policy for `ingredients` table
   - Write tests verifying tenant isolation
   - Estimated effort: 12-16 hours

3. **FastAPI Endpoint POC**
   - Implement 2-3 endpoints:
     - `POST /api/ingredients` (create)
     - `GET /api/ingredients` (list)
     - `GET /api/ingredients/{id}` (detail)
   - JWT authentication with `tenant_id` extraction
   - Request/response schema validation
   - Estimated effort: 12-16 hours

4. **Svelte Component POC**
   - SvelteKit project scaffolding
   - Firebase Auth integration (login/logout)
   - Ingredient list page (calls FastAPI)
   - Ingredient form page (create new)
   - Basic responsive layout
   - Estimated effort: 16-20 hours

5. **End-to-End POC Test**
   - Create 2 test tenants
   - Login as Tenant A → Create ingredient "Flour"
   - Login as Tenant B → Verify "Flour" NOT visible
   - Login as Tenant B → Create ingredient "Sugar"
   - Verify complete isolation
   - Estimated effort: 4-6 hours

**Total POC Effort**: 48-64 hours over 4 weeks = 12-16 hours/week

**Resources**:
- Primary developer: 48-64 hours
- Claude Code: Implementation assistance
- Senior developer (optional): 4-8 hours for architecture review of POC

**Dependencies**:
- Auth provider selection (Week 2)
- Senior developer engaged (Week 4) for architecture guidance

**Success Criteria**:
- ✓ POC demonstrates complete tenant isolation
- ✓ Migration pattern validated (SQLite → Postgres, Service layer → API)
- ✓ JWT auth flow working
- ✓ Svelte calling FastAPI successfully

**Risks**:
- POC reveals unforeseen complexity → Mitigation: Time-boxed to 4 weeks, if blocked, escalate to senior developer
- RLS policies more complex than expected → Mitigation: Fallback to application-layer filtering if RLS issues

---

### Week 9-12: Production Preparation

**Deliverables**:
1. **Cloud Infrastructure Setup**
   - AWS/Render/Railway account created
   - Billing configured
   - PostgreSQL managed database provisioned (staging)
   - S3/R2 bucket for image uploads
   - Estimated effort: 8-12 hours (with senior developer assistance)

2. **CI/CD Pipeline Design**
   - GitHub Actions workflow for:
     - Run tests on push
     - Deploy to staging on merge to `develop`
     - Deploy to production on merge to `main`
   - Docker container build automation
   - Database migration automation
   - Estimated effort: 12-16 hours

3. **Monitoring & Logging Setup**
   - Sentry account for error tracking
   - Axiom/Logtail for application logs
   - PostHog/Mixpanel for analytics (optional, can defer)
   - Database monitoring (connection pool, query performance)
   - Estimated effort: 8-12 hours

4. **Security Checklist**
   - OWASP Top 10 review
   - SQL injection prevention (parameterized queries)
   - XSS prevention (Svelte auto-escaping)
   - CSRF protection (SameSite cookies)
   - Rate limiting on API endpoints
   - Secrets management (environment variables, not in code)
   - Estimated effort: 8-12 hours

5. **Migration Plan Document**
   - Week-by-week execution plan for Phase 1
   - Risk assessment for each migration step
   - Rollback procedures
   - Testing checkpoints
   - Estimated effort: 8-12 hours

**Total Preparation Effort**: 44-64 hours over 4 weeks = 11-16 hours/week

**Resources**:
- Primary developer: 24-32 hours
- Senior developer: 20-32 hours (infrastructure setup, security review)

**Dependencies**:
- POC success (Week 8)
- Senior developer engaged (Week 4)

**Risks**:
- AWS setup complexity → Mitigation: Senior developer leads this work
- CI/CD pipeline bugs → Mitigation: Manual deployment acceptable initially, automate incrementally

---

## Phase 1: Cloud Migration Execution (Weeks 13-28)
**Timing**: After desktop MVP completion
**Goal**: Full cloud deployment with multi-tenant + AI integration ready for beta testing

### Week 13-16: Backend Migration

**Deliverables**:
1. **Service Layer Refactor**
   - Add `tenant_id` parameter to ALL service methods
   - Update all database queries to filter by `tenant_id`
   - Migrate from SQLite to PostgreSQL (production-ready schema)
   - Implement ALL RLS policies
   - Estimated effort: 40-60 hours

2. **FastAPI Route Implementation**
   - Implement ALL CRUD endpoints for:
     - Ingredients (6 endpoints)
     - Recipes (8-10 endpoints)
     - Events (8-10 endpoints)
     - Purchases (6 endpoints)
     - Pantry/Inventory (6-8 endpoints)
   - Authentication middleware
   - Error handling
   - Estimated effort: 60-80 hours

3. **Test Suite Migration**
   - Port desktop tests to use `tenant_id`
   - Add multi-tenant isolation tests
   - API integration tests
   - Load testing (simulate 20 concurrent users)
   - Estimated effort: 20-30 hours

4. **Data Migration**
   - Export Marianne's data from desktop SQLite
   - Transform to include `tenant_id`
   - Import to cloud PostgreSQL
   - Validation (checksums, record counts)
   - Estimated effort: 8-12 hours

**Total Backend Effort**: 128-182 hours over 4 weeks = 32-46 hours/week

**Resources**:
- Primary developer: 100-140 hours
- Claude Code: Heavy implementation assistance (boilerplate, tests)
- Senior developer: 8-12 hours (code review, RLS validation)

**Dependencies**:
- Desktop MVP completed (provides validated service layer)
- Phase 0 POC success (migration pattern validated)

**Checkpoints**:
- End of Week 14: All service methods accept `tenant_id`
- End of Week 15: All FastAPI routes implemented
- End of Week 16: Tests passing, ready for frontend integration

**Risks**:
- Service layer refactor introduces bugs → Mitigation: Comprehensive test coverage, senior developer review
- PostgreSQL migration data loss → Mitigation: Multiple backups, validation scripts

---

### Week 17-22: Frontend Build

**Deliverables**:
1. **Core Page Components**
   - Ingredient list/form (2-3 components)
   - Recipe editor (5-8 components)
   - Event planner (6-10 components)
   - Pantry inventory (3-5 components)
   - Shopping list (2-3 components)
   - Estimated effort: 60-80 hours

2. **Responsive Layouts**
   - Mobile-first design (320px+)
   - Tablet layout (768px+)
   - Desktop layout (1024px+)
   - Navigation (header, sidebar, mobile menu)
   - Estimated effort: 16-24 hours

3. **Authentication Flows**
   - Login/logout
   - Signup
   - Password reset
   - Protected routes (redirect if not authenticated)
   - Estimated effort: 12-16 hours

4. **API Client Integration**
   - API client service (axios/fetch wrapper)
   - Error handling (401, 403, 500)
   - Loading states
   - Optimistic updates
   - Estimated effort: 12-16 hours

5. **PWA Configuration**
   - Web app manifest (icons, colors, display mode)
   - Service worker (offline caching strategy)
   - Install prompts
   - Offline fallback page
   - Estimated effort: 8-12 hours

**Total Frontend Effort**: 108-148 hours over 6 weeks = 18-25 hours/week

**Resources**:
- Primary developer: 108-148 hours (you lead this work)
- Claude Code: Component generation, boilerplate
- Senior developer: 4-8 hours (code review, performance audit)

**Dependencies**:
- Backend API complete (Week 16)
- Auth provider integrated (Firebase setup from Phase 0)

**Checkpoints**:
- End of Week 18: Core CRUD pages functional
- End of Week 20: Event planning UI complete
- End of Week 22: PWA installable, responsive layouts done

**Risks**:
- Svelte learning curve steeper than expected → Mitigation: Start with POC (Phase 0), Claude Code for patterns
- Desktop UX doesn't translate well to web → Mitigation: User testing early (Marianne tests staging)

---

### Week 23-26: AI Integration

**Deliverables**:
1. **FastMCP Server Setup**
   - FastAPI + FastMCP integration
   - MCP tools exposed as API endpoints
   - Connection testing with Gemini
   - Estimated effort: 8-12 hours

2. **MCP Tool Implementation**
   - `add_purchase` (voice + receipt photo)
     - Gemini Vision API for receipt OCR
     - Gemini voice-to-text
     - Tool schema definition
     - Service layer integration
     - Estimated effort: 16-20 hours
   
   - `adjust_inventory` (photo + percentage)
     - Gemini Vision API for pantry photo
     - Percentage estimation logic
     - FIFO adjustment integration
     - Estimated effort: 12-16 hours
   
   - `create_event` (voice description)
     - Natural language parsing
     - Recipe matching/suggestions
     - Event entity creation
     - Estimated effort: 12-16 hours

3. **Frontend AI Components**
   - Voice recording UI (Web Speech API)
   - Camera capture UI
   - Receipt photo upload
   - Inventory photo capture
   - Confirmation UI (show AI interpretation, allow edits)
   - Estimated effort: 20-28 hours

4. **Human-in-the-Loop Workflows**
   - Show AI-proposed data before save
   - Edit/approve/reject UI patterns
   - Undo functionality
   - Visual distinction (AI suggested vs. confirmed)
   - Estimated effort: 12-16 hours

**Total AI Integration Effort**: 80-108 hours over 4 weeks = 20-27 hours/week

**Resources**:
- Primary developer: 80-108 hours (you have Gemini API expertise)
- Claude Code: MCP boilerplate, UI components
- Senior developer: 4-6 hours (security review of AI workflows)

**Dependencies**:
- Backend API stable (Week 16+)
- Frontend pages functional (Week 22)
- Gemini API key and quota

**Checkpoints**:
- End of Week 24: Voice purchasing working
- End of Week 25: Receipt photo OCR working
- End of Week 26: All 3 MCP tools functional

**Risks**:
- Gemini hallucinations too frequent → Mitigation: Human-in-loop confirmation prevents bad data
- API quota limits → Mitigation: Monitor usage, request quota increase if needed
- MCP integration more complex than expected → Mitigation: Fallback to direct Gemini API calls if MCP issues

---

### Week 27-28: Testing & Launch Prep

**Deliverables**:
1. **Cross-Browser Testing**
   - Chrome (Windows, Mac, Android)
   - Safari (Mac, iOS)
   - Firefox (Windows, Mac)
   - Edge (Windows)
   - Bug fixes and compatibility patches
   - Estimated effort: 16-24 hours

2. **Performance Optimization**
   - Lighthouse audit (target 90+ score)
   - Image optimization
   - Code splitting
   - Lazy loading
   - Cache headers
   - Estimated effort: 12-16 hours

3. **Security Audit**
   - Senior developer led
   - Cross-tenant access tests
   - Penetration testing (basic)
   - SQL injection attempts
   - XSS attempts
   - OWASP checklist validation
   - Estimated effort: 12-16 hours (senior developer)

4. **Documentation**
   - User onboarding guide
   - Beta tester handbook
   - Admin dashboard (user management)
   - Support/FAQ
   - Estimated effort: 8-12 hours

5. **Beta User Recruitment**
   - Identify 15-20 potential testers
   - Outreach emails
   - Onboarding calendar
   - Feedback collection plan
   - Estimated effort: 8-12 hours

**Total Launch Prep Effort**: 56-80 hours over 2 weeks = 28-40 hours/week

**Resources**:
- Primary developer: 32-44 hours
- Senior developer: 12-16 hours (security audit)
- Claude Code: Documentation generation

**Dependencies**:
- AI integration complete (Week 26)
- All features functional

**Launch Criteria** (All must be met):
- ✓ Cross-browser testing passed (no critical bugs)
- ✓ Security audit passed (no high/critical vulnerabilities)
- ✓ Performance acceptable (Lighthouse 85+)
- ✓ 15+ beta testers confirmed
- ✓ Rollback plan documented
- ✓ Monitoring dashboards live

---

## Resource Summary

### Primary Developer (You) Time Investment

| **Phase** | **Weeks** | **Hours/Week** | **Total Hours** |
|-----------|-----------|----------------|-----------------|
| Phase 0: Preparation | 1-12 | 12-16 | 144-192 |
| Phase 1: Backend | 13-16 | 32-46 | 128-184 |
| Phase 1: Frontend | 17-22 | 18-25 | 108-150 |
| Phase 1: AI | 23-26 | 20-27 | 80-108 |
| Phase 1: Launch Prep | 27-28 | 28-40 | 56-80 |
| **TOTAL** | **28 weeks** | **Avg 22-30** | **516-714 hours** |

**Interpretation**: 
- Part-time (20 hours/week): 26-36 weeks
- Full-time (40 hours/week): 13-18 weeks
- **Realistic (30 hours/week): 17-24 weeks**

### Senior Developer Time Investment

| **Activity** | **Timing** | **Hours** |
|-------------|-----------|-----------|
| Initial scoping | Week 3-4 | 2-4 |
| Architecture review | Week 5-8 | 4-8 |
| Infrastructure setup | Week 9-12 | 20-32 |
| Backend code review | Week 13-16 | 8-12 |
| Frontend review | Week 17-22 | 4-8 |
| AI integration review | Week 23-26 | 4-6 |
| Security audit | Week 27-28 | 12-16 |
| **TOTAL** | **Across 28 weeks** | **54-86 hours** |

**Estimated Cost** (at $150-250/hour): **$8,100 - $21,500**

### Budget Breakdown

**One-Time Costs**:
- Senior developer: $8K-22K (or equity arrangement)
- Design assets (icons, logo): $500-2K (optional)
- Domain name: $15-50/year
- SSL certificate: $0 (Let's Encrypt free)
- **Total One-Time: $8.5K - $24K**

**Monthly Recurring Costs**:
- Hosting (Render/Railway): $50-100
- Database (managed PostgreSQL): $20-30
- Storage (S3/R2): $5-10
- Auth (Firebase): $0 (free tier)
- Monitoring (Sentry): $0-20 (free tier / startup plan)
- Gemini API: $50-150 (depends on usage)
- **Total Monthly: $125-310**

**Total Investment for Beta** (first 6 months):
- One-time: $8.5K-24K
- Ongoing (6 months): $750-1,860
- **Grand Total: $9.25K - $25.86K**

---

## Dependencies & Critical Path

### Critical Path Items
These tasks block subsequent work and cannot be parallelized:

1. **Desktop MVP Completion** → Blocks Phase 1 start
2. **Senior Developer Engagement (Week 4)** → Blocks infrastructure setup
3. **POC Success (Week 8)** → Blocks Phase 1 planning finalization
4. **Backend API Complete (Week 16)** → Blocks frontend integration
5. **Frontend Functional (Week 22)** → Blocks AI integration
6. **Security Audit Pass (Week 28)** → Blocks beta launch

**Total Critical Path**: 28 weeks (if no delays)

### Parallelizable Work
These can proceed simultaneously:

- **Phase 0 Weeks 1-8**: Schema design + API design + POC (all parallel)
- **Phase 1 Weeks 17-22**: Frontend build + backend bug fixes (parallel)
- **Phase 1 Weeks 23-26**: AI integration + performance optimization (parallel)

### Risk Dependencies
Tasks that create project risk if delayed:

| **Task** | **Delay Impact** | **Mitigation** |
|----------|------------------|----------------|
| Senior dev unavailable | +2-4 weeks (do AWS yourself) | Identify 2-3 options early |
| POC reveals issues | +2-6 weeks (rework approach) | Time-box POC to 4 weeks, escalate early |
| Backend bugs in Week 16 | +1-3 weeks (delays frontend) | Comprehensive testing, code review |
| Gemini API issues | +1-2 weeks (troubleshoot) | Build fallback direct API integration |
| Beta tester recruitment fails | Delays validation indefinitely | Start recruiting in Week 20, need 15 confirmed by Week 28 |

---

## Milestone Schedule

### Phase 0: Preparation (Parallel with Desktop)

**Milestone 1: Foundation Complete (Week 2)**
- ✓ Multi-tenant schema designed
- ✓ API endpoints mapped
- ✓ Technology stack selected
- **Checkpoint**: Review with senior developer

**Milestone 2: Team Aligned (Week 4)**
- ✓ Senior developer engaged
- ✓ SOW signed
- ✓ Communication plan established
- **Checkpoint**: Kickoff meeting

**Milestone 3: POC Success (Week 8)**
- ✓ Multi-tenant pattern validated
- ✓ End-to-end flow working locally
- ✓ Migration strategy proven
- **Checkpoint**: Go/no-go decision for Phase 1

**Milestone 4: Production Ready (Week 12)**
- ✓ Cloud infrastructure live
- ✓ CI/CD pipeline operational
- ✓ Monitoring in place
- **Checkpoint**: Ready to execute migration

---

### Phase 1: Migration (Post-Desktop)

**Milestone 5: Backend Live (Week 16)**
- ✓ All API endpoints implemented
- ✓ Tests passing
- ✓ Staging environment deployed
- **Checkpoint**: API ready for frontend integration

**Milestone 6: Frontend Functional (Week 22)**
- ✓ All core pages working
- ✓ PWA installable
- ✓ Responsive layouts complete
- **Checkpoint**: Marianne tests staging (UX validation)

**Milestone 7: AI Integrated (Week 26)**
- ✓ Voice purchasing working
- ✓ Photo-based inventory updates working
- ✓ Confirmation workflows implemented
- **Checkpoint**: AI UX validated with test users

**Milestone 8: Beta Launch (Week 28)**
- ✓ Security audit passed
- ✓ Cross-browser testing complete
- ✓ 15+ beta testers onboarded
- ✓ Production deployment successful
- **Checkpoint**: Beta program begins

---

## Communication Plan

### Weekly Sync (Primary Developer + Senior Developer)
**Frequency**: Every Monday, 30-60 minutes
**Format**: Video call
**Agenda**:
- Progress update (what was completed)
- Blockers (what needs help)
- Code review (senior dev feedback)
- Next week priorities

### Milestone Reviews
**Frequency**: Every 2-4 weeks (aligned with milestones)
**Format**: Written + async review
**Agenda**:
- Milestone checkpoint review
- Risks and mitigation strategies
- Budget/timeline status
- Go/no-go decisions

### Ad-Hoc Support
**Method**: Slack/Discord channel
**Expected Response Time**: <24 hours for non-urgent, <4 hours for blockers
**Use Cases**: 
- Architecture questions
- Security concerns
- Infrastructure issues

---

## Risk Management

### High-Impact Risks

**Risk**: Desktop MVP timeline slips
- **Probability**: Medium (software projects often slip)
- **Impact**: High (delays entire Phase 1)
- **Mitigation**: 
  - Track desktop progress weekly
  - Cut desktop scope if needed to hit timeline
  - Phase 0 preparation can extend if desktop delayed

**Risk**: Senior developer becomes unavailable mid-project
- **Probability**: Low (but possible)
- **Impact**: High (infrastructure and security work blocked)
- **Mitigation**:
  - Document all infrastructure setup (runbooks)
  - Identify backup senior developer
  - Front-load senior dev work (Weeks 9-16)

**Risk**: POC reveals multi-tenant approach unworkable
- **Probability**: Low (proven pattern)
- **Impact**: High (requires architecture rework)
- **Mitigation**:
  - Time-box POC to 4 weeks
  - Fallback: Database-per-tenant (SQLite per user)
  - Senior developer review of POC design

**Risk**: Beta tester recruitment fails (<10 users)
- **Probability**: Medium (user acquisition always uncertain)
- **Impact**: Medium (can't validate market)
- **Mitigation**:
  - Start recruiting in Week 20 (early)
  - Target 30 prospects to get 15 commits
  - Leverage existing baker networks

### Medium-Impact Risks

**Risk**: Gemini API cost exceeds budget
- **Probability**: Low (usage predictable for 20 users)
- **Impact**: Medium (need to reduce AI features or raise budget)
- **Mitigation**:
  - Monitor API usage weekly
  - Set Gemini API spending alerts
  - Optimize prompts for token efficiency

**Risk**: Svelte learning curve steeper than expected
- **Probability**: Medium (new framework)
- **Impact**: Medium (frontend delayed 1-2 weeks)
- **Mitigation**:
  - POC in Phase 0 validates Svelte feasibility
  - Claude Code provides component patterns
  - Can fallback to React if Svelte unworkable (cost: 2-3 weeks)

**Risk**: Cross-browser bugs on iOS Safari
- **Probability**: Medium (Safari often has quirks)
- **Impact**: Low (can fix post-launch if not critical)
- **Mitigation**:
  - Test on iOS early (Week 22)
  - BrowserStack for device testing
  - PWA fallback: use in browser if install issues

---

## Quality Gates

### Each milestone must pass quality gate before proceeding:

**Gate 1 (Week 2): Foundation Review**
- [ ] Schema design reviewed by senior developer
- [ ] API design reviewed by senior developer
- [ ] Technology choices justified in writing
- **Approval Required**: Senior developer sign-off

**Gate 2 (Week 8): POC Validation**
- [ ] Multi-tenant isolation demonstrated (2 test tenants)
- [ ] No data leakage in testing
- [ ] Performance acceptable (API <200ms)
- **Approval Required**: Senior developer review + your sign-off

**Gate 3 (Week 16): Backend Ready**
- [ ] All API endpoints implemented
- [ ] Test coverage >80%
- [ ] Security review passed (no high/critical issues)
- [ ] Staging environment stable
- **Approval Required**: Senior developer code review + tests passing

**Gate 4 (Week 22): Frontend Ready**
- [ ] All pages functional
- [ ] Responsive layouts working
- [ ] PWA installable
- [ ] Marianne validation complete
- **Approval Required**: User testing feedback + your sign-off

**Gate 5 (Week 28): Launch Ready**
- [ ] Security audit passed
- [ ] Cross-browser testing complete
- [ ] Performance metrics acceptable (Lighthouse 85+)
- [ ] 15+ beta testers confirmed
- [ ] Rollback plan documented
- **Approval Required**: Senior developer + your sign-off

**No milestone can start until previous gate passed**

---

## Tracking & Reporting

### Weekly Status Report Template
**To**: Project stakeholders (you, senior developer)
**Frequency**: Every Friday
**Format**: Markdown document

```markdown
# Week N Status Report

## Completed This Week
- [Task 1]
- [Task 2]

## In Progress
- [Task 3] - 60% complete, on track
- [Task 4] - blocked by [reason]

## Planned Next Week
- [Task 5]
- [Task 6]

## Risks & Issues
- [Risk 1]: [Status/mitigation]

## Budget Status
- Spent: $X
- Remaining: $Y

## Timeline Status
- On track / 1 week ahead / 2 weeks behind
```

### Burndown Tracking
Use GitHub Projects or similar:
- Kanban board: Backlog → In Progress → Review → Done
- Track story points or hours
- Monitor velocity (hours completed per week)
- Adjust estimates based on actual velocity

---

## Success Metrics

### Phase 0 Success
- ✓ POC demonstrates tenant isolation (zero cross-tenant access)
- ✓ Senior developer engaged within budget
- ✓ Infrastructure deployed and tested
- ✓ Go decision made by Week 12

### Phase 1 Success (Technical)
- ✓ Migration completed within 12-16 weeks
- ✓ Budget within $10-25K range
- ✓ Zero critical security vulnerabilities
- ✓ API performance <200ms (95th percentile)
- ✓ PWA installable on iOS + Android

### Beta Launch Success (Product)
- ✓ 15-20 users onboarded
- ✓ 70%+ retention after 4 weeks
- ✓ 80%+ AI input adoption (vs manual)
- ✓ No critical bugs reported
- ✓ Positive user testimonials collected

---

## Appendix: Tools & Platforms

### Development Tools
- **IDE**: VS Code
- **Version Control**: Git + GitHub
- **AI Assistance**: Claude Code, Cursor (code review)
- **API Testing**: Postman or Thunder Client
- **Database Tool**: pgAdmin or TablePlus

### Project Management
- **Task Tracking**: GitHub Projects or Linear
- **Documentation**: Markdown in repo
- **Communication**: Slack or Discord
- **Time Tracking**: Toggl or Clockify (optional)

### Infrastructure
- **Hosting**: Render or Railway (managed)
- **Database**: Managed PostgreSQL (same provider)
- **Storage**: Cloudflare R2 or AWS S3
- **CDN**: Cloudflare
- **Monitoring**: Sentry + Axiom/Logtail
- **Analytics**: PostHog or Mixpanel

### Testing
- **Unit Tests**: pytest (backend), Vitest (frontend)
- **E2E Tests**: Playwright or Cypress
- **Load Testing**: k6 or Locust
- **Cross-Browser**: BrowserStack

---

**Document Status**: Ready for project kickoff
**Next Steps**: 
1. Review with senior developer
2. Confirm timeline feasibility
3. Begin Week 1 deliverables
