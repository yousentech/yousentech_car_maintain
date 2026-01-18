# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

class CustomProduct_qty_cost(models.Model):
    _name = 'wo.services.analysis.view'
    _description = 'wo.services.analysis.view'
    _auto = False
    
    
    id = fields.Integer(string="تسلسل")
    header_id = fields.Many2one('mizan.car.work.procedure.master',string="رقم امر العمل")
    partner_id = fields.Many2one('res.partner', string='العميل', readonly=True)
    order_date = fields.Date( string='تاريخ الطلب',)
    create_date = fields.Datetime( string='تاريخ البدء',)
    branch_id= fields.Many2one('custom.branches',string='الفرع',)
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
    
    product_categ_id = fields.Many2one('product.categories', string='المجموعة المخزنية', readonly=True)     
    price_include = fields.Boolean(string='مشمولة السعر', readonly=True) 

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_services_analysis_view')
        
        self._cr.execute("""CREATE OR REPLACE VIEW wo_services_analysis_view AS
                        (  
                          select  ROW_NUMBER() OVER (ORDER BY product_id) AS id, 
                                wo.header_id, 
                                wo.partner_id,  
                                order_date,
                                wo.create_date, 
                                wo.branch_id,
                                wo.invoice_no,
                                wo.car_panel_no, 
                                wo.partner_mobile, 
                                wo.state, 
                                 wo.product_id, 
                                 
                                wo.unit_price,
                                wo.qty,
                                  wo.total,
                                    round(total_base::numeric - (total_base * (discount_perc/100)),2) as untaxed_amount , 
                                price_include,
                               discount_amount as discount,
                                 amount_tax, 
                            
                                round((total_base::numeric - (total_base * (discount_perc/100))::numeric) + amount_tax::numeric,2) as amount_with_tax, 
                              
                                 supervisor_id ,
                                   (select t.product_categ_id  from product_product p , product_template t   
                                 where p.product_tmpl_id=t.id and p.id=wo.product_id) as product_categ_id 
                            from (
                            select  m.id as header_id,
                            m.partner_id,en.order_date, m.create_date,m.branch_id,
                            m.create_invoice_manually_id as invoice_no,m.car_panel_no , m.partner_mobile , m.state,
                            
                            s.product_id,round(s.unit_price::numeric,2) as unit_price , 1 as qty,
                              case when  tx.price_include = True then  s.unit_price::numeric /1.15
                              when  tx.price_include = False then  s.unit_price::numeric 
                              else s.unit_price::numeric end total_base,
                              
                               
                            round(s.unit_price:: numeric,2) as total, 
                            tx.price_include,
                            
                              case when s.discount_type = 'percentage' and  s.discount_line > 0 then s.discount_line::numeric
                             when s.discount_type = 'amount' and s.unit_price>0 then (s.discount_line::numeric / s.unit_price::numeric)  * 100 else 0  end::numeric  as discount_perc,
                          
                             s.discount_amount,
                         
                         
                            round(s.amount_tax:: numeric,2) as amount_tax, 
                            
                            en.supervisor_name as supervisor_id


                            from mizan_car_work_procedure_line  s 
                            inner join mizan_car_work_procedure_master m on m.id =s.header_id  
                             inner join mizan_car_entry_card_master en on m.entry_card_id=en.id
                            left outer join account_tax tx on tx.id=s.product_tax
                           ) wo

                                        );
                                    """)
