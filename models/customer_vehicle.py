# -*- coding: utf-8 -*-
"""Vehicle registry foundation; existing visit fields remain unchanged."""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MizanCustomerVehicle(models.Model):
    _name = 'mizan.customer.vehicle'
    _description = 'Customer Vehicle'
    _rec_name = 'display_name'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='العميل', required=True, index=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='الشركة', required=True, default=lambda self: self.env.company, index=True)
    plate_number = fields.Char(string='رقم اللوحة', index=True)
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
