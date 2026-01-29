{
    'name': 'Car Maintenance System',
    'version': '17.0.1.0.0',
    'summary': 'Car Maintenance and Workshop Management',
    'category': 'Services/Maintenance',
    'author': 'Developers Team',
    'maintainer': 'qimamhd-Tech Techno Solutions',
    'company': 'qimamhd-Tech Techno Solutions',
    'website': 'https://www.qimamhd-tech.com',
    
    'depends': [
        'base',
        'account',
        'hr',
        'stock',
        'sale',
        'yousentech_inventory_minus_quantity'
    ],
    
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        
        'views/views.xml',
        
        # 'wizard/res_config_setting.xml',
        
        'views/product_template.xml',
        'views/entry_card_view.xml',
        'views/work_order_view.xml',
        'views/checkup_order_view.xml',
        'views/wo_services_lines_view.xml',
        
        'views/hr_tecnical_assignment_.xml',
        'views/hr_supervisor_assignment_.xml',
        'views/hr_salesman_assignment.xml',
        'views/special_emp_view.xml',
        
        'views/account_move.xml',
        'views/account_journal.xml',
        'views/account_move_close_cash.xml',
        'views/register_payment.xml',
        
        
        'views/sale_order.xml',
        
        'views/stock_picking.xml',
        'views/stock_picking_workstation.xml',
        'views/stock_locations.xml',
        'views/close_inventory_operations.xml',
        
        'views/cash_closed_view.xml',
        
        'views/wo_sales_analysis.xml',
        'views/wo_work_order_analysis.xml',
        'views/wo_services_analysis.xml',
        'views/wo_spare_part_analysis.xml',
        'views/wo_technicals_analysis.xml',
        'views/wo_auditor_analysis.xml',
        
        'views/mizan_product_wizard.xml',
        'wizard/message_confirm.xml',
        
        'pdf_templates/mizan_wo_report_module.xml',
        'pdf_templates/car_checkup_report.xml',
        'pdf_templates/car_work_order_report.xml',
        'pdf_templates/wo_invoice_payments_report.xml',
        'pdf_templates/close_cash_report.xml',
        'pdf_templates/wo_technical_report.xml',
        'pdf_templates/all_reports_views.xml',
        
       
    ],
    
    'demo': [],
    
    'assets': {
        'web.assets_backend': [
            # 'yousentech_car_maintain/static/src/js/*.js',
            # 'yousentech_car_maintain/static/src/css/*.css',
        ],
    },
    
    'license': 'LGPL-3',
    'images': [
        'static/description/icon.png',
    ],
    'sequence': -100,
    'installable': True,
    'application': True,
    'auto_install': False,
}