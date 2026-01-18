from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import pytz

class haraj_report(models.TransientModel):
    _name = 'mizan.wo.technical.report'

    date_start = fields.Date(string="Start Date", required=True, )
    date_end = fields.Date(string="End Date", required=True,  )
    partner_id = fields.Many2one('res.partner', string="العميل")
    wo_ids = fields.Many2many('mizan.car.work.procedure.master', string="امر التركيب")
    display_type = fields.Selection([('detail', 'تحليلي'),
                                     ('summary', 'اجمالي')], string='عرض التقرير', required=True,
                                    default='detail')
    branch_ids = fields.Many2many('custom.branches', string="الفرع", required=True, default=lambda self: self.env.user.allowed_branch_ids.ids)
    technical_ids = fields.Many2many('hr.technical.assignments',string="اسم الفني" )
    product_ids = fields.Many2many('product.product', string="الخدمة", copy=False,  
                                      domain=[('discount_product_flag','!=',True),('type','!=','product')])
    wo_completed = fields.Boolean(string="الخدمات المكتملة")
  
    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        
        # user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
        # l_start_date = pytz.utc.localize(self.date_start).astimezone(user_tz)
        # l_end_date = pytz.utc.localize(self.date_end).astimezone(user_tz)
        # print("l_start_date",l_start_date.time())
        
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'partner_id': [(i['id']) for i in self.partner_id],
                'wo_ids': [(i['id']) for i in self.wo_ids],
                'branch_ids': [(i['id']) for i in self.branch_ids],
                'technical_ids': [(i['id']) for i in self.technical_ids],
                'product_ids': [(i['id']) for i in self.product_ids],
                'display_type': self.display_type,
               'wo_completed': self.wo_completed,

            },
        }

        # use `module_name.report_id` as reference.
        # `report_action()` will call `_get_report_values()` and pass `data` automatically.
        return self.env.ref('qimamhd_mizan_car_13.print_wo_technical_report').report_action(self, data=data)

class ReportAttendanceRecap(models.AbstractModel):
    _name = 'report.qimamhd_mizan_car_13.print_wo_technical_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):

        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_wo_ids = data['form']['wo_ids']
        l_branch_ids = data['form']['branch_ids']
        l_technical_ids = data['form']['technical_ids']
        l_product_ids = data['form']['product_ids']
        l_display_type = data['form']['display_type']
        l_wo_completed = data['form']['wo_completed']
        domain = []

        domain = [('header_id.create_date', '>=', date_start), ('header_id.create_date', '<=', date_end)]

        if l_technical_ids:
            domain.append(('technical_name.id', 'in', l_technical_ids))

        if l_wo_ids:
            domain.append(('header_id', 'in', l_wo_ids))

        if l_branch_ids:
            domain.append(('header_id.entry_card_id.branch_id', 'in', l_branch_ids))
      
        if l_branch_ids:
            domain.append(('header_id.branch_id', 'in', l_branch_ids))
             
        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_product_ids:
            domain.append(('product_id', 'in', l_product_ids))
        
        if l_wo_completed:
            domain.append(('state', '=', 'complete'))

        print(domain)
        mizan_wo = self.env['mizan.car.work.procedure.line'].search(domain)
        print(mizan_wo)
        if mizan_wo:
            l_branchs = self.env['custom.branches'].search([('id', 'in', l_branch_ids)])
            l_partner = self.env['res.partner'].search([('id', 'in', l_partner_id)])
            l_products = self.env['product.product'].search([('id', 'in', l_product_ids)])
            l_technicals = self.env['hr.technical.assignments'].search([('id', 'in', l_technical_ids)])

            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'date_start': date_start,
                'date_end': date_end,
                'branchs': l_branchs,
                'customers': l_partner,
                'technical_ids': l_technicals,
                'products': l_products,
                'docs': mizan_wo,
                'display_type':l_display_type,
                'wo_completed':l_wo_completed,
            }

        else:
            raise ValidationError(
                "لا توجد بيانات")
