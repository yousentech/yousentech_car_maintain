from odoo import fields, models


class WorkshopEmployee(models.Model):
    _inherit = 'hr.employee'

    is_workshop_technician = fields.Boolean(
        string='فني ورشة',
        help='يظهر الموظف ضمن قائمة فنيي فحص السيارات.',
    )
