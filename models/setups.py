# -*- coding: utf-8 -*-
from odoo import models, fields, _

class mizan_services_types(models.Model):
    _name = 'mizan.services.types'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    en_name = fields.Char(string="الاسم الانجليزي")
    price = fields.Float(string="السعر")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    product_id = fields.Many2one('product.product', string="تحديد الصنف المطابق للخدمة لانشاء امر البيع")

class mizan_parts_results(models.Model):
    _name = 'mizan.parts.results'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    en_name = fields.Char(string="الاسم الانجليزي")

    _sql_constraints = [
        ('name_uniq', 'unique(name)',
         ' مكرر لا يمكن الاستمرار'),]

class mizan_car_manufactory(models.Model):
    _name = 'mizan.car.manufactory'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    car_types_lines = fields.One2many('mizan.car.types','header_id',ondelete='cascade')


class mizan_car_types(models.Model):
    _name = 'mizan.car.types'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    header_id = fields.Many2one('mizan.car.manufactory',string="الشركة المصنعة", ondelete='cascade')


class mizan_car_size(models.Model):
    _name = 'mizan.car.size'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    body_image = fields.Binary(string="اختر صورة السيارة لستخدم للفحص في البدي")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

class mizan_salesman_sides(models.Model):
    _name = 'mizan.salesman.sides'
    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)


class mizan_sales_man(models.Model):
    _name = 'mizan.sales.man'
    _rec_name = 'name'

    name = fields.Char(string="الاسم",required=True)
    sale_man_type = fields.Selection([('external', 'مندوب خارجي'),
                                    ('internal', 'مندوب داخلي')], string='نوع المندوب', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    salesman_side = fields.Many2one('mizan.salesman.sides',  string="جهة المندوب الخارجي")
    sale_user = fields.Many2one('res.users', string='مسئول المبيعات', index=True, track_visibility='onchange',
                                  track_sequence=2)


class mizan_computers_codes(models.Model):
    _name = 'mizan.computers.codes'
    _rec_name = 'name'

    name = fields.Char(string="الكود",required=True)
    desc_ar = fields.Char(string="الوصف بالعربي")
    desc_en = fields.Char(string="الوصف بالانجليزي",required=True)
    active_code = fields.Boolean(string="غير نشط",)
    notes = fields.Char(string="الملاحظات")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

class mizan_picking_workstation(models.Model):
    _name = 'mizan.picking.workstation'
    _rec_name = 'name'

    name = fields.Char(string="الورشة",required=True)
    company_id = fields.Many2one('res.company', required=True,string="الفرع")
