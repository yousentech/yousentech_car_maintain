from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class haraj_report(models.TransientModel):
    _name = 'mizan.message.confirm'

    desc = fields.Char(string="تنبيه / ", readonly=True)

    def confirm(self):
        model = self._context.get('active_model')
     
        records = self.env[model].search([('id','=', self._context.get('active_id'))])
     
        if records:
            records.sale_order()

