from odoo import models, fields, _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    default_customer = fields.Boolean(string="العميل الافتراضي في نظام الصيانة")
