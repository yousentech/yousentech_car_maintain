# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class mizan_car_entry_card_master(models.Model):
    _name = 'mizan.car.entry.card.master'
    _inherit = ['mail.thread']

    _description = 'Car checkup order master'
    _rec_name = 'seq'

    
    def _get_default_supervisor(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return [('supervisor_emp', '=', True), ('company_id', 'in',  self.env.companies.ids),
            ('company_id', '=', company_id)]


    seq = fields.Integer(
        string='رقم العملية',
        copy=False,
        readonly=True,
        default=lambda self: self._get_sequence(),)

    def _get_sequence(self):
        branch_id = self.env.user.company_id.id
        if branch_id:
            sql_query = "select max(COALESCE(seq,0)) as seq from mizan_car_entry_card_master where company_id=%s" % (branch_id)

            self.env.cr.execute(sql_query)
            seq = self.env.cr.fetchone()
            x = seq[0]
            if x:
                x = x + 1
                return (x)
            else:
                x = 1
                return (x)


    order_date = fields.Date(string="تاريخ الطلب", required=True, default=fields.Date.today,copy=False)
    complete_done_date = fields.Date(string="تاريخ انجاز العمل",copy=False)
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    execute_done = fields.Boolean()
    drum_counter = fields.Char(string="عداد طبلون")
    partner_mobile = fields.Char(string="رقم الجوال")
    gear_type = fields.Selection([('auto_gear', 'تماتيك'), ('manual', 'عادي')], string="نوع الجير")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس",)
    car_model = fields.Char(string="الموديل")
    car_manuf_id = fields.Many2one('mizan.car.manufactory', string="الشركة المصنعة")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة",domain="[('header_id','=', car_manuf_id)]")
    lines_payment = fields.One2many('mizan.register.payment', 'header_id', required=True,
                                    domain="[('company_id', '=', company_id)]")

    vin_no = fields.Char(string="رقم الشاصي")
    state = fields.Selection([('draft', 'مرحلة الاعداد'),('confirm', 'مرحلة التاكيد'),
                               ('execute_started', 'بدء الفحص'), ('work_order_started', 'امر العمل'),
                              ('execute_completed', 'اكتمال التنفيذ'), ('not_checkup_car', 'الخروج بدون فحص'),
                              ('return_to_modify', 'استعادة للتعديل'),
                               ('cancel_order', 'ملغي امر التركيب')

                              ], default='draft', readonly=True,copy=False)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    supervisor_name = fields.Many2one('hr.supervisor.assignments',string="اسم المشرف",copy=False,domain="[('company_id','=', company_id),('state','=', 'current')]")

    is_user_technical = fields.Boolean(default=lambda self: self._default_user_technical(),compute="_user_technical_edit_mode")

    is_user_supervisor = fields.Boolean(default=lambda self: self._default_user_supervisor(),
                                             compute="_user_supervisor_edit_mode")
    is_user_sale_man = fields.Boolean(default=lambda self: self._default_user_sale_man(), compute="_user_sale_man_edit_mode")
    
    partner_id = fields.Many2one('res.partner', string="العميل", required=True,)
    sale_man_id = fields.Many2one('mizan.salesman.assignments', string="المندوب",copy=False,domain="[('company_id','=', company_id),('state','=', 'current')]")
    commission = fields.Float(string="عمولة الفحص")
    pay_type = fields.Selection([('cash','نقدا'),('bank','بنكي'),('transfer','تحويل')],string="طريقة الدفع")
    checkup_id = fields.Many2one('mizan.car.checkup.procedure.master', string="الفحص",copy=False)
    maint_wo_id = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل",copy=False)

    @api.onchange('partner_id','car_panel_no','partner_mobile','car_size_id','car_model','car_type_id','vin_no','sale_man_id')
    def update_data(self):
        for rec in self:
            if rec.partner_id:
                if rec.maint_wo_id.sale_order_id:
                    raise ValidationError(
                        "تنبيه... لا يمكن تعديل البيانات لوجود امر بيع على هذا الفحص")

                if rec.checkup_id:
                    rec.checkup_id.write({ 'partner_id': rec.partner_id.id,
                     'car_panel_no': rec.car_panel_no,
                    'partner_mobile': rec.partner_mobile,
                    'car_size_id': rec.car_size_id.id,
                    'car_model': rec.car_model,
                    'car_type_id': rec.car_type_id.id,
                     'vin_no': rec.vin_no,
                    'sale_man_id': rec.sale_man_id.id,})

                if rec.maint_wo_id:
                   rec.maint_wo_id.write({ 'partner_id': rec.partner_id.id,
                     'car_panel_no': rec.car_panel_no,
                    'partner_mobile': rec.partner_mobile,
                    'car_size_id': rec.car_size_id.id,
                    'car_model': rec.car_model,
                    'car_type_id': rec.car_type_id.id,
                     'vin_no': rec.vin_no,
                    'sale_man_id': rec.sale_man_id.id, })

    @api.onchange('company_id')
    def _default_customer(self):
        for rec in self:
            default_cus = self.env['res.partner'].search([('company_id','=', rec.company_id.id),('category_id.name','=', 'DC')],limit=1)
 
            if default_cus:
                rec.partner_id= default_cus.id
  
    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True,copy=False,
        required=True, default=lambda self: self.env.uid)


    _sql_constraints = [
        ("sequence_by_branch_unique",
         "UNIQUE(seq, company_id)",
         "لا يمكن تكرار رقم العملية"),
    ]

    compelete_done_date_not_required_flag = fields.Boolean(
        default=lambda self: self._default_compelete_done_date_not_required_flag(),
        compute="_get_compelete_done_date_not_required_flag")

    def _get_compelete_done_date_not_required_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_compelete_done_date_not_required = params.get_param('compelete_done_date_not_required',
                                                              default=False)
        for rec in self:
            rec.compelete_done_date_not_required_flag = l_compelete_done_date_not_required

    def _default_compelete_done_date_not_required_flag(self):

        params = self.env['ir.config_parameter'].sudo()
        l_compelete_done_date_not_required = params.get_param('compelete_done_date_not_required',
                                                              default=False)

        return l_compelete_done_date_not_required


    car_no_required = fields.Boolean(default=lambda self: self._default_car_no_required_flag(),
                                     compute="_get_car_no_required_flag")

    def _get_car_no_required_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_car_no_required = params.get_param('car_no',
                                             default=False)
        for rec in self:
            rec.car_no_required = l_car_no_required

    def _default_car_no_required_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_car_no_required = params.get_param('car_no',
                                             default=False)
        return l_car_no_required

    vin_no_required = fields.Boolean(default=lambda self: self._default_vin_no_required_flag(),
                                     compute="_get_vin_no_required_flag")

    def _get_vin_no_required_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_vin_no_required = params.get_param('vin_no',
                                             default=False)
        for rec in self:
            rec.vin_no_required = l_vin_no_required

    def _default_vin_no_required_flag(self):
        params = self.env['ir.config_parameter'].sudo()
        l_vin_no_required = params.get_param('vin_no',
                                             default=False)
        return l_vin_no_required

    partner_mobile_not_required = fields.Boolean(default=lambda self: self._default_partner_mobile_required(),
                                         compute="_get_partner_mobile_required")

    def _get_partner_mobile_required(self):
        params = self.env['ir.config_parameter'].sudo()
        l_partner_mobile_not_required = params.get_param('partner_mobile_not_required',
                                             default=False)
 
        for rec in self:
            rec.partner_mobile_not_required = l_partner_mobile_not_required

    def _default_partner_mobile_required(self):
        params = self.env['ir.config_parameter'].sudo()
        l_partner_mobile_not_required = params.get_param('partner_mobile_not_required',
                                             default=False)
 
        return l_partner_mobile_not_required


    car_type_required = fields.Boolean(default=lambda self: self._default_car_type_required(),
                                                 compute="_get_car_type_required")

    def _get_car_type_required(self):
        params = self.env['ir.config_parameter'].sudo()
        l_car_type = params.get_param('car_type',   default=False)
        for rec in self:
            rec.car_type_required = l_car_type

    def _default_car_type_required(self):
        params = self.env['ir.config_parameter'].sudo()
        l_car_type = params.get_param('car_type',         default=False)
 
        return l_car_type

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
        for rec in self:
             rec.is_user_allow_delete = self.user_has_groups('yousentech_car_maintain.group_allow_delete_wo_priv')

    @api.onchange('partner_id')
    def get_partner_mobile(self):
        for rec in self:
            if rec.partner_id:
                rec.write({'partner_mobile': rec.partner_id.mobile})
 
    @api.constrains('partner_mobile')
    def set_line_branch(self):
        if self.partner_mobile:
            self.partner_id.write({'mobile': self.partner_mobile})
 

    def confirm_btn(self):
        for rec in self:
            rec.write({'state': 'confirm'})

    def not_checkup_car(self):
        for rec in self:
            rec.write({'state': 'not_checkup_car'})
            if rec.maint_wo_id:
                rec.maint_wo_id.write({'state': 'not_checkup_car'})
            if rec.checkup_id:
                rec.checkup_id.write({'state': 'not_checkup_car'})


    def return_to_modify(self):
        for rec in self:
            rec.write({'state': 'draft'})

            return {'type': 'ir.actions.client', 'tag': 'reload',}

    def execute_completed(self):
        for rec in self:
            if rec.checkup_id:
                rec.checkup_id.write({'state': 'execute_completed'})
            if rec.maint_wo_id:
                rec.maint_wo_id.write({'state': 'execute_completed'})
            rec.write({'state': 'execute_completed'})


    def unlink(self):
        for rec in self:
            if not rec.is_user_allow_delete or rec.checkup_id or rec.maint_wo_id:
                 raise ValidationError(
                    " تنبيه .. لا يمكن الحذف  لوجود ارتباطات بكرت الدخول او ان المستخدم لاتوجد له صلاحية  ")
        return super(mizan_car_entry_card_master, self).unlink()


    def cancel_order_btn(self):
        for rec in self:
            if not rec.is_user_allow_delete:
                   raise ValidationError(
                    " تنبيه .. لا يمكن الحذف  .. المستخدم لاتوجد له صلاحية  ")
            if rec.checkup_id:
                rec.checkup_id.write({'state': 'cancel_order'})
            if rec.maint_wo_id:
                rec.maint_wo_id.write({'state': 'cancel_order'})
            rec.write({'state': 'cancel_order'})


    def create_checkup_procedure(self):
        for rec in self:
                part_results = self.env['mizan.car.checkup.procedure.master'].search([('entry_card_id','=', rec.id)])
                if not part_results:
                        results_tmp = {
                            'partner_id': rec.partner_id.id,
                            'state': 'execute_started',
                            'car_panel_no': rec.car_panel_no,
                            'partner_mobile': rec.partner_mobile,
                            'car_size_id': rec.car_size_id.id,
                            'car_model': rec.car_model,
                            'car_type_id': rec.car_type_id.id,
                            'entry_card_id': rec.id,
                            'vin_no': rec.vin_no,
                            'sale_man_id': rec.sale_man_id.id,

                        }

                        checkup_procedure = self.env['mizan.car.checkup.procedure.master'].create(results_tmp)
                        rec.write({'checkup_id': checkup_procedure.id})
                        rec.write({'state': 'execute_started'})


                        action = self.env.ref('yousentech_car_maintain.action_car_checkup_procedure_view')
                        result = action.read()[0]
                        result.pop('id', None)
                        result['domain'] = [('entry_card_id', '=', rec.id)]
                        if checkup_procedure:
                            res = self.env.ref('yousentech_car_maintain.checkup_procedure_form_view', False)
                            result['views'] = [(res and res.id or False, 'form')]
                            result['res_id'] = checkup_procedure.id or False

                        return result

    def call_checkup_procedure(self):
        for rec in self:
            checkup_procedure = self.env['mizan.car.checkup.procedure.master'].search([('entry_card_id', '=', rec.id)])
            action = self.env.ref('yousentech_car_maintain.action_car_checkup_procedure_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('entry_card_id', '=', rec.id)]
            if checkup_procedure:
                res = self.env.ref('yousentech_car_maintain.checkup_procedure_form_view', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = checkup_procedure.id or False
            return result


    def call_wo_procedure(self):
        for rec in self:
            wo_procedure = self.env['mizan.car.work.procedure.master'].search([('entry_card_id', '=', rec.id)])
            action = self.env.ref('yousentech_car_maintain.action_work_procedure_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('entry_card_id', '=', rec.id)]
            if wo_procedure:
                res = self.env.ref('yousentech_car_maintain.work_procedure_form_view', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = wo_procedure.id or False
            return result

    def action_register_payment(self):
        for rec in self:
            payment = self.env['mizan.register.payment'].search(
                [('header_id', '=', rec.id)])

            action = self.env.ref('yousentech_car_maintain.action_mizan_payment_view')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('id', 'in', payment.ids)]
            return result


