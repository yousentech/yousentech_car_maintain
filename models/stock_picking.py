# -*- coding: utf-8 -*-
from odoo import models, fields, api, _,tools
from odoo.exceptions import ValidationError
from datetime import datetime

class view_mizan_picking(models.Model):
    _name = 'mizan.wo.picking'
    _description = 'mizan work orders view in picking'
    _auto = False
    id = fields.Integer(string="ID")
    name = fields.Char(strin="name")
    # branch_id = fields.Integer(string="branch_id")
    company_id = fields.Many2one('res.company',string="الفرع")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'mizan_wo_picking')
        # COALESCE(p.company_id, s.company_id) as company_id, p.picking_type_id,
        # COALESCE(case
        # when
        # s.quantity > 0
        # then
        # sl.location_dest_id else sl.location_id
        # end, 0) location_id
        ##
        # self._cr.execute("""CREATE OR REPLACE VIEW mizan_wo_picking AS
        #                 (select wo.id,'[ '|| 'ID ' || wo.id::text ||' ] '|| '[ '|| (select p.name from res_partner p where p.id=wo.partner_id)|| ' ] '||
        #                          case when  wo.car_panel_no is not null then ' [ ' ||  wo.car_panel_no ||' ] 'else ' ' end || ' [ ' || b.name || ']'
        #                       as name, en.branch_id as branch_id
        #                      from mizan_car_work_procedure_master wo, mizan_car_entry_card_master en, custom_branches b
        #                         where wo.sale_order_id is null and en.id = wo.entry_card_id and b.id= en.branch_id and wo.state not in ('execute_completed','cancel_order'));
        #                             """)
        ##
        # self._cr.execute("""CREATE OR REPLACE VIEW mizan_wo_picking AS
        #                 (select wo.id,'[ '|| 'ID ' || wo.id::text ||' ] '|| '[ '|| (select p.name from res_partner p where p.id=wo.partner_id)|| ' ] '||
        #                          case when  wo.car_panel_no is not null then ' [ ' ||  wo.car_panel_no ||' ] 'else ' ' end || ' [ ' || p.name || ']'
        #                       as name, en.company_id as company_id
        #                      from mizan_car_work_procedure_master wo, mizan_car_entry_card_master en
        #                         where wo.sale_order_id is null and en.id = wo.entry_card_id and wo.state not in ('execute_completed','cancel_order'));
        #                             """)
        self._cr.execute("""CREATE OR REPLACE VIEW mizan_wo_picking AS
            SELECT 
                wo.id,
                '[ID ' || wo.id::text || '] ' || 
                COALESCE(pt.name, 'No Partner') ||
                CASE 
                    WHEN wo.car_panel_no IS NOT NULL THEN ' [' || wo.car_panel_no || ']' 
                    ELSE '' 
                END ||
                ' [' || COALESCE(c.name, 'No Company') || ']' as name,
                en.company_id as company_id
            FROM 
                mizan_car_work_procedure_master wo
            JOIN 
                mizan_car_entry_card_master en ON en.id = wo.entry_card_id
            LEFT JOIN 
                res_partner pt ON pt.id = wo.partner_id
            LEFT JOIN 
                res_company c ON c.id = en.company_id
            WHERE 
                wo.sale_order_id IS NULL 
                AND wo.state NOT IN ('execute_completed', 'cancel_order');
        """)

class xx_stock_workstation_location(models.Model):
    _inherit = 'stock.location'

    workstation_location_id = fields.Boolean( string="موقع ورشة")

class xx_stock_picking_types(models.Model):
    _inherit = 'stock.picking.type'

    workstation_id = fields.Many2one('mizan.picking.workstation', string="الورشة")

class xx_stock_picking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_branches(self):

        return [('company_id', 'in',  self.env.companies.ids),
               ]

    manual_ref_no = fields.Char(string="مرجع امر الصرف")
    car_panel_no = fields.Char(string="رقم لوحة السيارة")
    partner_mobile = fields.Char(string="رقم الجوال")
    car_size_id = fields.Many2one('mizan.car.size', string="المقاس", )
    car_model = fields.Char(string="الموديل")
    car_type_id = fields.Many2one('mizan.car.types', string="نوع السيارة")

    work_order_id = fields.Many2one('mizan.wo.picking', string="امر العمل",domain=_get_default_branches)
    work_order_id1 = fields.Many2one('mizan.car.work.procedure.master', string="امر العمل")
    work_order_flag = fields.Boolean(string="عملية امر عمل")
    send_done_wo = fields.Boolean(string="تم ارسال الى امر العمل", readonly=True)

    workstation_id = fields.Many2one('mizan.picking.workstation', string="الورشة")

    workstation_flag_id = fields.Integer(default=lambda self: self._default_workstation_id(),
                                     compute="_get_workstation_id")

    total_all = fields.Float(compute="_calc_total", string="الاجمالي")


    @api.depends('move_ids_without_package')
    def _calc_total(self):
        for rec in self:

            rec.total_all = sum (l.total for l in rec.move_ids_without_package)
          

    @api.constrains('move_ids_without_package','workstation_id', 'work_order_id','location_dest_id')
    def get_price_of_product(self):
        for rec in self:
          
            if rec.location_dest_id.workstation_location_id and not rec.work_order_id1:
                 raise ValidationError(
                        "تنبيه..  لا يمكن اعتماد الشحنة لعدم تحديد امر العمل للجهة المصروفة [%s] " % rec.location_dest_id.name)
            if rec.workstation_id and rec.work_order_id:
                if not (
                        rec.workstation_id.company_id.id == rec.work_order_id.company_id):
                    raise ValidationError(
                        "تنبيه.. الفروع غير متوافقة بين امر العمل والوشة ")

            for line in rec.move_ids_without_package:
                line.product_id.product_tmpl_id.check_product_price_from_cost(line.unit_price,line.unit_cost)

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
                picking_type = self.env['stock.picking.type'].search([('workstation_id','=', rec.workstation_id.id)],limit=1)
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
                        'picking_type_id': ['|',('workstation_id', '!=', rec.workstation_flag_id), ('workstation_id', '=',False)],
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
                        'picking_type_id': ['|',('workstation_id', '!=', rec.workstation_flag_id), ('workstation_id', '=', False)],
                    }}

    @api.onchange('workstation_id','work_order_id')
    def check_branchs_in_picking(self):
        for rec in self:
            
            if rec.workstation_id and rec.work_order_id:
                #print("rec.workstation_id.branch_id.id", rec.workstation_id.branch_id.id)
                #print("rec.work_order_id.branch_id.id", rec.work_order_id.branch_id)

                if not(rec.workstation_id.company_id.id == rec.work_order_id.company_id):
                    raise ValidationError(
                        "تنبيه.. الفروع غير متوافقة بين امر العمل والورشة ")
 


    @api.onchange('work_order_id')
    def get_wo(self):
        for rec in self:
         
            if rec.work_order_id:
                rec.work_order_id1 = rec.work_order_id.id
                rec.work_order_flag = True
            else:
                rec.work_order_id1 = False


    def delete_products_from_wo(self):
        for rec in self:
        
            wo = self.env['mizan.car.spare.parts.lines'].search([('stock_picking_id','=', rec.id)])
            if wo:
                if wo.header_id.sale_order_id:
                    raise ValidationError(
                        " لا يمكن حذف الاصناف لامر العمل بسبب تم انشاء امر بيع ")
                else:
                    wo.unlink()

            rec.write({'send_done_wo': False})

            rec.work_order_id = False
            rec.work_order_id1 = False
            rec.work_order_flag =False


    def button_validate(self):
        for rec in self:
            if rec.work_order_id or rec.work_order_flag:
                for line in rec.move_ids_without_package:
                    if (line.product_qty != line.product_uom_qty) or not line.unit_price:
                        raise ValidationError(
                            " تنبيه ... الصنف [%s] قد يكن الكمية غير صحيحه او ان السعر غير صحيح " % line.product_id.name)
        return super(xx_stock_picking, self).button_validate()

    def send_products_to_wo(self):
        for rec in self:
            
            if rec.work_order_id:
                wo = self.env['mizan.car.work.procedure.master'].search([('id', '=', rec.work_order_id.id)])
               
                if wo.state in ('cancel_order','execute_completed'):
                    raise ValidationError("ارسال الاصناف لامر العمل اما ان يكون مكتمل او ملغي لا يمكن " )           
                sql_query = """          
                                        select count(*) as exist_res from  wo_period_closed
                                        where '{}' between inv_closed_from_date and inv_closed_to_date
                                        """.format(rec.date)

                if sql_query:
                    print("sql_query", sql_query)
                    self.env.cr.execute(sql_query)
                    seq = self.env.cr.fetchone()
                    x = seq[0]
                    if x:
                       
                            raise ValidationError(
                                "تنبيه .. لا يمكن اتمام العمليات بسبب تم ايقاف العمليات في هذه الفتره ")
                           
                
                if rec.scheduled_date:
                        sql_query = """          
                                            select count(*) as exist_res from  wo_period_closed
                                            where '{}' between inv_closed_from_date and inv_closed_to_date or 
                                                
                                            """.format(rec.scheduled_date)
                if  rec.date_done:
                    

                    sql_query = """          
                                        select count(*) as exist_res from  wo_period_closed
                                        where '{}' between inv_closed_from_date and inv_closed_to_date
                                        """.format(rec.date_done)

                if sql_query:
                    print("sql_query", sql_query)
                    self.env.cr.execute(sql_query)
                    seq = self.env.cr.fetchone()
                    x = seq[0]
                    if x:
                       
                            raise ValidationError(
                                "تنبيه .. لا يمكن اتمام العمليات بسبب تم ايقاف العمليات في هذه الفتره ")
                                
                # existing_wo_picking = wo.lines_spare_parts.filtered(lambda x: x.stock_picking_id)
                
                # if existing_wo_picking:
                #     raise ValidationError(
                #                 "تنبيه ..  لامر العمل مرتبطة بشحنة اخرى .. لا يمكن ارسال الشحنة ")

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
                            if product_id == wo_line.product_id.id and wo_line.stock_picking_id.id == rec.id:
                              

                                wo_line.write({'unit_price': round(unit_price/p_count,2),
                                                'qty': qty,
                                                'product_tax': wo_line.product_id.taxes_id.id,

                                                 })
                        if rec.id in wo.lines_spare_parts.stock_picking_id.ids:
                            if product_id not in wo.lines_spare_parts.product_id.ids and rec.id in wo.lines_spare_parts.stock_picking_id.ids:
                                prod = self.env['product.product'].search([('id', '=', product_id)])
                                products = self.env['mizan.car.spare.parts.lines'].create({
                                    # 'search_result': '',
                                    'product_id': prod.id,
                                    'name': prod.name,
                                    'unit_price': round(unit_price / p_count, 2),
                                    'qty': qty,
                                    'qty_done': qty,
                                    'product_tax': prod.taxes_id.id,
                                    'stock_picking_id': rec.id,

                                    'header_id': wo.id,
                                })

                        else:
                                prod = self.env['product.product'].search([('id','=', product_id)])
                                products = self.env['mizan.car.spare.parts.lines'].create({
                                # 'search_result': '',
                                'product_id': prod.id,
                                'name': prod.name,
                                'unit_price': round(unit_price/p_count,2),
                                'qty': qty,
                                'qty_done':qty,
                                'product_tax': prod.taxes_id.id,
                                    'stock_picking_id': rec.id,

                                    'header_id': wo.id,
                            })


                    rec.write({'send_done_wo':True})
                    wo._cal_spare_parts_amounts()
                    wo._cal_services_amounts()

            else:
                raise ValidationError(
                    " لا يمكن ارسال الاصناف لامر العمل   ")


class xx_stock_move(models.Model):
    _inherit = 'stock.move'

    unit_price = fields.Float(string="سعر البيع")
    total = fields.Float(compute="_calc_total", string="الاجمالي")
    unit_cost = fields.Float(compute="_calc_total", string="التكلفة")
    aval_qty = fields.Float(compute="_calc_total", string="الكمية المتوفرة")

    # @api.onchange('product_id')
    # def get_price_of_product(self):
    #     for rec in self:
    #             price = 0.00
    #             pricelist = self.env['product.pricelist'].search([('branch_id', '=', rec.picking_id.branch_id.id)])
    #             if pricelist:
    #                 print("pricelist22", pricelist)
    #                 for line in pricelist.item_ids:
    #
    #                     if line.product_tmpl_id.id == rec.product_id.product_tmpl_id.id:
    #                         price = line.fixed_price
    #                 if not price:
    #                     price = rec.product_id.list_price
    #             else:
    #                 price = rec.product_id.list_price
    #
    #             rec.unit_price= price

    @api.depends('unit_price', 'quantity', 'product_qty', 'product_id','unit_cost','product_uom_qty')
    def _calc_total(self):
        for rec in self:
            # rec.product_id.product_tmpl_id.check_product_price_from_cost(rec.unit_price)
          
            rec.total = rec.product_uom_qty * rec.unit_price

            prod_id = ("product.product" + "," + str(rec.product_id.id))
            rec.unit_cost = self.env['ir.property'].search([('res_id', '=', prod_id)]).value_float

            qty = 0.00
            if rec.product_id and rec.picking_id.location_id.id:
                qty = self.env['stock.quant'].search([('location_id','=',rec.picking_id.location_id.id),('product_id','=', rec.product_id.id)])

                qty = sum(l.quantity for l in qty)
                # if qty < 0 :
                #     raise ValidationError(
                #         "Warning_!: No enough Qty For product <<<<لا توجد كمية متوفر للصنف المحدد[ {} ][ "
                #         "{} ] .. الكمية المتوفره للصنف [ {} ]".format(
                #             rec.product_id.name, rec.product_id.default_code, qty))

            rec.aval_qty = qty

    @api.onchange('unit_price')
    def chk_price_of_product(self):
        for rec in self:
         
            if rec.product_id and rec.unit_price:
                rec.product_id.product_tmpl_id.check_product_price_from_cost(rec.unit_price,rec.unit_cost)

    # @api.onchange('product_uom_qty','aval_qty','quantity_done')
    # def chk_price_of_product(self):
    #     for rec in self:
    #         if rec.quantity_done > rec.aval_qty or rec.product_uom_qty > rec.aval_qty:
    #             raise ValidationError(
    #                 "Warning: No enough Qty For product <<<<لا توجد كمية متوفر للصنف المحدد[ {} ][ "
    #                 "{} ] .. الكمية المتوفره للصنف [ {} ]".format(
    #                     rec.product_id.name, rec.product_id.default_code, rec.aval_qty))
    #
