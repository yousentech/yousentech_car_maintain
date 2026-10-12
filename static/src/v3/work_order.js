/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class WorkshopV3Order extends Component {
    static template = "yousentech_car_maintain.WorkshopV3Order";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ loading: true, busy: false, order: null, services: [], parts: [], error: null, serviceProduct: "", partProduct: "", partQty: 1 });
        onWillStart(async () => {
            const orderId = Number(this.props.action?.params?.order_id);
            if (!Number.isSafeInteger(orderId) || orderId <= 0) {
                this.state.error = _t("Open this screen from a work order.");
                this.state.loading = false;
                return;
            }
            try {
                const rows = await this.orm.read("mizan.car.work.procedure.master", [orderId], [
                    "partner_id", "state", "car_panel_no", "vin_no", "car_model", "partner_mobile",
                    "sale_order_id", "advance_amount", "total_all_before_tax", "total_tax",
                    "total_all_with_tax", "result_lines", "lines_spare_parts", "technical_name",
                    "create_date", "company_id",
                ]);
                if (!rows.length) {
                    throw new Error(_t("Work order not found."));
                }
                this.state.order = rows[0];
                const [services, parts] = await Promise.all([
                    this.orm.read("mizan.car.work.procedure.line", rows[0].result_lines || [], ["product_id", "unit_price", "total", "technical_name"]),
                    this.orm.read("mizan.car.spare.parts.lines", rows[0].lines_spare_parts || [], ["product_id", "qty_done"]),
                ]);
                this.state.services = services;
                this.state.parts = parts;
            } catch (error) {
                this.state.error = error.message || _t("Unable to load work order.");
                this.notification.add(this.state.error, { type: "danger" });
            } finally {
                this.state.loading = false;
            }
        });
    }

    async addLine(kind) {
        const productId = Number(kind === "service" ? this.state.serviceProduct : this.state.partProduct);
        if (!Number.isSafeInteger(productId) || productId <= 0 || this.state.busy) return;
        this.state.busy = true;
        try {
            await this.orm.call("mizan.car.work.procedure.master", "action_v3_add_line", [[this.order.id], kind, productId, kind === "part" ? Number(this.state.partQty) : 1]);
            await this.action.doAction({ type: "ir.actions.client", tag: "workshop_v3.order", params: { order_id: this.order.id } });
        } catch (error) {
            this.notification.add(error.message || _t("Unable to add line"), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    async removeLine(kind, id) {
        if (this.state.busy) return;
        this.state.busy = true;
        try {
            await this.orm.call("mizan.car.work.procedure.master", "action_v3_remove_line", [[this.order.id], kind, id]);
            await this.action.doAction({ type: "ir.actions.client", tag: "workshop_v3.order", params: { order_id: this.order.id } });
        } catch (error) {
            this.notification.add(error.message || _t("Unable to remove line"), { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }

    get displayName() {
        return this.state.order ? `WO/${this.state.order.id}` : "";
    }

    get order() {
        return this.state.order;
    }

    get serviceCount() {
        return this.state.services.length;
    }

    get partCount() {
        return this.state.parts.length;
    }

    async openLegacy() {
        if (!this.order) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "mizan.car.work.procedure.master",
            res_id: this.order.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("workshop_v3.order", WorkshopV3Order);
