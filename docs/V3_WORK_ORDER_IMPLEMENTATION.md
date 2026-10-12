# Workshop V3 — OWL Work Order / Financial Integrity

Base: develop @ 7c1123577cc647ddbc048268b40174c9818a422a
Branch: develop_v3 (isolated; do not merge without review).

## UI contract
- One OWL work-order screen reflecting the approved screenshot: header, customer/vehicle, status, services and parts side by side, subtotals, taxes, grand total, notes, actions.
- Languages through Odoo translations: Arabic RTL preferred for Arabic users, English LTR for English users; no global forced direction. Arabic default for new users only via controlled installation/configuration policy, not override existing user preferences.
- Backend ORM holds all business rules; OWL is presentation, never source of truth for totals or status.

## Work order state machine
- Draft -> Confirmed -> In progress -> Ready -> Delivered -> Closed.
- Cancel allowed only after explicit analysis of linked sales, stock, payments and posted accounting.
- Reopen cannot delete or mutate posted invoices/journal entries. Financial reversal is through native credit notes and stock returns, never unlinking accounting.
- Explicit audit reason and actor on cancellation/reopening.
- Lock per order for all irreversible transitions, recheck state under lock.

## Services/parts/sales/invoice
- Define one immutable source association for each line to prevent duplicate creation.
- One sale order per work order, idempotent confirmation; services use service products, parts use storable products.
- Stock reservations/delivery performed with Odoo stock pickings; invoice policy defined and audited, prevent duplicate invoicing.
- Invoice only for delivered quantities under applicable policy; taxes from fiscal position/product, currency and company consistent.
- Never directly reduce product quantities or manually create valuation entries.
- Split returns: source picking -> stock return wizard, source invoice -> credit note, source sale line referenced; allow partial quantities and enforce <= outstanding.
- Reconciliation of advances against final invoice through Odoo payments/outstanding credits; never double-count cash or VAT.
- A refund is a separate controlled operation from a credit note.

## Required test matrix (Odoo 17 database)
1. Arabic RTL / English LTR, assets loading, normal and narrow widths.
2. Multi-company / restricted users / malicious RPC, record rules enforced.
3. Same work order clicked twice: only one sale order, invoice, picking.
4. Service-only, parts-only, mixed orders, tax-inclusive/exclusive, discounts, rounding.
5. Insufficient stock, partial delivery, returns, serial/lot tracking.
6. Advance then final invoice, excess advance, multi-payment, partial refund.
7. Cancel draft, confirmed sale, posted invoice, paid invoice, delivered stock; safe blocked states.
8. Reopen only when no un-reversed financial/stock conflicts, preserve histories.
9. Partial refund and stock return, repeated refunds rejected.
10. Verify journals, receivables, payment reconciliation, stock valuation and balance per company.

## Development constraints
- No edits to main/develop/other branches.
- Keep legacy workflow untouched until new code is independently validated.
- No production deployment or database migration before passing integration tests.
- Avoid any claim of accounting correctness without tests against a configured Odoo 17 environment.
