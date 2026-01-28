# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError

class product_template(models.Model):
    _inherit = 'product.template'

    en_name = fields.Char(string="الاسم بالانجليزي", help='English Name')
    discount_product_flag = fields.Boolean(string="خصم")
    is_checkup_product = fields.Boolean(string="صنف فحص")
    guarantee_product = fields.Boolean(string="صنف ضمان")

    guarantee_able = fields.Boolean(string="خاضع للضمان")

    results_lines = fields.One2many('mizan.default.results', 'product_id',
                                    string="النتائج الافتراضية")
 
    def check_product_price_from_cost(self, sale_price,cost):
        self.ensure_one()
        if sale_price < cost:
            raise ValidationError(_("Sale price must be greater than product cost!"))

