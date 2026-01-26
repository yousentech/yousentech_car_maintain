# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProductWizard(models.TransientModel):
    _name = 'mizan.product.wizard'
    _description ='Product Wizard'
    ##
    product_ids = fields.Many2many('product.product', string='Products',domain=[('is_checkup_product','=',True)])

    def add_products(self):
        if self._context.get('active_id', False):

            checkup_id = self.env['mizan.car.checkup.procedure.master'].search([('id','=', self._context.get('active_id', False))])
            for product in self.product_ids:
                lines = self.env['mizan.car.checkup.procedure.line'].create({
                    'checkup_part_id': product.id,
                    'name': product.name,
                    'header_id': checkup_id.id,
                })
                lines.get_default_results()