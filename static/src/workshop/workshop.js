/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WorkshopV2 extends Component {
    static template = "ycm_v2.Workshop";
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.ui = useState({ loading: true, orders: [], customers: [], vehicles: [], products: [], detail: null, selected: null, search: "", kind: "service", product: "", qty: 1, customer: "", vehicle: "", complaint: "", showCreate: false, currency: "" });
        onWillStart(() => this.refresh());
    }
    get filteredOrders() {
        const q = this.ui.search.trim().toLowerCase();
        return this.ui.orders.filter(o => !q || [o.name, o.partner_id?.[1], o.vehicle_id?.[1]].some(v => (v || "").toLowerCase().includes(q)));
    }
    get allowedVehicles() { return this.ui.vehicles.filter(v => String(v.partner_id?.[0]) === this.ui.customer); }
    get filteredProducts() { return this.ui.products.filter(p => p.detailed_type === (this.ui.kind === "service" ? "service" : "product")); }
    get amount() { return this.ui.detail?.order?.amount_total || 0; }
    async refresh() {
        try {
            const d = await this.orm.call("ycm.v2.order", "ui_bootstrap", []);
            Object.assign(this.ui, { orders: d.orders, customers: d.customers, vehicles: d.vehicles, products: d.products, currency: d.currency });
            if (this.ui.selected) await this.openOrder(this.ui.selected);
        } catch(e) { this.error(e); } finally { this.ui.loading = false; }
    }
    async openOrder(id) {
        try { this.ui.selected = id; this.ui.detail = await this.orm.call("ycm.v2.order", "ui_detail", [id]); }
        catch(e) { this.error(e); }
    }
    async createOrder() {
        if (!this.ui.customer || !this.ui.vehicle) return this.notification.add("اختر العميل والسيارة", { type: "warning" });
        try {
            const id = await this.orm.call("ycm.v2.order", "ui_create", [Number(this.ui.customer), Number(this.ui.vehicle), this.ui.complaint]);
            this.ui.showCreate = false; this.ui.customer = ""; this.ui.vehicle = ""; this.ui.complaint = "";
            await this.refresh(); await this.openOrder(id);
        } catch(e) { this.error(e); }
    }
    async addLine() {
        if (!this.ui.product) return this.notification.add("اختر صنفًا", { type: "warning" });
        try {
            await this.orm.call("ycm.v2.order", "ui_add_line", [[this.ui.selected], Number(this.ui.product), this.ui.kind, Number(this.ui.qty)]);
            this.ui.product = ""; this.ui.qty = 1; await this.refresh();
        } catch(e) { this.error(e); }
    }
    async transition(state) {
        try { await this.orm.call("ycm.v2.order", "action_transition", [[this.ui.selected], state]); await this.refresh(); }
        catch(e) { this.error(e); }
    }
    error(e) { this.notification.add(e?.data?.message || e?.message || "تعذر إتمام العملية", { type: "danger" }); }
}
registry.category("actions").add("ycm_v2.workshop", WorkshopV2);
