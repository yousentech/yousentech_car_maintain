# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

# "تحليل مبيعات الفنيين"
class wo_technicals_analysis_view(models.Model):
    _name = 'wo.technicals.analysis.view'
    _description = 'wo.technicals.analysis.view'
    _auto = False
 
    id = fields.Integer(string="تسلسل")
    header_id = fields.Many2one(
        'mizan.car.work.procedure.master', string="رقم امر العمل")
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)
    order_date = fields.Date(string='تاريخ الطلب',)
    create_date = fields.Datetime(string='تاريخ البدء العمل',)
    end_date = fields.Datetime(string='تاريخ انتهاء العمل',)
    company_id = fields.Many2one('res.company', string='الفرع',)
    invoice_no = fields.Many2one('account.move', string='رقم الفاتورة',)
    car_panel_no = fields.Char(string='رقم اللوحة',)
    partner_mobile = fields.Char(string='جوال العميل',)
    state = fields.Char(string='الحالة',)
    product_id = fields.Many2one('product.product', string='المنتج',)
    unit_price = fields.Float(string='سعر البيع', default=0)
    qty = fields.Float(string='الكمية', default=0)
    total = fields.Float(string='اجمالي ', default=0)
    untaxed_amount = fields.Float(string='اجمالي قبل الضريبة', default=0)
    discount = fields.Float(string='الخصم', default=0)
    amount_tax = fields.Float(string='الضريبة', default=0)
    amount_with_tax = fields.Float(string='اجمالي شامل الضريبة', default=0)

    supervisor_id = fields.Many2one(
        'hr.supervisor.assignments', string='المشرف', readonly=True)

    product_categ_id = fields.Many2one(
        'product.category', string='المجموعة المخزنية', readonly=True)
    technical_count = fields.Integer(string='عدد الفنيين في الخدمة', default=0)
    hr_technical_assignments_id = fields.Many2one(
        'hr.technical.assignments', string='الفني', readonly=True)
    time_difference = fields.Char(string='مدة انجاز امر العمل', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_technicals_analysis_view')

        self._cr.execute("""CREATE OR REPLACE VIEW wo_technicals_analysis_view AS
                        (SELECT 
    ROW_NUMBER() OVER (ORDER BY wo.hr_technical_assignments_id) AS id, 
    wo.header_id, 
    wo.partner_id,  
    wo.order_date,
    wo.create_date, 
    wo.end_date, 
    wo.company_id,
    wo.invoice_no,
    wo.car_panel_no, 
    wo.partner_mobile, 
    wo.state, 
    wo.product_id, 
    wo.unit_price,
    wo.qty,
    wo.total,
    wo.untaxed_amount, 
    wo.discount, 
    wo.amount_tax, 
    wo.amount_with_tax, 
    wo.supervisor_id,
    t.categ_id as product_categ_id, 
    wo.technical_count,
    wo.hr_technical_assignments_id,

    -- حساب الفرق بين تاريخ البدء والانتهاء بصيغة hh:mm:ss
    TO_CHAR(
        INTERVAL '1 second' * EXTRACT(EPOCH FROM (wo.end_date - wo.create_date)), 
        'HH24:MI:SS'
    ) AS time_difference

FROM (
    SELECT 
        m.id AS header_id,
        m.partner_id,
        en.order_date,
        m.create_date,
        m.end_date,
        m.company_id,
        m.create_invoice_manually_id AS invoice_no,
        m.car_panel_no,
        m.partner_mobile,
        m.state,
        s.product_id,
        ROUND(s.unit_price::numeric, 2) AS unit_price,
        1 AS qty,
        ROUND(s.unit_price::numeric, 2) AS total,
        ROUND((s.unit_price / 1.15)::numeric, 2) AS untaxed_amount,
        ROUND(s.discount_amount::numeric, 2) AS discount,
        ROUND(s.amount_tax::numeric, 2) AS amount_tax,
        ROUND(((s.unit_price / 1.15)::numeric - s.discount_amount::numeric + s.amount_tax::numeric)::numeric, 2) AS amount_with_tax,
        en.supervisor_name AS supervisor_id, 
        -- حساب عدد المرات التي تم فيها تعيين وظيفة فنية
        COUNT(tech.hr_technical_assignments_id) AS technical_count,
        -- الاستعلام للوصول إلى hr_technical_assignments_id
        tech.hr_technical_assignments_id 
    FROM 
        mizan_car_work_procedure_master m
    JOIN mizan_car_work_procedure_line s ON m.id = s.header_id
    JOIN mizan_car_entry_card_master en ON m.entry_card_id = en.id
    LEFT JOIN (
        SELECT ss.mizan_car_work_procedure_line_id, ss.hr_technical_assignments_id
        FROM hr_technical_assignments_mizan_car_work_procedure_line_rel ss
        JOIN hr_technical_assignments th ON ss.hr_technical_assignments_id = th.id
    ) tech ON tech.mizan_car_work_procedure_line_id = s.id
    GROUP BY 
         tech.hr_technical_assignments_id ,
        m.id, 
        m.partner_id, 
        en.order_date, 
        m.create_date, 
        m.end_date, 
        m.company_id, 
        m.create_invoice_manually_id, 
        m.car_panel_no, 
        m.partner_mobile, 
        m.state, 
        s.product_id, 
        s.unit_price, 
        s.discount_amount, 
        s.amount_tax, 
        en.supervisor_name
       
) wo
-- ربط جدول المنتجات للحصول على product_categ_id مباشرة
LEFT JOIN product_product p ON p.id = wo.product_id
LEFT JOIN product_template t ON p.product_tmpl_id = t.id
 
                                        );
                                    """)
