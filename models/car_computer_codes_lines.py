# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class mizan_car_computer_codes_lines(models.Model):
    _name = 'mizan.car.computer.codes.lines'

    _description = 'Car checkup order computer codes Lines'
    sequence = fields.Integer(string="التسلسل", default=14)

    computer_code = fields.Many2one('mizan.computers.codes', domain=[('active_code','=', False)] , string="الكود", required=True,copy=False)
    desc_ar = fields.Char(string="الوصف بالعربي")
    desc_en = fields.Char(string="الوصف بالانجليزي")
    notes = fields.Char(string="الملاحظات")
    header_id = fields.Many2one('mizan.car.checkup.procedure.master',ondelete='cascade')

    _sql_constraints = [
        ('computer_code_uniq', 'unique(computer_code,header_id)',
         ' مكرر لا يمكن الاستمرار'),]


    @api.onchange('computer_code')
    def get_desc(self):
        for rec in self:
            rec.desc_ar = rec.computer_code.desc_ar if rec.computer_code.desc_ar else False
            rec.desc_en = rec.computer_code.desc_en if rec.computer_code.desc_en else False
            rec.notes = rec.computer_code.notes if rec.computer_code.notes else False

