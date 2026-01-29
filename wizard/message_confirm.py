from odoo import models, fields, _

class mizan_message_confirm(models.TransientModel):
    _name = 'mizan.message.confirm'

    desc = fields.Char(string="تنبيه / ", readonly=True)

    def confirm(self):
        model = self._context.get('active_model')
     
        records = self.env[model].search([('id','=', self._context.get('active_id'))])
     
        if records:
            records.sale_order()

