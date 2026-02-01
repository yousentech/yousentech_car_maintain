# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError

# "تقرير تتبع حركة العمليات"
class wo_auditor_analysis_view(models.Model):
    _name = 'wo.auditor.analysis.view'
    _description = 'wo.auditor.analysis.view'
    _auto = False

    id = fields.Integer(string="تسلسل")
    account_move_id = fields.Many2one('account.move')
    account_payment_id = fields.Many2one('account.payment')
    operation_date = fields.Date()
    subject = fields.Char()
    model = fields.Char()
    record_name = fields.Char()
    write_uid = fields.Many2one('res.users')
    field = fields.Char()
    # field_desc = fields.Char()
    # field_type = fields.Char()
    old_value_integer = fields.Char()
    new_value_integer = fields.Char()

    def init(self):
        tools.drop_view_if_exists(self._cr, 'wo_auditor_analysis_view')
        ##
        self._cr.execute("""CREATE OR REPLACE VIEW wo_auditor_analysis_view AS
                        (
                         select id,account_move_id	,account_payment_id	,operation_date,	subject	,model,	record_name	,write_uid,field,old_value_integer,	new_value_integer

                            from (
                                    SELECT
                                        ROW_NUMBER() OVER (PARTITION BY m.res_id ORDER BY m.id) AS id,
                                        m.res_id,
                                        (select min(mm.id) from mail_message mm
                                                  join mail_tracking_value t on t.mail_message_id = mm.id and mm.res_id = m.res_id ) min_id,
                                        m.id AS operation_id,
                                        m.res_id AS account_move_id,
                                        NULL AS account_payment_id,
                                        DATE(m.date) AS operation_date,
                                        m.subject,
                                        m.model,
                                        m.record_name,
                                        m.write_uid,
                                        t.field_id as field,
                                      
                                        t.old_value_integer,
                                        t.new_value_integer
                                    FROM mail_message m
                                    JOIN mail_tracking_value t ON t.mail_message_id = m.id
                                    WHERE m.model = 'account.move'

                                    UNION ALL

                                    -- account.payment (إن وجد)
                                    SELECT
                                        ROW_NUMBER() OVER (PARTITION BY m.res_id ORDER BY m.id) AS id,
                                        m.res_id,
                                        0 as min_id,
                                        m.id AS operation_id,
                                        NULL AS account_move_id,
                                        m.res_id AS account_payment_id,
                                        DATE(m.date) AS operation_date,
                                        m.subject,
                                        m.model,
                                        m.record_name,
                                        m.write_uid,
                                        t.field_id as field,
                                       
                                        t.old_value_integer,
                                        t.new_value_integer
                                    FROM mail_message m
                                    JOIN mail_tracking_value t ON t.mail_message_id = m.id
                                    WHERE m.model = 'account.payment'  
                                    ) x  
                                    
                                    where   operation_id > min_id
                                    order by res_id,id
                                        );
                                    """)