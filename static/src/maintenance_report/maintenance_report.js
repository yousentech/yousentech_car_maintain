/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const LOADERS = {
    customer: "get_customer_report",
    upcoming: "get_dues_report",
    overdue: "get_dues_report",
    lapsed: "get_lapsed_report",
    statement: "get_statement_report",
};

/**
 * Customer follow-up & periodic maintenance reports (REPORTS_DESIGN.md §11).
 * All figures and labels are prepared server-side by yt.maintenance.report;
 * this component only renders and routes actions.
 */
export class YtMaintenanceReport extends Component {
    static template = "yousentech_car_maintain.MaintenanceReport";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.userService = useService("user");
        this.params = (this.props.action && this.props.action.params) || {};
        this.type = this.params.report_type || false;
        this.state = useState({ loading: true, error: "", data: null, vehicle: null, tab: "timeline" });
        this.canFollow = false;
        for (const method of ["reload", "openVehicle", "closeVehicle", "setTab", "openFollowup",
            "openOrder", "printPdf", "editFilters"]) {
            this[method] = this[method].bind(this);
        }
        onWillStart(async () => {
            this.canFollow = await this.userService.hasGroup("yousentech_car_maintain.group_workshop_followup");
            await this.reload();
        });
    }

    async reload() {
        if (!this.type || !LOADERS[this.type]) {
            this.state.loading = false;
            this.state.error = "افتح التقرير من قائمة التقارير لاختيار الفلاتر.";
            return;
        }
        this.state.loading = true;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call("yt.maintenance.report", LOADERS[this.type], [this.params]);
            if (this.state.vehicle) {
                await this.openVehicle(this.state.vehicle.id, true);
            }
        } catch (error) {
            this.state.error = (error && error.data && error.data.message) || "تعذر تحميل التقرير.";
        } finally {
            this.state.loading = false;
        }
    }

    async openVehicle(vehicleId, keepTab = false) {
        const detail = await this.orm.call("yt.maintenance.report", "get_vehicle_detail",
            [{ ...this.params, vehicle_id: vehicleId }]);
        this.state.vehicle = detail;
        if (!keepTab) {
            this.state.tab = "timeline";
            window.scrollTo({ top: 0 });
        }
    }

    closeVehicle() {
        this.state.vehicle = null;
    }

    setTab(tab) {
        this.state.tab = tab;
    }

    openFollowup(vehicleId, partnerId, trackKey) {
        const context = { default_vehicle_id: vehicleId, default_partner_id: partnerId };
        if (trackKey === "periodic") {
            context.default_track_type = "periodic";
        } else if (trackKey && trackKey.startsWith("oil:")) {
            context.default_track_type = "oil";
            context.default_oil_type_id = parseInt(trackKey.split(":")[1], 10);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تسجيل متابعة",
            res_model: "yt.vehicle.followup",
            views: [[false, "form"]],
            target: "new",
            context,
        }, { onClose: () => this.reload() });
    }

    openOrder(orderId) {
        if (!orderId) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "yt.reception.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    printPdf(vehicleId) {
        this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: "yousentech_car_maintain.report_customer_maintenance",
            report_file: "yousentech_car_maintain.report_customer_maintenance",
            data: { vehicle_id: vehicleId },
            context: { active_model: "yt.reception.vehicle", active_ids: [vehicleId], active_id: vehicleId },
        });
    }

    editFilters() {
        if (this.type) {
            this.action.doAction(`yousentech_car_maintain.action_yt_report_${this.type}`);
        }
    }
}

registry.category("actions").add("yt_maintenance_report", YtMaintenanceReport);
