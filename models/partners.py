from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class partner_swilim(models.Model):
    _inherit = 'res.partner'
    
    default_customer = fields.Boolean(string="العميل الافتراضي في نظام الصيانة")
