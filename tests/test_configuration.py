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

    def test_make_model_relationship_and_snapshot(self):
        partner = self.env['res.partner'].create({'name': 'Catalog owner'})
        Make = self.env['ycm.v2.vehicle.make']
        Model = self.env['ycm.v2.vehicle.model']
        toyota = Make.create({'name': 'Toyota TEST'})
        hyundai = Make.create({'name': 'Hyundai TEST'})
        yaris = Model.create({'name': 'Yaris TEST', 'make_id': toyota.id})
        accent = Model.create({'name': 'Accent TEST', 'make_id': hyundai.id})
        vehicle = self.env['ycm.v2.vehicle'].create({
            'partner_id': partner.id, 'plate_number': 'CAT 123',
            'make_id': toyota.id, 'model_id': yaris.id,
        })
        self.assertEqual(vehicle.make, toyota.name)
        self.assertEqual(vehicle.model, yaris.name)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            vehicle.write({'model_id': accent.id})
        vehicle.write({'make_id': hyundai.id})
        self.assertFalse(vehicle.model_id)
        self.assertFalse(vehicle.model)
        vehicle.write({'model_id': accent.id})
        self.assertEqual(vehicle.model, accent.name)

    def test_completed_order_does_not_block_owner_transfer(self):
        original = self.env['res.partner'].create({'name': 'Previous Owner TEST'})
        current = self.env['res.partner'].create({'name': 'Current Owner TEST'})
        vehicle = self.env['ycm.v2.vehicle'].create({
            'partner_id': original.id, 'plate_number': 'TRANSFER 123',
        })
        order = self.env['ycm.v2.order'].create({
            'partner_id': original.id, 'vehicle_id': vehicle.id,
        })
        order.with_context(ycm_v2_transition=True).write({'state': 'completed'})
        vehicle.write({'partner_id': current.id})
        self.assertEqual(vehicle.partner_id, current)
        self.assertEqual(order.partner_id, original)
        self.assertEqual(len(vehicle.ownership_history_ids), 2)
