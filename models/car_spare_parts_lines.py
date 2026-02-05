# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class mizan_car_spare_parts_lines(models.Model):
    _name = 'mizan.car.spare.parts.lines'

    _description = 'Car checkup order spare parts Lines'

    sequence = fields.Integer(string="التسلسل", default=20)
    product_id = fields.Many2one('product.product', string="القطع المستبدلة",
                                 required=True, copy=False, domain=[('type', '=', 'product')],)
    name = fields.Char(string="وصف الخدمة", required=True, copy=False)
    company_id = fields.Many2one(
        'res.company', copy=False, default=lambda self: self._default_branch_id(), compute="_get_branch_id")

    technical_name = fields.Many2many('hr.technical.assignments', string="اسم الفني",
                                      domain="[('company_id','=', company_id),('state','=', 'current')]")
    qty = fields.Float(string="الكمية")
    qty_done = fields.Float(string="الكمية الفعلية")
    unit_price = fields.Float(string="السعر")
    discount_type = fields.Selection(
        [('amount', 'مبلغ'), ('percentage', 'نسبة')], string="نوع الخصم", default='percentage')
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

    stock_picking_id = fields.Many2one('stock.picking')
    unit_cost = fields.Float(compute="_calc_total", string="التكلفة")
    aval_qty = fields.Float(compute="_calc_total", string="الكمية المتوفرة")

    notes = fields.Char(string="الملاحظات")

    user_id = fields.Many2one(
        'res.users', string='مدخل البيانات/مسئول المبيعات', readonly=True,
        required=True, related='header_id.user_id')

    header_id = fields.Many2one(
        'mizan.car.work.procedure.master', ondelete='cascade')

    
    _sql_constraints = [
    ('unique_product_id',
     'UNIQUE(product_id,header_id)',
     ' مكرر لا يمكن الاستمرار'),
]

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

  
    @api.onchange('qty_done')
    def set_qty_done(self):
        for rec in self:
            rec.qty = rec.qty_done


    @api.onchange('qty', 'qty_done')
    def check_qty_done(self):
        for rec in self:
            if rec.qty_done > rec.qty:
                raise ValidationError(
                    "تنبيه .. الكمية الفعلية للصنف (%s) اكبر من الكمية المصروفة من المستودع " % (
                        rec.product_id.name))

    @api.constrains('qty', 'qty_done')
    def cons_check_qty_done(self):
        for rec in self:

            if rec.qty_done > rec.qty:
                raise ValidationError(
                    "تنبيه .. الكمية الفعلية للصنف (%s) اكبر من الكمية المصروفة من المستودع " % (
                        rec.product_id.name))

    @api.depends('qty_done', 'unit_price', 'discount_line', 'discount_type', 'product_tax', 'aval_qty', 'unit_cost')
    def _calc_total(self):
        for rec in self:
            prod_id = ("product.product" + "," + str(rec.product_id.id))
            rec.unit_cost = self.env['ir.property'].search(
                [('res_id', '=', prod_id)]).value_float

            qty = 0.00
            if rec.product_id:
                whs_id = self.env['stock.warehouse'].search(
                    [('company_id', '=', rec.header_id.entry_card_id.company_id.id)], limit=1)
                sql_query = "select COALESCE(sum(quantity), 0::numeric) as qty from stock_quant a where a.product_id = {} and location_id in (" \
                            "select ld.id from stock_warehouse w, stock_location ls ,stock_location ld " \
                            "where w.id={} and w.code=ls.name and ls.id=ld.location_id and ld.active=true)".format(
                                rec.product_id.id, whs_id.id)

                self.env.cr.execute(sql_query)
                qty = self.env.cr.fetchone()[0]

            rec.aval_qty = qty

            if rec.discount_type == 'percentage':
                rec.total = (rec.qty_done * rec.unit_price) - \
                    ((rec.qty_done * rec.unit_price) * (rec.discount_line / 100))
                rec.discount_amount = (
                    (rec.qty_done * rec.unit_price) * (rec.discount_line / 100))

            elif rec.discount_type == 'amount':
                rec.total = (rec.qty_done * rec.unit_price) - \
                    (rec.discount_line)
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
                rec.unit_price = rec.header_id.get_price_of_product(
                    rec.product_id)

