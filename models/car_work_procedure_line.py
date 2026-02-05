# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class mizan_car_work_procedure_line(models.Model):
    _name = 'mizan.car.work.procedure.line'
    _description = 'Car work order line'

    sequence = fields.Integer(string="التسلسل", default=12)
    product_id = fields.Many2one('product.product', string="المنتج", copy=False, required=True,
                                 domain=[('discount_product_flag', '!=', True), ('detailed_type', '!=', 'product')])
    name = fields.Char(string="وصف الفحص", copy=False, required=True)

    company_id = fields.Many2one(
        'res.company', copy=False, default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    discount_type = fields.Selection([('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم",
                                     default='percentage')
    discount_line = fields.Float(string="الخصم")
    discount_amount = fields.Float(string="مبلغ الخصم")

    tax_id = fields.Integer(default=lambda self: self._default_tax_id(),
                            compute="_get_tax_id")

    product_tax = fields.Many2one(
        'account.tax', string="الضريبة", domain="[('id','=',tax_id)]")
    amount_tax = fields.Float()
    total = fields.Float(
        string="الاجمالي", compute="_calc_total", readonly=True)
    total_before_tax = fields.Float(
        string="الاجمالي قبل الضريبة", compute="_calc_total", readonly=True)

    total_tax = fields.Float(
        string="الاجمالي بعد الضريبة", compute="_calc_total", readonly=True)

    technical_name = fields.Many2many('hr.technical.assignments', string="اسم الفني",
                                      domain="[('company_id','=', company_id),('state','=', 'current')]")
    unit_price = fields.Float(string="السعر", required=True)
    is_guarantee_flag = fields.Boolean(default=False)
    product_has_guarantee_flag = fields.Boolean(string="الضمان", default=False)

    notes = fields.Char(string="الملاحظات")
    header_id = fields.Many2one(
        'mizan.car.work.procedure.master', ondelete='cascade')
    technical_is_done = fields.Many2one(
        'hr.technical.assignments', string=" اعتمد بواسطة",)
    technical_is_started = fields.Many2one(
        'hr.technical.assignments', string="بدأ بواسطة")
    state = fields.Selection(
        [('complete', ' completed / مكتمل'), ('started', 'started / البدء')], string="الحالة")
    complete_date = fields.Datetime(string="تاريخ ووقت الاكتمال")
    start_Service_date = fields.Datetime(string="تاريخ ووقت البدء")
    diff_times = fields.Char(
        string="فتره الانجاز(ساعة)", compute="get_diff_times")
 
    _sql_constraints = [
    ('unique_product_id',
     'UNIQUE(product_id,header_id)',
     ' مكرر لا يمكن الاستمرار'),
]
    @api.depends('start_Service_date', 'complete_date')
    def get_diff_times(self):
        for rec in self:
            if rec.start_Service_date and rec.complete_date:
                time_difference = rec.complete_date - rec.start_Service_date
                days, seconds = time_difference.days, time_difference.seconds
                hours = days * 24 + seconds // 3600
                minutes = (seconds % 3600) // 60
                seconds = seconds % 60
                rec.diff_times = "ساعة [%s] و [%s] دقيقة" % (hours, minutes)

            else:
                rec.diff_times = False

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

    @api.depends('unit_price', 'discount_line', 'discount_type', 'product_tax')
    def _calc_total(self):
        for rec in self:
            if rec.discount_type == 'percentage':
                rec.total = (rec.unit_price) - ((rec.unit_price)
                                                * (rec.discount_line / 100))
                rec.discount_amount = (
                    (rec.unit_price) * (rec.discount_line / 100))

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
                    rec.total_tax = round(rec.total, 2)
                else:
                    rec.total_tax = round(rec.total + (rec.total * 0.15), 2)

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
