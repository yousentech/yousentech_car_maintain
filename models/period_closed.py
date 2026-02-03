# -*- coding: utf-8 -*-
from odoo import models, fields, _

class wo_period_closed(models.Model):
    _name = 'wo.period.closed'
    _rec_name = 'id'

    inv_closed_from_date = fields.Date(required=True,string="ايقاف العمليات المخزنية من")
    inv_closed_to_date = fields.Date(required=True,string="الى تاريخ")