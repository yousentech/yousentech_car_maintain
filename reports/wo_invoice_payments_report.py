from odoo import models, fields, api, http
from odoo.http import request, content_disposition
import io
import xlsxwriter
from datetime import datetime
import json
from urllib.parse import urlencode
from odoo.exceptions import ValidationError


class mizan_wo_invoice_payments_report(models.TransientModel):
    _name = 'mizan.wo.invoice.payments.report'

    date_start = fields.Date(
        string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(
        string="End Date", required=True, default=fields.Date.today)
    partner_id = fields.Many2one('res.partner', string="العميل")
    cancel_state = fields.Boolean(
        string="اخفاء الاشعارات الملغية", default=True)
    display_type = fields.Selection([('detail', 'تحليلي'),
                                     ('summary', 'اجمالي')], string='عرض التقرير', required=True,
                                    default='detail')
    group_by_type = fields.Selection([('by_date', 'حسب التاريخ'),
                                      ('by_type', 'حسب النوع')], string='ترتيب التقرير', required=True,
                                     default='by_date')
    company_ids = fields.Many2many(comodel_name="res.company", string="الشركة", required=True,
                                   default=lambda self: self.env.companies.ids)
    # company_id = fields.Many2one('res.company', string="الفرع",
    #                              required=True, default=lambda self: self.env.user.company_id.id)
    supervisor_id = fields.Many2one(
        'hr.supervisor.assignments', string="المشرف", copy=False, domain="[('company_id','in', company_ids)]")

    @api.onchange('company_ids')
    def _get_allowed_branch_ids(self):
        select = [(i['id']) for i in self.env.user.sudo().company_ids]
        return {'domain': {'company_id': [('id', 'in', select)]}}

    def get_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'partner_id': [(i['id']) for i in self.partner_id],
                'company_ids': [(i['id']) for i in self.company_ids],
                # 'company_id': [(i['id']) for i in self.company_id],
                'supervisor_id': [(i['id']) for i in self.supervisor_id],
                'cancel_state': self.cancel_state,
                'display_type': self.display_type,
                'group_by_type': self.group_by_type,

            },
        }

        return self.env.ref('yousentech_car_maintain.print_wo_inv_pay_rpt').report_action(self, data=data)

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
        #         'company_ids': [(i['id']) for i in self.company_ids],
        #         # 'company_id': [(i['id']) for i in self.company_id],
        #         'supervisor_id': [(i['id']) for i in self.supervisor_id],
        #         'cancel_state': self.cancel_state,
        #         'display_type': self.display_type,
        #         'group_by_type': self.group_by_type,

        #     },
        # }
        form_data = {
            'date_start': self.date_start.strftime('%Y-%m-%d') if self.date_start else '',
            'date_end': self.date_end.strftime('%Y-%m-%d') if self.date_end else '',
            'partner_id': [(i['id']) for i in self.partner_id],
            'company_ids': [(i['id']) for i in self.company_ids],
            # 'company_id': [(i['id']) for i in self.company_id],
            'supervisor_id': [(i['id']) for i in self.supervisor_id],
            'cancel_state': self.cancel_state,
            'display_type': self.display_type,
            'group_by_type': self.group_by_type,
        }

        params = {
            'model': self._name,
            'data': json.dumps(form_data, default=str),
            'output_format': 'xlsx',
            'report_name': f'CompletedWorkOrder_{fields.Date.today()}'
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
        l_company_ids = data['form']['company_ids']
        # l_company_id = data['form']['company_id']
        l_supervisor_id = data['form']['supervisor_id']
        l_cancel_state = data['form']['cancel_state']
        l_display_type = data['form']['display_type']
        l_group_by_type = data['form']['group_by_type']

        domain = []

        domain = [('end_date', '>=', date_start), ('end_date', '<=', date_end)]

        if l_supervisor_id:
            domain.append(
                ('entry_card_id.supervisor_name', 'in', l_supervisor_id))

        if l_company_ids:
            domain.append(('entry_card_id.company_id', 'in', l_company_ids))

        # if l_company_id:
        #     domain.append(('company_id', 'in', l_company_id))

        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_cancel_state:
            domain.append(('state', '!=', 'cancel_order'))

        domain.append(('state', '=', 'execute_completed'))

        mizan_wo = self.env['mizan.car.work.procedure.master'].search(domain)
        # if mizan_wo:
        # if l_enable_custom_seq:
        #     sql_query += " group by b.date,a.seq_2, b.move_name,p.name, b.company_id,a.id order by date "
        # else:
        #     sql_query += " group by b.date, b.move_name,p.name, b.company_id,a.id order by date "

        l_companys = self.env['res.company'].search(
            [('id', 'in', l_company_ids)])
        # l_branchs = self.env['custom.branches'].search([('id', 'in', l_branch_id)])

        l_partner = self.env['res.partner'].search(
            [('id', 'in', l_partner_id)])

        l_supervisors = self.env['hr.supervisor.assignments'].search(
            [('id', 'in', l_supervisor_id)])

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

            self.env.cr.execute(sql_payments)
            res_payments = self.env.cr.dictfetchall()

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

                self.env.cr.execute(sql_payments)
                res_payments = self.env.cr.dictfetchall()

        for account in l_companys:
            work_order_date = []
            for rec in mizan_wo.sorted(lambda o: o.end_date):
                if len(work_order_date) == 0:
                    work_order_date.append(
                        rec.end_date.strftime('%Y-%m-%d'))

                if rec.end_date.strftime('%Y-%m-%d') not in work_order_date:
                    work_order_date.append(
                        rec.end_date.strftime('%Y-%m-%d'))

            sheet = workbook.add_worksheet('تقرير اوامر العمل المكتملة')
            sheet.right_to_left()
            format_company = workbook.add_format(
                {'bold': True, 'align': 'center', 'font': 'Arial', 'font_size': 20})

            format_header = workbook.add_format(
                {'bold': True, 'align': 'center', 'font': 'Arial', 'font_size': 14})
            format_header.set_bg_color('gray')

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

            if l_group_by_type == 'by_date':
                if l_display_type == 'detail':
                    # for l_date in sorted(set(work_order_date)):
                    #     date_row = 2
                    #     date_col = 1
                    #
                    address_col = 1
                    address_row = 12
                    #     sheet.merge_range(address_row, address_col, date_row, date_col + 1,
                    #                       l_date + ' تاريخ ',
                    #                       format_header)
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

                    sheet.write(address_row, address_col,
                                ' الرقم ', format_address)
                    sheet.write(address_row, address_col + 1,
                                ' التاريخ', format_address)
                    sheet.write(address_row, address_col + 2,
                                'رقم امر العمل', format_address)
                    sheet.write(address_row, address_col + 3,
                                'رقم الفاتورة', format_address)
                    sheet.write(address_row, address_col +
                                4, 'العميل', format_address)
                    sheet.write(address_row, address_col + 5,
                                'نوع السيارة', format_address)
                    sheet.write(address_row, address_col + 6,
                                'رقم اللوحة', format_address)
                    sheet.write(address_row, address_col +
                                7, 'خدمة', format_address)
                    sheet.write(address_row, address_col + 8,
                                'قطع غيار', format_address)
                    sheet.write(address_row, address_col +
                                9, 'الخصم', format_address)
                    sheet.write(address_row, address_col + 10,
                                'الاجمالي قبل الضريبة', format_address)

                    sheet.write(address_row, address_col +
                                11, 'الضريبة', format_address)
                    sheet.write(address_row, address_col + 12,
                                'الاجمالي', format_address)
                    sheet.write(address_row, address_col + 13,
                                'الدفع نقد', format_address)
                    sheet.write(address_row, address_col + 14,
                                'الدفع شبكة', format_address)
                    address_row += 1
                    l_cnt = 0
                    l_services_total = 0
                    l_spare_parts_total = 0
                    l_discount_total = 0
                    l_tax_total = 0
                    l_amount_total = 0
                    l_total_before_total = 0
                    l_cash = 0
                    l_bank = 0
                    for line in mizan_wo:
                        address_row += 1
                        l_cnt += 1
                        l_services_total += sum(
                            l.total_before_tax for l in line.result_lines)
                        l_spare_parts_total += sum(
                            l.total_before_tax for l in line.lines_spare_parts)
                        l_discount_total += sum((l.quantity * l.price_unit * (l.discount / 100))
                                                for l in line.create_invoice_manually_id.invoice_line_ids)
                        l_tax_total += line.create_invoice_manually_id.amount_tax
                        l_total_before_total += (sum(l.total_before_tax for l in line.result_lines) + sum(
                            l.total_before_tax for l in line.lines_spare_parts))
                        l_amount_total += line.create_invoice_manually_id.amount_total
                        l_cash += line.create_invoice_manually_id.get_payment_amt_of_invoice(
                            'cash')
                        l_bank += line.create_invoice_manually_id.get_payment_amt_of_invoice(
                            'bank')
                        sheet.write(address_row, address_col,
                                    l_cnt, format_string)
                        sheet.write(
                            address_row, address_col + 1, line.create_invoice_manually_id.invoice_date, format_string)
                        sheet.write(address_row, address_col +
                                    2, line.id, format_string)
                        sheet.write(
                            address_row, address_col + 3, line.create_invoice_manually_id.name, format_string)
                        sheet.write(
                            address_row, address_col + 4, line.create_invoice_manually_id.partner_id.name, format_string)

                        sheet.write(address_row, address_col + 5,
                                    line.car_type_id.name, format_string)
                        sheet.write(
                            address_row, address_col + 6, line.entry_card_id.car_panel_no, format_string)
                        sheet.write(address_row, address_col + 7, round(
                            sum(l.total_before_tax for l in line.result_lines), 2), format_string)
                        sheet.write(address_row, address_col + 8, round(
                            sum(l.total_before_tax for l in line.lines_spare_parts), 2), format_string)
                        sheet.write(address_row, address_col + 9, round(sum((l.quantity * l.price_unit * (l.discount / 100))
                                    for l in line.create_invoice_manually_id.invoice_line_ids), 2), format_string)
                        sheet.write(address_row, address_col + 10, round(sum(l.total_before_tax for l in line.result_lines) + sum(
                            l.total_before_tax for l in line.lines_spare_parts), 2), format_string)
                        sheet.write(
                            address_row, address_col + 11, line.create_invoice_manually_id.amount_tax, format_string)
                        sheet.write(
                            address_row, address_col + 12, line.create_invoice_manually_id.amount_total, format_string)
                        sheet.write(
                            address_row, address_col + 13, line.create_invoice_manually_id.get_payment_amt_of_invoice('cash'), format_string)
                        sheet.write(
                            address_row, address_col + 14, line.create_invoice_manually_id.get_payment_amt_of_invoice('bank'), format_string)

                    address_row += 1
                    sheet.merge_range(address_row, address_col + 6, address_row, header_col + 2,
                                        'اجمالي  ', format_totally_row)
                    sheet.write(address_row, address_col + 7,
                                l_services_total, format_totally_row)
                    sheet.write(address_row, address_col + 8,
                                l_spare_parts_total, format_totally_row)
                    sheet.write(address_row, address_col + 9, l_discount_total,
                                format_totally_row)
                    sheet.write(address_row, address_col + 10, l_total_before_total,
                                format_totally_row)
                    sheet.write(address_row, address_col + 11,
                                l_tax_total,
                                format_totally_row)
                    sheet.write(address_row, address_col + 12, l_amount_total,
                                format_totally_row)
                    sheet.write(address_row, address_col + 13,
                                l_cash,
                                format_totally_row)
                    sheet.write(address_row, address_col + 14,
                                l_bank,
                                format_totally_row)

        # return {
        #     'doc_ids': data['ids'],
        #     'doc_model': data['model'],
        #     'date_start': date_start,
        #     'date_end': date_end,
        #     'companys': l_companys,
        #     # 'branchs': l_branchs,
        #     'customers': l_partner,
        #     'supervisors': l_supervisors,
        #     # 'payments': payments,
        #     'docs': mizan_wo,
        #     'payments_sum': res_payments,
        #     'display_type': l_display_type,
        #     'group_by_type': l_group_by_type,

        # }
        workbook.close()
        output.seek(0)
        excel_data = output.read()
        output.close()
        return excel_data
        # else:
        #     raise ValidationError(
        #         "لا توجد بيانات")


class mizan_wo_invoice_payments_report_pdf_report(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.print_wo_inv_pay_rpt_view'

    @api.model
    def _get_report_values(self, docids, data=None):

        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        l_partner_id = data['form']['partner_id']
        l_company_ids = data['form']['company_ids']
        # l_company_id = data['form']['company_id']
        l_supervisor_id = data['form']['supervisor_id']
        l_cancel_state = data['form']['cancel_state']
        l_display_type = data['form']['display_type']
        l_group_by_type = data['form']['group_by_type']

        domain = []

        domain = [('end_date', '>=', date_start), ('end_date', '<=', date_end)]

        if l_supervisor_id:
            domain.append(
                ('entry_card_id.supervisor_name', 'in', l_supervisor_id))

        if l_company_ids:
            domain.append(('entry_card_id.company_id', 'in', l_company_ids))

        # if l_company_id:
        #     domain.append(('company_id', 'in', l_company_id))

        if l_partner_id:
            domain.append(('partner_id', '=', l_partner_id))

        if l_cancel_state:
            domain.append(('state', '!=', 'cancel_order'))

        domain.append(('state', '=', 'execute_completed'))

        mizan_wo = self.env['mizan.car.work.procedure.master'].search(domain)
        # if mizan_wo:
        l_companys = self.env['res.company'].search(
            [('id', 'in', l_company_ids)])
        l_partner = self.env['res.partner'].search(
            [('id', 'in', l_partner_id)])

        l_supervisors = self.env['hr.supervisor.assignments'].search(
            [('id', 'in', l_supervisor_id)])

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

            self.env.cr.execute(sql_payments)
            res_payments = self.env.cr.dictfetchall()
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

                self.env.cr.execute(sql_payments)
                res_payments = self.env.cr.dictfetchall()

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start,
            'date_end': date_end,
            'companys': l_companys,
            # 'branchs': l_branchs,
            'customers': l_partner,
            'supervisors': l_supervisors,
            # 'payments': payments,
            'docs': mizan_wo,
            'payments_sum': res_payments,
            'display_type': l_display_type,
            'group_by_type': l_group_by_type,

        }
        # else:
        #     raise ValidationError(
        #         "لا توجد بيانات")
