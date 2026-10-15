{
 'name': 'YousenTech Workshop Reception V4',
 'version': '17.0.4.4.0',
 'category': 'Services/Automotive',
 'license': 'LGPL-3',
 'depends': ['base', 'web', 'mail', 'hr', 'product', 'sale_management', 'sale_stock', 'account', 'yousentech_inventory_default', 'yousentech_inventory_minus_quantity', 'yousentech_invoicing_base_journal', 'yousentech_invoicing_journal', 'yousentech_invoicing_payment_journal'],
 'data': [
  'security/record_rules.xml',
  'security/ir.model.access.csv',
  'views/reception.xml',
  'reports/inspection_report.xml',
  'reports/workshop_order_report.xml',
  'views/workshop_sales.xml',
 ],
 'assets': {
  'web.assets_backend': [
   'yousentech_car_maintain/static/src/reception/native_reception.scss',
  ],
 },
 'installable': True,
 'application': True,
}
