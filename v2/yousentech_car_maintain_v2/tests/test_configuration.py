from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWorkshopV2Configuration(TransactionCase):
    def test_plate_normalization_and_duplicate(self):
        partner = self.env['res.partner'].create({'name': 'Workshop test customer'})
        Vehicle = self.env['ycm.v2.vehicle']
        first = Vehicle.create({'partner_id': partner.id, 'plate_number': 'ABC 123',
                                'plate_country': 'SA', 'plate_type': 'private'})
        self.assertEqual(first.plate_key, 'ABC123')
        with self.assertRaises(Exception), self.cr.savepoint():
            Vehicle.create({'partner_id': partner.id, 'plate_number': 'abc-123',
                            'plate_country': 'SA', 'plate_type': 'private'})

    def test_invalid_plate(self):
        partner = self.env['res.partner'].create({'name': 'Workshop test customer 2'})
        with self.assertRaises(ValidationError):
            self.env['ycm.v2.vehicle'].create({'partner_id': partner.id, 'plate_number': ' '})
