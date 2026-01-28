from odoo import models, fields, _
class res_company(models.Model):
    _inherit = 'res.company'
    
    task_start_date = fields.Date(string="تاريخ البدء لمهام التطبيق")
  
    