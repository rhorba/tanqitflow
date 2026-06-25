# Document-First Artifact Chain

## Overview

For medium-to-large features and new projects, follow a strict artifact chain where each document
feeds the next. This ensures zero context loss and aligned understanding.

```
PRD (what & why) → Architecture (how) → Epics & Stories (what to build) → Implementation
```

**YAGNI**: Skip the chain for small tasks (bug fixes, quick features). Use it for:
- New projects
- Large features (3+ days of work)
- Features with multiple specialists involved
- Anything with security, compliance, or data model implications

---

## Artifact 1: Product Requirements Document (PRD)

**Owner**: Project Manager (with input from user)
**Save as**: `docs/prd-[feature-name].md`

```markdown
# PRD: [Feature Name]
**Version**: 1.0 | **Date**: [date] | **Author**: PM | **Status**: Draft / Approved

## 1. Problem Statement
[What problem are we solving? Who has this problem? 2-3 sentences max.]

## 2. Goals & Success Metrics
| Goal | Metric | Target |
|---|---|---|
| [goal 1] | [how we measure] | [number] |
| [goal 2] | [how we measure] | [number] |

## 3. User Stories
As a [user], I want to [action], so that [benefit].
- [ ] Story 1: ...
- [ ] Story 2: ...
- [ ] Story 3: ...

## 4. Scope
### In Scope
- [feature/capability 1]
- [feature/capability 2]

### Out of Scope
- [explicitly excluded 1]
- [explicitly excluded 2]

## 5. Requirements
### Functional
- FR-1: [requirement]
- FR-2: [requirement]

### Non-Functional
- NFR-1: Performance — [target]
- NFR-2: Security — [requirement]
- NFR-3: Accessibility — [standard]

## 6. Constraints & Assumptions
- [constraint 1]
- [assumption 1]

## 7. Risks
| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| [risk] | H/M/L | H/M/L | [action] |

## 8. Timeline
| Milestone | Target Date |
|---|---|
| PRD Approved | [date] |
| Architecture Done | [date] |
| Implementation Start | [date] |
| MVP Ready | [date] |
```

### PRD Validation Checklist
Before approving:
- [ ] Problem clearly stated (not a solution disguised as a problem)
- [ ] Success metrics are measurable
- [ ] Scope has explicit "out of scope" items
- [ ] User stories follow As a/I want/So that format
- [ ] Requirements are testable (can write acceptance criteria)
- [ ] Risks identified with mitigations

---

## Artifact 2: Architecture Document

**Owner**: Tech Lead (with input from DBA, Security Engineer)
**Depends on**: Approved PRD
**Save as**: `docs/architecture-[feature-name].md`

```markdown
# Architecture: [Feature Name]
**PRD Reference**: docs/prd-[feature-name].md
**Version**: 1.0 | **Date**: [date] | **Author**: Tech Lead

## 1. Overview
[1-2 sentences: what this architecture covers and the chosen approach]

## 2. Architecture Decision Records
### ADR-1: [Decision Title]
- **Context**: [why we need to decide]
- **Decision**: [what we chose]
- **Alternatives**: [what we rejected and why]
- **Consequences**: [what changes because of this]

## 3. System Design
[Text-based diagram of components and data flow]
```
[Client] → [API Gateway] → [Service] → [Database]
                                ↓
                          [External API]
```

## 4. Data Model
[Key entities and relationships — hand off to DBA for full schema]
```
User ──1:N──> Post ──1:N──> Comment
User ──N:N──> Role (via user_roles)
```

## 5. API Design
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /api/v1/[resource] | Create | Required |
| GET | /api/v1/[resource] | List | Required |
| GET | /api/v1/[resource]/:id | Get one | Required |
| PUT | /api/v1/[resource]/:id | Update | Owner |
| DELETE | /api/v1/[resource]/:id | Delete | Admin |

## 6. Security Considerations
[From Security Engineer review]
- Authentication: [method]
- Authorization: [model]
- Data protection: [encryption, PII handling]
- Key risks: [from threat model]

## 7. Infrastructure
- Hosting: [where]
- Database: [what]
- CI/CD: [pipeline]
- Monitoring: [tools]

## 8. Technical Risks
| Risk | Mitigation | Owner |
|---|---|---|
| [risk] | [action] | [who] |
```

### Architecture Validation Checklist
- [ ] Every PRD requirement has an architectural solution
- [ ] ADRs document all significant choices
- [ ] Data model supports all user stories
- [ ] API design covers all functional requirements
- [ ] Security requirements addressed
- [ ] NFRs have architectural support (caching, scaling, etc.)
- [ ] No over-engineering (YAGNI check)

---

## Artifact 3: Epics & Stories

**Owner**: Scrum Master (with input from Tech Lead)
**Depends on**: Approved Architecture
**Save as**: `docs/stories-[feature-name].md`

```markdown
# Stories: [Feature Name]
**PRD**: docs/prd-[feature-name].md
**Architecture**: docs/architecture-[feature-name].md

## Epic 1: [Epic Name]
[1-sentence description — what this epic delivers]

### Story 1.1: [Story Title]
**Priority**: Must / Should / Could
**Size**: S / M / L
**Specialist**: [Backend Dev / Frontend Dev / etc.]

**Description**:
As a [user], I want to [action], so that [benefit].

**Acceptance Criteria** (from Test Architect — ATDD):
```gherkin
Given [context]
When [action]
Then [expected result]
```

**Technical Notes** (from Architecture):
- Uses [API endpoint] from architecture doc
- Touches [data model / component]
- Security: [relevant requirement]

**Dependencies**: [other stories this depends on]

---

### Story 1.2: [Story Title]
...

## Epic 2: [Epic Name]
...

## Sprint Allocation
| Sprint | Stories | Estimated Effort |
|---|---|---|
| Sprint 1 | 1.1, 1.2, 1.3 | [X days] |
| Sprint 2 | 2.1, 2.2 | [X days] |
```

### Story Validation Checklist
- [ ] Every PRD requirement maps to at least one story
- [ ] Every story has testable acceptance criteria
- [ ] Dependencies are identified and ordered correctly
- [ ] Sizes are realistic (nothing larger than L — split if bigger)
- [ ] Architecture decisions are referenced in technical notes
- [ ] Security requirements are reflected in relevant stories

---

## Artifact Chain Workflow

### For New Projects
```
1. PM creates PRD → User approves
   📝 Log: MILESTONE "PRD approved" → .logs/activity.md
   
2. Tech Lead + DBA + Security create Architecture → User approves
   📝 Log: MILESTONE "Architecture approved" → .logs/activity.md
   📝 Log: ARCHITECTURE decisions → .logs/decisions.md
   
3. Scrum Master + Test Architect create Stories → User approves
   📝 Log: MILESTONE "Stories ready" → .logs/activity.md
   
4. Execute stories batch by batch (normal Execute workflow)
```

### For Large Features (add to existing project)
```
1. PM creates mini-PRD (sections 1-5 only) → User approves
2. Tech Lead creates architecture delta (what changes) → User approves
3. Scrum Master creates stories → User approves
4. Execute
```

### For Medium Features (2-3 days)
```
1. Skip PRD — PM writes a 3-line scope note
2. Tech Lead makes architecture decision (ADR only, no full doc)
3. Scrum Master creates stories directly
4. Execute
```

### For Small Tasks (< 1 day)
```
Skip the chain entirely. Go straight to Execute.
```

---

## Traceability

Every story should trace back to a PRD requirement and forward to a test:

```
PRD Requirement → Architecture Decision → Story → Acceptance Test → Code
     FR-1      →      ADR-1            → S1.1  →   Scenario 1   → auth.ts
```

This chain ensures nothing is built without a reason, nothing is untested, and nothing is undocumented.
