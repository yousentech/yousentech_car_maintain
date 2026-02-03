# -*- coding: utf-8 -*-
from odoo import models, fields, _

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    supervisor_emp = fields.Boolean(string="المشرف الفني")
    technical_emp = fields.Boolean(string="فني الصيانة")
    face_features_line_id = fields.One2many('emp.face.features','employee_id',copy=False ,ondelete='cascade')
    