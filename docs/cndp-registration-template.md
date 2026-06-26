# TanqitFlow — CNDP Registration Template

**Commission Nationale de Contrôle de la Protection des Données à Caractère Personnel (CNDP)**  
Based on Law 09-08 — Déclaration de traitement (Article 13)

---

## Section 1 — Identity of the Controller

| Field | Value |
|-------|-------|
| **Denomination** | [Nom de la régie / ONEE Direction Régionale] |
| **Forme juridique** | Établissement public / Société d'État |
| **Adresse du siège social** | [Adresse complète, ville, code postal] |
| **Représentant légal** | [Nom, Prénom, Titre] |
| **Coordonnées DPO** | [Nom, email, téléphone] |

---

## Section 2 — Description du Traitement

| Field | Value |
|-------|-------|
| **Dénomination du traitement** | TanqitFlow — Plateforme de gestion des Eaux Non Facturées |
| **Finalité principale** | Calcul et suivi de l'eau non facturée (NRW) par zone de distribution, détection de fuites, planification des interventions |
| **Finalités secondaires** | Audit et traçabilité des actions utilisateurs ; génération de rapports de gestion |
| **Base légale** | Art. 3 — Traitement nécessaire à l'exécution d'une mission de service public (distribution d'eau potable) |

---

## Section 3 — Catégories de Données Traitées

| Catégorie | Champs | Personnes concernées | Sensibilité |
|-----------|--------|---------------------|-------------|
| Données d'identification employés | Adresse e-mail, nom complet (chiffré) | Agents de la régie (admin, analyste, agent terrain) | Normale |
| Données de consommation abonnés | Identifiant compteur, date, volume consommé | Abonnés (indirectement — via meter_id) | Normale |
| Données de journalisation | ID utilisateur, action, horodatage | Agents de la régie | Normale |

**Données sensibles (Art. 1 §9)**: Aucune donnée sensible traitée.

---

## Section 4 — Durées de Conservation

| Catégorie | Durée active | Action à l'échéance |
|-----------|-------------|---------------------|
| Comptes utilisateurs — champs PII | 5 ans d'inactivité | Effacement automatique (nullification) |
| Relevés compteurs | 5 ans | Archivage dans stockage froid MinIO |
| Journaux d'audit | 3 ans | Suppression physique |
| Rapports PDF | 1 an | Suppression automatique depuis MinIO |

---

## Section 5 — Destinataires des Données

| Destinataire | Qualité | Données communiquées |
|-------------|---------|---------------------|
| Agents de la régie | Utilisateurs internes (roles définis) | Selon leur rôle (principle of least privilege) |
| Aucun tiers externe | — | — |

**Transferts hors Maroc**: Aucun.

---

## Section 6 — Mesures de Sécurité

| Mesure | Détail |
|--------|--------|
| Authentification | JWT HS256, expiration 15 min, refresh 7 jours |
| Contrôle d'accès | RBAC 3 niveaux : utility_admin, analyst, field_viewer |
| Chiffrement des données PII | Fernet (AES-128-CBC + HMAC) — clé dans variable d'environnement `PII_ENCRYPTION_KEY` |
| Chiffrement des communications | TLS 1.2/1.3 — HSTS enforced |
| Isolation multi-tenant | Schéma PostgreSQL par régie — aucun partage de table |
| Journalisation | Toutes les opérations d'écriture journalisées (append-only) |
| Effacement sur demande | Endpoint `DELETE /users/{id}/pii` disponible pour les administrateurs |

---

## Section 7 — Droits des Personnes Concernées

Les personnes concernées peuvent exercer leurs droits (accès, rectification, suppression, opposition) en contactant le DPO à l'adresse indiquée en Section 1.

Délai de réponse : **30 jours** conformément à l'Art. 7 de la Loi 09-08.

---

## Section 8 — Déclaration

Je soussigné(e), [Nom du Représentant Légal], déclare que les informations ci-dessus sont exactes et conformes aux dispositions de la Loi 09-08 relative à la protection des personnes physiques à l'égard du traitement des données à caractère personnel.

**Date de déclaration**: [JJ/MM/AAAA]  
**Signature**: ___________________________  
**N° d'accusé CNDP**: [À compléter après enregistrement]
