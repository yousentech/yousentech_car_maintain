# -*- coding: utf-8 -*-
from odoo import models, api, _
from datetime import datetime

class mizan_car_work_procedure_master(models.Model):
    _inherit = 'mizan.car.work.procedure.master'

    @api.model
    def return_technical_id(self, emp_pin_code):
        if emp_pin_code:
            emp_id = self.env['hr.technical.assignments'].search(
                [('technical_emp_id.pin', '=', emp_pin_code), ('state', '=', 'current')])
            if len(emp_id) == 1:
                data = {
                    'technical_id': emp_id.id,
                    'technical_name': emp_id.technical_emp_id.name,
                    'image': emp_id.technical_emp_id.image_1920,
                    'emp_id': emp_id.technical_emp_id.id,
                }

                return data
            else:
                return False
        else:
            return False

    @api.model
    def return_car_data(self, technical_id):
        fixed_date = datetime(2025, 5, 31)

        wo_lines = self.env['mizan.car.work.procedure.line'].search([('technical_name', 'in', technical_id),
                                                                     ('state', '!=',
                                                                      'complete'),
                                                                     ('create_date', '>', fixed_date)])

        select = []
        for header in wo_lines.header_id:
            car_data = {'partner_id': header.partner_id.id,
                        'partner_name': header.partner_id.name,
                        'partner_mobile': header.partner_mobile,
                        'work_order_id': header.id,
                        'wo_date': header.create_date,
                        'car_type': header.car_type_id.name,
                        'car_type_id': header.car_type_id.id,
                        'car_panel_no': header.car_panel_no,
                        'branch_name': header.company_id.name,
                        }
            select.append(car_data)
        return select
