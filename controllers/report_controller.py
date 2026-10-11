from odoo import http
from werkzeug.exceptions import BadRequest, Forbidden
from odoo.http import request
import json

class XLSXReport(http.Controller):
    @http.route('/xlsx_report', type='http', auth='user', csrf=True)
    def get_report_xlsx(self, **kwargs):
        """Generate an XLSX report"""
        try:
            # Get parameters
            model = kwargs.get('model')
            allowed_models = {'mizan.wo.report.module', 'mizan.wo.invoice.payments.report', 'mizan.wo.technical.report'}
            if model not in allowed_models:
                raise Forbidden('Report model is not allowed')
            data_str = kwargs.get('data', '{}')
            report_name = kwargs.get('report_name', 'report')
            
            # Parse data
            form_data = json.loads(data_str)
            if not isinstance(form_data, dict):
                raise BadRequest('Invalid report data')
            data = {'form': form_data}
            
            # Generate Excel
            ReportModel = request.env[model].with_user(request.session.uid)
            ReportModel.check_access_rights('read')
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
            
        except (Forbidden, BadRequest):
            raise
        except Exception:
            return request.make_response('Report generation failed', status=500, headers=[('Content-Type', 'text/plain')])







