from odoo import models, fields, api, http
from odoo.http import request, content_disposition
import io
import xlsxwriter
from datetime import datetime
import json
from urllib.parse import urlencode
from odoo.exceptions import ValidationError


class mizan_wo_technical_report(models.TransientModel):
    _name = 'mizan.wo.technical.report'

    date_start = fields.Date(string="Start Date", required=True, )
    date_end = fields.Date(string="End Date", required=True,)
    partner_id = fields.Many2one('res.partner', string="العميل")
    wo_ids = fields.Many2many(
        'mizan.car.work.procedure.master', string="امر التركيب")
    display_type = fields.Selection([('detail', 'تحليلي'),
                                     ('summary', 'اجمالي')], string='عرض التقرير', required=True,
                                    default='detail')
    company_ids = fields.Many2many(
        'res.company', string="الفرع", required=True, default=lambda self: self.env.user.company_ids.ids)
    technical_ids = fields.Many2many(
        'hr.technical.assignments', string="اسم الفني")
    product_ids = fields.Many2many('product.product', string="الخدمة", copy=False,
                                   domain=[('discount_product_flag', '!=', True), ('type', '!=', 'product')])
    wo_completed = fields.Boolean(string="الخدمات المكتملة")

    def get_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'partner_id': [(i['id']) for i in self.partner_id],
                'wo_ids': [(i['id']) for i in self.wo_ids],
                'company_ids': [(i['id']) for i in self.company_ids],
                'technical_ids': [(i['id']) for i in self.technical_ids],
                'product_ids': [(i['id']) for i in self.product_ids],
                'display_type': self.display_type,
                'wo_completed': self.wo_completed,

            },
        }

        return self.env.ref('yousentech_car_maintain.print_wo_technical_report').report_action(self, data=data)


    def action_download_excel(self):
        """Button action to download Excel"""
        self.ensure_one()
        # data = {
        #     'ids': self.ids,
        #     'model': self._name,
        #     'form': {
        #         'date_start': self.date_start,
        #         'date_end': self.date_end,
        #         'partner_id': [(i['id']) for i in self.partner_id],
        #         'wo_ids': [(i['id']) for i in self.wo_ids],
        #         'company_ids': [(i['id']) for i in self.company_ids],
        #         'technical_ids': [(i['id']) for i in self.technical_ids],
        #         'product_ids': [(i['id']) for i in self.product_ids],
        #         'display_type': self.display_type,
        #        'wo_completed': self.wo_completed,

        #     },
        # }
        form_data = {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'partner_id': [(i['id']) for i in self.partner_id],
            'wo_ids': [(i['id']) for i in self.wo_ids],
            'company_ids': [(i['id']) for i in self.company_ids],
            'technical_ids': [(i['id']) for i in self.technical_ids],
            'product_ids': [(i['id']) for i in self.product_ids],
            'display_type': self.display_type,
            'wo_completed': self.wo_completed,

        }

        params = {
            'model': self._name,
            'data': json.dumps(form_data, default=str),
            'output_format': 'xlsx',
            'report_name': f'TechnicalReport_{fields.Date.today()}'
        }

        # URL encode
        encoded_params = urlencode(params)

        return {
            'type': 'ir.actions.act_url',
            'url': f'/xlsx_report?{encoded_params}',
            'target': 'new',
        }

    @api.model
    def get_xlsx_report(self, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_wo_ids = data['form']['wo_ids']
        l_company_ids = data['form']['company_ids']
        l_technical_ids = data['form']['technical_ids']
        l_product_ids = data['form']['product_ids']
        l_display_type = data['form']['display_type']
        l_wo_completed = data['form']['wo_completed']
        domain = []

        domain = [('header_id.create_date', '>=', date_start),
                  ('header_id.create_date', '<=', date_end)]

        if l_technical_ids:
            domain.append(('technical_name.id', 'in', l_technical_ids))

        if l_wo_ids:
            domain.append(('header_id', 'in', l_wo_ids))

        if l_company_ids:
            domain.append(
                ('header_id.entry_card_id.company_id', 'in', l_company_ids))

        if l_company_ids:
            domain.append(('header_id.company_id', 'in', l_company_ids))

        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_product_ids:
            domain.append(('product_id', 'in', l_product_ids))

        if l_wo_completed:
            domain.append(('state', '=', 'complete'))

        mizan_wo = self.env['mizan.car.work.procedure.line'].search(domain)
        if mizan_wo:
            l_company = self.env['res.company'].search(
                [('id', 'in', l_company_ids)])
            l_partner = self.env['res.partner'].search(
                [('id', 'in', l_partner_id)])
            l_products = self.env['product.product'].search(
                [('id', 'in', l_product_ids)])
            l_technicals = []
            if l_technical_ids:
                l_technicals = self.env['hr.technical.assignments'].search(
                    [('id', 'in', l_technical_ids)])
            else:
                l_technicals = self.env['hr.technical.assignments'].search(
                    [('id', 'in', mizan_wo.technical_name.ids)])

            l_companys = self.env['res.company'].search(
                [('id', '=', self.env.company.id)])
            for account in l_companys:
                sheet = workbook.add_worksheet('تقرير الفنيين ')
                sheet.right_to_left()
                format_company = workbook.add_format(
                    {'bold': True, 'align': 'center', 'font': 'Arial', 'font_size': 20})

                format_header = workbook.add_format(
                    {'bold': True, 'align': 'center', 'font': 'Arial', 'font_size': 14})

                format_header.set_bg_color('gray')
                format_header_date = workbook.add_format(
                    {'bold': True, 'align': 'center', 'font': 'Arial', 'font_size': 14})

                format_header_date.set_bg_color('orange')

                format_address = workbook.add_format(
                    {'bold': True, 'align': 'center', 'bg_color': 'yellow', 'font': 'Arial', 'font_size': 12})
                format_totally_row = workbook.add_format(
                    {'bold': True, 'align': 'center', "num_format": u"#,##0.00", 'font': 'Arial', 'font_size': 10})
                format_date = workbook.add_format(
                    {'num_format': 'dd-mm-yyyy', 'align': 'center', 'font': 'Arial', 'font_size': 10})
                format_num = workbook.add_format(
                    {"num_format": u"#,##0.00", 'align': 'center', 'font': 'Arial', 'font_size': 10})
                format_string = workbook.add_format(
                    {'align': 'center', 'font': 'Arial', 'font_size': 10})

                company_col = 1
                company_row = 1
                sheet.merge_range(company_row, company_col, company_row,
                                  company_col + 2, 'الاسم', format_company)
                sheet.merge_range(company_row + 1, company_col, company_row + 1, company_col + 2, 'العنوان',
                                  format_company)
                sheet.merge_range(company_row + 2, company_col, company_row + 2, company_col + 2, 'الجوال',
                                  format_company)
                sheet.merge_range(company_row + 3, company_col, company_row + 3, company_col + 2, 'رقم الضريبي',
                                  format_company)
                sheet.merge_range(company_row + 4, company_col, company_row + 4, company_col + 2, 'سجل المؤسسة',
                                  format_company)

                sheet.merge_range(company_row, company_col + 3, company_row, company_col + 4, account.name,
                                  format_company)
                sheet.merge_range(company_row + 1, company_col + 3, company_row + 1, company_col + 4,
                                  account.street, format_company)
                sheet.merge_range(company_row + 2, company_col + 3, company_row + 2, company_col + 4, account.phone,
                                  format_company)
                sheet.merge_range(company_row + 3, company_col + 3, company_row + 3, company_col + 4, account.vat,
                                  format_company)
                sheet.merge_range(company_row + 4, company_col + 3, company_row + 4, company_col + 4,
                                  account.company_registry, format_company)

                header_col = 1
                header_row = 8

                date_row = 10
                date_col = 1

                sheet.merge_range(date_row, date_col, date_row, date_col + 1,
                                  f'من تاريخ {date_start}',
                                  format_header)
                date_col += 1
                sheet.merge_range(date_row, date_col+1, date_row, date_col + 2,
                                  f'من تاريخ {date_end}',
                                  format_header)

                if l_display_type == 'detail':

                    address_col = 1
                    address_row = 15

                    sheet.set_column('C:C', 12)
                    sheet.set_column('D:D', 30)
                    sheet.set_column('E:E', 20)
                    sheet.set_column('F:F', 20)
                    sheet.set_column('G:G', 20)
                    sheet.set_column('H:H', 20)
                    sheet.set_column('I:I', 20)
                    sheet.set_column('J:J', 20)
                    sheet.set_column('K:K', 20)
                    sheet.set_column('L:L', 20)

                    for tech in l_technicals:

                        address_col = 1
                        address_row += 5
                        sheet.merge_range(address_row, date_col, address_row, date_col + 3,
                                          tech.technical_emp_id.name, format_header)
                        address_row += 2
                        sheet.write(address_row, address_col,
                                    ' الرقم ', format_address)
                        sheet.write(address_row, address_col +
                                    1, ' الخدمة', format_address)
                        sheet.write(address_row, address_col + 2,
                                    'تاريخ البدء', format_address)
                        sheet.write(address_row, address_col + 3,
                                    'تاريخ الانتهاء', format_address)
                        sheet.write(address_row, address_col + 4,
                                    'فترة الانجاز', format_address)
                        sheet.write(address_row, address_col + 5,
                                    'الفني المعتمد', format_address)
                        sheet.write(address_row, address_col + 6,
                                    'حالة الانجاز', format_address)
                        sheet.write(address_row, address_col + 7,
                                    'الفنيين المشتركين', format_address)
                        sheet.write(address_row, address_col + 8,
                                    'رقم امر العمل', format_address)
                        sheet.write(address_row, address_col +
                                    9, 'العميل', format_address)
                        sheet.write(address_row, address_col + 10,
                                    'جوال العميل', format_address)

                        sheet.write(address_row, address_col + 11,
                                    'لوحة السيارة', format_address)

                        address_row += 1
                        l_cnt = 0
                        l_services_total = 0
                        l_spare_parts_total = 0

                        for line in mizan_wo.filtered(lambda x: tech.id in x.technical_name.ids):
                            address_row += 1
                            l_cnt += 1
                            line_state = ""
                            if line.state == "complete":
                                line_state = "مكتمل / completed"
                            else:
                                line_state = "البدء /started"

                            sheet.write(address_row, address_col,
                                        l_cnt, format_string)

                            sheet.write(address_row, address_col + 1,
                                        line.product_id.name, format_string)
                            sheet.write(address_row, address_col + 2, line.header_id.get_datetime_zone_user(
                                line.start_Service_date), format_date)
                            sheet.write(address_row, address_col + 3, line.header_id.get_datetime_zone_user(
                                line.complete_date), format_date)
                            sheet.write(address_row, address_col + 4,
                                        line.diff_times, format_string)

                            sheet.write(
                                address_row, address_col + 5, line.technical_is_done.technical_emp_id.name, format_string)
                            sheet.write(address_row, address_col +
                                        6, line_state, format_string)
                            sheet.write(address_row, address_col + 7, ', '.join(g['name'] for g in line.technical_name.filtered(
                                lambda x: x.id != tech.id).technical_emp_id), format_string)
                            sheet.write(address_row, address_col + 8,
                                        line.header_id.id, format_string)
                            sheet.write(address_row, address_col + 9,
                                        line.header_id.partner_id.name, format_string)
                            sheet.write(address_row, address_col + 10,
                                        line.header_id.partner_mobile, format_string)
                            sheet.write(address_row, address_col + 11,
                                        line.header_id.car_panel_no, format_string)

                            # ================================================================================================
                elif l_display_type == 'summary':

                    address_col = 1
                    address_row = 15

                    sheet.set_column('B:B', 40)
                    sheet.set_column('C:C', 30)
                    sheet.set_column('D:D', 30)

                    sheet.write(address_row, address_col,
                                ' الفني', format_address)
                    sheet.write(address_row, address_col + 1,
                                ' عدد الخدمات المنجزة', format_address)
                    sheet.write(address_row, address_col + 2,
                                'الايرادات المحققة', format_address)
                    total = 0
                    for tech in l_technicals:
                        address_row += 1
                        l_services_total = sum(l.total_before_tax / len(l.technical_name) for l in mizan_wo.filtered(
                            lambda x: tech.id in x.technical_name.ids and len(x.technical_name.ids) > 0))
                        l_service_count = len(
                            [l for l in mizan_wo if tech.id in l.technical_name.ids])
                        total += l_services_total

                        sheet.write(address_row, address_col,
                                    tech.technical_emp_id.name, format_string)

                        sheet.write(address_row, address_col + 1,
                                    l_service_count, format_string)
                        sheet.write(address_row, address_col + 2,
                                    round(l_services_total, 2), format_num)
                    address_row += 1
                    sheet.merge_range(address_row, address_col, address_row, address_col + 1,
                                      'الاجمالي',
                                      format_header)

                    sheet.write(address_row, address_col +
                                2, total, format_num)

                    # ================================================================================================

            workbook.close()
            output.seek(0)
            excel_data = output.read() 
            output.close()
            return excel_data


        else:
            raise ValidationError(
                "لا توجد بيانات")


class mizan_wo_technical_report_pdf(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.print_wo_technical_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):

        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_wo_ids = data['form']['wo_ids']
        l_company_ids = data['form']['company_ids']
        l_technical_ids = data['form']['technical_ids']
        l_product_ids = data['form']['product_ids']
        l_display_type = data['form']['display_type']
        l_wo_completed = data['form']['wo_completed']
        domain = []

        domain = [('header_id.create_date', '>=', date_start),
                  ('header_id.create_date', '<=', date_end)]

        if l_technical_ids:
            domain.append(('technical_name.id', 'in', l_technical_ids))

        if l_wo_ids:
            domain.append(('header_id', 'in', l_wo_ids))

        if l_company_ids:
            domain.append(
                ('header_id.entry_card_id.company_id', 'in', l_company_ids))

        if l_company_ids:
            domain.append(('header_id.company_id', 'in', l_company_ids))

        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_product_ids:
            domain.append(('product_id', 'in', l_product_ids))

        if l_wo_completed:
            domain.append(('state', '=', 'complete'))

        mizan_wo = self.env['mizan.car.work.procedure.line'].search(domain)
        if mizan_wo:
            l_companies = self.env['res.company'].search(
                [('id', 'in', l_company_ids)])
            l_partner = self.env['res.partner'].search(
                [('id', 'in', l_partner_id)])
            l_products = self.env['product.product'].search(
                [('id', 'in', l_product_ids)])
            l_technicals = self.env['hr.technical.assignments'].search(
                [('id', 'in', l_technical_ids)])

            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'date_start': date_start,
                'date_end': date_end,
                'company': l_companies,
                'customers': l_partner,
                'technical_ids': l_technicals,
                'products': l_products,
                'docs': mizan_wo,
                'display_type': l_display_type,
                'wo_completed': l_wo_completed,
            }

        else:
            raise ValidationError(
                "لا توجد بيانات")
