# -*- coding: utf-8 -*-
from odoo import models, fields, api, _,tools
from odoo.exceptions import ValidationError
from datetime import datetime,time
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import pytz


class xx_account_move(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals_list):
        invoice = super(xx_account_move, self).create(vals_list)
   
        if vals_list.get('work_order_id'):
            wo_move = self.env['mizan.car.work.procedure.master'].search([('id', '=', vals_list.get('work_order_id'))])
            if wo_move:
                wo_move.write({'create_invoice_manually_id': invoice.id})

        return invoice

class xx_sale_order_line(models.Model):
     _inherit = 'sale.order.line'

     product_has_guarantee_flag = fields.Boolean(string="خاضع للضمان",default=False)

     def _prepare_invoice_line(self):
        res = super(xx_sale_order_line, self)._prepare_invoice_line()
        res.update({'product_has_guarantee_flag': self.product_has_guarantee_flag or False})

        return res

class xx_sale_order(models.Model):
    _inherit = 'sale.order'

    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="رقم امر الفحص", readony=True,copy=False)
    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="رقم كرت الدخول", readony=True,copy=False)
    work_order_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل",copy=False)
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    partner_mobile = fields.Char(string="رقم الجوال")
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")
    vin_no = fields.Char(string="رقم الشاصي")
    car_type = fields.Char(string="نوع السيارة")
    sale_man_id = fields.Many2one('mizan.salesman.assignments', string="المندوب",copy=False,domain="[('branch_id','=', branch_id),('state','=', 'current')]")
    is_guarantee = fields.Boolean(string="اضافة ضمان",default=False)


    def _prepare_invoice(self):
        invoice_vals = super(xx_sale_order, self)._prepare_invoice()
        invoice_vals.update({'work_order_id': self.work_order_id.id or False})
        invoice_vals.update({'entry_card_id': self.entry_card_id.id or False})
        invoice_vals.update({'sale_order_id': self.id or False})
        invoice_vals.update({'car_panel_no': self.car_panel_no or False})
        invoice_vals.update({'partner_mobile': self.partner_mobile or False})
        invoice_vals.update({'pay_type': self.pay_type or False})
        invoice_vals.update({'vin_no': self.vin_no or False})
        invoice_vals.update({'car_type': self.car_type or False})
        invoice_vals.update({'sale_man_id': self.sale_man_id.id or False})
        invoice_vals.update({'is_guarantee': self.is_guarantee or False})

        return invoice_vals

    def action_confirm(self):

        self.check_available_qty()
        sale_order_confirm = super(xx_sale_order, self).action_confirm()

        return sale_order_confirm
    def action_cancel(self):
        for rec in self:
            if rec.work_order_id:
                rec.work_order_id.write({'sale_order_id': False})
                rec.work_order_id.write({'state': 'work_order_started'})
                rec.entry_card_id.write({'state': 'work_order_started'})
                rec.work_order_id.checkup_id.write({'state': 'work_order_started'})
                rec.work_order_id.write({'end_date':False})
                rec.write({'work_order_id': False})
 
        return super(xx_sale_order, self).action_cancel()

    def unlink(self):
        for rec in self:
           if rec.work_order_id:
               rec.work_order_id.write({'sale_order_id': False})
               rec.work_order_id.write({'state': 'work_order_started'})
               rec.entry_card_id.write({'state': 'work_order_started'})
               rec.work_order_id.checkup_id.write({'state': 'work_order_started'})
               rec.work_order_id.write({'end_date': False})

        return super(xx_sale_order, self).unlink()


class xx_car_checkup(models.Model):
    _name = 'mizan.car.work.procedure.master'
    _description = 'Car work procedure master'


    _rec_name = 'id'


    partner_id = fields.Many2one('res.partner', string="العميل", required=True)
    state = fields.Selection([('draft', 'مرحلة الاعداد'), ('confirm', 'مرحلة التاكيد'),
                              ('execute_started', 'بدء الفحص'), ('work_order_started', 'امر العمل'),
                              ('execute_completed', 'اكتمال التنفيذ'), ('not_checkup_car', 'الخروج بدون فحص'),
                              ('return_to_modify', 'استعادة للتعديل'),
                              ('cancel_order', 'ملغي امر التركيب')

                              ], default='work_order_started', readonly=True, copy=False)

    create_date = fields.Datetime(string="بدء الفحص", required=True, default=fields.Datetime.now, copy=False)
    end_date = fields.Datetime(string="انتهاء العمل",  copy=False)

    car_panel_no = fields.Char(string="رقم لوحة السيارة")

    execute_done = fields.Boolean()

    partner_mobile = fields.Char(string="رقم الجوال")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس")
    car_model = fields.Char(string="الموديل")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة", )

    sale_order_id = fields.Many2one('sale.order', string="رقم امر البيع", readony=True, copy=False)
    create_invoice_manually_id = fields.Many2one('account.move',copy=False,readony=True)

    # body_image = fields.Binary(string="اختر صورة مكان الفحص في البدي",copy=False)
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")

    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="الفحص",copy=False)
    entry_card_id = fields.Many2one('mizan.car.entry.card.master', string="بيانات كرت الدخول",copy=False)
    vin_no = fields.Char(string="رقم الشاصي")
    branch_id = fields.Integer(copy=False,
                               default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    sale_man_id = fields.Many2one('mizan.salesman.assignments', string="المندوب",copy=False,domain="[('branch_id','=', branch_id),('state','=', 'current')]")

    result_lines = fields.One2many('mizan.car.work.procedure.line', 'header_id', ondelete='cascade', copy=False)
    lines_spare_parts = fields.One2many('mizan.car.spare.parts.lines', 'header_id', ondelete='cascade', copy=False)
    discount_inv_posted = fields.Boolean(default=lambda self: self._default_discount_posted_flag(),
                                         compute="_get_discount_posted_flag")
    add_user_spare_parts_flag = fields.Boolean(default=lambda self: self._default_add_spare_parts_flag(),
                                         compute="_get_add_spare_parts_flag")

    branch_id = fields.Many2one('custom.branches', string='الفرع', readonly=True, copy=False)
    no_spare_parts_flag = fields.Boolean(string="امر البيع لا يحتاج قطع مستبدلة")
    is_guarantee = fields.Boolean(string="اضافة ضمان",default=True)
    additional_services = fields.Selection([('change_of_guarantee','التغيير على الضمان'),('internal_branches_services','خدمات داخلية بين الفروع')],string="خدمات اضافية",)

    services_amt_after_tax = fields.Float(string="الاجمالي بعد الضريبة",stote=True)
    services_amt_before_tax = fields.Float(string="الاجمالي قبل الضريبة",stote=True)
    services_amt_tax = fields.Float(string="اجمالي الضريبة",stote=True)
    services_discount = fields.Float (string="اجمالي الخصم",stote=True)

    spare_parts_amt_after_tax = fields.Float(string="الاجمالي بعد الضريبة", stote=True)
    spare_parts_amt_before_tax = fields.Float(string="الاجمالي قبل الضريبة", stote=True)
    spare_parts_amt_tax = fields.Float(string="اجمالي الضريبة", stote=True)
    spare_parts_discount = fields.Float(string="اجمالي الخصم", stote=True)

    total_all_before_tax = fields.Float(string="الاجمالي قبل الضريبة", compute="_cal_tot_price", )
    total_tax = fields.Float(string="اجمالي الضريبة", compute="_cal_tot_price")

    total_discount = fields.Float(string="اجمالي الخصم", compute="_cal_tot_price")
    total_all_with_tax = fields.Float(string="الاجمالي شامل الضريبة", compute="_cal_tot_price")
    advance_amount = fields.Float(string="المبلغ المدفوع")
    technical_name = fields.Many2one('hr.technical.assignments',string="اسم الفني",domain="[('branch_id','=', branch_id),('state','=', 'current')]")

    discount_type = fields.Selection([('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم",
                                     default='percentage')
    discount_line = fields.Float(string="الخصم")
    supervisor_amount = fields.Float(string="مبلغ المشرف")
    pricelist_id = fields.Many2one('product.pricelist',string="التسعيرة حسب", domain="[('branch_id','=',branch_id )]",
                                   default=lambda self: self._default_pricelist_branch()
                                   )
    use_pricelist = fields.Boolean(default=lambda self: self._default_pricelist_flag(),
                                   compute="_get_pricelist_flag")
    confirm_message_flag = fields.Boolean()
    @api.model
    def _default_pricelist_flag(self):
        
        return self.user_has_groups('product.group_product_pricelist')

    def _get_pricelist_flag(self):
      
        for rec in self:
            rec.use_pricelist = self.user_has_groups('product.group_product_pricelist')

    def _default_pricelist_branch(self):
        for rec in self:
           
            pricelist = self.env['product.pricelist'].search([('branch_id','=', rec.branch_id.id)])
            return pricelist

    # @api.model
    # def return_technical_id(self,emp_pin_code):
    #     if emp_pin_code:
    #         emp_id = self.env['hr.technical.assignments'].search([('technical_emp_id.pin','=',emp_pin_code),('state','=','current')])
    #         if emp_id:
    #             data = {
    #                     'technical_id': emp_id.id,
    #                     'technical_name': emp_id.technical_emp_id.name,
    #                     }
            
    #             return data
    #         else:
    #             return False
    #     else:
    #             return False
                

    @api.onchange('discount_type','discount_line')
    def set_discount_in_lines(self):
        for rec in self:
          
            if rec.discount_type and rec.discount_line:
                for line in rec.result_lines:
                    # if line.unit_price:
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
                    line.write({'technical_name': [(4, rec.technical_name.id)]})
            else:
                for line in rec.result_lines:

                    line.write({'technical_name': False,

                                })

    # @api.onchange('supervisor_amount')
    # def set_supervisor_amount_as_discount_lines(self):
    #     for rec in self:
    #         if rec.supervisor_amount < rec.services_amt_after_tax:
    #
    #             if rec.supervisor_amount and rec.services_amt_after_tax:
    #                 for line in rec.result_lines:
    #                     line.write({'discount_type': False,
    #                                 'discount_line':False,
    #                                                 })
    #                 rec._cal_services_amounts()
    #
    #                 print(" rec.services_amt_after_tax ",  rec.services_amt_after_tax )
    #
    #                 diff = rec.services_amt_after_tax - rec.supervisor_amount
    #                 if round(diff, 0) != 0:
    #                         discount = (diff / rec.services_amt_after_tax) * 100
    #                         print("discount",discount)
    #                         if discount != 0:
    #                             rec.write({'discount_type': 'percentage',
    #                                        'discount_line': discount,
    #                                        })
    #
    #                             rec.set_discount_in_lines()
    #
    #                         # for line in rec.result_lines:
    #                         #     # if line.unit_price:
    #                         #     #     amt_per = (line.total_before_tax/ rec.services_amt_before_tax) * 100
    #                         #     # #
    #                         #     #     print("amt_per",amt_per)
    #                         #
    #                         #     line.write({'discount_type': 'percentage',
    #                         #                 'discount_line':discount,
    #                         #                 })
    #                         else:
    #                             rec.write({'discount_type': False,
    #                                        'discount_line': False,
    #                                        })
    #                             rec.set_discount_in_lines()
    #
    #                 else:
    #                     rec.write({'discount_type': False,
    #                                'discount_line': False,
    #                                })
    #                     rec.set_discount_in_lines()
    #             else:
    #                 rec.write({'discount_type': False,
    #                            'discount_line': False,
    #                            })
    #                 rec.set_discount_in_lines()
    #
    #             rec._cal_tot_price()
    #         else:
    #             raise ValidationError(
    #                 "لا يمكن ان يكون مبلغ المشرف اكبر من مبلغ امر العمل")

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
                                amt_per = (line.total_before_tax / rec.services_amt_before_tax)
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
            # else:
            #     raise ValidationError(
            #         "لا يمكن ان يكون مبلغ المشرف اكبر من مبلغ امر العمل")

    # @api.constrains('supervisor_amount')
    # def check_supervisor_amount(self):
    #     for rec in self:
    #         if rec.supervisor_amount > rec.services_amt_after_tax:


    #             raise ValidationError(
    #                 "لا يمكن ان يكون مبلغ المشرف اكبر من مبلغ امر العمل")

    @api.onchange('is_guarantee')
    def add_guarantee_product(self):
        for rec in self:
           
            if rec.is_guarantee:
                # print("rec.is_guarantee",rec.is_guarantee)
                # g_product = self.env['product.product'].search([('guarantee_product','=', True)],limit=1)
                # if g_product:
                #     products = self.env['mizan.car.work.procedure.line'].create({
                #         'product_id': g_product.id,
                #         'name': g_product.name,
                #         'unit_price': g_product.list_price,
                #         'product_tax': g_product.taxes_id.id,
                #         'is_guarantee_flag': True,
                #
                #          'header_id': rec.id,
                #     })

                for line in rec.result_lines:
                    if line.name:
                        if not line.product_id.guarantee_able and not line.product_id.guarantee_product:
                            line.write({'name': line.name + '[غير خاضع للضمان]'})
                        if line.product_id.guarantee_able:
                            line.write({'product_has_guarantee_flag': True })


                # else:
                #     raise ValidationError(
                #         "يجب تحديد صنف خدمي ضمان ")

            else:
                # for line in rec.lines_spare_parts:
                #     line.write({'name': line.product_id.name})

                for line in rec.result_lines:
                    if line.product_id:
                        line.write({'name': line.product_id.name })
                        line.write({'product_has_guarantee_flag': False})

                    # if line.is_guarantee_flag:
                    #     line.unlink()


    @api.model
    def _default_branch_id(self):
        for rec in self:
            return rec.entry_card_id.branch_id.id

    @api.depends('entry_card_id')
    def _get_branch_id(self):
        for rec in self:
            if rec.entry_card_id:
                rec.branch_id = rec.entry_card_id.branch_id.id
            else:
                rec.branch_id = 0

    @api.onchange('result_lines')
    def _cal_services_amounts(self):
        for rec in self:
        
            if rec.result_lines:
                rec.services_amt_after_tax = sum(l.total_tax for l in rec.result_lines)
                rec.services_amt_before_tax = sum(l.total_before_tax for l in rec.result_lines)
                rec.services_amt_tax = sum(l.amount_tax for l in rec.result_lines)
                rec.services_discount = sum(l.discount_amount for l in rec.result_lines)
            else:
                rec.services_amt_after_tax = 0
                rec.services_amt_before_tax = 0
                rec.services_amt_tax = 0
                rec.services_discount = 0

    @api.onchange('lines_spare_parts')
    def _cal_spare_parts_amounts(self):
        for rec in self:
         
            if rec.lines_spare_parts:
                rec.spare_parts_amt_after_tax = sum(l.total_tax for l in rec.lines_spare_parts)
                rec.spare_parts_amt_before_tax = sum(l.total_before_tax for l in rec.lines_spare_parts)
                rec.spare_parts_amt_tax = sum(l.amount_tax for l in rec.lines_spare_parts)
                rec.spare_parts_discount = sum(l.discount_amount for l in rec.lines_spare_parts)
            else:
                rec.spare_parts_amt_after_tax = 0
                rec.spare_parts_amt_before_tax = 0
                rec.spare_parts_amt_tax = 0
                rec.spare_parts_discount = 0

    @api.constrains('lines_spare_parts','supervisor_amount')
    def check_price_of_product_from_cost(self):
        for rec in self:
          
            for line in rec.lines_spare_parts:
                line.product_id.product_tmpl_id.check_product_price_from_cost(line.unit_price)
            
            if rec.supervisor_amount > rec.services_amt_after_tax:
                raise ValidationError(
                    "لا يمكن ان يكون مبلغ المشرف اكبر من مبلغ امر العمل")
            
            whs_id = self.env['stock.warehouse'].search(
                [('branch_id', '=', rec.entry_card_id.branch_id.id)], limit=1)
            
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
                                raise ValidationError(
                                    "Warning: No enough Qty For product <<<<لا توجد كمية متوفر للصنف المحدد[ {} ][ "
                                    "{} ] .. الكمية المتوفره للصنف [ {} ]".format(
                                        line.product_id.name, line.product_id.default_code, aval_qty))
                
            

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True,
        required=True,default=lambda self: self.env.uid)


    # @api.depends('company_id')
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

    # ===========================================================================================
    service_price_include_tax_flag = fields.Boolean(default=lambda self: self._default_service_price_include_tax_flag(),
                                                    compute="_get_service_price_include_tax_flag")

    # @api.depends('company_id')
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

        # ===========================================================================================
        # ===========================================================================================
    is_user_technical = fields.Boolean(default=lambda self: self._default_user_technical(),compute="_user_technical_edit_mode")

    is_user_supervisor = fields.Boolean(default=lambda self: self._default_user_supervisor(),
                                             compute="_user_supervisor_edit_mode")
    is_user_sale_man = fields.Boolean(default=lambda self: self._default_user_sale_man(), compute="_user_sale_man_edit_mode")

    @api.model
    def _default_user_technical(self):
    
        return self.user_has_groups('qimamhd_mizan_car_13.group_technician_priv')

    def _user_technical_edit_mode(self):
   
        self.is_user_technical = self.user_has_groups('qimamhd_mizan_car_13.group_technician_priv')

    @api.model
    def _default_user_supervisor(self):
        
        return self.user_has_groups('qimamhd_mizan_car_13.group_supervisor_priv')

    def _user_supervisor_edit_mode(self):
       
        self.is_user_supervisor = self.user_has_groups('qimamhd_mizan_car_13.group_supervisor_priv')

    @api.model
    def _default_user_sale_man(self):
        
        return self.user_has_groups('qimamhd_mizan_car_13.group_sales_man_priv')

    def _user_sale_man_edit_mode(self):
        
        self.is_user_sale_man = self.user_has_groups('qimamhd_mizan_car_13.group_sales_man_priv')

    @api.model
    def _default_add_spare_parts_flag(self):
      
        return self.user_has_groups('qimamhd_mizan_car_13.group_add_spare_parts_priv')

    def _get_add_spare_parts_flag(self):
       
        self.add_user_spare_parts_flag = self.user_has_groups('qimamhd_mizan_car_13.group_add_spare_parts_priv')



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
            picking = self.env['stock.picking'].search([('work_order_id1','=', rec.id)])
            if picking:
                picking.send_products_to_wo()

    def get_datetime_zone_user(self, convert_date_time):
        if convert_date_time:
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
            l_convert_date_time = pytz.utc.localize(convert_date_time).astimezone(user_tz)

            # if l_convert_date_time.strftime('%H:%M') == '03:00':
            #
            #     return l_convert_date_time.strftime('%Y-%m-%d')
            # else:
            return l_convert_date_time.strftime('%Y-%m-%d %H:%M')
    
        #========================================================================================================================== 
    is_user_allow_delete = fields.Boolean(default=lambda self: self._default_user_allow_delete(), compute="_user_allow_delete")
    @api.model
    def _default_user_allow_delete(self):
        return self.user_has_groups('qimamhd_mizan_car_13.group_allow_delete_wo_priv')

    def _user_allow_delete(self):
        
        self.is_user_allow_delete = self.user_has_groups('qimamhd_mizan_car_13.group_allow_delete_wo_priv')


    def sale_order(self):

        for rec in self:
            # rec.check_data()
            # rec.check_all_lines()

            whs_id = self.env['stock.warehouse'].search([('branch_id', '=', rec.entry_card_id.branch_id.id)], limit=1)
            rec.get_available_qty()

            sale_order_check = self.env['sale.order'].search([('work_order_id', '=', rec.id)])
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
                'branch_id': rec.entry_card_id.branch_id.id,
                'user_id': rec.user_id.id,
                'warehouse_id': whs_id.id,
                'work_order_id': rec.id,
                'entry_card_id': rec.entry_card_id.id,

                'car_panel_no': rec.car_panel_no,
                'partner_mobile': rec.partner_mobile,
                'pay_type': rec.pay_type,
                'vin_no': rec.vin_no,
                'car_type': rec.car_type_id.name,
                'sale_man_id': rec.sale_man_id.id,
                'company_id': rec.entry_card_id.company_id.id,
                'require_signature': True,
                'require_payment': False,
                'pricelist_id':  1,
                'invoice_status': 'no',
                'is_guarantee': rec.is_guarantee,
                 # 'team_id': 1,
            }

            sale_order = self.env['sale.order'].create(sale_order_tmp)
            for line_sale in rec.lines_spare_parts:
                discount_sale_perc = 0
                if line_sale.discount_line and line_sale.discount_type == 'percentage':
                    discount_sale_perc = line_sale.discount_line
                elif line_sale.discount_line and line_sale.discount_type == 'amount':
                    discount_sale_perc = ((line_sale.discount_line) / (line_sale.qty * line_sale.unit_price)) * 100

                if line_sale.qty_done:

                    sale_order_line = self.env['sale.order.line'].create({
                        'product_id': line_sale.product_id.id,
                        'name': line_sale.name,
                        'product_rac_id': line_sale.product_id.product_rac_id_lines.filtered(
                                           lambda m: m.branch_id.id == rec.entry_card_id.branch_id.id).product_rac_id.ids,

                        'product_uom_qty': line_sale.qty_done,
                        'state': 'draft',
                        'product_uom': line_sale.product_id.uom_id.id,
                        'discount': discount_sale_perc if not rec.discount_inv_posted else False,
                        'price_unit': line_sale.unit_price,
                          'tax_id': line_sale.product_tax.ids if line_sale.product_tax else [],

                        'order_id': sale_order.id,
                        'branch_id': rec.entry_card_id.branch_id.id,
                        'invoice_status': 'no',
                        'salesman_id': self.env.user.id,
                        'company_id': rec.entry_card_id.company_id.id,
                        'currency_id': self.env.company.currency_id.id,
                        # 'price_subtotal': 1,
                        # 'price_tax':1,
                        # 'price_total': 1,
                        'qty_delivered_method': 'manual',
                        'qty_delivered': 0,
                        'qty_delivered_manual': 0,
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
                    discount_sale_perc = ((line.discount_line) / (line.unit_price)) * 100

                sale_order_line = self.env['sale.order.line'].create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_rac_id': line.product_id.product_rac_id_lines.filtered(
                                           lambda m: m.branch_id.id == rec.entry_card_id.branch_id.id).product_rac_id.ids,

                    'product_uom_qty': 1,
                    'product_uom': line.product_id.uom_id.id,
                    'discount': discount_sale_perc if not rec.discount_inv_posted else False,
                    'state': 'draft',
                    'price_unit': line.unit_price,
                    'tax_id': line.product_tax.ids if line.product_tax else [],
                    'order_id': sale_order.id,
                    'branch_id': rec.entry_card_id.branch_id.id,
                    'invoice_status': 'no',
                    'salesman_id': self.env.user.id,
                    'company_id': rec.entry_card_id.company_id.id,
                    'product_has_guarantee_flag': line.product_has_guarantee_flag,
                    'currency_id': self.env.company.currency_id.id,
                    # 'price_subtotal': 1,
                    # 'price_tax':1,
                    # 'price_total': 1,
                    'qty_delivered_method': 'manual',
                    'qty_delivered': 0,
                    'qty_delivered_manual': 0,
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

                if discount_product and (rec.services_price - rec.services_price_after_discount):
                    sale_order_line = self.env['sale.order.line'].create({
                        'product_id': discount_product.id,
                        'name': discount_product.name,
                        'product_uom_qty': -1,
                        'state': 'draft',
                        'product_uom': discount_product.uom_id.id,
                        'discount': False,
                        'price_unit': rec.services_price - rec.services_price_after_discount,
                        'order_id': sale_order.id,
                        'branch_id': rec.entry_card_id.branch_id.id,
                        'invoice_status': 'no',
                        'salesman_id': self.env.user.id,
                        'company_id': rec.company_id.id,
                        'currency_id': self.env.company.currency_id.id,
                        # 'price_subtotal': 1,
                        # 'price_tax':1,
                        # 'price_total': 1,
                        'qty_delivered_method': 'manual',
                        'qty_delivered': 0,
                        'qty_delivered_manual': 0,
                        'qty_to_invoice': 0,
                        'qty_invoiced': 0,
                        'order_partner_id': rec.partner_id.id,
                        'customer_lead': 0,
                    })

            rec.sale_order_count = len(sale_order)
            rec.write({'state': 'execute_completed'})
            rec.entry_card_id.write({'state': 'execute_completed'})
            rec.checkup_id.write({'state': 'execute_completed'})

            rec.write({'sale_order_id': sale_order.id})
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

    def call_sale_order(self):
        for rec in self:
            sale_order = self.env['sale.order'].search([('work_order_id', '=', rec.id)])

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

                rec.entry_card_id.write({'work_order_id': False})
                rec.checkup_id.write({'work_order_id': False})

            else:
                raise ValidationError(
                    "تنبيه .. لا يمكن الحذف بسبب تم انشاء امر بيع (%s) " % rec.sale_order_id.name)
        return super(xx_car_checkup, self).unlink()



    @api.depends('result_lines', 'lines_spare_parts')
    def _cal_tot_price(self):
        for rec in self:
         

            total_all_before_tax = 0
            total_tax = 0
            total_discount = 0
            total_all_with_tax = 0

            total_all_before_tax = sum(line_srv.total_before_tax for line_srv in rec.result_lines)
            total_tax = sum(line_srv.amount_tax for line_srv in rec.result_lines)
            total_discount = sum(line_srv.discount_amount for line_srv in rec.result_lines)
            total_all_with_tax = sum(line_srv.total_tax for line_srv in rec.result_lines)

            total_all_before_tax += sum(line_srv.total_before_tax for line_srv in rec.lines_spare_parts)
            total_tax += sum(line_srv.amount_tax for line_srv in rec.lines_spare_parts)
            total_discount += sum(line_srv.discount_amount for line_srv in rec.lines_spare_parts)
            total_all_with_tax += sum(line_srv.total_tax for line_srv in rec.lines_spare_parts)

            rec.total_all_before_tax = total_all_before_tax
            rec.total_tax = total_tax
            rec.total_discount = total_discount
            rec.total_all_with_tax = total_all_with_tax

 
    @api.onchange('lines_spare_parts')
    def get_available_qty(self):
        for rec in self:
            

            whs_id = self.env['stock.warehouse'].search(
                [('branch_id', '=', rec.entry_card_id.branch_id.id)], limit=1)
          
            if not rec.use_minus_qty:

                 for line in rec.lines_spare_parts:

                    if not line.product_id.categ_id.temp_categ_flag:

                        if line.qty_done and line.product_id and line.product_id.name.upper() != "DISCOUNT" and line.product_id.type == 'product':
                                sql_query = "select COALESCE(sum(quantity), 0::numeric) as qty from stock_quant a where a.product_id = {} and location_id in (" \
                                            "select ld.id from stock_warehouse w, stock_location ls ,stock_location ld " \
                                            "where w.id={} and w.code=ls.name and ls.id=ld.location_id and ld.active=true)".format(line.product_id.id, whs_id.id)

                                self.env.cr.execute(sql_query)
                                aval_qty = self.env.cr.fetchone()[0]
                              
                                if line.qty_done > aval_qty:
                                    raise ValidationError("Warning: No enough Qty For product <<<<لا توجد كمية متوفر للصنف المحدد[ {} ][ "
                                                          "{} ] .. الكمية المتوفره للصنف [ {} ]".format(
                                        line.product_id.name, line.product_id.default_code, aval_qty))

    def action_register_payment(self):
        for rec in self:
            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.entry_card_id.id),('work_order_id','=', rec.id)])

            action = self.env.ref('qimamhd_mizan_car_13.action_mizan_payment_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', 'in', payment.ids)]
            return result

    def register_payment(self):
        advanced_amount = 0
        remaining_amount = 0
        for rec in self:
            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.entry_card_id.id),('work_order_id','=', rec.id)])
 

            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            # if advanced_amount >= rec.total_all_with_tax:
            #     raise ValidationError(
            #         "اكتمل الدفع لامر العمل .. لا يمكن انشاء مفوعات جديدة ")

            remaining_amount = rec.total_all_with_tax - advanced_amount

            return {
                'name': _('Register Payment'),
                'view_mode': 'form',
                'res_model': 'mizan.register.payment',
                'view_id': self.env.ref('qimamhd_mizan_car_13.mizan_payment_view').id,
                'type': 'ir.actions.act_window',
                'context': {'default_invoice_amount': rec.total_all_with_tax,
                            'default_advanced_amount': advanced_amount,
                            'default_remaining_amount': remaining_amount, 'default_branch_id': rec.entry_card_id.branch_id.id,
                            'default_payment_note': "دفعة مقدمة لامر العمل",

                            'default_header_id': rec.entry_card_id.id, 'default_work_order_id': rec.id, 'default_payment_amount': remaining_amount if remaining_amount else 0,
                            },
                'target': 'current'
            }

    def get_price_of_product(self, product_id):
        for rec in self:
           
            if product_id:
                price = 0.00
                if rec.use_pricelist:
                    pricelist = self.env['product.pricelist'].search(
                        [('branch_id', '=', rec.entry_card_id.branch_id.id)])
                  
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
            
            if not rec.additional_services:
                if rec.total_all_with_tax :
                    message = "اجمالي المبلغ المستحق هو  [ %s ] .. هل تريد الاستمرار " % round(rec.total_all_with_tax,2)
                    message_en = " Total amount will be [ %s ] >> do you want to continue " % round(rec.total_all_with_tax,2)

                    action = self.env.ref('qimamhd_mizan_car_13.message_confirm_action')
                    result = action.read()[0]
                    result.pop('id', None)
                    result['context'] = {'default_desc':message_en + message}
                    return result

                else:
                    raise ValidationError("تنبيه: خطأ في اجمالي الخدمات وقطع الغيار ")
            else:
                message = "اجمالي المبلغ المستحق هو  [ %s ] .. هل تريد الاستمرار " % rec.total_all_with_tax
                message_en = " Total amount will be [ %s ] >> do you want to continue " % rec.total_all_with_tax

                action = self.env.ref('qimamhd_mizan_car_13.message_confirm_action')
                result = action.read()[0]
                result.pop('id', None)
                result['context'] = {'default_desc': message_en + message}
                return result


class xx_car_checkup_sub_lines_line_add(models.Model):
    _name = 'mizan.car.work.procedure.line'

    _description = 'Car work order line'

    # def _get_default_technical_emp(self):
    #     company_id = self.env.context.get('default_company_id', self.env.company.id)
    #a
    #     return [('technical_emp', '=', True), ('branch_id', '=', self.env.user.allowed_branch_ids.ids),
    #             ('company_id', '=', company_id)]

    sequence = fields.Integer(string="التسلسل", default=12)
    product_id = fields.Many2one('product.product', string="المنتج", copy=False, required=True,
                                      domain=[('discount_product_flag','!=',True),('type','!=','product')])
    name = fields.Char(string="وصف الفحص", copy=False, required=True)
    branch_id = fields.Integer(copy=False,
                               default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    discount_type = fields.Selection([('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم",
                                     default='percentage')
    discount_line = fields.Float(string="الخصم")
    discount_amount = fields.Float(string="مبلغ الخصم")
 

    tax_id = fields.Integer(default=lambda self: self._default_tax_id(),
                                         compute="_get_tax_id")

    product_tax =  fields.Many2one('account.tax',string="الضريبة",domain="[('id','=',tax_id)]")
    amount_tax = fields.Float()
    total = fields.Float(string="الاجمالي", compute="_calc_total", readonly=True)
    total_before_tax = fields.Float(string="الاجمالي قبل الضريبة", compute="_calc_total", readonly=True)

    total_tax = fields.Float(string="الاجمالي بعد الضريبة", compute="_calc_total", readonly=True)

    technical_name = fields.Many2many('hr.technical.assignments',string="اسم الفني",domain="[('branch_id','=', branch_id),('state','=', 'current')]")
    unit_price = fields.Float(string="السعر",required=True)
    is_guarantee_flag = fields.Boolean(default=False)
    product_has_guarantee_flag = fields.Boolean(string="الضمان",default=False)

    notes = fields.Char(string="الملاحظات")
    header_id = fields.Many2one('mizan.car.work.procedure.master', ondelete='cascade')
    technical_is_done = fields.Many2one('hr.technical.assignments',string=" اعتمد بواسطة",)
    technical_is_started = fields.Many2one('hr.technical.assignments',string="بدأ بواسطة")
    state = fields.Selection([('complete',' completed / مكتمل'),('started','started / البدء')],string="الحالة")
    complete_date = fields.Datetime(string="تاريخ ووقت الاكتمال")
    start_Service_date = fields.Datetime(string="تاريخ ووقت البدء")
    diff_times = fields.Char(string="فتره الانجاز(ساعة)",compute="get_diff_times")
    _sql_constraints = [
        ('product_id_uniq', 'unique(product_id,header_id)',
         ' مكرر لا يمكن الاستمرار'),

    ]
    
    
    @api.depends('start_Service_date','complete_date')
    def get_diff_times(self):
        for rec in self:
            if rec.start_Service_date and rec.complete_date:
               
                # if rec.start_Service_date >= rec.complete_date:
                    time_difference =  rec.complete_date - rec.start_Service_date
                    print("time_difference",time_difference)
                    
                    print("time_difference",time_difference.total_seconds())
                    
                    days, seconds = time_difference.days, time_difference.seconds
                    hours = days * 24 + seconds // 3600
                    minutes = (seconds % 3600) // 60
                    seconds = seconds % 60
                    rec.diff_times ="ساعة [%s] و [%s] دقيقة" % (hours,minutes)
                # else:
                #     rec.diff_times = False
            else:
                 rec.diff_times = False
            
    
    @api.model
    def _default_branch_id(self):
        for rec in self:
            return rec.header_id.entry_card_id.branch_id.id

    @api.depends('header_id')
    def _get_branch_id(self):
        for rec in self:
            if rec.header_id:
                rec.branch_id = rec.header_id.entry_card_id.branch_id.id
            else:
                rec.branch_id = 0

    @api.model
    def _default_tax_id(self):
        for rec in self:
            rec.tax_id = rec.product_id.taxes_id.id

    def _get_tax_id(self):
        for rec in self:
            rec.tax_id = rec.product_id.taxes_id.id

    @api.onchange('product_id')
    def get_product_tax(self):
        for rec in self:
            rec.product_tax = rec.product_id.taxes_id.id

    @api.onchange('product_has_guarantee_flag')
    def check_guarantee(self):
        for rec in self:
            if not rec.product_has_guarantee_flag:
                if rec.name:
                    rec.write({'name': rec.name + '[غير خاضع للضمان]'})
            else:
                if rec.product_id:
                   rec.write({'name': rec.product_id.name})

    @api.depends('unit_price', 'discount_line', 'discount_type','product_tax')
    def _calc_total(self):
        for rec in self:
            if rec.discount_type == 'percentage':
                rec.total = (rec.unit_price) - ((rec.unit_price) * (rec.discount_line / 100))
                rec.discount_amount = ((rec.unit_price) * (rec.discount_line / 100))

            elif rec.discount_type == 'amount':
                rec.total = (rec.unit_price) - (rec.discount_line)
                rec.discount_amount = (rec.discount_line)

            else:
                rec.total = (rec.unit_price)
                rec.discount_amount = 0

            if rec.product_tax:
                if rec.product_tax.price_include:
                    rec.total_before_tax = round((rec.total / 1.15), 2)
                else:
                    rec.total_before_tax = round(rec.total, 2)

            else:
                rec.total_before_tax = rec.total

            if rec.product_tax:
                if rec.product_tax.price_include:
                   rec.total_tax = round(rec.total ,2)
                else:
                   rec.total_tax = round(rec.total + (rec.total * 0.15),2)

                rec.amount_tax = abs(rec.total_before_tax - rec.total_tax)
            else:
                rec.total_tax = rec.total
                rec.amount_tax = abs(rec.total_before_tax - rec.total_tax)



    @api.onchange('product_id')
    def set_name(self):
        for rec in self:
           

            rec.name = rec.product_id.name
            rec.unit_price = rec.header_id.get_price_of_product(rec.product_id)

            if rec.product_id:
                if rec.header_id.is_guarantee:
                    if rec.name:
                        if not rec.product_id.guarantee_able and not rec.product_id.guarantee_product:
                            rec.write({'name': rec.name + '[غير خاضع للضمان]'})
                        if rec.product_id.guarantee_able:
                            rec.write({'product_has_guarantee_flag': True})
    
    # def diff_start_compelete_date_time(self):
    #     for rec in self:
            


class xx_car_checkup_spare_parts_lines(models.Model):
    _name = 'mizan.car.spare.parts.lines'

    _description = 'Car checkup order spare parts Lines'
    # _rec_name = 'cart_part_id'

    # def _get_default_technical_emp(self):
    #     company_id = self.env.context.get('default_company_id', self.env.company.id)
    #
    #     return [('technical_emp', '=', True), ('branch_id', '=', self.env.user.allowed_branch_ids.ids),
    #             ('company_id', '=', company_id)]

    sequence = fields.Integer(string="التسلسل", default=20)

    product_id = fields.Many2one('product.product', string="القطع المستبدلة", required=True,copy=False,domain=[('type','=','product')],)
    name = fields.Char(string="وصف الخدمة", required=True,copy=False)
    branch_id = fields.Integer(copy=False,
                               default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    technical_name = fields.Many2many('hr.technical.assignments',string="اسم الفني",domain="[('branch_id','=', branch_id),('state','=', 'current')]")
    qty = fields.Float(string="الكمية")
    qty_done = fields.Float(string="الكمية الفعلية")
    unit_price = fields.Float(string="السعر")
    discount_type = fields.Selection([('amount','مبلغ'),('percentage','نسبة')],string="نوع الخصم", default= 'percentage')
    discount_line = fields.Float(string="الخصم")
    discount_amount = fields.Float(string="مبلغ الخصم")

    tax_id = fields.Integer(default=lambda self: self._default_tax_id(),
                            compute="_get_tax_id")

    product_tax = fields.Many2one('account.tax', string="الضريبة", domain="[('id','=',tax_id)]")
    amount_tax = fields.Float()

    total = fields.Float(string="الاجمالي", compute="_calc_total", readonly=True)
    total_before_tax = fields.Float(string="الاجمالي قبل الضريبة", compute="_calc_total", readonly=True)

    total_tax = fields.Float(string="الاجمالي بعد الضريبة", compute="_calc_total", readonly=True)

    stock_picking_id = fields.Many2one('stock.picking')
    unit_cost = fields.Float(compute="_calc_total", string="التكلفة")
    aval_qty = fields.Float(compute="_calc_total", string="الكمية المتوفرة")

    notes = fields.Char(string="الملاحظات")

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True,
        required=True, related='header_id.user_id')


    header_id = fields.Many2one('mizan.car.work.procedure.master',ondelete='cascade')

    _sql_constraints = [
        ('product_id_uniq', 'unique(product_id,header_id)',
         ' مكرر لا يمكن الاستمرار'),

    ]

    @api.model
    def _default_branch_id(self):
        for rec in self:
            return rec.header_id.entry_card_id.branch_id.id

    @api.depends('header_id')
    def _get_branch_id(self):
        for rec in self:
            if rec.header_id:
                rec.branch_id = rec.header_id.entry_card_id.branch_id.id
            else:
                rec.branch_id = 0



    @api.model
    def _default_tax_id(self):
        for rec in self:
            rec.tax_id = rec.product_id.taxes_id.id

    def _get_tax_id(self):
        for rec in self:
            rec.tax_id = rec.product_id.taxes_id.id

    @api.onchange('product_id')
    def get_product_tax(self):
        for rec in self:
            rec.product_tax = rec.product_id.taxes_id.id


    @api.onchange('qty','qty_done')
    def check_qty_done(self):
        for rec in self:
             if rec.qty_done > rec.qty:
                 raise ValidationError(
                     "تنبيه .. الكمية الفعلية للصنف (%s) اكبر من الكمية المصروفة من المستودع " % (
                         rec.product_id.name))

    @api.constrains('qty', 'qty_done')
    def check_qty_done(self):
        for rec in self:
         

            if rec.qty_done > rec.qty:
                raise ValidationError(
                    "تنبيه .. الكمية الفعلية للصنف (%s) اكبر من الكمية المصروفة من المستودع " % (
                        rec.product_id.name))

    # @api.onchange('unit_price')
    # def ck_price_of_product(self):
    #     for rec in self:
    #         if rec.product_id and rec.unit_price:
    #             rec.product_id.product_tmpl_id.check_product_price_from_cost(rec.unit_price)


    @api.depends('qty_done','unit_price', 'discount_line', 'discount_type', 'product_tax','aval_qty','unit_cost')
    def _calc_total(self):
        for rec in self:
      

            prod_id = ("product.product" + "," + str(rec.product_id.id))
            rec.unit_cost = self.env['ir.property'].search([('res_id', '=', prod_id)]).value_float

            qty = 0.00
            if rec.product_id:
                whs_id = self.env['stock.warehouse'].search(
                    [('branch_id', '=', rec.header_id.entry_card_id.branch_id.id)], limit=1)
                sql_query = "select COALESCE(sum(quantity), 0::numeric) as qty from stock_quant a where a.product_id = {} and location_id in (" \
                            "select ld.id from stock_warehouse w, stock_location ls ,stock_location ld " \
                            "where w.id={} and w.code=ls.name and ls.id=ld.location_id and ld.active=true)".format(
                                    rec.product_id.id, whs_id.id)

                self.env.cr.execute(sql_query)
                qty = self.env.cr.fetchone()[0]

            rec.aval_qty = qty

            if rec.discount_type == 'percentage':
                rec.total = (rec.qty_done *rec.unit_price) - ((rec.qty_done * rec.unit_price) * (rec.discount_line / 100))
                rec.discount_amount = ((rec.qty_done * rec.unit_price) * (rec.discount_line / 100))

            elif rec.discount_type == 'amount':
                rec.total = (rec.qty_done * rec.unit_price) - (rec.discount_line)
                rec.discount_amount = (rec.discount_line)

            else:
                rec.total = (rec.qty_done * rec.unit_price)
                rec.discount_amount = 0

            if rec.product_tax:
                if rec.product_tax.price_include:
                    rec.total_before_tax = round((rec.total / 1.15), 2)
                else:
                    rec.total_before_tax = round(rec.total, 2)

            else:
                rec.total_before_tax = rec.total

            if rec.product_tax:
                if rec.product_tax.price_include:
                    rec.total_tax = round(rec.total, 2)
                else:
                    rec.total_tax = round(rec.total + (rec.total * 0.15), 2)

                rec.amount_tax = abs(rec.total_before_tax - rec.total_tax)
            else:
                rec.total_tax = rec.total
                rec.amount_tax = abs(rec.total_before_tax - rec.total_tax)


    @api.onchange('product_id')
    def set_name1(self):
        for rec in self:
           

            if rec.product_id:
                rec.name = rec.product_id.name
                rec.unit_price = rec.header_id.get_price_of_product(rec.product_id)

    # def unlink(self):
    #     for rec in self:
    #         if not rec.header_id.is_user_supervisor:
    #             raise ValidationError(
    #                 "تنبيه .. حذف القطعة المستبدلة (%s) عبر المشرف " % (
    #                     rec.product_id.name))
    #
    #     return super(xx_car_checkup_spare_parts_lines, self).unlink()


class xx_checkup_register_payment(models.Model):
    _inherit = 'mizan.register.payment'

    def create_payment_wo(self):
        for rec in self:
            if rec.payment_amount <= 0:
                raise ValidationError(
                    "يجب تحديد المبلغ اولا")

            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.id),('work_order_id','=', rec.header_id.work_order_id.id)])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount

            # if advanced_amount > rec.header_id.work_order_id.total_all_with_tax:
            #     raise ValidationError(
            #         "اكتمل الدفع لامر العمل .. لا يمكن انشاء مفوعات جديدة ")
            #
            # if rec.payment_amount > rec.remaining_amount:
            #         raise ValidationError(
            #             "المبلغ المدفوع اكبر من المبلغ المتبقي.. لا يمكن انشاء مفوعات جديدة ")

            self.inbound_payment_method = self.env['account.payment.method'].create({
                'name': 'inbound',
                'code': 'IN',
                'payment_type': 'inbound',
            })
            payment = self.env['account.payment'].create({
                'payment_date': self.pay_date,
                'payment_method_id': self.inbound_payment_method.id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.header_id.partner_id.id,
                'amount': self.payment_amount,
                'journal_id': self.journal_id.id,
                'company_id': self.header_id.company_id.id,
                'branch_id': self.header_id.branch_id.id,
                'currency_id': self.env.company.currency_id.id,
                'payment_difference_handling': 'reconcile',
                'communication': self.payment_note,
                'entry_card_id': self.header_id.id,
                'work_order_id': self.header_id.work_order_id.id,
                  })
            payment.post()
            self.write({'state': 'posted'})

            payment = self.env['mizan.register.payment'].search([('header_id', '=', rec.header_id.id),('work_order_id','=', rec.header_id.work_order_id.id)])
            advanced_amount = 0
            for line in payment:
                advanced_amount = advanced_amount + line.payment_amount



            wo = self.env['mizan.car.work.procedure.master'].search([('id', '=', rec.header_id.work_order_id.id)])

            wo.write({'advance_amount': advanced_amount})
