# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
class stock_move(models.Model):
    _inherit = 'stock.move'

    unit_price = fields.Float(string="سعر البيع")
    total = fields.Float(compute="_calc_total", string="الاجمالي")
    unit_cost = fields.Float(compute="_calc_total", string="التكلفة")
    aval_qty = fields.Float(compute="_calc_total", string="الكمية المتوفرة")


    @api.depends('unit_price', 'quantity', 'product_qty', 'product_id', 'unit_cost', 'product_uom_qty')
    def _calc_total(self):
        for rec in self:
            rec.total = rec.product_uom_qty * rec.unit_price
            if rec.product_id and rec.picking_id.picking_type_id.code == 'outgoing':
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.picking_id.location_id.id), ])
                rec.aval_qty = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
              
            else:
                rec.aval_qty = 0.0

    @api.onchange('unit_price')
    def chk_price_of_product(self):
        for rec in self:
            if rec.product_id and rec.unit_price:
                rec.product_id.product_tmpl_id.check_product_price_from_cost(
                    rec.unit_price, rec.unit_cost)

 