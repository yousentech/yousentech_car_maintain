# Workshop V2 — Strict operating and accounting policy (draft)

## Scope and isolation
New branch feature/workshop-v2-core-ledger-20261011, based on the existing V2 prototype. Do not merge into develop until acceptance and full Odoo 17 integration tests. Existing V2 prototype is NOT production ready.

## Identity
- One partner may own unlimited vehicles. Normalize plate (country, plate type, letters/numbers); enforce unique active vehicle identity across company, independent of customer. If a plate is transferred/reassigned, record effective-dated ownership history rather than duplicate identity. Use database unique indexes, not only Python constraints. VIN must be 17 characters excluding I/O/Q, unique per company when present.
- Workshop config: company, internal workshop location, source parts-store location, returns location, picking types, stock warehouse, journals, payment and credit policies. Reject activation if missing/incompatible company or non-internal locations.

## Quantity ledger
- Work order line holds requested, approved, received, reserved, consumed, returned, billable, invoiced, credited quantities. Never infer stock consumption from a transfer receipt.
- Internal transfer store -> workshop increases workshop on-hand; actual consumption uses a separate stock move workshop -> designated consumption location (or a suitable Odoo supported consumption flow). Unused parts return workshop -> store. A physically consumed part cannot be returned to store without physical return and appropriate reversal.
- Invariant per order/product/lot/UoM: received = consumed + returned_to_store + still_at_workshop (adjusted for explicitly documented movements). Billable <= approved_consumed unless a controlled non-stock/service policy applies. Invoiced <= billable; credited <= invoiced. Check lot/serial tracking and UoM conversions.
- Example: receive 2, consume 1, return 1; bill and invoice 1. Receipt does not automatically create a sales invoice.
- Manual entry is permission-controlled but never bypasses physical stock ledger. Require reason, source location, lot/serial where tracked, and audit record.

## Financial documents
- Work order -> unique sale.order link -> one or more invoices using native sale order invoicing policies. For parts, invoice actual approved usage; service pricing may be fixed or time/materials per approved policy. Use Odoo native taxes/currency and fiscal position.
- Advance payments are posted account.payment / standard accounting entries tied to partner and order, with reconciliation against invoice when issued. No duplicate reconciliation; use explicit allocation ledger. Refund excess advances using native outbound payments after approval.
- Invoice return: native account.move reversal/credit note. Financial refund is independent from physical return: a price correction can create a credit note without moving stock. Physical return requires validated stock return flow. Track credited quantity against original invoice line and stock move, and reconcile refund payments using Odoo accounting.
- Posted documents are immutable via workflow. Corrections use reversals; never unlink posted records.

## State policy
Draft -> diagnosis -> estimate -> awaiting_customer_approval -> approved -> in_progress -> technical_complete -> stock_reconciled -> ready_to_invoice -> invoiced -> ready_to_deliver -> delivered -> closed.
Cancelled and returned/rework are controlled exception flows, not arbitrary state edits. After completion, do not unlock historic lines; create revision/change order, credit note, stock return or warranty/rework work order with references.
- Gate technical_complete: checklist, labor confirmations, used quantities.
- Gate stock_reconciled: all received parts consumed/returned/explicitly retained, no unvalidated transfers, lot/serial reconciliation.
- Gate ready_to_invoice: approval, price/tax snapshot, billable quantities, verified accounting and stock config.
- Gate ready_to_deliver: invoice posted and payment settled OR explicitly approved credit policy; signed checklist, keys/vehicle release.

## Integrity & authorization
- Use server-side ACL + record rules for company/workshop/role; groups: reception, advisor, technician, parts clerk, warehouse manager, cashier, accountant, supervisor, manager, auditor.
- Use SQL constraints, row-level locks on critical transitions, unique idempotency keys for transfer/issue/invoice/refund actions, transaction savepoints, and post-commit external notifications. Do not commit mid-request.
- No sudo in user-facing methods except tightly scoped audited system operations. Validate ownership/company, UoM, lot, serial, negative stock policy, approval ceilings, posted state, credit terms.
- Maintain append-only business event log (actor, company, time, origin, before/after, reason, related move and accounting document). Never edit history to mask reversals.

## Reports
WIP by status, daily orders, technician productivity, service profitability, parts sent/received/used/returned, stock discrepancies, outstanding advances, invoiced vs consumed, open credits/refunds, return reasons, warranty and rework, audit exceptions.

## Acceptance scenarios
1. Same customer, multiple plates; duplicate normalized plate rejected across customers.
2. Two concurrent receptions with same plate; only one succeeds.
3. Two parts transferred, one used, one returned: exactly one invoiced and one consumed.
4. Repeat issue/invoice click and retry after network failure: no duplicate records.
5. Partial receipt, missing lot, wrong company/location, serial collision: reject.
6. Advance payment, invoice, partial reconcile, excess refund: balanced accounting.
7. Full/partial credit note with and without physical return: correct separate flows.
8. Locked completed order cannot silently change pricing or consumed qty.
9. Concurrent return and invoice: serialization prevents inconsistent quantities.
10. Multi-company ACL tests, record-rule tests, transaction rollback and recovery.

## Implementation order
A. Configuration + vehicle registry + SQL uniqueness and tests.
B. Work order lines, state engine and authorization.
C. Internal transfers, consumption, return and reconciliation ledger.
D. Sale orders, invoicing, advance allocation and credit notes.
E. OWL single-screen workspace + reports and full integration tests.
F. Versioned API and mobile application after Odoo acceptance.

This file specifies intended behavior; it does not claim the code already enforces these rules.
