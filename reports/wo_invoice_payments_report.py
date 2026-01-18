from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class haraj_report(models.TransientModel):
    _name = 'mizan.wo.invoice.payments.report'


    date_start = fields.Date(string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string="العميل")
    cancel_state = fields.Boolean(string="اخفاء الاشعارات الملغية", default=True)
    display_type = fields.Selection([('detail', 'تحليلي'),
                                     ('summary', 'اجمالي')], string='عرض التقرير', required=True,
                                    default='detail')
    group_by_type = fields.Selection([('by_date', 'حسب التاريخ'),
                                      ('by_type', 'حسب النوع')], string='ترتيب التقرير', required=True,
                                     default='by_date')
    company_ids1 = fields.Many2many(comodel_name="res.company", string="الشركة", required=True,
                                    default=lambda self: self.env.user.company_ids.ids)
    branch_id = fields.Many2one('custom.branches', string="الفرع", required=True, default=lambda self: self.env.user.branch_id.id)
    supervisor_id = fields.Many2one('hr.supervisor.assignments', string="المشرف",copy=False,domain="[('branch_id','=', branch_id)]")

    @api.onchange('company_ids1')
    def _get_allowed_branch_ids(self):
        print(self.env.user.sudo().allowed_branch_ids)
        select = [(i['id']) for i in self.env.user.sudo().allowed_branch_ids]
        return {'domain': {'branch_id': [('id', 'in', select)]}}

    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'partner_id': [(i['id']) for i in self.partner_id],
                'company_ids1': [(i['id']) for i in self.company_ids1],
                'branch_id': [(i['id']) for i in self.branch_id],
                'supervisor_id': [(i['id']) for i in self.supervisor_id],
                'cancel_state': self.cancel_state,
                'display_type': self.display_type,
                'group_by_type': self.group_by_type,

            },
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `_get_report_values()` and pass `data` automatically.
        return self.env.ref('qimamhd_mizan_car_13.print_wo_inv_pay_rpt').report_action(self, data=data)

class ReportAttendanceRecap(models.AbstractModel):
    _name = 'report.qimamhd_mizan_car_13.print_wo_inv_pay_rpt_view'

    @api.model
    def _get_report_values(self, docids, data=None):

        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_company_ids1 = data['form']['company_ids1']
        l_branch_id = data['form']['branch_id']
        l_supervisor_id = data['form']['supervisor_id']
        l_cancel_state = data['form']['cancel_state']
        l_display_type = data['form']['display_type']
        l_group_by_type = data['form']['group_by_type']

        domain = []

        domain = [('end_date', '>=', date_start), ('end_date', '<=', date_end)]

        if l_supervisor_id:
            domain.append(('entry_card_id.supervisor_name', 'in', l_supervisor_id))

        if l_company_ids1:
            domain.append(('entry_card_id.company_id', '=', l_company_ids1))

        if l_branch_id:
            domain.append(('branch_id', 'in', l_branch_id))

        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_cancel_state:
            domain.append(('state', '!=', 'cancel_order'))

        domain.append(('state', '=', 'execute_completed'))


        print(domain)
        mizan_wo = self.env['mizan.car.work.procedure.master'].search(domain)
        print(mizan_wo)
        if mizan_wo:
            # if l_enable_custom_seq:
            #     sql_query += " group by b.date,a.seq_2, b.move_name,p.name, b.company_id,a.id order by date "
            # else:
            #     sql_query += " group by b.date, b.move_name,p.name, b.company_id,a.id order by date "

            l_companys = self.env['res.company'].search([('id', 'in', l_company_ids1)])
            l_branchs = self.env['custom.branches'].search([('id', 'in', l_branch_id)])

            l_partner = self.env['res.partner'].search([('id', 'in', l_partner_id)])

            l_supervisors = self.env['hr.supervisor.assignments'].search([('id', 'in', l_supervisor_id)])

            res_payments = ""
            sql_payments = ""
            if len(mizan_wo.create_invoice_manually_id.ids) > 1:
                sql_payments = """
                                               select sum(amount) as amount,journal_name
                                                           from (select sum(r.amount) amount,j.name as journal_name,am.id as move_id from  account_partial_reconcile r, account_move_line rl,account_move am,account_move_line l,
                                                           account_journal j
                                                            where r.credit_move_id=rl.id and rl.journal_id=j.id   and r.debit_move_id=l.id
                                                            and l.move_id=am.id
                                                            and am.id in {}
                                                            group by j.name,am.id
                                                           union all
                                                           select (sum(r.amount) * -1) amount,j.name,am.id as move_id from  account_partial_reconcile r, account_move_line rl,account_move am,account_move_line l,
                                                           account_journal j
                                                            where r.credit_move_id=l.id and rl.journal_id=j.id  
                                                            and r.debit_move_id=rl.id
                                                            and l.move_id=am.id
                                                            and am.id in {}
                                                            group by j.name,am.id ) x group by journal_name
                                                    """.format(tuple(mizan_wo.create_invoice_manually_id.ids), tuple(mizan_wo.create_invoice_manually_id.ids), )
            else:
                if len(mizan_wo.create_invoice_manually_id.ids) == 1:
                    sql_payments = """
                                               select sum(amount) as amount,journal_name
                                                           from (select sum(r.amount) amount,j.name as journal_name,am.id as move_id from  account_partial_reconcile r, account_move_line rl,account_move am,account_move_line l,
                                                           account_journal j
                                                            where r.credit_move_id=rl.id and rl.journal_id=j.id  and r.debit_move_id=l.id
                                                            and l.move_id=am.id
                                                            and am.id = {}
                                                            group by j.name,am.id
                                                           union all
                                                           select (sum(r.amount) * -1) amount,j.name,am.id as move_id from  account_partial_reconcile r, account_move_line rl,account_move am,account_move_line l,
                                                           account_journal j
                                                            where r.credit_move_id=l.id and rl.journal_id=j.id  
                                                            and r.debit_move_id=rl.id
                                                            and l.move_id=am.id
                                                            and am.id = {}
                                                            group by j.name,am.id ) x group by journal_name
                                                        """.format(mizan_wo.create_invoice_manually_id.id, mizan_wo.create_invoice_manually_id.id)




            print(sql_payments)

            self.env.cr.execute(sql_payments)
            res_payments = self.env.cr.dictfetchall()
            print(res_payments)

            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'date_start': date_start,
                'date_end': date_end,
                'companys': l_companys,
                'branchs': l_branchs,
                'customers': l_partner,
                'supervisors': l_supervisors,
                # 'payments': payments,
                'docs': mizan_wo,
                'payments_sum': res_payments,
                'display_type':l_display_type,
                'group_by_type': l_group_by_type,

            }
        else:
            raise ValidationError(
                "لا توجد بيانات")
