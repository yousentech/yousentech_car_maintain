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

    def test_customer_multiple_vehicles_and_lookup(self):
        partner = self.env['res.partner'].create({'name': 'Fleet customer'})
        Vehicle = self.env['ycm.v2.vehicle']
        one = Vehicle.create({'partner_id': partner.id, 'plate_number': 'FLEET 101'})
        two = Vehicle.create({'partner_id': partner.id, 'plate_number': 'FLEET 102'})
        self.assertEqual(set(partner.workshop_vehicle_ids.ids), {one.id, two.id})
        found = Vehicle.find_existing_vehicle(plate_number='fleet-101')
        self.assertEqual(found[0]['id'], one.id)
        self.assertEqual(len(one.ownership_history_ids), 1)
        with self.assertRaises(ValidationError):
            Vehicle.create({'partner_id': partner.id, 'plate_number': 'fleet-101'})

    def test_existing_vehicle_not_reassigned_on_duplicate(self):
        first_owner = self.env['res.partner'].create({'name': 'Owner One'})
        second_owner = self.env['res.partner'].create({'name': 'Owner Two'})
        Vehicle = self.env['ycm.v2.vehicle']
        car = Vehicle.create({'partner_id': first_owner.id, 'plate_number': 'OWNER 100'})
        with self.assertRaises(ValidationError):
            Vehicle.create({'partner_id': second_owner.id, 'plate_number': 'owner100'})
        self.assertEqual(car.partner_id, first_owner)
