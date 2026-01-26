from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, time,timedelta

class haraj_report(models.TransientModel):
    _inherit = 'mizan.wo.invoice.payments.report'


    def get_report_excel(self):
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
        return self.env.ref('yousentech_car_maintain.print_wo_inv_pay_xlsx').report_action(self, data=data)

class ReportAttendanceRecap(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.print_wo_inv_pay_xlsx_view'
    _inherit = 'report.odoo_report_xlsx.abstract'

    @api.model
    def generate_xlsx_report(self, workbook, data,partners):

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

            for account in l_companys:
                work_order_date = []
                for rec in mizan_wo.sorted(lambda o: o.end_date):
                    if len(work_order_date)== 0:
                        work_order_date.append(rec.end_date.strftime('%Y-%m-%d'))

                    if rec.end_date.strftime('%Y-%m-%d') not in work_order_date:
                        work_order_date.append(rec.end_date.strftime('%Y-%m-%d'))

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
                sheet.merge_range(company_row, company_col, company_row, company_col + 2, 'الاسم', format_company)
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

                sheet.merge_range(date_row , date_col, date_row, date_col + 1,
                            date_start + ' من تاريخ ',
                              format_header)
                date_col +=1
                sheet.merge_range(date_row , date_col+1, date_row, date_col + 2,
                                  date_end + ' الى تاريخ ',
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

                        sheet.write(address_row, address_col , ' الرقم ', format_address)
                        sheet.write(address_row, address_col + 1, ' التاريخ', format_address)
                        sheet.write(address_row, address_col + 2, 'رقم امر العمل', format_address)
                        sheet.write(address_row, address_col + 3, 'رقم الفاتورة', format_address)
                        sheet.write(address_row, address_col + 4, 'العميل', format_address)
                        sheet.write(address_row, address_col + 5, 'نوع السيارة', format_address)
                        sheet.write(address_row, address_col + 6, 'رقم اللوحة', format_address)
                        sheet.write(address_row, address_col + 7, 'خدمة', format_address)
                        sheet.write(address_row, address_col + 8, 'قطع غيار', format_address)
                        sheet.write(address_row, address_col + 9, 'الخصم', format_address)
                        sheet.write(address_row, address_col + 10, 'الاجمالي قبل الضريبة', format_address)

                        sheet.write(address_row, address_col + 11, 'الضريبة', format_address)
                        sheet.write(address_row, address_col + 12, 'الاجمالي', format_address)
                        sheet.write(address_row, address_col + 13, 'الدفع نقد', format_address)
                        sheet.write(address_row, address_col + 14, 'الدفع شبكة', format_address)
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
                            l_services_total += sum(l.total_before_tax for l in line.result_lines)
                            l_spare_parts_total += sum(l.total_before_tax for l in line.lines_spare_parts)
                            l_discount_total += sum((l.quantity * l.price_unit * (l.discount /100)) for l in line.create_invoice_manually_id.invoice_line_ids)
                            l_tax_total += line.create_invoice_manually_id.amount_tax
                            l_total_before_total += (sum(l.total_before_tax for l in line.result_lines) + sum(l.total_before_tax for l in line.lines_spare_parts))
                            l_amount_total += line.create_invoice_manually_id.amount_total
                            l_cash += line.create_invoice_manually_id.get_payment_amt_of_invoice('cash')
                            l_bank += line.create_invoice_manually_id.get_payment_amt_of_invoice('bank')
                            sheet.write(address_row, address_col , l_cnt , format_string)
                            sheet.write(address_row, address_col + 1 ,line.create_invoice_manually_id.invoice_date, format_string)
                            sheet.write(address_row, address_col + 2 , line.id, format_string)
                            sheet.write(address_row, address_col + 3 , line.create_invoice_manually_id.name , format_string)
                            sheet.write(address_row, address_col + 4 , line.create_invoice_manually_id.partner_id.name , format_string)

                            sheet.write(address_row, address_col + 5 , line.car_type_id.name , format_string)
                            sheet.write(address_row, address_col + 6 , line.entry_card_id.car_panel_no , format_string)
                            sheet.write(address_row, address_col + 7 , round(sum(l.total_before_tax for l in line.result_lines),2) , format_string)
                            sheet.write(address_row, address_col + 8 , round(sum(l.total_before_tax for l in line.lines_spare_parts),2) , format_string)
                            sheet.write(address_row, address_col + 9 , round(sum((l.quantity * l.price_unit * (l.discount /100)) for l in line.create_invoice_manually_id.invoice_line_ids),2) , format_string)
                            sheet.write(address_row, address_col + 10 , round(sum(l.total_before_tax for l in line.result_lines) + sum(l.total_before_tax for l in line.lines_spare_parts),2) , format_string)
                            sheet.write(address_row, address_col + 11 , line.create_invoice_manually_id.amount_tax , format_string)
                            sheet.write(address_row, address_col + 12 , line.create_invoice_manually_id.amount_total , format_string)
                            sheet.write(address_row, address_col + 13 , line.create_invoice_manually_id.get_payment_amt_of_invoice('cash') , format_string)
                            sheet.write(address_row, address_col + 14 , line.create_invoice_manually_id.get_payment_amt_of_invoice('bank') , format_string)


                        address_row += 1
                        sheet.merge_range(address_row, address_col + 6, address_row, header_col + 2,
                                         'اجمالي  ', format_totally_row)
                        sheet.write(address_row, address_col + 7, l_services_total , format_totally_row)
                        sheet.write(address_row, address_col + 8, l_spare_parts_total, format_totally_row)
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

                        # address_row += 10
                        # sheet.write(address_row, address_col + 1, ' دفعت ', format_totally_row)
                        # sheet.write(address_row, address_col + 2, ' اجمالي المبلغ', format_totally_row)
                        # address_row += 1
                        # for pay in res_payments:
                        #     sheet.write(address_row, address_col + 1, pay['journal_name'], format_string)
                        #     sheet.write(address_row, address_col + 2, pay['amount'] , format_string)
                        #



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
