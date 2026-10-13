{
 'name': 'YousenTech Workshop Reception V4',
 'version': '17.0.4.3.0',
 'category': 'Services/Automotive',
 'license': 'LGPL-3',
 'depends': ['base', 'web', 'mail', 'hr', 'product', 'sale_management', 'sale_stock', 'account', 'yousentech_inventory_default', 'yousentech_inventory_minus_quantity'],
 'data': [
  'security/ir.model.access.csv',
  'security/record_rules.xml',
  'views/reception.xml',
  'views/workshop_sales.xml',
  'reports/inspection_report.xml',
 ],
 'assets': {
  'web.assets_backend': [
   'yousentech_car_maintain/static/src/reception/native_reception.scss',
  ],
 },
 'installable': True,
 'application': True,
}
