# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

class wo_work_order_analysis_view(models.Model):
    _name = 'wo.work.order.analysis.view'
    _description = 'wo.work.order.analysis.view'
    _auto = False
    
    id = fields.Integer(string="تسلسل")
    header_id = fields.Many2one('mizan.car.work.procedure.master',string="رقم امر العمل")
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)

    order_date = fields.Date( string='تاريخ الطلب',)
    create_date = fields.Datetime( string='تاريخ البدء',)
    company_id= fields.Many2one('res.company',string='الفرع',)
    invoice_no= fields.Many2one('account.move', string='رقم الفاتورة',)
    car_panel_no = fields.Char( string='رقم اللوحة',)
    partner_mobile = fields.Char( string='جوال العميل',)
    state = fields.Char( string='الحالة',)
    services_amt_after_tax = fields.Float( string=' اجمالي شامل الضريبة للخدمات',default=0)
    services_amt_before_tax = fields.Float( string='اجمالي قبل الضريبة للخدمات',default=0)
    services_amt_tax = fields.Float( string='الضريبة للخدمات',default=0)
    services_discount = fields.Float( string='اجمالي الخصم للخدمات',default=0)
    spare_parts_amt_after_tax = fields.Float( string='اجمالي شامل الضريبة لقطع الغيار',default=0)
    spare_parts_amt_before_tax = fields.Float( string='اجمالي قبل الضريبة لقطع الغيار',default=0)
    spare_parts_amt_tax = fields.Float( string='اجمالي الضريبة لقطع الغيار',default=0)
    spare_parts_discount = fields.Float( string='اجمالي الخصم لقطع الغيار',default=0)
 
    invoice_amout_total = fields.Float( string='اجمالي الفاتورة شامل الضريبة',default=0)
    
    supervisor_amount = fields.Float( string='المببلغ المحدد من المشرف',default=0)
    supervisor_id = fields.Many2one('hr.supervisor.assignments', string='المشرف', readonly=True)
   
     

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_work_order_analysis_view')
        
        self._cr.execute("""CREATE OR REPLACE VIEW wo_work_order_analysis_view AS
                        (   SELECT 
                                    ROW_NUMBER() OVER (ORDER BY m.id) AS id,
                                    m.id AS header_id,
                                    m.partner_id,
                                    en.order_date,
                                    m.create_date,
                                    m.company_id,
                                    m.create_invoice_manually_id AS invoice_no,
                                    m.car_panel_no,
                                    m.partner_mobile,
                                    m.state,
                                    m.services_amt_after_tax,
                                    m.services_amt_before_tax,
                                    m.services_amt_tax,
                                    m.services_discount,
                                    CASE WHEN lines_count > 0 THEN m.spare_parts_amt_after_tax ELSE 0 END AS spare_parts_amt_after_tax,
                                    CASE WHEN lines_count > 0 THEN m.spare_parts_amt_before_tax ELSE 0 END AS spare_parts_amt_before_tax,
                                    CASE WHEN lines_count > 0 THEN m.spare_parts_amt_tax ELSE 0 END AS spare_parts_amt_tax,
                                    CASE WHEN lines_count > 0 THEN m.spare_parts_discount ELSE 0 END AS spare_parts_discount,
                                    am.amount_total AS invoice_amout_total,
                                    m.supervisor_amount,
                                    en.supervisor_name AS supervisor_id
                                FROM 
                                    mizan_car_work_procedure_master m
                                JOIN 
                                    mizan_car_entry_card_master en ON m.entry_card_id = en.id
                                LEFT JOIN 
                                    (SELECT header_id, COUNT(*) AS lines_count FROM mizan_car_spare_parts_lines GROUP BY header_id) spl ON spl.header_id = m.id
                                LEFT JOIN 
                                    account_move am ON am.id = m.create_invoice_manually_id

                                        );
                                    """)
