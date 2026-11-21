from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMaintenanceEvents(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('yousentech_car_maintain.group_workshop_periodic')
        cls.company = cls.env.company
        cls.settings = cls.env['yt.workshop.finance.settings'].search(
            [('company_id', '=', cls.company.id)], limit=1) or cls.env['yt.workshop.finance.settings'].create(
            {'company_id': cls.company.id})
        cls.settings.write({'periodic_interval_km': 10000, 'periodic_interval_days': 180})
        cls.partner = cls.env['res.partner'].create({'name': 'Maintenance Customer'})
        cls.vehicle = cls.env['yt.reception.vehicle'].create({
            'partner_id': cls.partner.id, 'plate': 'MNT100', 'plate_country': 'SA'})
        cls.engine = cls.env['yt.oil.type'].create({'name': 'Engine Oil Test'})
        cls.gear = cls.env['yt.oil.type'].create({'name': 'Gear Oil Test'})
        Product = cls.env['product.product']
        cls.service = Product.create({'name': 'Periodic Service', 'type': 'service', 'sale_ok': True})
        cls.service_short = Product.create({
            'name': 'Short Service', 'type': 'service', 'sale_ok': True,
            'yt_periodic_interval_km': 5000, 'yt_periodic_interval_days': 120})
        cls.service_long = Product.create({
            'name': 'Long Service', 'type': 'service', 'sale_ok': True,
            'yt_periodic_interval_km': 8000, 'yt_periodic_interval_days': 90})
        cls.engine_oil = Product.create({
            'name': 'Engine 5W30', 'type': 'consu', 'sale_ok': True, 'yt_is_oil': True,
            'yt_oil_type_id': cls.engine.id, 'yt_oil_interval_km': 5000, 'yt_oil_interval_days': 90})
        cls.engine_oil_2 = Product.create({
            'name': 'Engine 0W20', 'type': 'consu', 'sale_ok': True, 'yt_is_oil': True,
            'yt_oil_type_id': cls.engine.id, 'yt_oil_interval_km': 10000, 'yt_oil_interval_days': 60})
        cls.gear_oil = Product.create({
            'name': 'ATF', 'type': 'consu', 'sale_ok': True, 'yt_is_oil': True,
            'yt_oil_type_id': cls.gear.id, 'yt_oil_interval_km': 60000, 'yt_oil_interval_days': 730})

    def _order(self, products, odometer_in=80000, odometer_out=0, periodic=False):
        order = self.env['yt.reception.order'].create({
            'partner_id': self.partner.id, 'vehicle_id': self.vehicle.id,
            'odometer_in': odometer_in, 'odometer_out': odometer_out})
        self.env['yt.reception.sale.line'].create([
            {'order_id': order.id, 'product_id': p.id, 'name': p.name, 'price_unit': 10.0}
            for p in products])
        if periodic:
            order.yt_is_periodic = True
        return order

    def _complete(self, order):
        order.write({'state': 'done'})

    def test_periodic_event_uses_company_interval(self):
        order = self._order(self.service, odometer_in=80000, odometer_out=80100, periodic=True)
        self._complete(order)
        event = order.service_event_ids
        self.assertEqual(len(event), 1)
        self.assertEqual(event.track_type, 'periodic')
        self.assertEqual(event.interval_source, 'company')
        self.assertEqual(event.done_odometer, 80100)
        self.assertEqual(event.next_due_km, 90100)
        self.assertEqual(event.next_due_date, event.done_date + timedelta(days=180))
        self.assertTrue(order.done_at)

    def test_odometer_in_fallback_and_shortest_special_interval(self):
        order = self._order(self.service_short | self.service_long, odometer_in=50000, periodic=True)
        self._complete(order)
        event = order.service_event_ids
        self.assertEqual(event.done_odometer, 50000)
        self.assertEqual(event.interval_km, 5000)
        self.assertEqual(event.interval_days, 90)
        self.assertEqual(event.interval_source, 'service')

    def test_no_periodic_event_without_checkbox(self):
        order = self._order(self.service)
        self._complete(order)
        self.assertFalse(order.service_event_ids)

    def test_oil_events_one_per_type(self):
        order = self._order(self.engine_oil | self.engine_oil_2 | self.gear_oil, odometer_in=70000)
        self._complete(order)
        events = order.service_event_ids
        self.assertEqual(len(events), 2)
        engine = events.filtered(lambda e: e.oil_type_id == self.engine)
        self.assertEqual(engine.interval_km, 5000)
        self.assertEqual(engine.interval_days, 60)
        self.assertEqual(engine.next_due_km, 75000)

    def test_cancel_and_recomplete_does_not_duplicate(self):
        order = self._order(self.service | self.engine_oil, periodic=True)
        self._complete(order)
        self.assertEqual(len(order.service_event_ids), 2)
        order.write({'state': 'cancelled'})
        self.assertEqual(set(order.service_event_ids.mapped('state')), {'cancelled'})
        order.write({'state': 'draft'})
        order.write({'state': 'done'})
        self.assertEqual(len(order.service_event_ids), 2)
        self.assertEqual(set(order.service_event_ids.mapped('state')), {'active'})

    def test_missing_odometer_keeps_date_due_only(self):
        order = self._order(self.engine_oil, odometer_in=0)
        self._complete(order)
        event = order.service_event_ids
        self.assertFalse(event.has_odometer)
        self.assertEqual(event.next_due_km, 0.0)
        self.assertTrue(event.next_due_date)

    def test_periodic_flag_locked_after_completion(self):
        order = self._order(self.service, periodic=True)
        self._complete(order)
        with self.assertRaises(UserError):
            order.yt_is_periodic = False

    def test_settings_change_keeps_history(self):
        order = self._order(self.service, periodic=True)
        self._complete(order)
        self.settings.periodic_interval_km = 20000
        self.assertEqual(order.service_event_ids.interval_km, 10000)
        self.assertEqual(fields.Date.today() >= order.service_event_ids.done_date, True)
