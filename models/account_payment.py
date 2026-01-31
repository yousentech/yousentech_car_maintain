# -*- coding: utf-8 -*-
from odoo import models, fields, _
class account_payment(models.Model):
    _inherit = 'account.payment'

    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="رقم كرت الدخول",copy=False,readonly=True)
    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="امر الفحص", copy=False,readonly=True)
    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل", copy=False,readonly=True)


