# -*- coding: utf-8 -*-
"""Optional category cost-plus pricing for workshop spare parts."""
from odoo import api, fields, models


class ProductCategoryWorkshopMarkup(models.Model):
    _inherit = 'product.category'

    workshop_markup_enabled = fields.Boolean(string='تفعيل زيادة سعر قطع الغيار')
    workshop_markup_percent = fields.Float(string='نسبة الزيادة فوق التكلفة (%)', default=0.0)

    @api.constrains('workshop_markup_percent')
    def _check_workshop_markup_percent(self):
        from odoo.exceptions import ValidationError
        for category in self:
            if category.workshop_markup_percent < 0:
                raise ValidationError('نسبة الزيادة فوق التكلفة لا يمكن أن تكون سالبة.')


class WorkshopSparePartMarkup(models.Model):
    _inherit = 'mizan.car.spare.parts.lines'

    markup_applied = fields.Boolean(string='تسعير حسب الفئة', copy=False, readonly=True)
    markup_percent_snapshot = fields.Float(string='نسبة الزيادة المطبقة (%)', copy=False, readonly=True)
    markup_cost_snapshot = fields.Float(string='التكلفة وقت التسعير', copy=False, readonly=True)

    @api.onchange('product_id')
    def set_name1(self):
        result = super().set_name1()
        for line in self:
            product = line.product_id
            if not product:
                line.markup_applied = False
                line.markup_percent_snapshot = 0
                line.markup_cost_snapshot = 0
                continue
            category = product.categ_id
            if category.workshop_markup_enabled:
                cost = product.with_company(line.company_id or self.env.company).standard_price
                percentage = category.workshop_markup_percent
                line.unit_price = cost * (1 + percentage / 100.0)
                line.markup_applied = True
                line.markup_percent_snapshot = percentage
                line.markup_cost_snapshot = cost
            else:
                line.markup_applied = False
                line.markup_percent_snapshot = 0
                line.markup_cost_snapshot = 0
        return result
