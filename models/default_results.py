# -*- coding: utf-8 -*-
from odoo import models, fields, _

class mizan_default_results(models.Model):
    _name = 'mizan.default.results'

    _rec_name = "checkup_part_result_id"

    checkup_part_result_id = fields.Many2one('mizan.parts.results', string="نتيجة الفحص",
                                              copy=False, required=True)

    product_service_id = fields.Many2one('product.product', string="الخدمة المنجزة",
                                         domain=[('discount_product_flag', '!=', True), ('detailed_type', '!=', 'product')],
                                         copy=False, required=True)

    default_result = fields.Boolean(string="النتيجة الافتراضية")

    product_id = fields.Many2one('product.template')
