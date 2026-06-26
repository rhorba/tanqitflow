# TanqitFlow — Data Processing Register

**Law 09-08** — relative à la protection des personnes physiques à l'égard du traitement des données à caractère personnel (Maroc)  
**Version**: 1.0 | **Date**: 2026-06-26 | **Controller**: [Régie / ONEE Branch] | **DPO**: [To be appointed]

---

## Article 19 — Register of Processing Activities

### Processing Activity 1 — User Account Management

| Field | Value |
|-------|-------|
| **Purpose** | Authentication, access control, audit trail |
| **Legal basis** | Legitimate interest (platform operation) |
| **Data categories** | Email address (pseudonymized identifier), encrypted full name, role, login timestamps |
| **Data subjects** | Utility employees (admins, analysts, field viewers) |
| **Retention** | Active while account exists; `full_name_enc` erased after 5 years of inactivity (monthly Celery task) |
| **Encryption** | `full_name_enc`: Fernet AES-128-CBC + HMAC-SHA256, key from `PII_ENCRYPTION_KEY` env var |
| **Erasure endpoint** | `DELETE /api/v1/users/{id}/pii` — sets PII fields to NULL, keeps audit row |
| **Processor** | TanqitFlow platform hosted on-premise / approved cloud |
| **Transfer outside Morocco** | None |

---

### Processing Activity 2 — Customer Meter Reads

| Field | Value |
|-------|-------|
| **Purpose** | Water balance calculation (SIV − SCV = NRW) |
| **Legal basis** | Public interest / service delivery (water utility mandate) |
| **Data categories** | Meter ID (internal reference), reading date, volume consumed — no direct personal identifier |
| **Data subjects** | Water subscribers (indirect — meter_id not linked to name in this system) |
| **Retention** | 5 years from reading date; archived to cold MinIO prefix `{tenant}/archive/` after retention period |
| **Encryption** | `customer_ref` field (if present): encrypted with Fernet using `PII_ENCRYPTION_KEY` |
| **Erasure** | Archived records not deleted immediately; destroy archive after 7 years per utility's data governance policy |
| **Transfer outside Morocco** | None |

---

### Processing Activity 3 — Audit Logs

| Field | Value |
|-------|-------|
| **Purpose** | Non-repudiation, compliance, incident investigation |
| **Legal basis** | Legal obligation (Law 09-08 Art. 7 — security obligation) |
| **Data categories** | User ID, HTTP method, path, tenant, timestamp — no payload content |
| **Retention** | 3 years (append-only, no modification) |
| **Access** | `utility_admin` role only via future admin UI |
| **Transfer outside Morocco** | None |

---

## Technical and Organizational Measures (Art. 23)

| Measure | Implementation |
|---------|---------------|
| Access control | JWT + RBAC (3 roles); principle of least privilege |
| Encryption at rest | Fernet AES-128 for PII fields; PostgreSQL data-at-rest encryption via OS-level disk encryption recommended |
| Encryption in transit | TLS 1.2/1.3 enforced by Nginx; HSTS with `max-age=63072000` |
| Pseudonymisation | `meter_id` is an internal reference not linked to subscriber name |
| Audit logging | All write operations logged to append-only `audit_log` table |
| Data minimisation | Only fields necessary for NRW calculation are collected |
| PII erasure | `DELETE /users/{id}/pii` endpoint; automated 5-year retention job |
| Breach notification | Incident response procedure: notify CNDP within 72 hours of confirmed breach |

---

## Contact

**Data Controller Representative**: [Director, Utility Name]  
**DPO Contact**: [dpo@utility.ma]  
**CNDP Registration Number**: [To be obtained — see cndp-registration-template.md]
