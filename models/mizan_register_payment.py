
# -*- coding: utf-8 -*-
from odoo import models, fields,api, _
from odoo.exceptions import ValidationError

class mizan_register_payment(models.Model):
    _name = 'mizan.register.payment'
    _description = 'Register Payment in Mizan Car order'

    _rec_name = "id"

    def get_journal_id(self):
        return [('type', '=', ['cash', 'bank'])]

    pay_date = fields.Date(string="تاريخ الدفع", default=fields.Date.today)
    user_id = fields.Many2one(
        'res.users', string='User name', readonly=True,
        required=True, default=lambda self: self.env.uid)
    
    state = fields.Selection([('draft','مسودة'),('posted','مرحل'),("cancel", "ملغي")])
    invoice_amount = fields.Float(string="مبلغ الفاتورة",readonly=True)
    advanced_amount = fields.Float(string="المبلغ المقدم",readonly=True)
    remaining_amount = fields.Float(string="المبلغ المتبقي",readonly=True)
    payment_amount = fields.Float(string="المبلغ المدفوع", reqiured=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,)

    payment_note = fields.Char(string="البيان")
    header_id = fields.Many2one('mizan.car.entry.card.master',string="رقم كرت الدخول", copy=False)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain=get_journal_id)

    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="الفحص", copy=False)
    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل", copy=False)
    payment_id = fields.Many2one('account.payment', )


    def create_payment(self):
        for rec in self:
            if rec.checkup_id:
                rec.create_payment_checkup()
            elif rec.maint_wo_id:
                rec.create_payment_wo()


    payment_method_line_id = fields.Many2one("account.payment.method.line")
  
    @api.depends("journal_id")
    def _compute_payment_method_line_id(self):
        for wizard in self:
            if wizard.journal_id:
                payment_type = "inbound"
                available_payment_method_lines = (
                    wizard.journal_id._get_available_payment_method_lines(payment_type)
                )
            else:
                available_payment_method_lines = False

            # Select the first available one by default.
            if available_payment_method_lines:
                wizard.payment_method_line_id = available_payment_method_lines[
                    0
                ]._origin
            else:
                wizard.payment_method_line_id = False
                
    def create_payment_checkup(self):
        for rec in self:
            if rec.payment_amount <= 0:
                raise ValidationError(
                    "يجب تحديد المبلغ اولا")

            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.id),('checkup_id','=', rec.header_id.checkup_id.id),('state', '!=', 'cancel')])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            account_payment = self.env['account.payment'].search([('maint_wo_id', '=', rec.header_id.checkup_id.id),('state', '!=', 'cancel')])
            amount_total = rec.header_id.checkup_id.service_type_price


            ready_amount = 0
            for line in account_payment:
                ready_amount = ready_amount + line.amount
              
            if ready_amount >= amount_total:
                raise ValidationError(
                    "اكتمل الدفع  في شاشة مدفوعات الفوترة لامر العمل المحدد .. لا يمكن انشاء مفوعات جديدة ")
          
           
            if advanced_amount >= amount_total:
                raise ValidationError(
                      "اكتمل الدفع لامر الفحص .. لا يمكن انشاء مفوعات جديدة ")

            if rec.payment_amount > rec.remaining_amount:
                    raise ValidationError(
                        "المبلغ المدفوع اكبر من المبلغ المتبقي.. لا يمكن انشاء مفوعات جديدة ")
            ################################################### :
            # inbound_payment_method = self.env['account.payment.method'].create({
            #     'name': 'inbound',
            #     'code': 'IN',
            #     'payment_type': 'inbound',
            # })
            # payment = self.env['account.payment'].create({
            #     'date': self.pay_date,
            #     'payment_method_id': inbound_payment_method.id,
            #     'payment_type': 'inbound',
            #     'partner_type': 'customer',
            #     'partner_id': self.header_id.partner_id.id,
            #     'amount': self.payment_amount,
            #     'journal_id': self.journal_id.id,
            #     'company_id': self.header_id.company_id.id,
            #     'company_id': self.header_id.company_id.id,
            #     'currency_id': self.env.company.currency_id.id,
            #     # 'payment_difference_handling': 'reconcile',
            #     'ref': self.payment_note,
            #     'entry_card_id': self.header_id.id,
            #     'checkup_id': self.header_id.checkup_id.id,
            #       })
            # payment.action_post()
            ############################################################# :
            # payment_method_line_id = fields.Many2one("account.payment.method.line")
            
            payment = self.env['account.payment'].create({
                "amount":  self.payment_amount,
                "ref": self.payment_note,
                "date": self.pay_date,
                "journal_id":  self.journal_id.id,
                "payment_method_line_id": self.payment_method_line_id.id,
                "state": "draft",
                "payment_type": "inbound",
                "partner_type": "customer", 
                "partner_id": self.header_id.partner_id.id,
                "currency_id": self.env.company.currency_id.id,
                'entry_card_id': self.header_id.id,
                'checkup_id': self.header_id.checkup_id.id,
                'company_id': self.header_id.company_id.id,
               
                  })
            payment.action_post()
            self.write({'payment_id': payment.id})
            ################################################################################
            self.write({'state': 'posted'})

            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.id),('checkup_id','=', rec.header_id.checkup_id.id)])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount
 
            wo = self.env['mizan.car.checkup.procedure.master'].search([('id', '=', rec.header_id.checkup_id.id)])

            wo.write({'advance_amount': advanced_amount})



    def create_payment_wo(self):
        for rec in self:
            if rec.payment_amount <= 0:
                raise ValidationError(
                    "يجب تحديد المبلغ اولا")

            payment = self.env['mizan.register.payment'].search(
                [('header_id', '=', rec.header_id.id), ('maint_wo_id', '=', rec.header_id.maint_wo_id.id)])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            # if advanced_amount > rec.header_id.maint_wo_id.total_all_with_tax:
            #     raise ValidationError(
            #         "اكتمل الدفع لامر العمل .. لا يمكن انشاء مفوعات جديدة ")
            #
            # if rec.payment_amount > rec.remaining_amount:
            #         raise ValidationError(
            #             "المبلغ المدفوع اكبر من المبلغ المتبقي.. لا يمكن انشاء مفوعات جديدة ")
            ###########################################################################
            # self.inbound_payment_method = self.env['account.payment.method'].create({
            #     'name': 'inbound',
            #     'code': 'IN',
            #     'payment_type': 'inbound',
            # })
            # payment = self.env['account.payment'].create({
            #     'date': self.pay_date,
            #     'payment_method_id': self.inbound_payment_method.id,
            #     'payment_type': 'inbound',
            #     'partner_type': 'customer',
            #     'partner_id': self.header_id.partner_id.id,
            #     'amount': self.payment_amount,
            #     'journal_id': self.journal_id.id,
            #     'company_id': self.header_id.company_id.id,
            #     # 'branch_id': self.header_id.branch_id.id,
            #     'currency_id': self.env.company.currency_id.id,
            #     ##
            #     # 'payment_difference_handling': 'reconcile',
            #     'ref': self.payment_note,
            #     'entry_card_id': self.header_id.id,
            #     'work_order_id': self.header_id.work_order_id.id,
            #       })
            # payment.action_post()
            # :
            # payment_method = self.env['account.payment.method'].search([
            #     ('code', '=', 'IN'),
            #     ('payment_type', '=', 'inbound')
            # ], limit=1)

            # if not payment_method:
            #     payment_method = self.env['account.payment.method'].create({
            #         'name': 'Manual Inbound',
            #         'code': 'IN',
            #         'payment_type': 'inbound',
            #     })

            # payment_method_line = self.journal_id.inbound_payment_method_line_ids.filtered(
            #     lambda line: line.payment_method_id == payment_method
            # )

            # if not payment_method_line:
            #     payment_method_line = self.env['account.payment.method.line'].create({
            #         'name': payment_method.name,
            #         'payment_method_id': payment_method.id,
            #         'journal_id': self.journal_id.id,
            #     })
            # else:
            #     payment_method_line = payment_method_line[0]

            payment = self.env['account.payment'].create({
                'date': self.pay_date,
                'payment_method_line_id': self.payment_method_line_id.id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.header_id.partner_id.id,
                'amount': self.payment_amount,
                'journal_id': self.journal_id.id,
                'company_id': self.header_id.company_id.id,
                'currency_id': self.env.company.currency_id.id,
                'ref': self.payment_note,
                'entry_card_id': self.header_id.id,
                'maint_wo_id': self.header_id.maint_wo_id.id,
            })

            payment.action_post()
            ###############################################
            self.write({'state': 'posted'})

            payment = self.env['mizan.register.payment'].search(
                [('header_id', '=', rec.header_id.id), ('maint_wo_id', '=', rec.header_id.maint_wo_id.id)])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            wo = self.env['mizan.car.work.procedure.master'].search(
                [('id', '=', rec.header_id.maint_wo_id.id)])

            wo.write({'advance_amount': advanced_amount})
    
    
    def cancel_checkup_payment_btn(self):
        for rec in self:
            if not self.user_has_groups('yousentech_car_maintain.group_cancel_register_payment'):
              raise ValidationError(
                    "لا توجد لديك صلاحية الغاء المدفوعات")
            else:
                rec.write({'state': 'cancel'})
                if self.payment_id:
                    self.payment_id.action_draft()
                    self.payment_id.cancel()

                payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.checkup_id.id),('state', '!=', 'cancel')])
            
                advanced_amount = 0
                for line in payment:
                    advanced_amount = advanced_amount + line.payment_amount

                wo = self.env['mizan.car.work.procedure.master'].search([('id', '=', rec.header_id.checkup_id.id)])

                wo.write({'advance_amount': advanced_amount})
    
    def cancel_payment_btn(self):
        for rec in self:
            if not self.user_has_groups('yousentech_car_maintain.group_cancel_register_payment'):
              raise ValidationError(
                    "لا توجد لديك صلاحية الغاء المدفوعات")
            else:
                rec.write({'state': 'cancel'})
                if self.payment_id:
                    self.payment_id.action_draft()
                    self.payment_id.cancel()

                payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.maint_wo_id.id),('state', '!=', 'cancel')])
            
                advanced_amount = 0
                for line in payment:
                    advanced_amount = advanced_amount + line.payment_amount

                wo = self.env['mizan.car.work.procedure.master'].search([('id', '=', rec.header_id.maint_wo_id.id)])

                wo.write({'advance_amount': advanced_amount})