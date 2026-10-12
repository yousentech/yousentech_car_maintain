from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestReception(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name':'Test Workshop Customer'})
        cls.make = cls.env['yt.reception.make'].create({'name':'Test Make'})
        cls.model = cls.env['yt.reception.model'].create({'name':'Test Model','make_id':cls.make.id})
        cls.vehicle = cls.env['yt.reception.vehicle'].create({
            'partner_id':cls.partner.id,'plate':'ABC-123','plate_country':'SA',
            'make_id':cls.make.id,'model_id':cls.model.id,'year':2021,
        })

    def test_vehicle_and_order_save(self):
        order=self.env['yt.reception.order'].create({
            'partner_id':self.partner.id,'vehicle_id':self.vehicle.id,
            'odometer_in':1234,
        })
        result=order.save_reception({'reception_notes':'Checked'},['Noise when starting'],['Oil change'])
        self.assertEqual(result['name'],order.name)
        self.assertEqual(order.complaint_ids.name,'Noise when starting')
        self.assertEqual(order.request_ids.name,'Oil change')
        order.save_reception({'odometer_in':1300},['Second complaint'],[])
        self.assertEqual(len(order.complaint_ids),1)
        self.assertEqual(order.complaint_ids.name,'Second complaint')

    def test_vin_validation(self):
        with self.assertRaises(ValidationError):
            self.env['yt.reception.vehicle'].create({
                'partner_id':self.partner.id,'plate':'ZZZ9','vin':'IOQ00000000000000'
            })

    def test_vehicle_partner_validation(self):
        partner2=self.env['res.partner'].create({'name':'Other Customer'})
        with self.assertRaises(ValidationError):
            self.env['yt.reception.order'].create({'partner_id':partner2.id,'vehicle_id':self.vehicle.id})
