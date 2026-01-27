{
    'name': 'Car Maintenance System',
    'version': '17.0.1.0.0',
    'summary': 'Car Maintenance and Workshop Management',
    'category': 'Services/Maintenance',
    'author': 'Developers Team',
    'maintainer': 'QimamHD-Tech Techno Solutions',
    'company': 'QimamHD-Tech Techno Solutions',
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
        # Security
        'security/ir.model.access.csv',
        'security/security.xml',
        
        # Main menu views 
        'views/views.xml',
        
        # Configuration
        'views/res_config_setting.xml',
        
        # Models
        'views/product_template.xml',
        'views/entry_card_view.xml',
        'views/work_order_view.xml',
        'views/checkup_order_view.xml',
        'views/wo_services_lines_view.xml',
        
        # HR related
        'views/hr_tecnical_assignment_.xml',
        'views/hr_supervisor_assignment_.xml',
        'views/hr_salesman_assignment.xml',
        'views/special_emp_view.xml',
        
        # Accounting
        'views/account_move.xml',
        'views/account_journal.xml',
        'views/account_move_close_cash.xml',
        'views/register_payment.xml',
        
        # Sales
        'views/sale_order.xml',
        
        # Inventory
        'views/stock_picking.xml',
        'views/stock_picking_workstation.xml',
        'views/stock_locations.xml',
        'views/close_inventory_operations.xml',
        
        # Cash Management
        'views/cash_closed_view.xml',
        
        # Analysis Views
        'views/wo_sales_analysis.xml',
        'views/wo_work_order_analysis.xml',
        'views/wo_services_analysis.xml',
        'views/wo_spare_part_analysis.xml',
        'views/wo_technicals_analysis.xml',
        'views/wo_auditor_analysis.xml',
        
        # Wizards
        'views/mizan_product_wizard.xml',
        'views/message_confirm.xml',
        
        # Reports
        'reports/car_checkup_report.xml',
        'reports/car_work_order_report.xml',
        'reports/work_order_sum_report.xml',
        'reports/wo_invoice_payments_report.xml',
        'reports/close_cash_report.xml',
        'reports/wo_technical_report.xml',
        'reports/all_reports_views.xml',
        
       
    ],
    
    'demo': [],
    
    'assets': {
        'web.assets_backend': [
            # Add JS/CSS files here if needed
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