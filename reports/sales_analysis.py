# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

# "تحليل مبيعات الخدمات وقطع الغيار"
class wo_sales_analysis(models.Model):
    _name = 'wo.sales.analysis'
    _description = 'wo.sales.analysis'
    _auto = False

    id = fields.Integer(string="تسلسل")
    header_id = fields.Many2one(
        'mizan.car.work.procedure.master', string="رقم امر العمل")
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)
    technical_1 = fields.Char(string='الفني 1',)
    technical_2 = fields.Char(string='الفني 2',)
    technical_3 = fields.Char(string='الفني 3',)
    technical_4 = fields.Char(string='الفني 4',)
    supervisor_name_id = fields.Many2one(
        'hr.supervisor.assignments', string='المشرف', readonly=True)
    car_panel_no = fields.Char(string='رقم اللوحة',)
    partner_mobile = fields.Char(string='جوال العميل',)
    state = fields.Char(string='الحالة',)
    invoice_no = fields.Many2one('account.move', string='رقم الفاتورة',)
    # branch_name= fields.Many2one('custom.branches',string='الفرع',)
    company_id = fields.Many2one('res.company', string='الفرع')

    unit_price = fields.Float(string='سعر البيع', default=0)
    qty = fields.Float(string='العدد/الكمية', default=0)
    total = fields.Float(string='الاجمالي', default=0)
    untaxed_amount = fields.Float(string='المبلغ قبل الضريبة', default=0)
    discount = fields.Float(string='الخصم', default=0)
    amount_tax = fields.Float(string='مبلغ الضريبة', default=0)
    amount_with_tax = fields.Float(string='مبلغ شامل الضريبة', default=0)
    invoice_with_tax = fields.Float(string='مبلغ الفاتورة', default=0)
    create_date = fields.Datetime(string='تاريخ البدء',)
    name = fields.Char(string='وصف الخدمة',)
    product_id = fields.Many2one(
        'product.product', string='المنتج', readonly=True)
    type = fields.Char(string='نوع المنتج',)
    product_categ_id = fields.Many2one(
        'product.category', string='المجموعة المخزنية', readonly=True)

    product_tmpl_id = fields.Many2one('product.template', string='Product Template',
                                      related='product_id.product_tmpl_id', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_sales_analysis')
        ##
        self._cr.execute("""CREATE OR REPLACE VIEW wo_sales_analysis AS
                        (
                           SELECT   ROW_NUMBER() OVER (ORDER BY header_id) AS id,
                                wo.header_id, 
                                wo.partner_id, 
                                
                                (string_to_array(wo.technical_name, ' , '))[1] AS technical_1,
                                (string_to_array(wo.technical_name, ' , '))[2] AS technical_2,
                                (string_to_array(wo.technical_name, ' , '))[3] AS technical_3,
                                (string_to_array(wo.technical_name, ' , '))[4] AS technical_4,
                                wo.supervisor_name_id, 
                                wo.car_panel_no, 
                                wo.partner_mobile, 
                                wo.state, 
                                wo.create_invoice_manually_id as invoice_no,
                                
                                wo.company_id ,
                                wo.unit_price,
                                wo.qty,
                                
                                (wo.unit_price* wo.qty) AS total,
                                round(wo.untaxed_amount::numeric, 2) as untaxed_amount, 
                            
                                round(wo.discount::numeric, 2) as discount, 
                                round(wo.amount_tax::numeric, 2) as amount_tax, 
                            
                                ROUND((wo.untaxed_amount - wo.discount + wo.amount_tax)::numeric, 2) AS amount_with_tax, 
                                (select x.amount_total from account_move x where x.id= wo.create_invoice_manually_id) as invoice_with_tax,
                                wo.create_date, 
                                wo.name, 
                            
                            
                                wo.product_id, 
                                p.detailed_type, 
                                p.categ_id 
                            from 
                            (select  s.header_id , m.partner_id , m.company_id, m.create_invoice_manually_id 
                            ,(s.unit_price / 1.15) as untaxed_amount, s.discount_amount as discount, s.amount_tax as amount_tax, 
                            (SELECT string_agg( emp.name::text, ' , ')
                            FROM 
                            hr_technical_assignments_mizan_car_work_procedure_line_rel ss,hr_technical_assignments th,hr_employee emp
                            WHERE  ss.mizan_car_work_procedure_line_id = s.id and  ss.hr_technical_assignments_id = th.id and th.technical_emp_id = emp.id)  as technical_name,
                            (select supervisor_name from mizan_car_entry_card_master en where id=m.entry_card_id) supervisor_name_id , m.car_panel_no , m.partner_mobile , m.state ,
                             m.create_date ,s.product_id ,s.name ,s.unit_price , 1 as qty  
                            from mizan_car_work_procedure_master m , mizan_car_work_procedure_line s 
                            where m.id =s.header_id 
                            group by s.header_id , m.partner_id ,m.entry_card_id , m.car_panel_no , m.partner_mobile , m.state ,s.id,
                            m.create_date ,s.product_id ,s.name ,s.unit_price , s.amount_tax , 
                            m.create_invoice_manually_id ,m.company_id

                            union all 
                            select  s.header_id , m.partner_id ,  m.company_id , m.create_invoice_manually_id 
                             ,((s.qty_done * s.unit_price) / 1.15) as untaxed_amount, s.discount_amount as discount, s.amount_tax  ,
                            
                            (SELECT string_agg( emp.name::text, ' , ')
                            FROM 
                            hr_technical_assignments_mizan_car_spare_parts_lines_rel ss,hr_technical_assignments th,hr_employee emp
                            WHERE  ss.mizan_car_spare_parts_lines_id = s.id and  ss.hr_technical_assignments_id = th.id and th.technical_emp_id = emp.id)  as technical_name,
                            (select supervisor_name from mizan_car_entry_card_master en where id=m.entry_card_id) supervisor_name_id , m.car_panel_no , m.partner_mobile , m.state ,
                            m.create_date ,s.product_id ,s.name ,s.unit_price , s.qty_done as qty 
                            from mizan_car_work_procedure_master m , mizan_car_spare_parts_lines s 
                            where m.id =s.header_id 
                            group by  s.header_id , m.partner_id ,m.entry_card_id ,s.id,
                            m.car_panel_no , m.partner_mobile , m.state ,
                            m.create_date ,s.product_id ,s.name ,s.unit_price , s.amount_tax , s.unit_price,  
                            m.create_invoice_manually_id  ,m.company_id
                            ) wo  ,
                            (select p.id, t.name , t.categ_id , (select name from product_category pc where pc.id=t.categ_id) as category_name  , t.detailed_type
                            from product_product p , product_template t
                            where p.product_tmpl_id=t.id
                            ) p
                            where wo.product_id = p.id

                                        );
                                    """)
        
        

