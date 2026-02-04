from odoo import http
from odoo.http import request
import json

class XLSXReport(http.Controller):
    @http.route('/xlsx_report', type='http', auth='user', csrf=False)
    def get_report_xlsx(self, **kwargs):
        """Generate an XLSX report"""
        try:
            # Get parameters
            model = kwargs.get('model')
            data_str = kwargs.get('data', '{}')
            report_name = kwargs.get('report_name', 'report')
            
            # Parse data
            form_data = json.loads(data_str)
            data = {'form': form_data}
            
            # Generate Excel
            ReportModel = request.env[model].with_user(request.session.uid)
            excel_data = ReportModel.get_xlsx_report(data)
            
            if not excel_data:
                return request.make_response("No data", status=500)
            
            # **CRITICAL: Return proper response with Excel data**
            return request.make_response(
                excel_data,  # The binary Excel data
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{report_name}.xlsx"'),
                    ('Content-Length', str(len(excel_data))) 
                ]
            )
            
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            return request.make_response(error_msg, headers=[('Content-Type', 'text/plain')])







