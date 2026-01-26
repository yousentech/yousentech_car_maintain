# -*- coding: utf-8 -*-
{
    'name': 'yousentech_car_maintain',
	'version': '17.0.1.0.0',
	'summary': 'yousentech_car_maintain',
	'category': 'Tools',
	'author': 'Developers team',
	'maintainer': 'qimamhd-tech Techno Solutions',
	'company': 'qimamhd-tech Techno Solutions',
	'website': 'https://www.qimamhd-tech.com',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','hr','stock','sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'views/hr_tecnical_assignment_.xml',
        'views/hr_supervisor_assignment_.xml',
        'views/hr_salesman_assignment.xml',

        'views/special_emp_view.xml',
        'views/mizan_product_wizard.xml',
        'views/register_payment.xml',

        'views/checkup_order_view.xml',
        'views/product_template.xml',

        'views/res_config_setting.xml',
        'views/entry_card_view.xml',
        'views/work_order_view.xml',
        'reports/car_checkup_report.xml',
        'views/stock_picking.xml',
        'views/stock_picking_workstation.xml',
        'views/account_move.xml',
        'views/sale_order.xml',
        'reports/car_work_order_report.xml',
        'reports/all_reports_views.xml',
        'reports/work_order_sum_report.xml',
        'reports/wo_invoice_payments_report.xml',

        'views/account_journal.xml',

        'views/cash_closed_view.xml',
        'views/account_move_close_cash.xml',
        'reports/close_cash_report.xml',
        'views/message_confirm.xml',
        #  'views/company.xml',
        'views/wo_services_lines_view.xml',
        'views/stock_locations.xml',
        'reports/wo_technical_report.xml',
        'views/wo_sales_analysis.xml',
        'views/wo_work_order_analysis.xml',
         'views/wo_services_analysis.xml',
         'views/wo_spare_part_analysis.xml',
           'views/wo_technicals_analysis.xml',
           'views/wo_auditor_analysis.xml',
                'views/close_inventory_operations.xml',
        #'wizards/recap.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
