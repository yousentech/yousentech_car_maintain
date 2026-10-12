# -*- coding: utf-8 -*-
from odoo import models, _


class WorkshopV3WorkOrder(models.Model):
    _inherit = "mizan.car.work.procedure.master"

    def action_open_workshop_v3(self):
        self.ensure_one()
        self.check_access_rights("read")
        self.check_access_rule("read")
        return {
            "type": "ir.actions.client",
            "name": _("Work Order"),
            "tag": "workshop_v3.order",
            "params": {"order_id": self.id},
        }
