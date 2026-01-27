from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class haraj_report(models.TransientModel):
    _name = 'mizan.wo.report.module'


    date_start = fields.Date(string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string="العميل")
    cancel_state = fields.Boolean(string="اخفاء الاشعارات الملغية", default=True)
    hide_uncompleted_orders = fields.Boolean(string="اخفاء الاوامر الغير مكتملة")
    group_by_type = fields.Selection([('by_date', 'حسب التاريخ'),
                                     ('by_type', 'حسب النوع')], string='ترتيب التقرير', required=True,
                                    default='by_date')
    company_ids1 = fields.Many2many(comodel_name="res.company", string="الشركة", required=True,
                                    default=lambda self: self.env.user.company_ids.ids)
    company_id = fields.Many2one('res.company', string="الفرع", required=True, default=lambda self: self.env.user.company_id.id)
    supervisor_id = fields.Many2one('hr.supervisor.assignments', string="المشرف",copy=False,domain="[('company_id','=', company_id)]")

    @api.onchange('company_ids1')
    def _get_allowed_branch_ids(self):
        print(self.env.user.sudo().company_ids)
        select = [(i['id']) for i in self.env.user.sudo().company_ids]
        return {'domain': {'company_id': [('id', 'in', select)]}}

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
                'company_id': [(i['id']) for i in self.company_id],
                'supervisor_id': [(i['id']) for i in self.supervisor_id],
                'cancel_state': self.cancel_state,
                'hide_uncompleted_orders': self.hide_uncompleted_orders,
                'group_by_type': self.group_by_type,

            },
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `_get_report_values()` and pass `data` automatically.
        return self.env.ref('yousentech_car_maintain.print_wo_sum_report').report_action(self, data=data)

class ReportAttendanceRecap(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.work_order_sum_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):

        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_company_ids1 = data['form']['company_ids1']
        l_company_id = data['form']['company_id']
        l_supervisor_id = data['form']['supervisor_id']
        l_cancel_state = data['form']['cancel_state']
        l_hide_uncompleted_orders = data['form']['hide_uncompleted_orders']
        l_group_by_type = data['form']['group_by_type']

        domain_compelete = []
        domain_un_compelete = []

        domain_compelete = [('end_date', '>=', date_start), ('end_date', '<=', date_end),('state', '=', 'execute_completed')]
        domain_un_compelete = [('create_date', '>=', date_start), ('create_date', '<=', date_end),('state', '!=', 'execute_completed')]

        if l_supervisor_id:
            domain_compelete.append(('entry_card_id.supervisor_name', 'in', l_supervisor_id))
            domain_un_compelete.append(('entry_card_id.supervisor_name', 'in', l_supervisor_id))

        if l_company_ids1:
            domain_compelete.append(('entry_card_id.company_id', '=', l_company_ids1))
            domain_un_compelete.append(('entry_card_id.company_id', '=', l_company_ids1))

        if l_company_id:
            domain_compelete.append(('company_id', 'in', l_company_id))
            domain_un_compelete.append(('company_id', 'in', l_company_id))

        if l_partner_id:
            domain_compelete.append(('partner_id', '=', l_partner_id))
            domain_un_compelete.append(('partner_id', '=', l_partner_id))

        if l_cancel_state:
            domain_compelete.append(('state', '!=', 'cancel_order'))
            domain_un_compelete.append(('state', '!=', 'cancel_order'))

        if l_hide_uncompleted_orders:
            domain_compelete.append(('state', '=', 'execute_completed'))
            domain_un_compelete.append(('state', '=', 'execute_completed'))


        print(domain_compelete)
        harajs_compelete = self.env['mizan.car.work.procedure.master'].search(domain_compelete)
        harajs_un_compelete = self.env['mizan.car.work.procedure.master'].search(domain_un_compelete)
        print(harajs_compelete)
        if harajs_compelete or harajs_un_compelete:

            l_companys = self.env['res.company'].search([('id', 'in', l_company_ids1)])
            l_company = self.env['res.company'].search([('id', 'in', l_company_id)])

            l_partner = self.env['res.partner'].search([('id', 'in', l_partner_id)])

            l_supervisors = self.env['hr.supervisor.assignments'].search([('id', 'in', l_supervisor_id)])

            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'date_start': date_start,
                'date_end': date_end,
                'companys': l_companys,
                'company': l_company,
                'customers': l_partner,
                'group_by_type':l_group_by_type,
                'supervisors': l_supervisors,
                'docs_compelete': harajs_compelete,
                'docs_un_compelete': harajs_un_compelete,

            }
        else:
            raise ValidationError(
                "لا توجد بيانات")
