# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class xx_services_types(models.Model):
    _name = 'mizan.services.types'

    _rec_name = 'name'


    name = fields.Char(string="الاسم")
    en_name = fields.Char(string="الاسم الانجليزي")

    price = fields.Float(string="السعر")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    product_id = fields.Many2one('product.product', string="تحديد الصنف المطابق للخدمة لانشاء امر البيع")
    # service_areas_lines = fields.One2many('mizan.services.types.areas.lines','header_id',ondelete='cascade')

#
# class xx_services_with_areas(models.Model):
#     _name = 'mizan.services.types.areas.lines'
#
#     _rec_name = 'service_rela_area_id'
#
#     service_rela_area_id = fields.Many2one('mizan.service.areas.relation', string="منطقة الخدمة",required=True)
#     header_id = fields.Many2one('mizan.services.types',ondelete='cascade')
#
#     _sql_constraints = [
#         ('serv_types_areas_lines_uniq', 'unique(service_area_id,header_id)',
#          ' مكرر لا يمكن الاستمرار'),
#     ]
#
# class xx_car_category(models.Model):
#     _name = 'mizan.service.areas'
#
#     _rec_name = 'name'
#
#     name = fields.Char(string="الاسم")
#     en_name = fields.Char(string="الاسم الانجليزي")
#     area_image = fields.Binary(string="الرمز")
#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
#
# class xx_service_areas_relation(models.Model):
#     _name = 'mizan.service.areas.relation'
#
#     _rec_name = 'service_area_id'
#
#     service_area_id = fields.Many2one('mizan.service.areas',string="منطقة الخدمة",required=True)
#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
#     # product_id = fields.Many2one('product.product', string="تحديد الصنف المطابق لمنطقة الخدمة لانشاء امر البيع")
#     parent_id = fields.Many2one('mizan.service.areas.relation', string="منطقة الخدمة الرئيسي")
#     have_parts = fields.Boolean(string="يحتوي على نتائج فحص")
#     parts_lines = fields.One2many('mizan.service.areas.lines','header_id',ondelete='cascade')
#     technicals_lines = fields.One2many('mizan.service.areas.technicals','header_id',ondelete='cascade')
#
#     _sql_constraints = [
#         ('areas_relation_uniq', 'unique(service_area_id,parent_id)',
#          ' مكرر لا يمكن الاستمرار'),
#         ('areas_relation1_uniq', 'unique(service_area_id,parent_id,have_parts)',
#          ' مكرر لا يمكن الاستمرار')
#     ]

    # @api.onchange('service_area_id')
    # def set_parts(self):
    #     for rec in self:
    #         if rec.service_area_id:
    #             if rec.service_area_id.have_parts:
    #                 rec.write({'have_parts': True})
    #             else:
    #                 rec.write({'have_parts': False})
    #         else:
    #             rec.write({'have_parts': False})


# class technical_area_lines(models.Model):
#     _name = 'mizan.service.areas.technicals'
#
#     _rec_name = 'technical_id'
#
#     branch_id = fields.Many2one('custom.branches', string='الفرع', required=True, copy=False,
#                                 default=lambda self: self.env.user.branch_id.id)
#     technical_id = fields.Many2one('hr.employee', string="اسم الفني",domain="[('technical_emp', '=', True),('branch_id','=', branch_id)]")
#
#     header_id = fields.Many2one('mizan.service.areas.relation',required=True,ondelete='cascade')
#     _sql_constraints = [
#             ('areas_technicals_uniq', 'unique(branch_id,technical_id,header_id)',
#              ' مكرر لا يمكن الاستمرار'),
#
#         ]
#
# class xx_services_areas_parts_lines(models.Model):
#     _name = 'mizan.service.areas.lines'
#
#     _rec_name = 'part_id'
#
#     sequence = fields.Integer(string="التسلسل", default=5)
#
#     part_id = fields.Many2one('mizan.parts',string="الاسم")
#     description = fields.Char(string="الوصف",readonly=True,compute="get_description")
#
#     header_id = fields.Many2one('mizan.service.areas.relation',required=True,ondelete='cascade')
#
#     _sql_constraints = [
#         ('areas_lines_uniq', 'unique(part_id,header_id)',
#          ' مكرر لا يمكن الاستمرار'),
#
#     ]
#
#     # @api.onchange('part_id')
#     def get_description(self):
#         for rec in self:
#             if rec.part_id:
#                 rec.description = rec.part_id.description
#             else:
#                 rec.description = False
#
#
#
# class xx_car_parts(models.Model):
#     _name = 'mizan.parts'
#
#     _rec_name = 'name'
#
#     name = fields.Char(string="الاسم/كود")
#     description = fields.Char(string="الوصف")
#     en_name = fields.Char(string="الاسم الانجليزي")
#
#     company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
#     result_lines = fields.One2many('mizan.parts.main.result.lines','header_id',ondelete='cascade')
#     sub_result_id = fields.One2many('mizan.parts.sub.result.lines','header_id',ondelete='cascade')
#
#
# class xx_car_parts_rs_main_lines(models.Model):
#     _name = 'mizan.parts.main.result.lines'
#
#
#     _rec_name = 'main_result_id'
#
#
#     main_result_id = fields.Many2one('mizan.parts.result.lines',string="نتيجة الفحص",required=True)
#     description = fields.Char(string="الوصف")
#     set_default_result = fields.Boolean(string="نتيجة الافتراضية للفحص")
#
#     header_id = fields.Many2one('mizan.parts',string="نوع الفحص",required=True,ondelete='cascade')
#
#     _sql_constraints = [
#         ('parts_lines_uniq', 'unique(main_result_id,header_id)',
#          ' مكرر لا يمكن الاستمرار'),
#
#     ]


class xx_car_parts_rs_lines(models.Model):
    _name = 'mizan.parts.results'

    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    en_name = fields.Char(string="الاسم الانجليزي")

    _sql_constraints = [
        ('name_uniq', 'unique(name)',
         ' مكرر لا يمكن الاستمرار'),

    ]

# class xx_car_parts_sub_rs_lines(models.Model):
#     _name = 'mizan.parts.sub.result.lines'
#
#     _rec_name = 'name'
#
#     name = fields.Char(string="الاسم")
#     en_name = fields.Char(string="الاسم الانجليزي")
#     header_id = fields.Many2one('mizan.parts',string="نوع الفحص",required=True,ondelete='cascade')


class xx_car_manufactory(models.Model):
    _name = 'mizan.car.manufactory'

    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    car_types_lines = fields.One2many('mizan.car.types','header_id',ondelete='cascade')


class xx_car_types(models.Model):
    _name = 'mizan.car.types'

    _rec_name = 'name'

    name = fields.Char(string="الاسم")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    header_id = fields.Many2one('mizan.car.manufactory',string="الشركة المصنعة", ondelete='cascade')


class xx_car_size(models.Model):
    _name = 'mizan.car.size'

    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    body_image = fields.Binary(string="اختر صورة السيارة لستخدم للفحص في البدي")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

class xx_salesman_agency(models.Model):
    _name = 'mizan.salesman.sides'

    _rec_name = 'name'

    name = fields.Char(string="الاسم")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)


class xx_sales_man(models.Model):
    _name = 'mizan.sales.man'

    _rec_name = 'name'

    name = fields.Char(string="الاسم",required=True)
    sale_man_type = fields.Selection([('external', 'مندوب خارجي'),
                                    ('internal', 'مندوب داخلي')], string='نوع المندوب', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    # branch_id = fields.Many2one('custom.branches', required=True, string="الفرع")
    salesman_side = fields.Many2one('mizan.salesman.sides',  string="جهة المندوب الخارجي")
    sale_user = fields.Many2one('res.users', string='مسئول المبيعات', index=True, track_visibility='onchange',
                                  track_sequence=2)


class xx_computer_c0des(models.Model):
    _name = 'mizan.computers.codes'

    _rec_name = 'name'

    name = fields.Char(string="الكود",required=True)
    desc_ar = fields.Char(string="الوصف بالعربي")
    desc_en = fields.Char(string="الوصف بالانجليزي",required=True)
    active_code = fields.Boolean(string="غير نشط",)
    notes = fields.Char(string="الملاحظات")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

class xx_picking_types(models.Model):
    _name = 'mizan.picking.workstation'

    _rec_name = 'name'

    name = fields.Char(string="الورشة",required=True)
    # branch_id = fields.Many2one('custom.branches', required=True, string="الفرع")
    company_id = fields.Many2one('res.company', required=True,string="الفرع")
