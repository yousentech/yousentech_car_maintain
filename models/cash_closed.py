# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class cash_close_closed(models.Model):
    _name = 'cash.close.closed'
    _inherit = ['mail.thread']

    _rec_name = 'id'
    seq = fields.Integer(
        string='رقم العملية',
        copy=False,
        readonly=True,
        default=lambda self: self._get_sequence(),)

    def _get_sequence(self):
        branch_id = self.env.user.company_id.id
        if branch_id:
            sql_query = "select max(COALESCE(seq,0)) as seq from cash_close_closed where company_id=%s" % (
                branch_id)

            self.env.cr.execute(sql_query)
            seq = self.env.cr.fetchone()
            x = seq[0]
            if x:
                x = x + 1
                return (x)
            else:
                x = 1
                return (x)

    order_date = fields.Date(
        string="تاريخ الاقفال", required=True, default=fields.Date.today, copy=False)

    branch_cash_journal_id = fields.Many2one('account.journal', required=True, string="صندوق النقدية للفرع", domain="[('type','=', 'cash'),('company_id','=', company_id)]",
                                             default=lambda self: self._default_cash_close())
    main_cash_journal_id = fields.Many2one('account.journal', required=True, string="صندوق النقدية المركز الرئيسي",
                                           domain=[('type', '=', 'cash'), ('use_main_cash_close', '=', True)], default=lambda self: self._default_main_cash_close())
    description = fields.Char(string="الوصف")
    closed_flag = fields.Boolean(string="تم الاقفال")
    matched_flag = fields.Boolean(string="تم المطابقة")

    matched_amount = fields.Float(
        string="مبلغ المطابقة", required=True, copy=False)
    remaining_matched_amount = fields.Float(
        string="فرق المطابقة", copy=False, compute="calc_remaining_matched", store=True)
    amount = fields.Float(string="المبلغ", required=True, copy=False)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, readonly=True, string="الشركة")
    account_move_id = fields.Many2one('account.move', copy=False)

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True, copy=False,
        required=True, default=lambda self: self.env.uid)

    def _default_cash_close(self):
        journal_id = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', self.company_id.id)],
                                                        limit=1)
        return journal_id

    def _default_main_cash_close(self):
        journal_id = self.env['account.journal'].search([('type', '=', 'cash'), ('use_main_cash_close', '=', True)],
                                                        limit=1)
        return journal_id

    def matching_cah_btn(self):
        for rec in self:
            rec.write({'matched_flag': True})

    def write(self, vals):
        if not self.user_has_groups('yousentech_car_maintain.group_allow_matched_cash_priv'):
            raise ValidationError(
                "تنبيه .. لا توجد لديك صلاحية التعديل.. تواصل مع مدير النظام ")
        res = super(cash_close_closed, self).write(vals)
        return res

    ##
    def closed_cash(self):
        for rec in self:
            if (rec.amount - rec.matched_amount) != 0:
                raise ValidationError(
                    "تنبيه .. لا يمكن انشاء القيد بسبب عدم المطابقة ")

            if rec.branch_cash_journal_id and rec.main_cash_journal_id and rec.amount:
                line_ids = []
                if not rec.account_move_id:
                    credit_vals = (0, 0, {
                        'name': rec.description,
                        'amount_currency': 0.0,

                        'company_currency_id': rec.company_id.currency_id.id,
                        'debit': 0.0,
                        'credit': rec.amount,
                        'date': rec.order_date,
                        'date_maturity': rec.order_date,
                        ##
                        # 'account_id': rec.branch_cash_journal_id.default_credit_account_id.id,
                        # 'account_internal_type': rec.branch_cash_journal_id.default_credit_account_id.internal_type,
                        'account_id': rec.branch_cash_journal_id.default_account_id.id,
                        # 'account_internal_type':rec.branch_cash_journal_id.default_credit_account_id.internal_type,
                        'ref': 'اقفال صندوق الفرع : ' + str(rec.company_id.name),
                        'journal_id': rec.main_cash_journal_id.id,
                        'company_id': rec.company_id.id,
                        'quantity': 1,

                    })
                    line_ids.append(credit_vals)
                    debit_vals = (0, 0, {
                        'name': rec.description,
                        'amount_currency': 0.0,
                        'company_currency_id': rec.company_id.currency_id.id,
                        'debit': rec.amount,
                        'credit': 0.0,
                        'date': rec.order_date,
                        'date_maturity': rec.order_date,
                        ##
                        # 'account_id': rec.main_cash_journal_id.default_debit_account_id.id,
                        # 'account_internal_type': rec.main_cash_journal_id.default_debit_account_id.internal_type,
                        'account_id': rec.main_cash_journal_id.default_account_id.id,
                        # 'account_internal_type': rec.main_cash_journal_id.default_debit_account_id.internal_type,
                        'ref': 'اقفال صندوق الفرع : ' + str(rec.company_id.name),
                        'journal_id': rec.main_cash_journal_id.id,
                        'company_id': rec.company_id.id,
                        'quantity': 1,

                    })

                    line_ids.append(debit_vals, )
                if line_ids:
                    ref = 'اقفال صندوق الفرع : ' + str(rec.company_id.name),
                    mov_vals = {
                        'date': rec.order_date,
                        'ref': ref,
                        'type': 'entry',
                        'journal_id': rec.main_cash_journal_id.id,
                        'company_id': rec.company_id.id,
                        'currency_id': rec.company_id.currency_id.id,
                        'cash_close_id': rec.id,
                        'invoice_user_id': self.env.uid,
                        'line_ids': line_ids,
                    }

                    entry_moves = self.env['account.move'].create(mov_vals)
                    rec.write({'account_move_id': entry_moves.id})
                    rec.write({'closed_flag': True})

                else:
                    raise ValidationError(
                        "تنبيه .. تم اقفال الصندوق مسبقا   ")
            else:

                raise ValidationError(
                    "تنبيه .. لا يمكن الاستمرار توجد بينات غير مكتملة ")

    def un_closed_cash(self):
        for rec in self:
            if rec.account_move_id:
                rec.account_move_id.unlink()

    @api.depends('matched_amount', 'amount')
    def calc_remaining_matched(self):
        for rec in self:
            rec.remaining_matched_amount = rec.amount - rec.matched_amount

    def call_entry(self):
        for rec in self:
            action = self.env.ref('account.action_move_journal_line')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('cash_close_id', '=', rec.id), ('move_type', '=', 'entry')
                                ]
            return result
