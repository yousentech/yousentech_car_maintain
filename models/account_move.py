# -*- coding: utf-8 -*-
from odoo import models, fields,api, _
from odoo.exceptions import ValidationError

class account_move(models.Model):
    _inherit = 'account.move'

    collecting_products_report_flag = fields.Boolean(default=lambda self: self._default_collecting_products_flag(),
                                                     compute="_get_collecting_products_flag")

    def _get_collecting_products_flag(self):

        params = self.env['ir.config_parameter'].sudo()
        l_collecting_products = params.get_param('collecting_products',
                                                 default=False)

        for rec in self:
            rec.collecting_products_report_flag = l_collecting_products

    def _default_collecting_products_flag(self):

        params = self.env['ir.config_parameter'].sudo()
        l_collecting_products = params.get_param('collecting_products',
                                                 default=False)

        return l_collecting_products

    def get_payment_amt_of_invoice(self, pay_type):
        sql_query = ""

        if not pay_type or pay_type not in ('bank', 'cash'):
            raise ValidationError(
                "تنبيه .. يجب تمرير طريقه الدفع للفنكشن [cash, bank]   ")

        if self.move_type == 'out_invoice':
            if pay_type == 'cash':
                sql_query = """
                                select COALESCE(sum(r.amount),0):: numeric  as amount from  account_partial_reconcile r, account_move_line rl
                                ,account_move am,account_move_line l,
                                account_journal j
                                where r.credit_move_id=rl.id and rl.journal_id=j.id and j.move_type='cash' and r.debit_move_id=l.id
                                and l.move_id=am.id
                                 and am.id ={}
                            """.format(self.id)
            if pay_type == 'bank':
                sql_query = """
                                   select COALESCE(sum(r.amount),0):: numeric  as amount from  account_partial_reconcile r, account_move_line rl
                                   ,account_move am,account_move_line l,
                                   account_journal j
                                   where r.credit_move_id=rl.id and rl.journal_id=j.id and j.move_type='bank' and r.debit_move_id=l.id
                                   and l.move_id=am.id
                                    and am.id ={}
                               """.format(self.id)

        if self.move_type == 'out_refund':
            if pay_type == 'cash':
                sql_query = """
                                select COALESCE(sum(r.amount) * -1,0):: numeric   as amount from  account_partial_reconcile r, account_move_line rl
                                ,account_move am,account_move_line l,
                                account_journal j
                                where r.credit_move_id=rl.id and rl.journal_id=j.id and j.move_type='cash' and r.debit_move_id=l.id
                                and l.move_id=am.id
                                 and am.id ={}
                            """.format(self.id)
            if pay_type == 'bank':
                sql_query = """
                                   select  COALESCE(sum(r.amount) * -1,0):: numeric  as amount from  account_partial_reconcile r, account_move_line rl
                                   ,account_move am,account_move_line l,
                                   account_journal j
                                   where r.credit_move_id=rl.id and rl.journal_id=j.id and j.move_type='bank' and r.debit_move_id=l.id
                                   and l.move_id=am.id
                                    and am.id ={}
                               """.format(self.id)

        if sql_query:
            self.env.cr.execute(sql_query)
            res = self.env.cr.fetchone()
            amount = res[0]

            if res:
                return amount
        else:
            return 0


    cash_close_id = fields.Many2one('cash.close.closed', copy=False,string="رقم اقفال الصندوق")

    def unlink(self):
        for rec in self:
            if rec.move_type== 'entry':
                if rec.cash_close_id:
                    rec.cash_close_id.write({'account_move_id': False})
                    rec.cash_close_id.write({'closed_flag': False})
                    rec.cash_close_id.write({'matched_amount': False})
                    rec.cash_close_id.write({'matched_flag': False})
                    rec.write({'cash_close_id': False})
           
            if rec.checkup_id:
               rec.checkup_id.write({'create_invoice_manually_id': False})
                  
        return super(account_move, self).unlink()
    
    
    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="رقم امر الفحص",readony=True,copy=False)
    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل",copy=False)
    sale_order_id = fields.Many2one('sale.order', string="امر البيع",copy=False)
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    partner_mobile = fields.Char(string="رقم الجوال")
    vin_no = fields.Char(string="رقم الشاصي")
    car_type = fields.Char(string="نوع السيارة")
    sale_man_id = fields.Many2one('mizan.salesman.assignments', string="المندوب",copy=False,domain="[('company_id','=', company_id),('state','=', 'current')]")
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")
    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="رقم كرت الدخول", readony=True,copy=False)
    is_guarantee = fields.Boolean(string="اضافة ضمان",default=False)



    @api.model
    def create(self, vals_list):
        invoice = super(account_move, self).create(vals_list)
        if vals_list.get('maint_wo_id'):
            wo_move = self.env['mizan.car.work.procedure.master'].search([('id', '=', vals_list.get('maint_wo_id'))])
            if wo_move:
                wo_move.write({'create_invoice_manually_id': invoice.id})

        return invoice

class account_move_line(models.Model):
    _inherit = 'account.move.line'

    product_has_guarantee_flag = fields.Boolean(string="خاضع للضمان",default=False)

