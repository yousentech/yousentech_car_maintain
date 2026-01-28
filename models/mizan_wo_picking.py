# -*- coding: utf-8 -*-
from odoo import models, fields, _, tools


class view_mizan_picking(models.Model):
    _name = 'mizan.wo.picking'
    _description = 'mizan work orders view in picking'
    _auto = False
    
    id = fields.Integer(string="ID")
    name = fields.Char(strin="name")
    company_id = fields.Many2one('res.company', string="الفرع")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'mizan_wo_picking')
        ##
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

