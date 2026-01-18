# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class xx_register_payment(models.Model):
    _inherit = 'account.payment'

    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="رقم كرت الدخول",copy=False,readonly=True)
    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="امر الفحص", copy=False,readonly=True)
    work_order_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل", copy=False,readonly=True)

    #
    # @api.model
    # def create(self, vals):
    #     active_ids = self._context.get('active_ids', []) or []
    #     for record in self.env['wo.installation.order.mst'].browse(active_ids):
    #         if vals.get("installation_order_id"):
    #             print(vals.get("amount"))
    #             record.update({'advance_amount': vals.get("amount")})
    #     return super(xx_register_payment, self).create(vals)
