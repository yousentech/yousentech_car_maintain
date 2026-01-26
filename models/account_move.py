# -*- coding: utf-8 -*-
from odoo import models, fields, api, _,tools
from odoo.exceptions import ValidationError
from datetime import datetime

class xx_account_move(models.Model):
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

    def get_payment_amt_of_invoice(self,pay_type):
            sql_query= ""

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
                res =  self.env.cr.fetchone()
                amount = res[0]

                if res:
                    return amount
            else:
                return 0