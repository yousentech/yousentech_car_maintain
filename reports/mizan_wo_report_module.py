from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import io
import xlsxwriter
class mizan_wo_report_module(models.TransientModel):
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

        return self.env.ref('yousentech_car_maintain.print_wo_sum_report').report_action(self, data=data)

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
                'company_id': [(i['id']) for i in self.company_id],
                'supervisor_id': [(i['id']) for i in self.supervisor_id],
                'cancel_state': self.cancel_state,
                'hide_uncompleted_orders': self.hide_uncompleted_orders,
                'group_by_type': self.group_by_type,

            },
        }
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # data = json.loads(data_excel)
        return self.generate_xlsx_report(workbook,data)
        # return self.env.ref('yousentech_car_maintain.print_wo_sum_xlsx').report_action(self, data=data)
    
    @api.model
    def generate_xlsx_report(self, workbook, data):

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


        harajs_compelete = self.env['mizan.car.work.procedure.master'].search(domain_compelete)
        harajs_un_compelete = self.env['mizan.car.work.procedure.master'].search(domain_un_compelete)
        if harajs_compelete or harajs_un_compelete:
            l_companys = self.env['res.company'].search([('id', 'in', l_company_ids1)])
            l_company = self.env['res.company'].search([('id', 'in', l_company_id)])
            l_partner = self.env['res.partner'].search([('id', 'in', l_partner_id)])
            l_supervisors = self.env['hr.supervisor.assignments'].search([('id', 'in', l_supervisor_id)])

            for account in l_companys:
                work_order_date = []
            
                for rec in harajs_compelete.sorted(lambda o: o.end_date):
                    if len(work_order_date)== 0:
                        work_order_date.append(rec.end_date.strftime('%Y-%m-%d'))

                    if rec.end_date.strftime('%Y-%m-%d') not in work_order_date:
                        work_order_date.append(rec.end_date.strftime('%Y-%m-%d'))
                for rec in harajs_un_compelete.sorted(lambda o: o.end_date):
                    if len(work_order_date)== 0:
                        work_order_date.append(rec.create_date.strftime('%Y-%m-%d'))

                    if rec.create_date.strftime('%Y-%m-%d') not in work_order_date:
                        work_order_date.append(rec.create_date.strftime('%Y-%m-%d'))
                 
                
                sheet = workbook.add_worksheet('تقرير اوامر العمل ')
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
                print("l_group_by_type",l_group_by_type)
                if l_group_by_type == 'by_type':
                                
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
                        
                        sheet.merge_range(address_row , date_col, address_row, date_col + 3,
                            ' الاوامر المكتملة ',
                              format_header)
                        address_col = 1
                        address_row = 20
                        sheet.write(address_row, address_col , ' الرقم ', format_address)
                        sheet.write(address_row, address_col + 1, ' تاريخ الخروج', format_address)
                        sheet.write(address_row, address_col + 2, 'نوع السيارة', format_address)
                        sheet.write(address_row, address_col + 3, 'رقم اللوحة', format_address)
                        sheet.write(address_row, address_col + 4, 'خدمة', format_address)
                        sheet.write(address_row, address_col + 5, 'قطع غيار', format_address)
                        sheet.write(address_row, address_col + 6, 'امر العمل', format_address)
                        sheet.write(address_row, address_col + 7, 'رقم الفاتورة', format_address)
                        sheet.write(address_row, address_col + 8, 'الحالة', format_address)
                        sheet.write(address_row, address_col + 9, 'وقت الدخول', format_address)
                        sheet.write(address_row, address_col + 10, 'وقت الخروج', format_address)

                        sheet.write(address_row, address_col + 11, 'المشرف', format_address)
                       
                        address_row += 1
                        l_cnt = 0
                        l_services_total = 0
                        l_spare_parts_total = 0
                       
                        for line in harajs_compelete:
                            address_row += 1
                            l_cnt += 1
                         
                            l_services_total += sum(l.total_before_tax for l in line.result_lines)
                            l_spare_parts_total += sum(l.total_before_tax for l in line.lines_spare_parts)
                            sheet.write(address_row, address_col , l_cnt , format_string)
                            if line.end_date:
                                sheet.write(address_row, address_col + 1 ,line.end_date.strftime('%d-%m-%Y'), format_string)
                            else:
                                sheet.write(address_row, address_col + 1 ,"", format_string)

                            
                            sheet.write(address_row, address_col + 2 , line.car_type_id.name, format_string)
                            sheet.write(address_row, address_col + 3 ,line.entry_card_id.car_panel_no, format_string)
                            sheet.write(address_row, address_col + 4 ,  round(sum(l.total_before_tax for l in line.result_lines),2)  , format_string)

                            sheet.write(address_row, address_col + 5 , round(sum(l.total_before_tax for l in line.lines_spare_parts),2), format_string)
                            sheet.write(address_row, address_col + 6 ,line.id  , format_string)
                            sheet.write(address_row, address_col + 7 , line.create_invoice_manually_id.name  , format_string)
                            sheet.write(address_row, address_col + 8 , line.state , format_string)
                            sheet.write(address_row, address_col + 9 , line.get_datetime_zone_user(line.create_date) , format_string)
                            sheet.write(address_row, address_col + 10 , line.get_datetime_zone_user(line.end_date) , format_string)
                            sheet.write(address_row, address_col + 11 , line.entry_card_id.supervisor_name.supervisor_emp_id.name , format_string)
                            

                        address_row += 1
                        sheet.merge_range(address_row, address_col, address_row, address_col + 3,
                                         'اجمالي الاوامر المكتملة  ', format_totally_row)
                        sheet.write(address_row, address_col + 4, l_services_total , format_totally_row)
                        sheet.write(address_row, address_col + 5, l_spare_parts_total, format_totally_row)
                        # ================================================================================================
                        address_row += 5
                        sheet.merge_range(address_row , date_col, address_row, date_col + 3,
                            ' الاوامر الغير مكتملة ',
                              format_header)
                        address_col = 1
                        address_row = 20
                        sheet.write(address_row, address_col , ' الرقم ', format_address)
                        sheet.write(address_row, address_col + 1, ' تاريخ الخروج', format_address)
                        sheet.write(address_row, address_col + 2, 'نوع السيارة', format_address)
                        sheet.write(address_row, address_col + 3, 'رقم اللوحة', format_address)
                        sheet.write(address_row, address_col + 4, 'خدمة', format_address)
                        sheet.write(address_row, address_col + 5, 'قطع غيار', format_address)
                        sheet.write(address_row, address_col + 6, 'امر العمل', format_address)
                        sheet.write(address_row, address_col + 7, 'رقم الفاتورة', format_address)
                        sheet.write(address_row, address_col + 8, 'الحالة', format_address)
                        sheet.write(address_row, address_col + 9, 'وقت الدخول', format_address)
                        sheet.write(address_row, address_col + 10, 'وقت الخروج', format_address)

                        sheet.write(address_row, address_col + 11, 'المشرف', format_address)
                       
                        address_row += 1
                        l_cnt = 0
                        l_services_total = 0
                        l_spare_parts_total = 0
                       
                        for line in harajs_un_compelete:
                            address_row += 1
                            l_cnt += 1
                         
                            l_services_total += sum(l.total_before_tax for l in line.result_lines)
                            l_spare_parts_total += sum(l.total_before_tax for l in line.lines_spare_parts)
                            sheet.write(address_row, address_col , l_cnt , format_string)
                            if line.end_date:
                                sheet.write(address_row, address_col + 1 ,line.end_date.strftime('%d-%m-%Y'), format_string)
                            else:
                                sheet.write(address_row, address_col + 1 ,"", format_string)

                            
                            sheet.write(address_row, address_col + 2 , line.car_type_id.name, format_string)
                            sheet.write(address_row, address_col + 3 ,line.entry_card_id.car_panel_no, format_string)
                            sheet.write(address_row, address_col + 4 ,  round(sum(l.total_before_tax for l in line.result_lines),2)  , format_string)

                            sheet.write(address_row, address_col + 5 , round(sum(l.total_before_tax for l in line.lines_spare_parts),2), format_string)
                            sheet.write(address_row, address_col + 6 ,line.id  , format_string)
                            sheet.write(address_row, address_col + 7 , line.create_invoice_manually_id.name  , format_string)
                            sheet.write(address_row, address_col + 8 , line.state , format_string)
                            sheet.write(address_row, address_col + 9 , line.get_datetime_zone_user(line.create_date) , format_string)
                            sheet.write(address_row, address_col + 10 , line.get_datetime_zone_user(line.end_date) , format_string)
                            sheet.write(address_row, address_col + 11 , line.entry_card_id.supervisor_name.supervisor_emp_id.name , format_string)
                            

                        address_row += 1
                        sheet.merge_range(address_row, address_col, address_row, address_col + 3,
                                         'اجمالي الاوامر الغير مكتملة  ', format_totally_row)
                        sheet.write(address_row, address_col + 4, l_services_total , format_totally_row)
                        sheet.write(address_row, address_col + 5, l_spare_parts_total, format_totally_row)

                elif l_group_by_type == 'by_date':
                                
                       
                     
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
                        
                       
                        l_cnt = 0
                        l_services_total = 0
                        l_spare_parts_total = 0
                        address_row = 14
                        for l_date in work_order_date:
                            address_col = 1
                            address_row += 1
                            sheet.merge_range(address_row , date_col, address_row, date_col + 13,
                                    ' تاريخ' + l_date,  format_header_date)
                            address_row += 2
                            sheet.merge_range(address_row , date_col, address_row, date_col + 3,
                            ' الاوامر المكتملة ' ,  format_header)
                           
                            address_col = 1
                            address_row += 2
                            sheet.write(address_row, address_col , ' الرقم ', format_address)
                            sheet.write(address_row, address_col + 1, ' تاريخ الخروج', format_address)
                            sheet.write(address_row, address_col + 2, 'نوع السيارة', format_address)
                            sheet.write(address_row, address_col + 3, 'رقم اللوحة', format_address)
                            sheet.write(address_row, address_col + 4, 'خدمة', format_address)
                            sheet.write(address_row, address_col + 5, 'قطع غيار', format_address)
                            sheet.write(address_row, address_col + 6, 'امر العمل', format_address)
                            sheet.write(address_row, address_col + 7, 'رقم الفاتورة', format_address)
                            sheet.write(address_row, address_col + 8, 'الحالة', format_address)
                            sheet.write(address_row, address_col + 9, 'وقت الدخول', format_address)
                            sheet.write(address_row, address_col + 10, 'وقت الخروج', format_address)

                            sheet.write(address_row, address_col + 11, 'المشرف', format_address)
                       
                            for line in harajs_compelete.filtered(lambda x:x.end_date.strftime('%Y-%m-%d') == l_date):
                                address_row += 1
                                l_cnt += 1
                            
                                l_services_total += sum(l.total_before_tax for l in line.result_lines)
                                l_spare_parts_total += sum(l.total_before_tax for l in line.lines_spare_parts)
                                sheet.write(address_row, address_col , l_cnt , format_string)
                                if line.end_date:
                                    sheet.write(address_row, address_col + 1 ,line.end_date.strftime('%d-%m-%Y'), format_string)
                                else:
                                    sheet.write(address_row, address_col + 1 ," ", format_string)

                                
                                sheet.write(address_row, address_col + 2 , line.car_type_id.name, format_string)
                                sheet.write(address_row, address_col + 3 ,line.entry_card_id.car_panel_no, format_string)
                                sheet.write(address_row, address_col + 4 ,  round(sum(l.total_before_tax for l in line.result_lines),2)  , format_string)

                                sheet.write(address_row, address_col + 5 , round(sum(l.total_before_tax for l in line.lines_spare_parts),2), format_string)
                                sheet.write(address_row, address_col + 6 ,line.id  , format_string)
                                sheet.write(address_row, address_col + 7 , line.create_invoice_manually_id.name  , format_string)
                                sheet.write(address_row, address_col + 8 , line.state , format_string)
                                sheet.write(address_row, address_col + 9 , line.get_datetime_zone_user(line.create_date) , format_string)
                                sheet.write(address_row, address_col + 10 , line.get_datetime_zone_user(line.end_date) , format_string)
                                sheet.write(address_row, address_col + 11 , line.entry_card_id.supervisor_name.supervisor_emp_id.name , format_string)
                                

                            address_row += 1
                            sheet.merge_range(address_row, address_col, address_row, address_col + 3,
                                            'اجمالي الاوامر المكتملة  بتاريخ: ' + l_date, format_totally_row)
                            sheet.write(address_row, address_col + 4, l_services_total , format_totally_row)
                            sheet.write(address_row, address_col + 5, l_spare_parts_total, format_totally_row)
                            # ================================================================================================
                            address_row += 2
                            sheet.merge_range(address_row , date_col, address_row, date_col + 3,
                                ' الاوامر الغير مكتملة ',
                                format_header)
                            address_col = 1
                            address_row += 2
                            sheet.write(address_row, address_col , ' الرقم ', format_address)
                            sheet.write(address_row, address_col + 1, ' تاريخ الخروج', format_address)
                            sheet.write(address_row, address_col + 2, 'نوع السيارة', format_address)
                            sheet.write(address_row, address_col + 3, 'رقم اللوحة', format_address)
                            sheet.write(address_row, address_col + 4, 'خدمة', format_address)
                            sheet.write(address_row, address_col + 5, 'قطع غيار', format_address)
                            sheet.write(address_row, address_col + 6, 'امر العمل', format_address)
                            sheet.write(address_row, address_col + 7, 'رقم الفاتورة', format_address)
                            sheet.write(address_row, address_col + 8, 'الحالة', format_address)
                            sheet.write(address_row, address_col + 9, 'وقت الدخول', format_address)
                            sheet.write(address_row, address_col + 10, 'وقت الخروج', format_address)

                            sheet.write(address_row, address_col + 11, 'المشرف', format_address)
                        
                            address_row += 1
                            l_cnt = 0
                            l_services_total = 0
                            l_spare_parts_total = 0
                        
                            for line in harajs_un_compelete:
                                address_row += 1
                                l_cnt += 1
                            
                                l_services_total += sum(l.total_before_tax for l in line.result_lines)
                                l_spare_parts_total += sum(l.total_before_tax for l in line.lines_spare_parts)
                                sheet.write(address_row, address_col , l_cnt , format_string)
                                if line.end_date:
                                    sheet.write(address_row, address_col + 1 ,line.end_date.strftime('%d-%m-%Y'), format_string)
                                else:
                                    sheet.write(address_row, address_col + 1 ,"", format_string)
                                sheet.write(address_row, address_col + 2 , line.car_type_id.name, format_string)
                                sheet.write(address_row, address_col + 3 ,line.entry_card_id.car_panel_no, format_string)
                                sheet.write(address_row, address_col + 4 ,  round(sum(l.total_before_tax for l in line.result_lines),2)  , format_string)

                                sheet.write(address_row, address_col + 5 , round(sum(l.total_before_tax for l in line.lines_spare_parts),2), format_string)
                                sheet.write(address_row, address_col + 6 ,line.id  , format_string)
                                sheet.write(address_row, address_col + 7 , line.create_invoice_manually_id.name  , format_string)
                                sheet.write(address_row, address_col + 8 , line.state , format_string)
                                sheet.write(address_row, address_col + 9 , line.get_datetime_zone_user(line.create_date) , format_string)
                                sheet.write(address_row, address_col + 10 , line.get_datetime_zone_user(line.end_date) , format_string)
                                sheet.write(address_row, address_col + 11 , line.entry_card_id.supervisor_name.supervisor_emp_id.name , format_string)
                                

                            address_row += 1
                            sheet.merge_range(address_row, address_col, address_row, address_col + 3,
                                            'اجمالي الاوامر الغير مكتملة بتاريخ : '+ l_date, format_totally_row)
                            sheet.write(address_row, address_col + 4, l_services_total , format_totally_row)
                            sheet.write(address_row, address_col + 5, l_spare_parts_total, format_totally_row)
                            address_row += 1
                            sheet.merge_range(address_row, address_col ,address_row, address_col + 13,
                            "===============================================================================", format_string)
                            address_row += 5
    
        else:
            raise ValidationError("لا توجد بيانات")

    
    
class mizan_wo_report_module_pdf_report(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.work_order_sum_report_view'

    @api.model
    def _get_report_values(self, *args, data=None):
        arg = data
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

        harajs_compelete = self.env['mizan.car.work.procedure.master'].search(domain_compelete)
        harajs_un_compelete = self.env['mizan.car.work.procedure.master'].search(domain_un_compelete)
      
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
