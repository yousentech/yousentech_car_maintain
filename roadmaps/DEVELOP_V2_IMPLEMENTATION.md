# develop_v2 — OWL wizard implementation

## Design contract
Six stages: Reception, Inspection, Services & Parts, Customer Approval, Execution, Closure & Delivery. RTL, low-saturation UI, one work order, persistent customer/vehicle, mobile-friendly layout.

## Implemented in this commit
- Six-stage OWL navigation and persistent work-order context.
- Reception view using existing saved data.
- Inspection notes saved with a permission-checked model RPC.
- Service/part catalog search, addition, price/tax summaries using existing Odoo calculations.
- Approval and execution actions reuse server-enforced transitions.
- Closure displays actual status and amount; no simulated delivery.
- Vehicle registration and make/model quick creation retained.

## Not yet implemented — must not claim production ready
- Inspection checklists, damage map, photo attachments and tyre/fluid readings with persistent backend models.
- External customer authorization, estimate sharing and immutable approval trail.
- Technician assignments, per-task time tracking and inventory moves.
- Quality gate, invoicing, payments, signature, actual handover.
- Arabic/English translated terms via Odoo i18n; existing wizard copy is Arabic.
- Odoo 17 runtime installation, ACL tests, OWL browser tests and regression suite.

## Mandatory verification before release
1. Upgrade module on isolated Odoo 17 test database; inspect logs.
2. Confirm OWL/QWeb asset compilation and navigation of all six stages.
3. Create customer, vehicle, order; save diagnosis; reload and confirm persistence.
4. Add service and part, verify tax and totals; confirm state locking.
5. Confirm no stock/accounting documents are created implicitly.
6. Verify access rights, company isolation, responsive layouts and RTL.
