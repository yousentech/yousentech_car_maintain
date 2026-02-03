# -*- coding: utf-8 -*-
from odoo import models, fields, _
class sale_order(models.Model):
    _inherit = 'sale.order'

    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="رقم امر الفحص", readony=True,copy=False)
    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="رقم كرت الدخول", readony=True,copy=False)
    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل",copy=False)
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    partner_mobile = fields.Char(string="رقم الجوال")
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")
    vin_no = fields.Char(string="رقم الشاصي")
    car_type = fields.Char(string="نوع السيارة")
    is_guarantee = fields.Boolean(string="اضافة ضمان",default=False)


    def _prepare_invoice(self):
        invoice_vals = super(sale_order, self)._prepare_invoice()
        invoice_vals.update({'maint_wo_id': self.maint_wo_id.id or False})
        invoice_vals.update({'entry_card_id': self.entry_card_id.id or False})
        invoice_vals.update({'sale_order_id': self.id or False})
        invoice_vals.update({'car_panel_no': self.car_panel_no or False})
        invoice_vals.update({'partner_mobile': self.partner_mobile or False})
        invoice_vals.update({'pay_type': self.pay_type or False})
        invoice_vals.update({'vin_no': self.vin_no or False})
        invoice_vals.update({'car_type': self.car_type or False})
        invoice_vals.update({'is_guarantee': self.is_guarantee or False})

        return invoice_vals

    def action_confirm(self):
        sale_order_confirm = super(sale_order, self).action_confirm()
        return sale_order_confirm
    
    def action_cancel(self):
        for rec in self:
            if rec.maint_wo_id:
                rec.maint_wo_id.write({'sale_order_id': False})
                rec.maint_wo_id.write({'state': 'work_order_started'})
                rec.entry_card_id.write({'state': 'work_order_started'})
                rec.maint_wo_id.checkup_id.write({'state': 'work_order_started'})
                rec.maint_wo_id.write({'end_date':False})
                rec.write({'maint_wo_id': False})
 
        return super(sale_order, self).action_cancel()

    def unlink(self):
        for rec in self:
           if rec.maint_wo_id:
               rec.maint_wo_id.write({'sale_order_id': False})
               rec.maint_wo_id.write({'state': 'work_order_started'})
               rec.entry_card_id.write({'state': 'work_order_started'})
               rec.maint_wo_id.checkup_id.write({'state': 'work_order_started'})
               rec.maint_wo_id.write({'end_date': False})

        return super(sale_order, self).unlink()
    


class sale_order_line(models.Model):
     _inherit = 'sale.order.line'

     product_has_guarantee_flag = fields.Boolean(string="خاضع للضمان",default=False)

     def _prepare_invoice_line(self):
        res = super(sale_order_line, self)._prepare_invoice_line()
        res.update({'product_has_guarantee_flag': self.product_has_guarantee_flag or False})

        return res
