<div dir="rtl">

# تنقيت فلو — TanqitFlow

**منصة ذكاء المياه غير المُدرّة للإيراد | Plateforme d'Intelligence Eau Non Facturée**

[![CI](https://github.com/rhorba/tanqitflow/actions/workflows/ci.yml/badge.svg)](https://github.com/rhorba/tanqitflow/actions/workflows/ci.yml)
[![Deploy](https://github.com/rhorba/tanqitflow/actions/workflows/deploy.yml/badge.svg)](https://github.com/rhorba/tanqitflow/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/rhorba/tanqitflow/releases/tag/v1.0)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)
[![Coverage](https://img.shields.io/badge/coverage-81%25-brightgreen)](https://github.com/rhorba/tanqitflow/actions/workflows/ci.yml)

</div>

---

## نظرة عامة على المشروع | Vue d'ensemble du projet

<div dir="rtl">

### المشكلة التي يحلّها تنقيت فلو

يُعاني قطاع المياه في المغرب من خسائر ضخمة في المياه المعالجة والمحلّاة تُعرف بـ **"المياه غير المُدرّة للإيراد"** (MNF — Eau Non Facturée)، وتشمل:

- **التسرّبات الحقيقية** في شبكات التوزيع (أنابيب متهالكة، وصلات مكسورة)
- **الأخطاء في قراءة العدادات** وضعف الفوترة
- **السرقة والربط غير المشروع** بالشبكة

**الأرقام تتحدث عن نفسها:**
- تكلفة المياه المحلّاة: **~16 درهم للمتر المكعب** (4 أضعاف المياه التقليدية)
- نصيب الفرد من الموارد المائية: متجه نحو **480 م³/سنة** بحلول 2030
- المخطط الاستثماري لـ **ONEE 2025–2030** يُموَّل تحديدًا لتخفيض هذه الخسائر
- معظم المرافق المائية **لا تزال تتعقّب الخسائر يدويًا في جداول Excel**

### ما الذي يفعله تنقيت فلو؟

**تنقيت فلو** هو نظام ذكاء اصطناعي متكامل يحوّل البيانات الخام من أنظمة ERP ومحطات SCADA إلى قرارات إصلاح قابلة للتنفيذ، وذلك عبر:

</div>

### What TanqitFlow does

**TanqitFlow** transforms raw ERP exports and SCADA data into actionable repair decisions for Moroccan water utilities — automatically, bilingually, and at scale.

```
CSV Export (ERP/SCADA)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  1. INGESTION                                           │
│     Upload CSV → MinIO (audit trail) → Celery worker   │
│     Parse: DMA inflow / customer reads / pressure-flow  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  2. WATER BALANCE ENGINE  (IWA Standard Method)        │
│                                                         │
│  System Input Volume (SIV)                              │
│    ├── Billed Authorized Consumption (BAC)              │
│    └── Non-Revenue Water (NRW) ← what we minimize       │
│            ├── Apparent Losses (metering errors, theft) │
│            └── Real Losses (leaks)     ← target         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  3. LEAK DETECTION  (3 complementary signals)          │
│     • Minimum Night Flow (MNF) analysis per DMA        │
│     • Z-score anomaly detection (30-day rolling)       │
│     • Isolation Forest ML model (90-day features)      │
│     → Combined confidence score 0–100 per DMA          │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  4. PRIORITIZATION  (repair ROI ranking)               │
│     Score = loss_m³/month × cost_MAD/m³ × confidence   │
│     → Ranked worklist: "Fix DMA-07 first: saves        │
│       12,400 MAD/month with 87% confidence"            │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  5. DASHBOARD  (bilingual FR/AR, RTL-ready)            │
│     • KPI cards: NRW%, SIV, flagged DMAs               │
│     • Trend charts (Recharts)                          │
│     • Hotspot map (PostGIS + Leaflet)                  │
│     • Repair worklist with status tracking             │
│     • PDF report export in French or Arabic            │
└─────────────────────────────────────────────────────────┘
```

---

## الجمهور المستهدف | Cible

<div dir="rtl">

| المستخدم | الدور |
|----------|-------|
| **مدير إقليمي (ONEE)** | يرى ملخص نسبة ENF عبر جميع مناطق القياس، يُصدر التقارير |
| **مهندس تقني (محلل NRW)** | يرفع ملفات CSV من ERP، يراجع توازن المياه، يدير قائمة الإصلاحات |
| **مشرف ميداني** | يرى خريطة الأولويات على هاتفه، يُحدّث حالة الإصلاحات |

</div>

| User | Role |
|------|------|
| **ONEE Regional Director** | Sees NRW% summary across all DMAs, exports management reports |
| **NRW Analyst (Engineer)** | Uploads ERP CSV exports, reviews water balance, manages repair worklist |
| **Field Supervisor** | Views repair priorities on mobile, updates task status |

---

## السياق المغربي | Contexte marocain

<div dir="rtl">

- **ONEE** (المكتب الوطني للكهرباء والماء الصالح للشرب) هو الشريك الرئيسي للمشروع التجريبي
- **18 مُوزّعًا إقليميًا (SRM)** مثل RADEEMA و RADEES و AMENDIS يمثّلون السوق المستقبلي
- تنطبق على المشروع **قانون 09-08** المغربي لحماية البيانات الشخصية (ما يعادل RGPD)
- البيانات تبقى على خوادم مغربية أو أوروبية ذات سيادة (متطلب Docker Compose)
- الواجهة **ثنائية اللغة العربية/الفرنسية** مع دعم كامل للكتابة من اليمين إلى اليسار

</div>

- **ONEE** (Office National de l'Électricité et de l'Eau Potable) is the primary pilot partner
- **18 regional SRM distributors** (RADEEMA, RADEES, AMENDIS…) are the expansion market
- **Moroccan Law 09-08** (equivalent of GDPR) governs all PII handling — built-in compliance
- Data sovereignty: designed for **on-prem or Morocco-region cloud** deployment via Docker Compose
- UI is **fully bilingual French + Arabic (RTL)** — non-negotiable for government clients

---

## المزايا التقنية | Architecture technique

<div dir="rtl">

### الميزات الأمنية (بنية أساسية حكومية)

- **عزل المستأجرين على مستوى قاعدة البيانات**: مخطط PostgreSQL منفصل لكل مستأجر (أقوى من Row-Level Security)
- **تشفير البيانات الشخصية**: AES-256 عبر `pgcrypto` لجميع الحقول الحساسة
- **سجل مراجعة شامل**: كل عملية كتابة تُسجَّل (من، ماذا، متى، من أي عنوان IP)
- **نمذجة التهديدات STRIDE** + مراجعة عدائية على مكوّنات المصادقة وعزل المستأجرين
- **فحص OWASP ZAP DAST** في pipeline CI/CD
- مصادقة **JWT + RBAC** بثلاثة أدوار: مدير، محلل، مراقب ميداني

</div>

### Security posture (critical infrastructure grade)

- **Schema-per-tenant DB isolation** — hard boundary even if application bugs occur
- **AES-256 PII encryption** via pgcrypto — `customer_ref`, `full_name` never stored in plaintext
- **Append-only audit log** — every write operation logged with user, IP, before/after JSON
- **STRIDE threat model** + adversarial review checklist on auth and tenant boundaries
- **OWASP ZAP DAST** scanning in CI pipeline — build fails on any High finding
- **JWT + RBAC** — 3 roles, brute-force lockout (5 attempts → 15-min lockout via Redis)

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Gunicorn |
| Database | PostgreSQL 16 · **TimescaleDB** (time-series) · **PostGIS** (spatial) |
| Task Queue | Celery 5 · Redis 7 |
| Object Storage | **MinIO** S3-compatible (raw files + PDF reports) |
| Frontend | React 18 · Vite · TypeScript · Tailwind CSS |
| Maps | Leaflet · PostGIS GeoJSON (DMA polygons) |
| Charts | Recharts |
| i18n | i18next — **French + Arabic (RTL)** from day 1 |
| ML | scikit-learn Isolation Forest (per-DMA anomaly detection) |
| Reverse Proxy | Nginx (SSL, security headers, rate limiting) |
| CI/CD | GitHub Actions → GHCR → VPS |
| Deployment | **Docker Compose** (sovereignty-first, no vendor lock-in) |

---

## البدء السريع | Démarrage rapide

**Prerequisites**: Docker Desktop, Git

```bash
# 1. Clone
git clone https://github.com/rhorba/tanqitflow.git
cd tanqitflow

# 2. Configure environment
cp .env.example .env
# Edit .env — set: POSTGRES_PASSWORD, JWT_SECRET, PII_ENCRYPTION_KEY, MINIO_ROOT_PASSWORD

# 3. Start all 7 services
docker compose -f docker-compose.dev.yml up --build

# 4. Run DB migrations (first time only)
docker compose -f docker-compose.dev.yml exec api alembic upgrade head

# 5. Verify everything is healthy
curl http://localhost:8000/health
# → {"status":"ok","db":"ok","redis":"ok","minio":"ok"}
```

**Access points:**

| Service | URL |
|---------|-----|
| Frontend (React) | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

---

## هيكل المشروع | Structure du projet

```
tanqitflow/
├── api/                    # FastAPI backend (Python 3.12)
│   ├── routers/            # HTTP handlers (thin layer)
│   ├── services/           # Business logic orchestration
│   ├── domain/             # Pure algorithms (IWA engine, MNF, z-score, IF)
│   ├── repositories/       # DB access (SQLAlchemy async)
│   ├── models/             # ORM models (TimescaleDB hypertables + PostGIS)
│   ├── middleware/         # Tenant context + audit log
│   ├── tasks/              # Celery async tasks
│   ├── core/               # Storage (MinIO), security, permissions
│   ├── alembic/            # DB migrations (multi-tenant aware)
│   └── tests/              # Unit + integration tests (≥80% coverage gate)
│
├── frontend/               # React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── i18n/           # FR + AR translations (full RTL support)
│   │   │   ├── fr/         # French JSON translation files
│   │   │   └── ar/         # Arabic JSON translation files
│   │   ├── pages/          # Dashboard, Map, Worklist, Ingestion, Admin
│   │   ├── components/     # Shared UI + Layout + Charts + Map
│   │   ├── api/            # TanStack Query hooks + axios client
│   │   └── store/          # Zustand auth store
│   └── tests/e2e/          # Playwright tests (video recording)
│
├── nginx/                  # Nginx reverse proxy (prod only)
├── docs/                   # PRD · System Design · Architecture · Sprint Backlog
├── .logs/                  # CTS session logs (decisions, activity, issues)
├── .github/workflows/      # CI/CD (lint → test → SAST → build → deploy)
├── docker-compose.dev.yml  # Development (7 services)
├── docker-compose.prod.yml # Production (8 services + nginx)
└── .env.example            # All required environment variables documented
```

---

## خارطة الطريق | Roadmap (10 sprints × 2 semaines)

| Sprint | Thème | Statut |
|--------|-------|--------|
| **S1** | Foundation & Infrastructure | ✅ **Terminé** |
| **S2** | Auth + Multi-Tenant (JWT, RBAC, schema isolation) | ✅ **Terminé** |
| **S3** | Data Ingestion Pipeline (CSV → MinIO → Celery → TimescaleDB) | ✅ **Terminé** |
| **S4** | Water Balance Engine (algorithme IWA) | ✅ **Terminé** |
| **S5** | Leak Detection (MNF + Z-score + Isolation Forest) | ✅ **Terminé** |
| **S6** | Dashboard & Visualization (KPIs, carte, worklist) | ✅ **Terminé** |
| **S7** | Bilingual UI complete (FR/AR full RTL) | ✅ **Terminé** |
| **S8** | Security Hardening (STRIDE, DAST, Law 09-08) | ✅ **Terminé** |
| **S9** | Testing & Quality Gate (≥80% coverage, Playwright E2E) | ✅ **Terminé** |
| **S10** | Production Deploy & v1.0 Release | ✅ **Terminé** |

---

## الاختبار | Tests

**Current status:** 185 tests pass · 81% coverage (gate: 80%) · lint clean

```bash
# Backend unit + integration tests (185 tests, ≥80% coverage gate)
docker compose -f docker-compose.dev.yml exec api \
  pytest --cov=. --cov-report=term-missing

# Frontend lint (ESLint + TypeScript, 0 warnings allowed)
docker compose -f docker-compose.dev.yml exec frontend npm run lint

# Frontend production build
docker compose -f docker-compose.dev.yml exec frontend npm run build

# E2E tests (Playwright — requires running dev stack)
cd frontend && npx playwright test
```

### CI/CD pipeline

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | Every push | Lint Python · Lint TS · Test (coverage gate) · Build Vite · E2E (main only) |
| `pr.yml` | PRs → main | Lint Python · Lint TS · Test · Build |
| `security.yml` | Push main + weekly | OWASP ZAP DAST baseline scan |
| `deploy.yml` | Push main | All CI + Semgrep SAST + Docker build → GHCR + ZAP DAST + SSH deploy |

---

## التوثيق | Documentation

| Document | Description |
|----------|-------------|
| [PRD](docs/prd-tanqitflow.md) | Product Requirements — goals, user stories, functional & NFRs |
| [System Design](docs/system-design-tanqitflow.md) | Component topology, data flows, Docker services |
| [Architecture](docs/architecture-tanqitflow.md) | Module structure, DB schema (full SQL), ADRs, STRIDE, Law 09-08 |
| [Sprint Backlog](docs/stories-tanqitflow.md) | 10 sprints · 53 stories · full acceptance criteria |

---

## الترخيص | Licence

MIT © 2026 [Mohamed Rhorba](https://github.com/rhorba)
