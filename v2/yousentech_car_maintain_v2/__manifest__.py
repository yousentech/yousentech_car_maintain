{
    'name': 'Workshop V2 - One Screen OWL',
    'version': '17.0.2.1.0',
    'summary': 'Standalone automotive service workshop core',
    'category': 'Services/Maintenance',
    'author': 'YousenTech',
    'depends': ['base', 'web', 'product', 'account', 'stock'],
    'data': ['security/workshop_security.xml', 'security/ir.model.access.csv', 'views/workshop_action.xml'],
    'assets': {'web.assets_backend': [
        'yousentech_car_maintain_v2/static/src/workshop/workshop.js',
        'yousentech_car_maintain_v2/static/src/workshop/workshop.xml',
        'yousentech_car_maintain_v2/static/src/workshop/workshop.scss',
    ]},
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}
