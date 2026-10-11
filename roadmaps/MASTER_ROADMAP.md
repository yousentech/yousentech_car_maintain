# Workshop V2 — MASTER ROADMAP (Odoo 17)

> Version: 1.0 | Date: 2026-10-11 | Status: APPROVED FOR EXECUTION (plan, not implemented)
> Repository: yousentech/yousentech_car_maintain
> Development branch: feature/workshop-v2-core-ledger-20261011
> Technical addon: yousentech_car_maintain
> Principle: **Backend-first, tests-first, OWL last**. Never claim a phase complete without evidence.

## 0. Product charter

Build a production-grade Arabic-first multi-branch automotive workshop management system in Odoo 17: intake → digital inspection → diagnosis → estimate → documented approval → parts reservation/consumption → technician work → quality control → invoice/payment → vehicle handover → history/warranty/reporting. Support Saudi deployment and ZATCA through standard compliant Odoo accounting integration, not a parallel ledger.

### Competitive research (official product references, accessed 2026-10-11)
- Tekmetric: connected ROs, DVI, estimate approval, parts/inventory, technician board, payments, multi-shop, reporting. https://www.tekmetric.com/feature/shop-management
- AutoLeap: customer/vehicle check-in, VIN, photos, inspection checklist, technician assignments, time tracking, approvals. https://autoleap.com/features/work-order/ and https://autoleap.com/features/technician-app/
- Shopmonkey: inspection findings to estimate, work queues, parts and invoices. https://www.shopmonkey.io/demo-digital-vehicle-inspections and https://support.shopmonkey.io/hc/en-us/articles/38744406930068-Getting-Started-Shopmonkey-101
- Odoo 17 Repairs: repair orders for returned products; not a drop-in replacement for customer vehicle workshop operations. https://www.odoo.com/documentation/17.0/applications/inventory_and_mrp/repairs/repair_orders.html
- ZATCA: https://zatca.gov.sa/en/E-Invoicing/Introduction/Pages/Roll-out-phases.aspx

These are product-design references, not claims of functional parity.

## 1. Non-negotiable engineering policy

1. Feature branch only; no push/merge to main/develop without explicit approval. Each milestone uses a named checkpoint commit; avoid destructive migrations.
2. Preserve existing customers, vehicles, work orders, stock and accounting data. Upgrade scripts and backfills must be idempotent, tested on a DB clone and reversible by backup/restore plan.
3. Backend ORM and Odoo-native tree/form/search views must work independently of OWL. No new OWL feature before phase 7; only critical crash fixes.
4. No sudo, server restart, database install/upgrade, destructive SQL, stock posting, invoice posting, or outbound WhatsApp from development tooling without explicit operator approval and isolated environment.
5. Security: ACL + record rules + company checks + API access; never use sudo to bypass permissions in business endpoints; no cross-company leakage.
6. Immutable posted financial/stock events. Use native Odoo stock.move/stock.picking/account.move/account.payment mechanisms; cancellations and refunds through reversals/returns, never delete history.
7. Every workflow transition validates prerequisites server-side, with transaction-safe duplicate prevention and audit history.
8. Tests: Python compile, XML validation, install/update, ORM TransactionCase, access-control tests, negative cases, and end-to-end UAT on test DB. No phase complete with known critical/high defects.
9. Documentation, migrations, tests and changelog travel with the code in the same PR/commit group.
10. Definition of Done (DoD): requirements met + tests passing + no regressions + screenshots/logs or automated evidence + rollback instructions + explicit acceptance.

## 2. Domain architecture (source of truth)

| Area | Odoo model / strategy | Critical constraints |
| --- | --- | --- |
| Customer | res.partner extension | One customer owns many vehicles; normalized mobile and customer search; no parallel customer table |
| Manufacturer/model | ycm.v2.vehicle.make / ycm.v2.vehicle.model | Model belongs to exactly one make; no duplicate canonical names |
| Vehicle | ycm.v2.vehicle | VIN normalized and unique per company if provided; plate country/type/canonical number uniqueness; preserve legacy make/model text during migration |
| Ownership | ycm.v2.vehicle.owner | One active ownership period per vehicle; explicit transfer wizard, no implicit reassignment |
| Workshop/branch | ycm.v2.workshop linked to company, warehouse, stock locations, users | Multi-company and branch isolation |
| Visit/repair order | ycm.v2.order | Company/branch/customer/vehicle/advisor/odometer/intake snapshots, unique company-aware sequence |
| Inspection | ycm.v2.inspection + template/item/result/media | Snapshot checklist, findings, attachments, inspector, timestamp, immutable signed result |
| Estimate/approval | order lines + approval/version records | Labor/parts split, tax, discount, approval scope, approved version, rejected/deferred work |
| Execution | jobs/tasks, technician assignment, timers, QC | No completion with pending mandatory QC |
| Inventory | native stock.move / stock.picking | Reserve, issue, consume, return; no phantom inventory deduction |
| Finance | native account.move/payment + links to RO | No duplicate invoicing; down payments, partial payment, refunds, reconciliation |
| Audit/history | mail.thread or dedicated immutable event model | Actor, time, old/new state, evidence |
| Reporting | ORM/read_group/SQL reporting views | Per vehicle/customer/branch/tech/service, reconciliation with accounting |

### Vehicle identity edge cases
- Blank VIN is allowed; nonblank VIN must be valid 17-character normalized VIN (excluding I/O/Q).
- Normalize Arabic/Latin numerals and plate separators consistently; decide jurisdiction-specific plate parsing before migration.
- Plate may change; preserve plate history and do not merge distinct VINs silently.
- VIN and plate resolving to different cars is a blocking conflict, not automatic merge.
- Shared family/fleet users and owner vs driver/bill-to customer must be modeled separately.
- Concurrent duplicate creation must be guarded by SQL uniqueness, not only pre-search.

## 3. Delivery phases — sequential gates

### P0 — Stabilization and technical audit (BLOCKER; first)
**Deliver:** inventory of actual current models, XML IDs, ACLs, record rules, menus, tests, legacy data and upgrade paths; document schema gaps and errors; reproducible isolated Odoo test environment; baseline test results; backup/restore instructions.
**Fix before moving on:** test import, XML view integrity, missing form actions, access security, inconsistent catalog/vehicle data, broken OWL crash only if blocking access.
**Acceptance:** clean module install and upgrade on isolated DB; no registry errors; test suite runs; baseline recorded. Do not treat Python compile as Odoo runtime test.

### P1 — Master data + intake foundation
**Deliver:** res.partner search/create from RO, multiple vehicles, makes/models dependent catalog, VIN/plate dedup, ownership transfer/history, branch and advisors, odometer, complaint, promised date, intake condition/photos, quick create via Odoo native views.
**Automation:** select customer → filter cars; register vehicle in popup → persists in vehicle + owner tables; create RO with all relational IDs in one transaction; existing duplicate → select or ownership-transfer flow.
**Acceptance scenarios:** customer with 3 cars; two customers with same car blocked; invalid VIN rejected; different company isolated; ownership history retained; simultaneous duplicate create blocked; intake from empty database works.
**Gate:** >= 15 automated business/security tests + 8 manual UAT scenarios passing.

### P2 — Digital vehicle inspection (DVI)
**Deliver:** configurable checklists per service/vehicle class, green/amber/red/N/A results, measurements, photos, findings, recommendations, technician sign-off, inspection PDF, before/after condition and evidence.
**Acceptance:** completed inspection immutable/versioned; media access protected; checklist changes do not rewrite past inspections; red finding can create estimate suggestion; 10+ tests.

### P3 — Estimate, authorization, and pricing
**Deliver:** labor vs parts, packaged jobs/templates, labor time/rate, pricelists/taxes/discounts, approval versioning, approve/decline per item, partial approval, deferred jobs, documented authorization (internal first; customer electronic later).
**Acceptance:** unapproved items cannot be issued/charged; revisions invalidate stale approvals; totals match Odoo taxes; 12+ tests.

### P4 — Workshop execution and technician control
**Deliver:** dispatch board backend, technician assignments, start/pause/resume, workload/capacity, work logs, blocked/waiting-parts state, additional work authorization, QC checklist, ready-for-delivery.
**Acceptance:** time logs consistent; technicians see only allowed jobs; completed RO requires QC and approved scope; 10+ tests.

### P5 — Real stock and purchasing integration
**Deliver:** warehouse/location policy per branch, stock availability, reservation, pick/issue/consume, shortage/purchase requests, part substitutions, returns, warranty stock movements, traceability.
**Acceptance:** no negative phantom stock or duplicate moves on retries; cancellations reverse reservations; cross-branch transfers use native Odoo flows; quantity and valuation reconcile; 15+ tests.

### P6 — Billing, payments, delivery, warranty
**Deliver:** Odoo account.move customer invoices, tax/fiscal position, down payments, split payments, credit notes/refunds, invoice lock/idempotency, delivery confirmation, warranties, Arabic print layouts, Saudi localization/ZATCA integration through compliant configuration.
**Acceptance:** 1 invoice per billing event, no duplicate posts, reconciliation of balances, refunds and returns linked, branch/company isolation, legal invoice validation in target localization; 15+ tests.
**Note:** do not claim ZATCA compliance without actual localization, sandbox validation and acceptance by tax/accounting owner.

### P7 — OWL UX redesign AFTER backend gates
**Deliver:** design system RTL, navigation, one-screen reception, DVI workspace, estimate approval, technician board, stock and checkout; responsive layout, keyboard accessibility, loading/error/empty states, no clipped data.
**API contract:** typed documented RPC methods; no business logic only in JavaScript; use standard Odoo actions for fallbacks.
**Acceptance:** all approved P1–P6 flows executable in OWL; screenshot tests/manual responsive UAT; no lifecycle errors; no regression.

### P8 — Reporting, deployment and release
**Deliver:** vehicle/customer service history, average RO, gross margin, parts consumption, technician efficiency, inspection findings, repeat visits, warranty, branches, aging, daily cash reconciliation; role dashboards; demo seed; upgrade/migration scripts; user/admin manuals.
**Acceptance:** totals reconcile with posted invoices/stock; load tests with realistic dataset; restore drill; staging signoff; tagged release v2.0.0; zero critical/high bugs.

## 4. Strict stage gates and delivery tracking

| Phase | Current state (2026-10-11) | Gate |
| --- | --- | --- |
| P0 audit | NOT VERIFIED | installation/upgrade tests and baseline |
| P1 master data | PARTIAL CODE, UNTESTED | 15 automated + 8 UAT |
| P2 DVI | NOT STARTED | 10 tests |
| P3 estimate/approval | PARTIAL SKELETON | 12 tests |
| P4 technician execution | NOT STARTED | 10 tests |
| P5 stock | NOT STARTED | 15 tests |
| P6 finance/delivery | NOT STARTED | 15 tests |
| P7 OWL redesign | EXISTING PROTOTYPE ONLY | full flow UAT |
| P8 reports/release | NOT STARTED | reconciliation and release |

**Tracking format for every milestone:** issue ID, owner, files, dependencies, test IDs, acceptance evidence, commit SHA, risk, rollback, status (TODO/IN_PROGRESS/BLOCKED/QA/PASSED). No speculative PASS.

## 5. Immediate sprint (execute next; do not expand OWL)

1. Audit current root code, manifest, models, security, XML, and tests; write P0_AUDIT.md with blocker ranking.
2. Create isolated test DB and baseline module install/upgrade; record commands without touching other Odoo processes.
3. Repair backend structural defects, including vehicle identity and catalog migrations; build native form/tree/search intake.
4. Add tests for make/model relationship, VIN/plate collisions, ownership transfer, customer multi-car, company isolation, intake creation, unauthorized access and concurrent create.
5. Add demo data: 3 branches, 30 customers, 60 vehicles, 15 makes, 60 models, 100 orders, mixed states, sample inspections once P2 exists.
6. Publish P0 evidence and P1 test checklist; proceed only after gates pass.

## 6. Explicit exclusions and later decisions
- No speculative AI diagnostics, telematics, automatic VIN decoding provider, online booking, WhatsApp Cloud API or mobile app in initial release unless approved as a separately scoped extension.
- Define whether multi-branch requires OU, analytic account, company or warehouse dimension; do not mix them.
- Define inspection safety/liability language and consent for photos.
- Define tax country/company policy and ZATCA integration requirements before posting invoices.
- Define migration rules for legacy vehicle make/model strings and old workshop module data before production cutover.

## 7. Governance

- This file is the canonical roadmap. New feature requests go into backlog and must be mapped to a phase and acceptance tests.
- Scope changes require updating this file in the same commit, documenting impact and dependency.
- At each completed phase: commit + changelog + test report + rollback point. Only then open next phase.
- **Next action: P0 audit; do not claim P1 finished based on a working popup.**
