# -*- coding: utf-8 -*-
from odoo import models, fields, api, _,tools
from odoo.exceptions import ValidationError
from datetime import datetime

class xx_technical_assignments(models.Model):
    _name = 'hr.technical.assignments'
    _description = 'hr technical assignments'

    _rec_name = "technical_emp_id"

    technical_emp_id = fields.Many2one('hr.employee', required=True,string="الفني",domain=[('technical_emp','=',True)])
    assign_date = fields.Date(string="تاريخ الاسناد", required=True, default=fields.Date.today,copy=False)
    close_date = fields.Date(string="تاريخ الايقاف", copy=False,readonly=True)

    branch_id = fields.Many2one('custom.branches', string='الفرع المسند اليه', copy=False,required=True,)
    state = fields.Selection([('current','متوفر لدى الفرع'),('closed','ايقاف')],string="الحالة", default='current',readonly=True)


    @api.model
    def create(self, vals_list):
        print("vals_list", vals_list)
        technical_id = vals_list.get('technical_emp_id')
        assign_date = vals_list.get('assign_date')
        tech_assign = self.env['hr.technical.assignments'].search([('technical_emp_id','=',technical_id),('state','=', 'current')])
        for line in tech_assign:
            line.write({'close_date': assign_date,
                        'state': 'closed'})
        res = super(xx_technical_assignments, self).create(vals_list)

        return res

    def unlink(self):
        for rec in self:
            raise ValidationError(
                "تنبيه .. لا يمكن الحذف   ")
        return super(xx_technical_assignments, self).unlink()


class xx_supervisor_assignments(models.Model):
    _name = 'hr.supervisor.assignments'
    _description = 'hr supervisor assignments'

    _rec_name = "supervisor_emp_id"

    supervisor_emp_id = fields.Many2one('hr.employee', required=True,string="المشرف",domain=[('supervisor_emp','=',True)])
    assign_date = fields.Date(string="تاريخ الاسناد", required=True, default=fields.Date.today,copy=False)
    close_date = fields.Date(string="تاريخ الايقاف",  copy=False)

    branch_id = fields.Many2one('custom.branches', string='الفرع المسند اليه', copy=False,required=True,)
    state = fields.Selection([('current','متوفر لدى الفرع'),('closed','ايقاف')], string="الحالة", default='current',readonly=True)


    @api.model
    def create(self, vals_list):
        print("vals_list", vals_list)
        supervisor_id = vals_list.get('supervisor_emp_id')
        assign_date = vals_list.get('assign_date')
        supp_assign = self.env['hr.supervisor.assignments'].search([('supervisor_emp_id','=',supervisor_id),('state','=', 'current')])
        for line in supp_assign:
            line.write({'close_date': assign_date,
                        'state': 'closed'})
        res = super(xx_supervisor_assignments, self).create(vals_list)

        return res


    def unlink(self):
        for rec in self:
            raise ValidationError(
                "تنبيه .. لا يمكن الحذف   ")
        return super(xx_supervisor_assignments, self).unlink()



class xx_sales_man_assignments(models.Model):
    _name = 'mizan.salesman.assignments'
    _description = 'mizan salesman assignments'

    _rec_name = "salesman_id"

    salesman_id = fields.Many2one('mizan.sales.man', required=True,string="المندوب",domain=[('sale_man_type','=', 'internal')])
    assign_date = fields.Date(string="تاريخ الاسناد", required=True, default=fields.Date.today,copy=False)
    close_date = fields.Date(string="تاريخ الايقاف", copy=False,readonly=True)

    branch_id = fields.Many2one('custom.branches', string='الفرع المسند اليه', copy=False,required=True,)
    state = fields.Selection([('current','متوفر لدى الفرع'),('closed','ايقاف')],string="الحالة", default='current',readonly=True)


    @api.model
    def create(self, vals_list):
        print("vals_list", vals_list)
        salesman_id = vals_list.get('salesman_id')
        assign_date = vals_list.get('assign_date')
        salesman_assign = self.env['mizan.salesman.assignments'].search([('salesman_id','=',salesman_id),('state','=', 'current')])
        for line in salesman_assign:
            line.write({'close_date': assign_date,
                        'state': 'closed'})
        res = super(xx_sales_man_assignments, self).create(vals_list)

        return res

    def unlink(self):
        for rec in self:
            raise ValidationError(
                "تنبيه .. لا يمكن الحذف   ")
        return super(xx_sales_man_assignments, self).unlink()
