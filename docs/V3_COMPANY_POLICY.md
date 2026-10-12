# V3 company policy (approved)

The canonical company model is Odoo 17 `res.company`. No custom company master.

- Work orders use `company_id` pointing to `res.company`, consistent with the existing entry card.
- New related records must inherit the work order company; never silently use `env.company` when it differs.
- Sale orders, invoices, payments, journals, stock pickings, warehouses, picking types and stock locations must be checked against the order company.
- Enforce company access through Odoo `allowed_company_ids`, record rules, and `check_company` where applicable. No `sudo()` to bypass company boundaries in ordinary work order operations.
- Products and partners must be company-compatible (shared or assigned to the same company).
- Use `with_company(order.company_id)` for relevant pricing, taxes, fiscal positions, accounts, and stock configuration, after checking the user has access to that company.
- A company's financial and inventory transactions may not be moved to another company after confirmation.
- Cross-company transfers, if needed, require a separate explicit controlled workflow; never masquerade as an ordinary order.
- Tests: allowed company switch, unauthorized company RPC, mixed-company line rejection, taxes/journals/warehouses isolation, multi-company reports.

This is a design contract; implementation and integration tests remain pending.
