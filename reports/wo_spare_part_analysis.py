# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

class wo_spare_part_analysis_view(models.Model):
    _name = 'wo.spare.part.analysis.view'
    _description = 'wo.spare.part.analysis.view'
    _auto = False
    
    
    id = fields.Integer(string="تسلسل")
    header_id = fields.Many2one('mizan.car.work.procedure.master',string="رقم امر العمل")
    create_uid = fields.Many2one('res.users', string='البائع', readonly=True)
    stock_picking_id = fields.Many2one('stock.picking', string='رقم الشحنة', readonly=True)
    
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)
    order_date = fields.Date( string='تاريخ الطلب',)
    create_date = fields.Datetime( string='تاريخ البدء',)
    company_id= fields.Many2one('res.company',string='الفرع',)
    invoice_no= fields.Many2one('account.move', string='رقم الفاتورة',)
    car_panel_no = fields.Char( string='رقم اللوحة',)
    partner_mobile = fields.Char( string='جوال العميل',)
    state = fields.Char( string='الحالة',)
    product_id = fields.Many2one('product.product', string='المنتج',)
    unit_price = fields.Float( string='سعر البيع',default=0)
    qty = fields.Float( string='الكمية',default=0)
    total = fields.Float( string='اجمالي ',default=0)
    untaxed_amount = fields.Float( string='اجمالي قبل الضريبة',default=0)
    discount = fields.Float( string='الخصم',default=0)
    amount_tax = fields.Float( string='الضريبة',default=0)
    amount_with_tax = fields.Float( string='اجمالي شامل الضريبة',default=0)
   
    supervisor_id = fields.Many2one('hr.supervisor.assignments', string='المشرف', readonly=True)
    
    product_categ_id = fields.Many2one('product.category', string='المجموعة المخزنية', readonly=True)     

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_spare_part_analysis_view')
        
        self._cr.execute("""CREATE OR REPLACE VIEW wo_spare_part_analysis_view AS
                        (  
                          WITH product_categ AS (
                                        SELECT 
                                            p.id AS product_id,
                                            t.categ_id
                                        FROM product_product p
                                        JOIN product_template t ON p.product_tmpl_id = t.id
                                    ),
                                    calculated_discounts AS (
                                        SELECT
                                            s.id AS line_id,s.header_id,
                                            CASE 
                                                WHEN s.discount_type = 'percentage' AND s.discount_line > 0 THEN s.discount_line::numeric
                                                WHEN s.discount_type = 'amount' AND s.unit_price > 0 AND s.qty_done > 0 
                                                    THEN (s.discount_line::numeric / (s.qty_done::numeric * s.unit_price::numeric)) * 100 
                                                ELSE 0
                                            END AS discount_perc,
                                            round(s.amount_tax::numeric,2) AS amount_tax,
                                            round(s.unit_price::numeric,2) AS unit_price,
                                            s.qty_done AS qty,
                                            round(s.qty_done::numeric * s.unit_price::numeric,2) AS total,
                                            CASE 
                                                WHEN tx.price_include = TRUE THEN (s.qty_done::numeric * s.unit_price::numeric)::numeric / 1.15
                                                WHEN tx.price_include = FALSE THEN (s.qty_done::numeric * s.unit_price::numeric)::numeric
                                                ELSE s.qty_done::numeric * s.unit_price::numeric
                                            END AS total_base
                                        FROM mizan_car_spare_parts_lines s
                                        LEFT JOIN account_tax tx ON tx.id = s.product_tax
                                    )
                                    SELECT 
                                        ROW_NUMBER() OVER (ORDER BY wo.line_id) AS id,
                                        wo.header_id,
                                        wo.line_id,
                                        wo.create_uid,
                                        wo.stock_picking_id,
                                        wo.partner_id,
                                        wo.order_date,
                                        wo.create_date,
                                        wo.company_id,
                                        wo.invoice_no,
                                        wo.car_panel_no,
                                        wo.partner_mobile,
                                        wo.state,
                                        wo.product_id,
                                        cd.unit_price,
                                        cd.qty,
                                        cd.total,
                                        cd.total_base,
                                        round(cd.total_base::numeric - (cd.total_base * (cd.discount_perc / 100)), 2) AS untaxed_amount,
                                      
                                        cd.discount_perc AS discount,
                                        cd.amount_tax,
                                        round((cd.total_base::numeric - (cd.total_base * (cd.discount_perc / 100))::numeric) + cd.amount_tax::numeric, 2) AS amount_with_tax,
                                        wo.supervisor_id,
                                        pc.categ_id
                                    FROM (
                                        SELECT
                                            m.id AS header_id,
                                            s.id as line_id,
                                            m.partner_id,
                                            en.order_date,
                                            m.create_date,
                                            m.company_id,
                                            m.create_invoice_manually_id AS invoice_no,
                                            m.car_panel_no,
                                            m.partner_mobile,
                                            m.state,
                                            s.product_id,
                                            en.supervisor_name AS supervisor_id,
                                            p.create_uid,
                                            s.stock_picking_id
                                        FROM mizan_car_spare_parts_lines s
                                        JOIN mizan_car_work_procedure_master m ON m.id = s.header_id
                                        JOIN mizan_car_entry_card_master en ON m.entry_card_id = en.id
                                        LEFT JOIN stock_picking p ON p.id = s.stock_picking_id
                                        
                                        WHERE m.state != 'draft'  -- إذا كنت تحتاج إلى تصفية الحالة، يمكن تعديل ذلك
                                    ) AS wo
                                    JOIN calculated_discounts cd ON wo.header_id = cd.header_id and cd.line_id = wo.line_id
                                    LEFT JOIN product_categ pc ON wo.product_id = pc.product_id 
                        
                                        );
                                    """)
