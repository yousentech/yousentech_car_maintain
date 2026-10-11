# -*- coding: utf-8 -*-
"""Vehicle registry foundation; existing visit fields remain unchanged."""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError


class MizanCustomerVehicle(models.Model):
    _name = 'mizan.customer.vehicle'
    _description = 'Customer Vehicle'
    _rec_name = 'display_name'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='العميل', required=True, index=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='الشركة', required=True, default=lambda self: self.env.company, index=True)
    plate_number = fields.Char(string='رقم اللوحة', required=True, index=True)
    vin = fields.Char(string='رقم الهيكل', index=True, copy=False)
    manufacturer_id = fields.Many2one('mizan.car.manufactory', string='الشركة المصنعة')
    car_type_id = fields.Many2one('mizan.car.types', string='نوع السيارة')
    car_size_id = fields.Many2one('mizan.car.size', string='حجم السيارة')
    model_year = fields.Integer(string='سنة الصنع')
    color = fields.Char(string='اللون')
    last_odometer = fields.Float(string='آخر قراءة عداد')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='ملاحظات')
    display_name = fields.Char(compute='_compute_display_name')

    _sql_constraints = [
        ('vin_company_unique', 'unique(vin, company_id)', 'رقم الهيكل مسجل مسبقاً لهذه الشركة.'),
        ('odometer_nonnegative', 'CHECK(last_odometer >= 0)', 'قراءة العداد لا يمكن أن تكون سالبة.'),
    ]

    @api.depends('plate_number', 'vin', 'partner_id.name')
    def _compute_display_name(self):
        for vehicle in self:
            vehicle.display_name = vehicle.plate_number or vehicle.vin or vehicle.partner_id.name or _('سيارة')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('plate_number'):
                vals['plate_number'] = self._normalize_plate(vals['plate_number'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('plate_number'):
            vals = dict(vals, plate_number=self._normalize_plate(vals['plate_number']))
        return super().write(vals)

    @api.model
    def _normalize_plate(self, plate):
        return ' '.join((plate or '').strip().upper().split())

    @api.constrains('partner_id', 'company_id', 'plate_number')
    def _check_duplicate_customer_plate(self):
        for vehicle in self:
            if not vehicle.partner_id or not vehicle.plate_number:
                continue
            matches = self.search([('partner_id', '=', vehicle.partner_id.id),
                                   ('company_id', '=', vehicle.company_id.id),
                                   ('id', '!=', vehicle.id)])
            if any(self._normalize_plate(other.plate_number) == self._normalize_plate(vehicle.plate_number)
                   for other in matches):
                raise ValidationError(_('هذه اللوحة مسجلة مسبقًا لنفس العميل، اختر السيارة الموجودة بدل إنشاء سجل مكرر.'))

    @api.onchange('manufacturer_id')
    def _onchange_manufacturer(self):
        if self.car_type_id and self.car_type_id.header_id != self.manufacturer_id:
            self.car_type_id = False

    @api.constrains('manufacturer_id', 'car_type_id')
    def _check_manufacturer_type(self):
        for vehicle in self:
            if vehicle.car_type_id and vehicle.car_type_id.header_id != vehicle.manufacturer_id:
                raise ValidationError(_('نوع السيارة يجب أن يتبع الشركة المصنعة المختارة.'))

    @api.constrains('plate_number')
    def _check_plate_number(self):
        for vehicle in self:
            if not vehicle.plate_number or not vehicle.plate_number.strip():
                raise ValidationError(_('رقم لوحة السيارة مطلوب.'))

    @api.constrains('vin')
    def _check_vin(self):
        for vehicle in self:
            if vehicle.vin and (len(vehicle.vin) != 17 or any(c in 'IOQ' for c in vehicle.vin.upper())):
                raise ValidationError(_('رقم الهيكل يجب أن يتكون من 17 رمزاً دون I أو O أو Q.'))

    @api.constrains('model_year')
    def _check_model_year(self):
        for vehicle in self:
            if vehicle.model_year and not 1886 <= vehicle.model_year <= fields.Date.today().year + 2:
                raise ValidationError(_('سنة الصنع غير صحيحة.'))


class MizanEntryCardVehicle(models.Model):
    _inherit = 'mizan.car.entry.card.master'

    vehicle_id = fields.Many2one(
        'mizan.customer.vehicle', string='السيارة المسجلة',
        domain="[('partner_id', '=', partner_id), ('company_id', '=', company_id)]",
        copy=False, index=True,
    )

    @api.onchange('partner_id')
    def _onchange_vehicle_partner(self):
        if self.vehicle_id and self.vehicle_id.partner_id != self.partner_id:
            self.vehicle_id = False
            self.car_panel_no = False
            self.vin_no = False

    @api.constrains('vehicle_id', 'partner_id', 'company_id')
    def _check_vehicle_owner(self):
        for card in self:
            if card.vehicle_id and (
                card.vehicle_id.partner_id != card.partner_id
                or card.vehicle_id.company_id != card.company_id
            ):
                raise ValidationError(_('السيارة المختارة يجب أن تتبع العميل والشركة المحددين.'))

    @api.onchange('vehicle_id')
    def _onchange_registered_vehicle(self):
        if not self.vehicle_id:
            return
        vehicle = self.vehicle_id
        self.partner_id = vehicle.partner_id
        self.car_panel_no = vehicle.plate_number or False
        self.vin_no = vehicle.vin or False
        self.car_manuf_id = vehicle.manufacturer_id
        self.car_type_id = vehicle.car_type_id
        self.car_size_id = vehicle.car_size_id
