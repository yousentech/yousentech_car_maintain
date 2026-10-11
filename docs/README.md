# Workshop V2 — One-screen Work Order (Odoo 17)

This is an **independent next-generation addon** inside the existing Git repository. The legacy addon stays intact and operational.

## Design principles
- One OWL client action for work orders (list, create, select, service and parts lines, transitions).
- Separate visit/work-order state, with one owner for each state.
- Backend validations and ACLs are authoritative; mobile applications later consume versioned server APIs.
- No fabricated stock or financial operations. Phase 1 handles draft/estimate/approval/work status; stock moves, invoicing, payments and delivery are **not implemented yet**.
- Odoo services and products come from product.product; stock integration requires reservation and outgoing moves in a subsequent milestone.

## Installation
Copy **v2/yousentech_car_maintain_v2** to the Odoo addons path and update the Apps list, then install **Workshop V2**. Odoo 17 required. The original module is NOT a dependency. Launch **الصيانة V2 → أوامر العمل**.

## First release scope
Customers, registered cars, work orders and unified line types (labor/parts), pricing/taxes using Odoo tax engine, controlled lifecycle, OWL full-screen single workspace, multi-company access rules.

## Next milestones
1. Inventory reservation/issue/return + stock audits.
2. Quote approval and accounting documents linked idempotently, ZATCA handled by standard Odoo localization.
3. Delivery checklist with invoice/payment/credit-policy gate.
4. Versioned JSON API and mobile roles, photos, signature, notifications, offline conflict policy.

## Test plan
Run module installation/update in an isolated Odoo 17 database. Verify: users cannot see other companies; no cross-customer vehicle; VIN/plate normalization; taxes via account.tax.compute_all; cannot edit approved/executing records; no negative quantities; cancellation blocked after execution; OWL loads in RTL and LTR; no console errors; exact API authorization. Manual acceptance is required before merging into develop. No installation/runtime tests were performed by the GitHub connector.
