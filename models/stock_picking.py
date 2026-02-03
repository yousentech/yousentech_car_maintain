# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class stock_location(models.Model):
    _inherit = 'stock.location'

    workstation_location_id = fields.Boolean(string="موقع ورشة")


class stock_picking_types(models.Model):
    _inherit = 'stock.picking.type'

    workstation_id = fields.Many2one(
        'mizan.picking.workstation', string="الورشة")


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_branches(self):
        return [('company_id', 'in',  self.env.companies.ids)]

    manual_ref_no = fields.Char(string="مرجع امر الصرف")
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    partner_mobile = fields.Char(string="رقم الجوال")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس", )
    car_model = fields.Char(string="الموديل")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة")
    maint_wo_id = fields.Many2one(
        'mizan.wo.picking', string="امر العمل", domain=_get_default_branches)
    maint_wo_id1 = fields.Many2one(
        'mizan.car.work.procedure.master', string="امر العمل")
    work_order_flag = fields.Boolean(string="عملية امر عمل")
    send_done_wo = fields.Boolean(
        string="تم ارسال الى امر العمل", readonly=True)
    workstation_id = fields.Many2one(
        'mizan.picking.workstation', string="الورشة")
    workstation_flag_id = fields.Integer(default=lambda self: self._default_workstation_id(),
                                         compute="_get_workstation_id")
    total_all = fields.Float(compute="_calc_total", string="الاجمالي")

    ##
    line_spare_parts_ids = fields.One2many(
        'mizan.car.spare.parts.lines',
        'stock_picking_id',
        ondelete='cascade',
        copy=False
    )

    @api.depends('move_ids_without_package')
    def _calc_total(self):
        for rec in self:
            rec.total_all = sum(l.total for l in rec.move_ids_without_package)

    @api.constrains('move_ids_without_package', 'workstation_id', 'maint_wo_id', 'location_dest_id')
    def get_price_of_product(self):
        for rec in self:
            if rec.location_dest_id.workstation_location_id and not rec.maint_wo_id1:
                raise ValidationError(
                    "تنبيه..  لا يمكن اعتماد الشحنة لعدم تحديد امر العمل للجهة المصروفة [%s] " % rec.location_dest_id.name)
            if rec.workstation_id and rec.maint_wo_id:
                if not (
                        rec.workstation_id.company_id.id == rec.maint_wo_id.company_id):
                    raise ValidationError(
                        "تنبيه.. الفروع غير متوافقة بين امر العمل والوشة ")

            for line in rec.move_ids_without_package:
                line.product_id.product_tmpl_id.check_product_price_from_cost(
                    line.unit_price, line.unit_cost)

            for line in rec.move_ids_without_package:
                if not line.product_uom_qty:
                    raise ValidationError(
                        "Warning: No Qty For product <<<<لا توجد كمية للصنف المحدد[ {} ][ "
                        "{} ] ..  ".format(
                            rec.product_id.name, rec.product_id.default_code))

    @api.model
    def _default_workstation_id(self):
        for rec in self:
            return rec.workstation_id.id

    @api.depends('workstation_id')
    def _get_workstation_id(self):
        for rec in self:
            if rec.workstation_id:
                rec.workstation_flag_id = rec.workstation_id.id
                picking_type = self.env['stock.picking.type'].search(
                    [('workstation_id', '=', rec.workstation_id.id)], limit=1)
                if picking_type:
                    rec.picking_type_id = picking_type.id
                else:
                    rec.picking_type_id = False
                    rec.location_id = False
                    rec.location_dest_id = False
                return {
                    'domain': {
                        'picking_type_id': [('workstation_id', '=', rec.workstation_flag_id)],
                    }}
            else:
                rec.workstation_flag_id = False
                return {
                    'domain': {
                        'picking_type_id': ['|', ('workstation_id', '!=', rec.workstation_flag_id), ('workstation_id', '=', False)],
                    }}

    @api.onchange('workstation_id')
    def _default_workstation1_id(self):
        for rec in self:
            if rec.workstation_id:
                picking_type = self.env['stock.picking.type'].search([('workstation_id', '=', rec.workstation_id.id)],
                                                                     limit=1)
                if picking_type:
                    rec.picking_type_id = picking_type.id
                else:
                    rec.picking_type_id = False
                    rec.location_id = False
                    rec.location_dest_id = False

                return {
                    'domain': {
                        'picking_type_id': [('workstation_id', '=', rec.workstation_flag_id)],
                    }}
            else:
                return {
                    'domain': {
                        'picking_type_id': ['|', ('workstation_id', '!=', rec.workstation_flag_id), ('workstation_id', '=', False)],
                    }}

    @api.onchange('workstation_id', 'maint_wo_id')
    def check_branchs_in_picking(self):
        for rec in self:
            if rec.workstation_id and rec.maint_wo_id:
                if not (rec.workstation_id.company_id.id == rec.maint_wo_id.company_id):
                    raise ValidationError(
                        "تنبيه.. الفروع غير متوافقة بين امر العمل والورشة ")

    @api.onchange('maint_wo_id')
    def get_wo(self):
        for rec in self:
            if rec.maint_wo_id:
                rec.maint_wo_id1 = rec.maint_wo_id.id
                rec.work_order_flag = True
            else:
                rec.maint_wo_id1 = False

    def delete_products_from_wo(self):
        for rec in self:
            wo = self.env['mizan.car.spare.parts.lines'].search(
                [('stock_picking_id', '=', rec.id)])
            if wo:
                if wo.header_id.sale_order_id:
                    raise ValidationError(
                        " لا يمكن حذف الاصناف لامر العمل بسبب تم انشاء امر بيع ")
                else:
                    wo.unlink()

            rec.write({'send_done_wo': False})

            rec.maint_wo_id = False
            rec.maint_wo_id1 = False
            rec.work_order_flag = False

    def button_validate(self):
        for rec in self:
            if rec.maint_wo_id or rec.work_order_flag:
                for line in rec.move_ids_without_package:
                    if (line.product_qty != line.product_uom_qty) or not line.unit_price:
                        raise ValidationError(
                            " تنبيه ... الصنف [%s] قد يكن الكمية غير صحيحه او ان السعر غير صحيح " % line.product_id.name)
        return super(stock_picking, self).button_validate()

    def check_closed_period(self, date_field):
        if not date_field:
            return False

        sql_query = """
            SELECT COUNT(*) as exist_res 
            FROM wo_period_closed
            WHERE %s BETWEEN inv_closed_from_date AND inv_closed_to_date
        """
        try:
            self.env.cr.execute(sql_query, (date_field,))
            result = self.env.cr.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            print(f"Error checking closed period: {str(e)}")
            return False

    # def send_products_to_wo(self):
    #     for rec in self:
    #         if rec.maint_wo_id:
    #             wo = self.env['mizan.car.work.procedure.master'].search([('id', '=', rec.maint_wo_id.id)])

    #             if wo.state in ('cancel_order', 'execute_completed'):
    #                 raise ValidationError("ارسال الاصناف لامر العمل اما ان يكون مكتمل او ملغي لا يمكن ")

    #             # sql_query = """ select count(*) as exist_res from  wo_period_closed
    #             #                 where '{}' between inv_closed_from_date and inv_closed_to_date
    #             #                 """.format(rec.date)

    #             # if sql_query:
    #             #     self.env.cr.execute(sql_query)
    #             #     seq = self.env.cr.fetchone()
    #             #     x = seq[0]
    #             #     if x:
    #             #         raise ValidationError(
    #             #             "تنبيه .. لا يمكن اتمام العمليات بسبب تم ايقاف العمليات في هذه الفتره ")

    #             # if rec.scheduled_date:
    #             #     sql_query = """
    #             #                 select count(*) as exist_res from  wo_period_closed
    #             #                 where '{}' between inv_closed_from_date and inv_closed_to_date
    #             #                 """.format(rec.scheduled_date)
    #             # if rec.date_done:

    #             #     sql_query = """
    #             #                 select count(*) as exist_res from  wo_period_closed
    #             #                 where '{}' between inv_closed_from_date and inv_closed_to_date
    #             #                 """.format(rec.date_done)

    #             # if sql_query:
    #             #     self.env.cr.execute(sql_query)
    #             #     seq = self.env.cr.fetchone()
    #             #     x = seq[0]
    #             #     if x:
    #             #         raise ValidationError("تنبيه .. لا يمكن اتمام العمليات بسبب تم ايقاف العمليات في هذه الفترة ")

    #             if wo.sale_order_id:
    #                 raise ValidationError(" لا يمكن ارسال الاصناف لامر العمل بسبب تم انشاء امر بيع ")
    #             else:
    #                 for line in rec.move_ids_without_package:
    #                     if (line.product_qty <= 0 and not line.quantity) or not line.unit_price or (line.product_uom_qty != line.quantity):
    #                         raise ValidationError(
    #                             " تنبيه ... الصنف [%s] قد يكن الكمية غير صحيحه او ان السعر غير صحيح " % line.product_id.name)

    #                 for wo_line in wo.lines_spare_parts:
    #                     if wo_line.product_id.id not in rec.move_ids_without_package.product_id.ids and wo_line.stock_picking_id.id == rec.id:
    #                         wo_line.unlink()

    #                 products = []
    #                 for p_line in rec.move_ids_without_package.product_id:
    #                     products.append(p_line.id)

    #                 for product_id in products:
    #                     qty = 0
    #                     p_count = 0
    #                     unit_price = 0
    #                     ##
    #                     for line_move in rec.move_ids_without_package:
    #                         if line_move.product_id.id == product_id:

    #                             if rec.state == 'done':
    #                                 qty = qty + line_move.quantity
    #                                 unit_price = unit_price + line_move.unit_price
    #                                 p_count = p_count + 1

    #                     for wo_line in wo.lines_spare_parts:
    #                         if product_id == wo_line.product_id.id and wo_line.stock_picking_id.id == rec.id:

    #                             wo_line.write({'unit_price': round(unit_price/p_count, 2),
    #                                            'qty': qty,
    #                                            'product_tax': wo_line.product_id.taxes_id.id,

    #                                            })
    #                     if rec.id in wo.lines_spare_parts.stock_picking_id.ids:
    #                         if product_id not in wo.lines_spare_parts.product_id.ids and rec.id in wo.lines_spare_parts.stock_picking_id.ids:
    #                             prod = self.env['product.product'].search(
    #                                 [('id', '=', product_id)])
    #                             products = self.env['mizan.car.spare.parts.lines'].create({
    #                                 'product_id': prod.id,
    #                                 'name': prod.name,
    #                                 'unit_price': round(unit_price / p_count, 2),
    #                                 'qty': qty,
    #                                 'qty_done': qty,
    #                                 'product_tax': prod.taxes_id.id,
    #                                 'stock_picking_id': rec.id,
    #                                 'header_id': wo.id,
    #                             })

    #                     else:
    #                         prod = self.env['product.product'].search(
    #                             [('id', '=', product_id)])
    #                         products = self.env['mizan.car.spare.parts.lines'].create({
    #                             'product_id': prod.id,
    #                             'name': prod.name,
    #                             'unit_price': round(unit_price/p_count, 2),
    #                             'qty': qty,
    #                             'qty_done': qty,
    #                             'product_tax': prod.taxes_id.id,
    #                             'stock_picking_id': rec.id,
    #                             'header_id': wo.id,
    #                         })

    #                 rec.write({'send_done_wo': True})
    #                 wo._cal_spare_parts_amounts()
    #                 wo._cal_services_amounts()

    #         else:
    #             raise ValidationError(" لا يمكن ارسال الاصناف لامر العمل   ")

    def send_products_to_wo(self):
        for rec in self:
            if rec.maint_wo_id:
                wo = self.env['mizan.car.work.procedure.master'].search(
                    [('id', '=', rec.maint_wo_id.id)])


                dates_to_check = [rec.date, rec.scheduled_date, rec.date_done]
                if any(self.check_closed_period(d) for d in dates_to_check if d):
                    raise ValidationError(
                        "لا يمكن اتمام العمليات بسبب توقف العمليات في هذه الفترة")

                if wo.sale_order_id:
                    raise ValidationError(
                        " لا يمكن ارسال الاصناف لامر العمل بسبب تم انشاء امر بيع ")
                else:
                    for line in rec.move_ids_without_package:
                        if (line.product_qty <= 0 and not line.quantity) or not line.unit_price or (line.product_uom_qty != line.quantity):
                            raise ValidationError(
                                " تنبيه ... الصنف [%s] قد يكن الكمية غير صحيحه او ان السعر غير صحيح " % line.product_id.name)

                    for wo_line in wo.lines_spare_parts:
                        if wo_line.product_id.id not in rec.move_ids_without_package.product_id.ids and wo_line.stock_picking_id.id == rec.id:
                            wo_line.unlink()

                    products = []
                    for p_line in rec.move_ids_without_package.product_id:
                        products.append(p_line.id)

                    for product_id in products:
                        qty = 0
                        p_count = 0
                        unit_price = 0

                        for line_move in rec.move_ids_without_package:
                            if line_move.product_id.id == product_id:
                                if rec.state == 'done':
                                    qty = qty + line_move.quantity
                                    unit_price = unit_price + line_move.unit_price
                                    p_count = p_count + 1

                        for wo_line in wo.lines_spare_parts:
                            if product_id == wo_line.product_id.id and wo_line.stock_picking_id.id:
                                wo_line.write({'unit_price': round(unit_price/p_count, 2),
                                               'qty': wo_line.qty + qty,
                                               'product_tax': wo_line.product_id.taxes_id.id})
                                ##
                                rec.write(
                                    {'line_spare_parts_ids': [(4, wo_line.id, 0)]})
                        if wo.lines_spare_parts.stock_picking_id.ids:
                            if product_id not in wo.lines_spare_parts.product_id.ids and wo.lines_spare_parts.stock_picking_id.ids:
                                prod = self.env['product.product'].search(
                                    [('id', '=', product_id)])
                                line_spare_parts = self.env['mizan.car.spare.parts.lines'].create({
                                    'product_id': prod.id,
                                    'name': prod.name,
                                    'unit_price': round(unit_price / p_count, 2),
                                    'qty': qty,
                                    'qty_done': qty,
                                    'product_tax': prod.taxes_id.id,
                                    'stock_picking_id': rec.id,
                                    'header_id': wo.id,
                                })
                                ##
                                rec.write({'line_spare_parts_ids': [
                                          (4, line_spare_parts.id, 0)]})

                        else:
                            prod = self.env['product.product'].search(
                                [('id', '=', product_id)])
                            line_spare_parts = self.env['mizan.car.spare.parts.lines'].create({
                                'product_id': prod.id,
                                'name': prod.name,
                                'unit_price': round(unit_price/p_count, 2),
                                'qty': qty,
                                'qty_done': qty,
                                'product_tax': prod.taxes_id.id,
                                'stock_picking_id': rec.id,
                                'header_id': wo.id,
                            })
                            ##
                            rec.write({'line_spare_parts_ids': [
                                      (4, line_spare_parts.id, 0)]})

                    rec.write({'send_done_wo': True})
                    wo._cal_spare_parts_amounts()
                    wo._cal_services_amounts()

            else:
                raise ValidationError(" لا يمكن ارسال الاصناف لامر العمل   ")
