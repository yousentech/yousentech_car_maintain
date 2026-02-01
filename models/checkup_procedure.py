# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, time


class mizan_car_checkup_procedure_master(models.Model):
    _name = 'mizan.car.checkup.procedure.master'
    _description = 'Car checkup procedure master'


    _rec_name = 'id'
    partner_id = fields.Many2one('res.partner', string="العميل", required=True)
    create_date = fields.Date(string="بدء الفحص", required=True, default=fields.Datetime.now, copy=False)
    end_date = fields.Datetime(string="انتهاء الفحص", copy=False)

    state = fields.Selection([('draft', 'مرحلة الاعداد'), ('confirm', 'مرحلة التاكيد'),
                              ('execute_started', 'بدء الفحص'), ('work_order_started', 'امر العمل'),
                              ('execute_completed', 'اكتمال التنفيذ'), ('not_checkup_car', 'الخروج بدون فحص'),
                              ('return_to_modify', 'استعادة للتعديل'),
                              ('cancel_order', 'ملغي امر التركيب')

                              ], default='execute_started', readonly=True, related="entry_card_id.state",store=True, copy=False)

    car_panel_no = fields.Char(string="رقم لوحة السيارة")

    partner_mobile = fields.Char(string="رقم الجوال")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس",)
    car_model = fields.Char(string="الموديل")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة",)
    service_type_id = fields.Many2one('mizan.services.types', string="نوع الخدمة",)
    service_type_price = fields.Float(string="سعر الخدمة", )
    advance_amount = fields.Float(string="المبلغ المدفوع")

    
    drum_counter = fields.Char(string="عداد وقت الدخول")

    drum_counter_exit = fields.Char(string="عداد وقت الخروج")

    company_id = fields.Many2one('res.company',copy=False,
                               default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    ##
    services_price = fields.Float(string="الاجمالي", store=True,
                                  readonly=True)
    discount_type = fields.Selection([('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم",
                                     default='percentage')
    service_discount = fields.Float(string="الخصم")
    ##
    services_price_after_discount = fields.Float(string="الاجمالي بعد الخصم", store=True,
                                                 readonly=True)
    ##
    services_price_with_tax = fields.Float(string="الاجمالي شامل الضريبة", store=True,
                                           readonly=True)

    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل",copy=False)
    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="بيانات كرت الدخول",copy=False)

    result_lines = fields.One2many('mizan.car.checkup.procedure.line','header_id',ondelete='cascade',copy=False)
    lines_computer = fields.One2many('mizan.car.computer.codes.lines', 'header_id', required=True,
                                   ondelete='cascade', copy=False)
    create_invoice_manually_id = fields.Many2one('account.move',copy=False)

    discount_inv_posted = fields.Boolean(default=lambda self: self._default_discount_posted_flag(),
                                         compute="_get_discount_posted_flag")
    vin_no = fields.Char(string="رقم الشاصي")
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")

    use_pricelist = fields.Boolean(default=lambda self: self._default_pricelist_flag(),
                                         compute="_get_pricelist_flag")

    @api.model
    def _default_pricelist_flag(self):
         return self.user_has_groups('product.group_product_pricelist')

    def _get_pricelist_flag(self):
         self.use_pricelist = self.user_has_groups('product.group_product_pricelist')

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True,
        required=True, default=lambda self: self.env.uid)

    @api.model
    def _default_branch_id(self):
        for rec in self:
             return rec.entry_card_id.company_id.id

    @api.depends('entry_card_id')
    def _get_branch_id(self):
        for rec in self:
            if rec.entry_card_id:
                rec.company_id = rec.entry_card_id.company_id.id
            else:
                rec.company_id = False

    def _get_discount_posted_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_discount_posted = params.get_param('discount_posted',
                                             default=False)
 
        for rec in self:
            rec.discount_inv_posted = l_discount_posted

    def _default_discount_posted_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_discount_posted = params.get_param('discount_posted',
                                             default=False)
 
        return l_discount_posted

    service_price_include_tax_flag = fields.Boolean(default=lambda self: self._default_service_price_include_tax_flag(),
                                                    compute="_get_service_price_include_tax_flag")

    def _get_service_price_include_tax_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_service_price_include_tax = params.get_param('service_price_include_tax',
                                                       default=False)
 
        for rec in self:
            rec.service_price_include_tax_flag = l_service_price_include_tax

    def _default_service_price_include_tax_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_service_price_include_tax = params.get_param('service_price_include_tax', default=False)
 
        return l_service_price_include_tax

    is_user_technical = fields.Boolean(default=lambda self: self._default_user_technical(),compute="_user_technical_edit_mode")

    is_user_supervisor = fields.Boolean(default=lambda self: self._default_user_supervisor(),
                                             compute="_user_supervisor_edit_mode")
    is_user_sale_man = fields.Boolean(default=lambda self: self._default_user_sale_man(), compute="_user_sale_man_edit_mode")

    @api.model
    def _default_user_technical(self):
         return self.user_has_groups('yousentech_car_maintain.group_technician_priv')

    def _user_technical_edit_mode(self):
         self.is_user_technical = self.user_has_groups('yousentech_car_maintain.group_technician_priv')

    @api.model
    def _default_user_supervisor(self):
         return self.user_has_groups('yousentech_car_maintain.group_supervisor_priv')

    def _user_supervisor_edit_mode(self):
         self.is_user_supervisor = self.user_has_groups('yousentech_car_maintain.group_supervisor_priv')

    @api.model
    def _default_user_sale_man(self):
        return self.user_has_groups('yousentech_car_maintain.group_sales_man_priv')

    def _user_sale_man_edit_mode(self):
         self.is_user_sale_man = self.user_has_groups('yousentech_car_maintain.group_sales_man_priv')
    
    is_user_allow_delete = fields.Boolean(default=lambda self: self._default_user_allow_delete(), compute="_user_allow_delete")
  
    @api.model
    def _default_user_allow_delete(self):
        return self.user_has_groups('yousentech_car_maintain.group_allow_delete_wo_priv')

    def _user_allow_delete(self):
        self.is_user_allow_delete = self.user_has_groups('yousentech_car_maintain.group_allow_delete_wo_priv')


    @api.onchange('service_type_id')
    def get_service_price(self):
        for rec in self:
            if rec.service_type_id:
                rec.service_type_price = rec.service_type_id.price
            else:
                rec.service_type_price = 0

    def create_invoice_mannually(self):
        for rec in self:
            check_id = self.env['account.move'].search([('checkup_id', '=', rec.id),('company_id','=', rec.entry_card_id.company_id.id)])
            if check_id:
                raise ValidationError(
                    "لا يمكن انشاء فاتورة مبيعات مره اخرى لنفس امر الفحص")

            if not rec.service_type_id or not rec.service_type_price:
                 raise ValidationError(
                     "لا يمكن انشاء فاتورة مبيعات .. اما نوع الخدمة غير محدد او سعر الخمة غير محدد")


            inv_line_ids = []
            if rec.service_type_id:
                select = []
                discount_perc = 0
                if rec.service_discount:
                    if rec.service_discount and rec.discount_type == 'percentage':
                        discount_perc = rec.service_discount
                    elif rec.service_discount and rec.discount_type == 'amount':
                        discount_perc = ((rec.service_discount) / (rec.service_type_price)) * 100

                service_type_lines = {
                    'product_id': rec.service_type_id.product_id.id,
                    'name': rec.service_type_id.name,
                    'quantity': 1,
                    'product_uom_id': rec.service_type_id.product_id.uom_id.id,
                    'discount': discount_perc if not rec.discount_inv_posted else False,
                     'price_unit': rec.service_type_price,
                    'tax_ids': [(6, 0, rec.service_type_id.product_id.taxes_id.ids)],
                    'company_id': rec.entry_card_id.company_id.id,
                    'company_currency_id': rec.env.company.currency_id.id,

                        }
                inv_line_ids.append((0,0,service_type_lines))

            if rec.discount_inv_posted:
                discount_product_tmp = self.env['product.template'].search([('discount_product_flag', '=', True)],
                                                                           limit=1)
                discount_product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', discount_product_tmp.id)])

                if not discount_product:
                    raise ValidationError(
                        "تنبيه... نوع الخصم حسب الفاتورة يجب تهيئة الخصم من بطاقة الصنف")

                if discount_product and (rec.services_price - rec.services_price_after_discount):
                    discount_line = {
                        'product_id': discount_product.id,
                        'name': discount_product.name,
                        'quantity': -1,
                         'product_uom_id': discount_product.uom_id.id,
                        'discount': False,
                        'price_unit': rec.services_price - rec.services_price_after_discount,
                        'company_id': rec.entry_card_id.company_id.id,
                        'currency_id': self.env.company.currency_id.id,

                    }
                    inv_line_ids.append((0, 0, discount_line))

            if inv_line_ids:
                journal_id = self.env['account.journal'].search(
                    [('company_id', '=', self.env.user.company_id.id), ('type', '=', 'sale')], limit=1)
                journal_sale = ""
                if journal_id:
                    journal_sale = journal_id.id
                else:
                    journal_id = self.env['account.journal'].search(
                        [('type', '=', 'sale')], limit=1)

                    journal_sale = journal_id.id
                if not journal_sale:
                    raise ValidationError(
                        "تنبيه... لم يتم تهيئة دفتر المبيعات")

                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'journal_id': journal_sale,
                    'partner_id': rec.partner_id.id,
                    'commercial_partner_id': rec.partner_id.id,
                    'invoice_date': rec.entry_card_id.order_date,
                    'date': rec.entry_card_id.order_date,
                    'currency_id': self.env.company.currency_id.id,
                    'state': 'draft',
                    'invoice_user_id': rec.user_id.id,
                    'payment_state': 'not_paid',
                    'invoice_date_due': rec.entry_card_id.order_date,
                    'invoice_partner_display_name': rec.partner_id.name,
                    'company_id': rec.entry_card_id.company_id.id,
                    'checkup_id': rec.id,
                    'entry_card_id': rec.entry_card_id.id,
                    'car_panel_no': rec.car_panel_no,
                    'partner_mobile': rec.partner_mobile,
                    'pay_type': rec.pay_type,
                    'vin_no': rec.vin_no,
                    'car_type': rec.car_type_id.name,
                   
                    'company_id': rec.entry_card_id.company_id.id,
                    'invoice_line_ids': inv_line_ids,
                    })


                rec.write({'create_invoice_manually_id': invoice.id})
                action = self.env.ref('account.action_move_out_invoice_type')
                result = action.read()[0]
                result.pop('id', None)
                result['context'] = {}
                result['domain'] = [('id', '=', invoice.id)]
                if invoice:
                    res = self.env.ref('account.view_move_form', False)
                    result['views'] = [(res and res.id or False, 'form')]
                    result['res_id'] = invoice.id or False
                return result
            
    def call_invoice(self):
        for rec in self:
            invoice = self.env['account.move'].search([('checkup_id', '=', rec.id)])
            action = self.env.ref('account.action_move_out_invoice_type')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', '=', invoice.id)]

            if invoice:
                res = self.env.ref('account.view_move_form', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = invoice.id or False
            return result
  

    def get_price_of_product(self,product_id):
        for rec in self:
            if product_id:
                price = 0.00
                if rec.use_pricelist:
                    pricelist = self.env['product.pricelist'].search([('company_id', '=', rec.entry_card_id.company_id.id)])
                    for line in pricelist.item_ids:
                        if line.product_tmpl_id.id == product_id.product_tmpl_id.id:
                            price = line.fixed_price
                    if not price:
                        price = product_id.list_price

                else:
                    price = product_id.list_price

                return price
            else:
                return False

    def create_work_order_procedure(self):
        for rec in self:
            part_results = self.env['mizan.car.work.procedure.master'].search([('checkup_id', '=', rec.id)])
            if not part_results:
                pricelist = self.env['product.pricelist'].search([('company_id', '=', rec.entry_card_id.company_id.id)])
                results_tmp = {
                    'partner_id': rec.partner_id.id,
                    'state': 'work_order_started',
                    'car_panel_no': rec.car_panel_no,
                    'partner_mobile': rec.partner_mobile,
                    'car_size_id': rec.car_size_id.id,
                    'car_model': rec.car_model,
                    'car_type_id': rec.car_type_id.id,
                    'vin_no': rec.vin_no,
                    'checkup_id': rec.id,
                    'entry_card_id': rec.entry_card_id.id,
                    'company_id': rec.entry_card_id.company_id.id,
                    'pricelist_id': pricelist.id,

                }

                wo_procedure = self.env['mizan.car.work.procedure.master'].create(results_tmp)
                rec.write({'maint_wo_id': wo_procedure.id})
                rec.entry_card_id.write({'maint_wo_id':wo_procedure.id})
                rec.write({'state': 'work_order_started'})
                rec.entry_card_id.write({'state': 'work_order_started'})

                for line in rec.result_lines:
                    if line.selected:
                        for p in line.checkup_part_result_id:
                            if p.product_service_id:
                                products = self.env['mizan.car.work.procedure.line'].create({
                                    'product_id': p.product_service_id.id,
                                    'name': p.product_service_id.name,
                                     'unit_price': rec.get_price_of_product(p.product_service_id),
                                    'product_tax': p.product_service_id.taxes_id.id,
                                    'technical_name': line.technical_name.ids if line.technical_name else False,
                                    'header_id': wo_procedure.id,

                                })
                wo_procedure._cal_spare_parts_amounts()
                wo_procedure._cal_services_amounts()

                action = self.env.ref('yousentech_car_maintain.action_work_procedure_view')
                result = action.read()[0]
                result.pop('id', None)
                result['domain'] = [('checkup_id', '=', rec.id)]
                if wo_procedure:
                    res = self.env.ref('yousentech_car_maintain.work_procedure_form_view', False)
                    result['views'] = [(res and res.id or False, 'form')]
                    result['res_id'] = wo_procedure.id or False

                return result

    def call_wo_procedure(self):
        for rec in self:
            wo_procedure = self.env['mizan.car.work.procedure.master'].search([('checkup_id', '=', rec.id)])
            action = self.env.ref('yousentech_car_maintain.action_work_procedure_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('checkup_id', '=', rec.id)]
            if wo_procedure:
                res = self.env.ref('yousentech_car_maintain.work_procedure_form_view', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = wo_procedure.id or False

            return result

    def unlink(self):
        for rec in self:
            if rec.maint_wo_id:
                 raise ValidationError(
                    "تنبيه .. لا يمكن الحذف بسبب تم انشاء امر عمل (%s) " % rec.maint_wo_id.id)
            if rec.create_invoice_manually_id:
                raise ValidationError(
                    "تنبيه .. لا يمكن الحذف بسبب تم انشاء فاتورة مبيعات (%s) " % rec.create_invoice_manually_id.name)

            
            if not rec.is_user_allow_delete:
                 raise ValidationError(
                    " تنبيه .. لا يمكن الحذف .. المستخدم لاتوجد له صلاحية  ")
            rec.entry_card_id.write({'state': 'confirm'})
            rec.entry_card_id.write({'checkup_id': False})
            rec.maint_wo_id.write({'checkup_id': False})

        return super(mizan_car_checkup_procedure_master, self).unlink()

    def action_register_payment(self):
        for rec in self:
            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.entry_card_id.id),('checkup_id','=', rec.id)])

            action = self.env.ref('yousentech_car_maintain.action_mizan_payment_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', 'in', payment.ids)]
            return result

    def register_payment(self):
        advanced_amount = 0
        remaining_amount = 0
        for rec in self:
            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.entry_card_id.id),('checkup_id','=', rec.id)])
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount
            if advanced_amount >= rec.service_type_price:
                raise ValidationError(
                    "اكتمل الدفع لامر الفحص .. لا يمكن انشاء مفوعات جديدة ")

            remaining_amount = rec.service_type_price - advanced_amount
            return {

                'name': _('Register Payment'),
                'view_mode': 'form',
                'res_model': 'mizan.register.payment',
                'view_id': self.env.ref('yousentech_car_maintain.mizan_payment_view').id,
                'type': 'ir.actions.act_window',
                'context': {'default_invoice_amount': rec.service_type_price,
                            'default_advanced_amount': advanced_amount,
                            'default_remaining_amount': remaining_amount, 'default_company_id': rec.entry_card_id.company_id.id,
                            'default_payment_note': "دفعة مقدمة لامر الفحص",

                            'default_header_id': rec.entry_card_id.id, 'default_checkup_id': rec.id, 'default_payment_amount': remaining_amount,
                            },
                'target': 'current'
            }

class mizan_car_checkup_procedure_line(models.Model):
    _name = 'mizan.car.checkup.procedure.line'

    _description = 'Car checkup order Sub Lines line add'
    
    selected = fields.Boolean(string="اختيار", default=True)

    company_id = fields.Many2one( copy=False,
                                default=lambda self: self._default_branch_id(),compute="_get_branch_id")

    sequence = fields.Integer(string="التسلسل", default=12)
    checkup_part_id = fields.Many2one('product.product', string="نوع /كود الفحص", copy=False,required=True,domain=[('is_checkup_product','=',True)])
    name = fields.Char(string="وصف الفحص" , copy=False,required=True)
    technical_name = fields.Many2many('hr.technical.assignments',string="اسم الفني",domain="[('company_id','=', company_id),('state','=', 'current')]")
    product_tmpl_id = fields.Many2many('product.template',compute="_get_product_tmpl_id",)

    @api.depends('checkup_part_id')
    def _get_product_tmpl_id(self):
        for rec in self:
            if rec.checkup_part_id:
                rec.product_tmpl_id =  [(6, 0, rec.checkup_part_id.product_tmpl_id.id)]
            else:
                rec.product_tmpl_id = [(5, 0, 0)]
    
    checkup_part_result_id = fields.Many2many('mizan.default.results', string="نتيجة الفحص",
                                              copy=False, domain="[('product_id','=',product_tmpl_id)]")

    notes = fields.Char(string="الملاحظات")
    header_id = fields.Many2one('mizan.car.checkup.procedure.master',ondelete='cascade')


    _sql_constraints = [
        ('checkup_part_id_uniq', 'unique(checkup_part_id,header_id)',
         ' مكرر لا يمكن الاستمرار'),]

    @api.model
    def _default_branch_id(self):
        for rec in self:
             return rec.header_id.entry_card_id.company_id.id

    @api.depends('header_id')
    def _get_branch_id(self):
        for rec in self:
            if rec.header_id:
 
                rec.company_id = rec.header_id.entry_card_id.company_id.id
            else:
                rec.company_id = False

    # @api.model
    # def _default_product_tmpl_id(self):
    #     for rec in self:
    #          return rec.checkup_part_id.product_tmpl_id.id

    # @api.depends('checkup_part_id')
    # def _get_product_tmpl_id(self):
    #     for rec in self:
    #         if rec.checkup_part_id:
 
    #             rec.product_tmpl_id = rec.checkup_part_id.product_tmpl_id.ids
    #         else:
    #             rec.product_tmpl_id = False

    @api.onchange('checkup_part_id')
    def get_default_results(self):
        for rec in self:
            if rec.checkup_part_id:
                rec.write({'name':  rec.checkup_part_id.name})

                for l in rec.checkup_part_id.results_lines:
                    if l.default_result:
                        rec.write({'checkup_part_result_id':  [(4, l.id)]})

            else:
                rec.write({'checkup_part_result_id': False})



