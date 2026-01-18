import xmlrpc.client

url='http://localhost:8013'
db='almajd_2023'
username='admin'
password='admin'
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
common.version()
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
# models.execute_kw(db, uid, password, 'res.partner', 'check_access_rights', ['read'], {'raise_exception': False})
# models.execute_kw(db, uid, password, 'res.partner', 'search', [[['is_company', '=', True]]])
# models.execute_kw(db, uid, password, 'res.partner', 'search', [[['is_company', '=', True]]], {'offset': 10, 'limit': 5})
# models.execute_kw(db, uid, password, 'res.partner', 'search_count', [[['is_company', '=', True]]])
 
action_post = models.execute_kw(db, uid, password, 'mizan.car.work.procedure.master', 'return_car_data',[221])
print("action_post",action_post)

