# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class mizan_car_checkup_procedure_line(models.Model):
    _name = 'mizan.car.checkup.procedure.line'

    _description = 'Car checkup order Sub Lines line add'

    selected = fields.Boolean(string="اختيار", default=True)

    company_id = fields.Many2one('res.company',copy=False, related="header_id.entry_card_id.company_id", store=True)
    checkup_part_id = fields.Many2one('product.product', string="نوع /كود الفحص",
                                      copy=False, required=True, domain=[('is_checkup_product', '=', True)])

    sequence = fields.Integer(string="التسلسل", default=12)
    name = fields.Char(string="وصف الفحص", copy=False, required=True)
    technical_name = fields.Many2many('hr.technical.assignments', string="اسم الفني",
                                      domain="[('company_id','=', company_id),('state','=', 'current')]")

    checkup_part_result_id = fields.Many2many('mizan.default.results', string="نتيجة الفحص",
                                              copy=False, domain="[('product_id','=',checkup_part_id)]")

    notes = fields.Char(string="الملاحظات")
    header_id = fields.Many2one(
        'mizan.car.checkup.procedure.master', ondelete='cascade')


    _sql_constraints = [
    ('unique_checkup_part_id',
     'UNIQUE(checkup_part_id,header_id)',
     ' مكرر لا يمكن الاستمرار'),]

    @api.onchange('checkup_part_id')
    def get_default_results(self):
        for rec in self:
            if rec.checkup_part_id:
                rec.write({'name':  rec.checkup_part_id.name})

                for l in rec.checkup_part_id.results_lines:
                    if l.default_result:
                        rec.write({'checkup_part_result_id':  [(4, l.id)]})

            else:
                rec.write({'checkup_part_result_id': False})
