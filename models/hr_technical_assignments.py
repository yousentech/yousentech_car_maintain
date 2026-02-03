# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
class hr_technical_assignments(models.Model):
    _name = 'hr.technical.assignments'
    _description = 'hr technical assignments'
    _rec_name = "technical_emp_id"

    technical_emp_id = fields.Many2one('hr.employee', required=True,string="الفني",domain=[('technical_emp','=',True)])
    assign_date = fields.Date(string="تاريخ الاسناد", required=True, default=fields.Date.today,copy=False)
    close_date = fields.Date(string="تاريخ الايقاف", copy=False,readonly=True)
    company_id = fields.Many2one('res.company', string='الفرع المسند اليه', copy=False,required=True,)
    state = fields.Selection([('current','متوفر لدى الفرع'),('closed','ايقاف')],string="الحالة", default='current',readonly=True)


    @api.model
    def create(self, vals_list):
        technical_id = vals_list.get('technical_emp_id')
        assign_date = vals_list.get('assign_date')
        tech_assign = self.env['hr.technical.assignments'].search([('technical_emp_id','=',technical_id),('state','=', 'current')])
        for line in tech_assign:
            line.write({'close_date': assign_date,
                        'state': 'closed'})
        res = super(hr_technical_assignments, self).create(vals_list)
        return res

    def unlink(self):
        for rec in self:
            raise ValidationError(
                "تنبيه .. لا يمكن الحذف   ")
        return super(hr_technical_assignments, self).unlink()

