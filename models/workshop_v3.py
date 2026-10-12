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

    def action_v3_add_line(self, kind, product_id, quantity=1):
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        if self.state == "cancel_order" or self.sale_order_id or self.create_invoice_manually_id:
            from odoo.exceptions import UserError
            raise UserError(_("This work order cannot be edited after sale/invoice or cancellation."))
        if kind not in ("service", "part"):
            from odoo.exceptions import ValidationError
            raise ValidationError(_("Invalid line type."))
        product = self.env["product.product"].browse(int(product_id)).exists()
        if not product or (product.company_id and product.company_id != self.company_id):
            from odoo.exceptions import ValidationError
            raise ValidationError(_("Invalid product company."))
        if kind == "service" and product.detailed_type != "service":
            from odoo.exceptions import ValidationError
            raise ValidationError(_("Select a service product."))
        if kind == "part" and product.detailed_type != "product":
            from odoo.exceptions import ValidationError
            raise ValidationError(_("Select a stockable product."))
        if kind == "part" and (not isinstance(quantity, (int, float)) or quantity <= 0):
            from odoo.exceptions import ValidationError
            raise ValidationError(_("Quantity must be positive."))
        if kind == "service":
            return self.env["mizan.car.work.procedure.line"].create({
                "header_id": self.id, "product_id": product.id,
                "name": product.display_name, "unit_price": product.lst_price,
            }).id
        return self.env["mizan.car.spare.parts.lines"].create({
            "header_id": self.id, "product_id": product.id, "name": product.display_name,
            "qty": quantity, "qty_done": quantity, "unit_price": product.lst_price,
        }).id

    def action_v3_remove_line(self, kind, line_id):
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        from odoo.exceptions import UserError, ValidationError
        if self.sale_order_id or self.create_invoice_manually_id or self.state == "cancel_order":
            raise UserError(_("Cannot remove lines from a finalized or cancelled order."))
        if kind not in ("service", "part"):
            raise ValidationError(_("Invalid line type."))
        model = "mizan.car.work.procedure.line" if kind == "service" else "mizan.car.spare.parts.lines"
        line = self.env[model].browse(int(line_id)).exists()
        if not line or line.header_id != self:
            raise ValidationError(_("Line does not belong to this work order."))
        line.unlink()
        return True
