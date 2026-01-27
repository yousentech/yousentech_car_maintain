# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class xx_categorys_in_product(models.Model):
    _inherit = 'product.template'

    en_name = fields.Char(string="الاسم بالانجليزي", help='English Name')
    discount_product_flag = fields.Boolean(string="خصم")
    is_checkup_product = fields.Boolean(string="صنف فحص")
    guarantee_product = fields.Boolean(string="صنف ضمان")

    guarantee_able = fields.Boolean(string="خاضع للضمان")

    results_lines = fields.One2many('mizan.default.results', 'product_id',
                                    string="النتائج الافتراضية")
    # results_lines = fields.One2many('mizan.default.results.product', 'product_id',
    #                                               string="النتائج الافتراضية")


# class xx_mizan_product_results_lines(models.Model):
#     _name = 'mizan.default.results.product'
#
#     checkup_part_result_id = fields.Many2one('mizan.parts.results', string="نتيجة الفحص",
#                                               copy=False, required=True)
#
#     product_service_id = fields.Many2one('product.product', string="الخدمة المنجزة",
#                                          domain=[('discount_product_flag', '!=', True), ('type', '!=', 'product')],
#                                          copy=False, required=True)
#
#     default_result = fields.Boolean(string="النتيجة الافتراضية")
#
#     product_id = fields.Many2one('product.template')

#
# class xx_product_services_lines(models.Model):
#     _name = 'mizan.default.product.services'
#
#
#     product_id = fields.Many2one('product.template')


    def check_product_price_from_cost(self, sale_price,cost):
        self.ensure_one()
        if sale_price < cost:
            raise ValidationError(_("Sale price must be greater than product cost!"))

class xx_mizan_product_results_lines2(models.Model):
    _name = 'mizan.default.results'

    _rec_name = "checkup_part_result_id"

    checkup_part_result_id = fields.Many2one('mizan.parts.results', string="نتيجة الفحص",
                                              copy=False, required=True)

    product_service_id = fields.Many2one('product.product', string="الخدمة المنجزة",
                                         domain=[('discount_product_flag', '!=', True), ('detailed_type', '!=', 'product')],
                                         copy=False, required=True)

    default_result = fields.Boolean(string="النتيجة الافتراضية")

    product_id = fields.Many2one('product.template')
