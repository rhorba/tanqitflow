# Communications Log — TanqitFlow

---

## UNDERSTAND answers — 2026-06-25

**Q1 — Pilot scope**
- Target: Single ONEE regional branch (Rabat or Casablanca)
- DMAs in scope: HUNDREDS (~100–300 estimated)
- Implication: ~100–300K meter reads per weekly/monthly batch; millions of rows/year → TimescaleDB is justified but plain Postgres survives MVP

**Q2 — Input data reality**
- Format: Excel/CSV exports from a billing ERP (SAP, Oracle, or local custom)
- Frequency: batch, weekly or monthly
- Implication: sync or light-async CSV parser is sufficient; no webhook receiver needed in MVP

**Q3 — Deployment target**
- Docker Compose (dev + prod)
- GitHub Actions CI/CD
- GitHub repo: https://github.com/rhorba/tanqitflow
- Implication: standard JWT auth (no LDAP/AD), cloud VPS deployment, push-to-main triggers pipeline

**Additional constraints noted**
- Full sprint backlog required (not just Sprint 1)
- Skills folder must live under tanqitflow/.claude/skills/ (done)
- Push every sprint to github.com/rhorba/tanqitflow

---
