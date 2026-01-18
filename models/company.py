from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class company(models.Model):
    _inherit = 'res.company'
    
    task_start_date = fields.Date(string="تاريخ البدء لمهام التطبيق")
  
    