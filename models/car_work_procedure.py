# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
from datetime import datetime


class mizan_car_work_procedure_master(models.Model):
    _name = 'mizan.car.work.procedure.master'
    _description = 'Car work procedure master'
    _rec_name = 'id'

    partner_id = fields.Many2one('res.partner', string="العميل", required=True)
    state = fields.Selection([('draft', 'مرحلة الاعداد'), ('confirm', 'مرحلة التاكيد'),
                              ('execute_started',
                               'بدء الفحص'), ('work_order_started', 'امر العمل'),
                              ('execute_completed',
                               'اكتمال التنفيذ'), ('not_checkup_car', 'الخروج بدون فحص'),
                              ('return_to_modify', 'استعادة للتعديل'),
                              ('cancel_order', 'ملغي امر التركيب')
                              ], default='work_order_started', related="entry_card_id.state", readonly=True, store=True, copy=False)

    create_date = fields.Datetime(
        string="بدء الفحص", required=True, default=fields.Datetime.now, copy=False)
    end_date = fields.Datetime(string="انتهاء العمل",  copy=False)
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    execute_done = fields.Boolean()
    partner_mobile = fields.Char(string="رقم الجوال")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس")
    car_model = fields.Char(string="الموديل")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة", )
    sale_order_id = fields.Many2one(
        'sale.order', string="رقم امر البيع", readony=True, copy=False)
    create_invoice_manually_id = fields.Many2one(
        'account.move', copy=False, readony=True)
    pay_type = fields.Selection(
        [('cash', 'نقدا'), ('bank', 'بنكي'), ('transfer', 'تحويل')], string="طريقة الدفع")
    checkup_id = fields.Many2one(
        'mizan.car.checkup.procedure.master', string="الفحص", copy=False)
    entry_card_id = fields.Many2one(
        'mizan.car.entry.card.master', string="بيانات كرت الدخول", copy=False)
    vin_no = fields.Char(string="رقم الشاصي")

    result_lines = fields.One2many(
        'mizan.car.work.procedure.line', 'header_id', ondelete='cascade', copy=False)
    lines_spare_parts = fields.One2many(
        'mizan.car.spare.parts.lines', 'header_id', ondelete='cascade', copy=False)
    discount_inv_posted = fields.Boolean(default=lambda self: self._default_discount_posted_flag(),
                                         compute="_get_discount_posted_flag")
    add_user_spare_parts_flag = fields.Boolean(default=lambda self: self._default_add_spare_parts_flag(),
                                               compute="_get_add_spare_parts_flag")

    company_id = fields.Many2one('res.company', string='الفرع', copy=False, required=True,related="entry_card_id.company_id",store=True)
    no_spare_parts_flag = fields.Boolean(
        string="امر البيع لا يحتاج قطع مستبدلة")
    is_guarantee = fields.Boolean(string="اضافة ضمان", default=True)
    additional_services = fields.Selection([('change_of_guarantee', 'التغيير على الضمان'), (
        'internal_branches_services', 'خدمات داخلية بين الفروع')], string="خدمات اضافية",)

    services_amt_after_tax = fields.Float(
        string="الاجمالي بعد الضريبة", stote=True)
    services_amt_before_tax = fields.Float(
        string="الاجمالي قبل الضريبة", stote=True)
    services_amt_tax = fields.Float(string="اجمالي الضريبة", stote=True)
    services_discount = fields.Float(string="اجمالي الخصم", stote=True)

    spare_parts_amt_after_tax = fields.Float(
        string="الاجمالي بعد الضريبة", stote=True)
    spare_parts_amt_before_tax = fields.Float(
        string="الاجمالي قبل الضريبة", stote=True)
    spare_parts_amt_tax = fields.Float(string="اجمالي الضريبة", stote=True)
    spare_parts_discount = fields.Float(string="اجمالي الخصم", stote=True)

    total_all_before_tax = fields.Float(
        string="الاجمالي قبل الضريبة", compute="_cal_tot_price", )
    total_tax = fields.Float(string="اجمالي الضريبة", compute="_cal_tot_price")

    total_discount = fields.Float(
        string="اجمالي الخصم", compute="_cal_tot_price")
    total_all_with_tax = fields.Float(
        string="الاجمالي شامل الضريبة", compute="_cal_tot_price")
    advance_amount = fields.Float(string="المبلغ المدفوع")

    technical_name = fields.Many2one('hr.technical.assignments', string="اسم الفني",
                                     domain="[('company_id','=', company_id),('state','=', 'current')]")

    discount_type = fields.Selection([('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم",
                                     default='percentage')
    discount_line = fields.Float(string="الخصم")
    supervisor_amount = fields.Float(string="مبلغ المشرف")
    pricelist_id = fields.Many2one('product.pricelist', string="التسعيرة حسب", domain="[('company_id','=',company_id )]",
                                   default=lambda self: self._default_pricelist_branch()
                                   )
    use_pricelist = fields.Boolean(default=lambda self: self._default_pricelist_flag(),
                                   compute="_get_pricelist_flag")
    confirm_message_flag = fields.Boolean()

    drum_counter = fields.Char(string="عداد وقت الدخول")

    drum_counter_exit = fields.Char(string="عداد وقت الخروج")
    user_id = fields.Many2one('res.users', string='مدخل البيانات', readonly=True,  required=True, related="entry_card_id.user_id",store=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Place Of sale',
                                      domain="[('code', '=', ['outgoing']),('company_id','=',company_id)]",required=False)


    def _default_picking_type_id(self):
        for rec in self:
            user_config = rec.env['res.user.inventory.config'].search([('user_id', '=', rec.user_id.id),('company_id', '=', rec.company_id.id),('operation_type', '=', 'outgoing')], limit=1)
            is_exsiting_field_in_company = self.env['ir.model.fields'].sudo().search([('name', '=', 'sale_picking_type_id'), ('model', '=', 'res.company')])
            if user_config and user_config.picking_type_id:
                # Use the picking type from user's inventory config
                rec.picking_type_id = user_config.picking_type_id.id
            elif is_exsiting_field_in_company:
                if rec.company_id.sale_picking_type_id and rec.company_id.sale_picking_type_id.company_id.id == rec.company_id.id:
                    # Company's default if no user-specific setting
                    rec.picking_type_id = rec.company_id.sale_picking_type_id.id
            else:
                rec.picking_type_id = False

    @api.onchange("company_id", "partner_id","user_id","lines_spare_parts")
    def get_default_data(self):
        for rec in self:
            rec._default_picking_type_id()
 
 
    def validate_negative_quantity(self):
        # check quantity of product for prevent selling in negative value - منع البيع بالسالب
        self._default_picking_type_id()
        if self.user_has_groups('yousentech_inventory_minus_quantity.group_prevent_selling_negative_value'):
            is_exsiting_field_free_quantity = self.env['ir.model.fields'].sudo().search(
                [('name', '=', 'free_quantity'), ('model', '=', 'sale.order.line')])
            for line in self.lines_spare_parts.filtered(lambda x:x.product_id.detailed_type == 'product'):
                stock_quant = self.env['stock.quant'].search([('product_id', '=', line.product_id.id), 
                ('warehouse_id', '=', self.picking_type_id.warehouse_id.id), ('location_id', '=',  self.picking_type_id.default_location_src_id.id)])
                reserved_quantity = sum(
                    line.reserved_quantity for line in stock_quant)
                if not line.product_id.categ_id.temp_categ_flag:
                    if is_exsiting_field_free_quantity:
                        total_quantity = line.qty_done + line.free_quantity
                    else:
                        total_quantity = line.qty_done
                    print(" line.product_id+++++++++++++++++++++", line.product_id)
                    print("total_quantity+++++++++++++++++++++",total_quantity)
                    print("stock_quant-quantity+++++++++++++++++++++",stock_quant.quantity)
                    print("stock_quant+++++++++++++++++++++",stock_quant)
                    print("reserved_quantity+++++++++++++++++++++",reserved_quantity)
                    print(" self.picking_type_id.warehouse_id+++++++++++++++++++++", self.picking_type_id.warehouse_id)
                    print(" self.picking_type_id.default_location_src_id.ids+++++++++++++++++++++", self.picking_type_id.default_location_src_id.ids)
                    line.product_id.validate_product_quentity(
                        total_quantity, reserved_quantity, self.picking_type_id.warehouse_id.id, self.picking_type_id.default_location_src_id.ids)


    @api.model
    def _default_pricelist_flag(self):
        return self.user_has_groups('product.group_product_pricelist')

    def _get_pricelist_flag(self):
        for rec in self:
            rec.use_pricelist = self.user_has_groups(
                'product.group_product_pricelist')

    def _default_pricelist_branch(self):
        for rec in self:
            pricelist = self.env['product.pricelist'].search(
                [('company_id', '=', rec.company_id.id)])
            return pricelist

    @api.onchange('discount_type', 'discount_line')
    def set_discount_in_lines(self):
        for rec in self:
            if rec.discount_type and rec.discount_line:
                for line in rec.result_lines:
                    line.write({'discount_type': rec.discount_type,
                                'discount_line': rec.discount_line,
                                })
            else:
                for line in rec.result_lines:
                    line.write({'discount_type': False,
                                'discount_line': False,
                                })

    @api.onchange('technical_name')
    def set_technical_name_in_lines(self):
        for rec in self:
            if rec.technical_name:
                for line in rec.result_lines:
                    line.write(
                        {'technical_name': [(4, rec.technical_name.id)]})
            else:
                for line in rec.result_lines:

                    line.write({'technical_name': False,

                                })

    @api.onchange('supervisor_amount')
    def set_supervisor_amount_as_discount_lines(self):
        for rec in self:
            if rec.supervisor_amount and rec.services_amt_after_tax:
                for line in rec.result_lines:
                    line.write({'discount_type': False,
                                'discount_line': False,
                                })
                rec._cal_services_amounts()

                diff = rec.services_amt_after_tax - rec.supervisor_amount
                if round(diff, 0) != 0:
                    for line in rec.result_lines:
                        if line.unit_price:
                            amt_per = (line.total_before_tax /
                                       rec.services_amt_before_tax)
                            new_line_discount = diff * amt_per
                            line.write({'unit_price': line.unit_price - new_line_discount

                                        })

                else:
                    rec.write({'discount_type': False,
                               'discount_line': False,
                               })
                    rec.set_discount_in_lines()
            else:
                rec.write({'discount_type': False,
                           'discount_line': False,
                           })
                rec.set_discount_in_lines()
            rec._cal_services_amounts()

            rec._cal_tot_price()

    @api.onchange('is_guarantee')
    def add_guarantee_product(self):
        for rec in self:
            if rec.is_guarantee:
                for line in rec.result_lines:
                    if line.name:
                        if not line.product_id.guarantee_able and not line.product_id.guarantee_product:
                            line.write(
                                {'name': line.name + '[غير خاضع للضمان]'})
                        if line.product_id.guarantee_able:
                            line.write({'product_has_guarantee_flag': True})

            else:

                for line in rec.result_lines:
                    if line.product_id:
                        line.write({'name': line.product_id.name})
                        line.write({'product_has_guarantee_flag': False})

    # @api.model
    # def _default_branch_id(self):
    #     for rec in self:
    #         return rec.entry_card_id.company_id.id

    # @api.depends('entry_card_id')
    # def _get_branch_id(self):
    #     for rec in self:
    #         if rec.entry_card_id:
    #             rec.company_id = rec.entry_card_id.company_id.id
    #         else:
    #             rec.company_id = False

    @api.onchange('result_lines')
    def _cal_services_amounts(self):
        for rec in self:
            if rec.result_lines:
                rec.services_amt_after_tax = sum(
                    l.total_tax for l in rec.result_lines)
                rec.services_amt_before_tax = sum(
                    l.total_before_tax for l in rec.result_lines)
                rec.services_amt_tax = sum(
                    l.amount_tax for l in rec.result_lines)
                rec.services_discount = sum(
                    l.discount_amount for l in rec.result_lines)
            else:
                rec.services_amt_after_tax = 0
                rec.services_amt_before_tax = 0
                rec.services_amt_tax = 0
                rec.services_discount = 0

    @api.onchange('lines_spare_parts')
    def _cal_spare_parts_amounts(self):
        for rec in self:
            if rec.lines_spare_parts:
                rec.spare_parts_amt_after_tax = sum(
                    l.total_tax for l in rec.lines_spare_parts)
                rec.spare_parts_amt_before_tax = sum(
                    l.total_before_tax for l in rec.lines_spare_parts)
                rec.spare_parts_amt_tax = sum(
                    l.amount_tax for l in rec.lines_spare_parts)
                rec.spare_parts_discount = sum(
                    l.discount_amount for l in rec.lines_spare_parts)
            else:
                rec.spare_parts_amt_after_tax = 0
                rec.spare_parts_amt_before_tax = 0
                rec.spare_parts_amt_tax = 0
                rec.spare_parts_discount = 0

    @api.constrains('lines_spare_parts', 'supervisor_amount')
    def check_price_of_product_from_cost(self):
        for rec in self:
            for line in rec.lines_spare_parts:
                line.product_id.product_tmpl_id.check_product_price_from_cost(
                    line.unit_price, line.unit_cost)

            if rec.supervisor_amount > rec.services_amt_after_tax:
                raise ValidationError(
                    "لا يمكن ان يكون مبلغ المشرف اكبر من مبلغ امر العمل")

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات', readonly=True,
        required=True, default=lambda self: self.env.uid)

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
        l_service_price_include_tax = params.get_param(
            'service_price_include_tax', default=False)
        return l_service_price_include_tax

    is_user_technical = fields.Boolean(
        default=lambda self: self._default_user_technical(), compute="_user_technical_edit_mode")
    is_user_supervisor = fields.Boolean(default=lambda self: self._default_user_supervisor(),
                                        compute="_user_supervisor_edit_mode")
    is_user_sale_man = fields.Boolean(
        default=lambda self: self._default_user_sale_man(), compute="_user_sale_man_edit_mode")

    @api.model
    def _default_user_technical(self):
        return self.user_has_groups('yousentech_car_maintain.group_technician_priv')

    def _user_technical_edit_mode(self):
        self.is_user_technical = self.user_has_groups(
            'yousentech_car_maintain.group_technician_priv')

    @api.model
    def _default_user_supervisor(self):
        return self.user_has_groups('yousentech_car_maintain.group_supervisor_priv')

    def _user_supervisor_edit_mode(self):
        self.is_user_supervisor = self.user_has_groups(
            'yousentech_car_maintain.group_supervisor_priv')

    @api.model
    def _default_user_sale_man(self):
        return self.user_has_groups('yousentech_car_maintain.group_sales_man_priv')

    def _user_sale_man_edit_mode(self):
        self.is_user_sale_man = self.user_has_groups(
            'yousentech_car_maintain.group_sales_man_priv')

    @api.model
    def _default_add_spare_parts_flag(self):
        return self.user_has_groups('yousentech_car_maintain.group_add_spare_parts_priv')

    def _get_add_spare_parts_flag(self):
        self.add_user_spare_parts_flag = self.user_has_groups(
            'yousentech_car_maintain.group_add_spare_parts_priv')

    use_minus_qty = fields.Boolean(string="استخدام الكميات السالبة",
                                   default=lambda self: self._default_option_minus_qty(),
                                   compute="_check_option_minus_qty")

    def _default_option_minus_qty(self):
        params = self.env['ir.config_parameter'].sudo()
        l_use_minus_qty = params.get_param('use_minus_qty',
                                           default=False)
        return l_use_minus_qty

    def _check_option_minus_qty(self):
        params = self.env['ir.config_parameter'].sudo()
        l_use_minus_qty = params.get_param('use_minus_qty',
                                           default=False)
        for rec in self:
            rec.use_minus_qty = True if l_use_minus_qty else False

    def get_spare_parts_inv(self):
        for rec in self:
            picking = self.env['stock.picking'].search(
                [('maint_wo_id1', '=', rec.id)])
            if picking:
                picking.send_products_to_wo()

    def get_datetime_zone_user(self, convert_date_time):
        if convert_date_time:
            user_tz = pytz.timezone(
                self.env.context.get('tz') or self.env.user.tz)
            l_convert_date_time = pytz.utc.localize(
                convert_date_time).astimezone(user_tz)
            return l_convert_date_time.strftime('%Y-%m-%d %H:%M')

    is_user_allow_delete = fields.Boolean(
        default=lambda self: self._default_user_allow_delete(), compute="_user_allow_delete")

    @api.model
    def _default_user_allow_delete(self):
        return self.user_has_groups('yousentech_car_maintain.group_allow_delete_wo_priv')

    def _user_allow_delete(self):
        self.is_user_allow_delete = self.user_has_groups(
            'yousentech_car_maintain.group_allow_delete_wo_priv')

    def sale_order(self):
        for rec in self:
            whs_id = self.env['stock.warehouse'].search(
                [('company_id', '=', rec.entry_card_id.company_id.id)], limit=1)
            rec.get_available_qty()

            sale_order_check = self.env['sale.order'].search(
                [('maint_wo_id', '=', rec.id)])
            if sale_order_check:
                raise ValidationError(
                    "لا يمكن انشاء امر بيع مره اخرى لنفس امر العمل")
            if not rec.lines_spare_parts and not rec.result_lines:
                raise ValidationError(
                    "لا يمكن انشاء امر بيع لا توجد سجلات لانشاء امر بيع")

            if not rec.no_spare_parts_flag:
                if not rec.lines_spare_parts:
                    raise ValidationError(
                        "لا يمكن انشاء امر بيع لعدم وجود قطع غيار لامر العمل")

            for l in rec.lines_spare_parts:
                if l.qty_done > l.qty:
                    raise ValidationError(
                        "تنبيه .. الكمية الفعلية للصنف (%s) اكبر من الكمية المصروفة من المستودع " % (
                            l.product_id.name))

            for l in rec.lines_spare_parts:
                if not l.qty_done:
                    raise ValidationError(
                        "تنبيه .. الكمية الفعلية للصنف (%s) صفر " % (
                            l.product_id.name))

            rec.write({'end_date': datetime.today()})

            sale_order_tmp = {
                'partner_id': rec.partner_id.id,
                'partner_invoice_id': rec.partner_id.id,
                'partner_shipping_id': rec.partner_id.id,
                'date_order': rec.entry_card_id.order_date,
                'picking_policy': 'direct',
                'state': 'draft',
                'company_id': rec.entry_card_id.company_id.id,
                'user_id': rec.user_id.id,
                'warehouse_id': whs_id.id,
                'maint_wo_id': rec.id,
                'entry_card_id': rec.entry_card_id.id,
                'car_panel_no': rec.car_panel_no,
                'partner_mobile': rec.partner_mobile,
                'pay_type': rec.pay_type,
                'vin_no': rec.vin_no,
                'car_type': rec.car_type_id.name,
             
                'company_id': rec.entry_card_id.company_id.id,
                'require_signature': True,
                'require_payment': False,
                # 'pricelist_id':  1,
                'invoice_status': 'no',
                'is_guarantee': rec.is_guarantee,
            }

            sale_order = self.env['sale.order'].create(sale_order_tmp)

            is_exsiting_field_picking_type_id = self.env['ir.model.fields'].sudo().search([('name', '=', 'picking_type_id'), ('model', '=', 'sale.order')])
            if is_exsiting_field_picking_type_id :
                sale_order.picking_type_id = self.picking_type_id.id

            for line_sale in rec.lines_spare_parts:
                discount_sale_perc = 0
                if line_sale.discount_line and line_sale.discount_type == 'percentage':
                    discount_sale_perc = line_sale.discount_line
                elif line_sale.discount_line and line_sale.discount_type == 'amount':
                    discount_sale_perc = (
                        (line_sale.discount_line) / (line_sale.qty * line_sale.unit_price)) * 100

                if line_sale.qty_done:

                    sale_order_line = self.env['sale.order.line'].create({
                        'product_id': line_sale.product_id.id,
                        'name': line_sale.name,
                        'product_uom_qty': line_sale.qty_done,
                        'state': 'draft',
                        'product_uom': line_sale.product_id.uom_id.id,
                        'discount': discount_sale_perc if not rec.discount_inv_posted else False,
                        'price_unit': line_sale.unit_price,
                        'tax_id': line_sale.product_tax.ids if line_sale.product_tax else [],
                        'sequence': 10,
                        'order_id': sale_order.id,
                        'company_id': rec.entry_card_id.company_id.id,
                        'invoice_status': 'no',
                        'salesman_id': self.env.user.id,
                        'company_id': rec.entry_card_id.company_id.id,
                        'currency_id': self.env.company.currency_id.id,
                        'qty_delivered_method': 'manual',
                        'qty_delivered': 0,
                        'qty_to_invoice': 0,
                        'qty_invoiced': 0,
                        'order_partner_id': rec.partner_id.id,
                        'customer_lead': 0,
                    })

            for line in rec.result_lines:
                total_mislead = 0
                select = []
                discount_sale_perc = 0
                if line.discount_line and line.discount_type == 'percentage':
                    discount_sale_perc = line.discount_line
                elif line.discount_line and line.discount_type == 'amount':
                    discount_sale_perc = (
                        (line.discount_line) / (line.unit_price)) * 100

                sale_order_line = self.env['sale.order.line'].create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': 1,
                    'product_uom': line.product_id.uom_id.id,
                    'discount': discount_sale_perc if not rec.discount_inv_posted else False,
                    'state': 'draft',
                    'price_unit': line.unit_price,
                    'tax_id': line.product_tax.ids if line.product_tax else [],
                    'order_id': sale_order.id,
                    'company_id': rec.entry_card_id.company_id.id,
                    'invoice_status': 'no',
                    'salesman_id': self.env.user.id,
                    'company_id': rec.entry_card_id.company_id.id,
                    'product_has_guarantee_flag': line.product_has_guarantee_flag,
                    'currency_id': self.env.company.currency_id.id,
                    'qty_delivered_method': 'manual',
                    'qty_delivered': 0,
                    'qty_to_invoice': 0,
                    'qty_invoiced': 0,
                    'order_partner_id': rec.partner_id.id,
                    'customer_lead': 0,
                })

            if rec.discount_inv_posted:
                discount_product_tmp = self.env['product.template'].search([('discount_product_flag', '=', True)],
                                                                           limit=1)
                discount_product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', discount_product_tmp.id)])

                if not discount_product:
                    raise ValidationError(
                        "تنبيه... نوع الخصم حسب الفاتورة يجب تهيئة الخصم من بطاقة الصنف")

                if discount_product and (rec.total_discount):
                    sale_order_line = self.env['sale.order.line'].create({
                        'product_id': discount_product.id,
                        'name': discount_product.name,
                        'product_uom_qty': -1,
                        'state': 'draft',
                        'product_uom': discount_product.uom_id.id,
                        'discount': False,
                        'price_unit': rec.total_discount,
                        'order_id': sale_order.id,
                        'company_id': rec.entry_card_id.company_id.id,
                        'invoice_status': 'no',
                        'salesman_id': self.env.user.id,
                        'company_id': rec.company_id.id,
                        'currency_id': self.env.company.currency_id.id,
                        'qty_delivered_method': 'manual',
                        'qty_delivered': 0,
                        'qty_to_invoice': 0,
                        'qty_invoiced': 0,
                        'order_partner_id': rec.partner_id.id,
                        'customer_lead': 0,
                    })

            rec.write({'state': 'execute_completed'})
            rec.entry_card_id.write({'state': 'execute_completed'})
            rec.checkup_id.write({'state': 'execute_completed'})

            rec.write({'sale_order_id': sale_order.id})
            sale_order.action_confirm()
            rec.call_invoice()

    def call_invoice(self):
        for rec in self:
            invoice = self.env['account.move'].search(
                [('maint_wo_id', '=', rec.id)])

            action = self.env.ref('account.action_move_out_invoice_type')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', '=', invoice.id),
                                ('move_type', 'in', ['out_refund', 'out_invoice'])]

            if invoice:
                res = self.env.ref('account.view_move_form', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = invoice.id or False
            return result

    def call_sale_order(self):
        for rec in self:
            sale_order = self.env['sale.order'].search(
                [('maint_wo_id', '=', rec.id)])

            action = self.env.ref('sale.action_orders')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', '=', sale_order.id)]
            if sale_order:
                res = self.env.ref('sale.view_order_form', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = sale_order.id or False

            return result

    def unlink(self):
        for rec in self:
            if not rec.is_user_allow_delete:
                raise ValidationError(
                    " تنبيه .. لا يمكن الحذف ..  المستخدم لاتوجد له صلاحية  ")
            if not rec.sale_order_id:
                rec.entry_card_id.write({'state': 'execute_started'})
                rec.checkup_id.write({'state': 'execute_started'})

                rec.entry_card_id.write({'maint_wo_id': False})
                rec.checkup_id.write({'maint_wo_id': False})

            else:
                raise ValidationError(
                    "تنبيه .. لا يمكن الحذف بسبب تم انشاء امر بيع (%s) " % rec.sale_order_id.name)
        return super(mizan_car_work_procedure_master, self).unlink()

    @api.depends('result_lines', 'lines_spare_parts')
    def _cal_tot_price(self):
        for rec in self:

            total_all_before_tax = 0
            total_tax = 0
            total_discount = 0
            total_all_with_tax = 0

            total_all_before_tax = sum(
                line_srv.total_before_tax for line_srv in rec.result_lines)
            total_tax = sum(
                line_srv.amount_tax for line_srv in rec.result_lines)
            total_discount = sum(
                line_srv.discount_amount for line_srv in rec.result_lines)
            total_all_with_tax = sum(
                line_srv.total_tax for line_srv in rec.result_lines)

            total_all_before_tax += sum(
                line_srv.total_before_tax for line_srv in rec.lines_spare_parts)
            total_tax += sum(line_srv.amount_tax for line_srv in rec.lines_spare_parts)
            total_discount += sum(
                line_srv.discount_amount for line_srv in rec.lines_spare_parts)
            total_all_with_tax += sum(
                line_srv.total_tax for line_srv in rec.lines_spare_parts)

            rec.total_all_before_tax = total_all_before_tax
            rec.total_tax = total_tax
            rec.total_discount = total_discount
            rec.total_all_with_tax = total_all_with_tax

    @api.onchange('lines_spare_parts')
    def get_available_qty(self):
        for rec in self:
            whs_id = self.env['stock.warehouse'].search(
                [('company_id', '=', rec.entry_card_id.company_id.id)], limit=1)

            if not rec.use_minus_qty:

                for line in rec.lines_spare_parts:

                    if not line.product_id.categ_id.temp_categ_flag:

                        if line.qty_done and line.product_id and line.product_id.name.upper() != "DISCOUNT" and line.product_id.type == 'product':
                            sql_query = "select COALESCE(sum(quantity), 0::numeric) as qty from stock_quant a where a.product_id = {} and location_id in (" \
                                        "select ld.id from stock_warehouse w, stock_location ls ,stock_location ld " \
                                        "where w.id={} and w.code=ls.name and ls.id=ld.location_id and ld.active=true)".format(
                                            line.product_id.id, whs_id.id)

                            self.env.cr.execute(sql_query)
                            aval_qty = self.env.cr.fetchone()[0]

                            if line.qty_done > aval_qty:
                                raise ValidationError("Warning: No enough Qty For product <<<<لا توجد كمية متوفر للصنف المحدد[ {} ][ "
                                                      "{} ] .. الكمية المتوفره للصنف [ {} ]".format(
                                                          line.product_id.name, line.product_id.default_code, aval_qty))

    def action_register_payment(self):
        for rec in self:
            payment = self.env['mizan.register.payment'].search(
                [('header_id', '=', rec.entry_card_id.id), ('maint_wo_id', '=', rec.id)])

            action = self.env.ref(
                'yousentech_car_maintain.action_mizan_payment_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', 'in', payment.ids)]
            return result

    def register_payment(self):
        advanced_amount = 0
        remaining_amount = 0
        for rec in self:
            payment = self.env['mizan.register.payment'].search(
                [('header_id', '=', rec.entry_card_id.id), ('state', '!=', 'cancel'), ('maint_wo_id', '=', rec.id)])
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            if advanced_amount >= rec.total_all_with_tax:
                raise ValidationError(
                    "اكتمل الدفع  .. لا يمكن انشاء مفوعات جديدة ")

            remaining_amount = rec.total_all_with_tax - advanced_amount
            return {
                'name': _('Register Payment'),
                'view_mode': 'form',
                'res_model': 'mizan.register.payment',
                'view_id': self.env.ref('yousentech_car_maintain.mizan_payment_view').id,
                'type': 'ir.actions.act_window',
                'context': {'default_invoice_amount': rec.total_all_with_tax,
                            'default_advanced_amount': advanced_amount,
                            'default_remaining_amount': remaining_amount, 'default_branch_id': rec.entry_card_id.company_id.id,
                            'default_payment_note': "دفعة مقدمة لامر العمل",

                            'default_header_id': rec.entry_card_id.id, 'default_maint_wo_id': rec.id, 'default_payment_amount': remaining_amount if remaining_amount else 0,
                            },
                'target': 'current'
            }

    def get_price_of_product(self, product_id):
        for rec in self:
            if product_id:
                price = 0.00
                if rec.use_pricelist:
                    pricelist = self.env['product.pricelist'].search(
                        [('company_id', '=', rec.entry_card_id.company_id.id)])

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

    def call_confirm_message_dailog(self):
        for rec in self:
            rec.validate_negative_quantity()
            if not rec.additional_services:
                if rec.total_all_with_tax:
                    message = "اجمالي المبلغ المستحق هو  [ %s ] .. هل تريد الاستمرار " % round(
                        rec.total_all_with_tax, 2)
                    message_en = " Total amount will be [ %s ] >> do you want to continue " % round(
                        rec.total_all_with_tax, 2)

                    action = self.env.ref(
                        'yousentech_car_maintain.message_confirm_action')
                    result = action.read()[0]
                    result.pop('id', None)
                    result['context'] = {'default_desc': message_en + message}
                    return result

                else:
                    raise ValidationError(
                        "تنبيه: خطأ في اجمالي الخدمات وقطع الغيار ")
            else:
                message = "اجمالي المبلغ المستحق هو  [ %s ] .. هل تريد الاستمرار " % rec.total_all_with_tax
                message_en = " Total amount will be [ %s ] >> do you want to continue " % rec.total_all_with_tax

                action = self.env.ref(
                    'yousentech_car_maintain.message_confirm_action')
                result = action.read()[0]
                result.pop('id', None)
                result['context'] = {
                    'default_desc': message_en + "/" + message}
                return result
