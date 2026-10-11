import re
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WorkshopV2VehicleIntegrity(models.Model):
    _inherit = 'ycm.v2.vehicle'

    plate_country = fields.Char(required=True, default='SA', index=True)
    plate_type = fields.Selection([
        ('private', 'Private'), ('commercial', 'Commercial'),
        ('public', 'Public'), ('other', 'Other'),
    ], required=True, default='private')
    plate_key = fields.Char(required=True, index=True, copy=False,
                            help='Canonical plate identity, computed from plate_number.')
    ownership_history_ids = fields.One2many('ycm.v2.vehicle.owner', 'vehicle_id', readonly=True)

    _sql_constraints = [
        ('plate_identity_company_unique',
         'unique(company_id, plate_country, plate_type, plate_key)',
         'This vehicle plate is already registered in this company.'),
    ]

    @api.model
    def _canonical_plate(self, value):
        value = unicodedata.normalize('NFKC', value or '').upper()
        value = ''.join(str(unicodedata.digit(c)) if c.isdigit() and not c.isascii() else c for c in value)
        return ''.join(c for c in value if c.isalnum())

    @api.model
    def _normalize_identity(self, vals):
        vals = dict(vals)
        if 'plate_country' in vals and vals['plate_country']:
            vals['plate_country'] = vals['plate_country'].strip().upper()
        if 'plate_number' in vals:
            vals['plate_key'] = self._canonical_plate(vals['plate_number'])
        return vals

    @api.model
    def find_existing_vehicle(self, plate_number=False, vin=False,
                              plate_country='SA', plate_type='private'):
        """Look up a vehicle before intake; never reassign its owner silently."""
        self.check_access_rights('read')
        company = self.env.company
        candidates = self.browse()
        if vin:
            normalized_vin = ''.join(str(vin).strip().upper().split())
            candidates |= self.search([
                ('company_id', '=', company.id), ('vin', '=', normalized_vin),
            ], limit=1)
        if plate_number:
            key = self._canonical_plate(plate_number)
            if key:
                candidates |= self.search([
                    ('company_id', '=', company.id),
                    ('plate_country', '=', (plate_country or 'SA').strip().upper()),
                    ('plate_type', '=', plate_type),
                    ('plate_key', '=', key),
                ], limit=1)
        if len(candidates) > 1:
            raise ValidationError(_('Plate and VIN belong to different registered vehicles.'))
        return candidates.read(['plate_number', 'vin', 'partner_id', 'make', 'model', 'year'])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            normalized = self._normalize_identity(vals)
            matches = self.find_existing_vehicle(
                normalized.get('plate_number'),
                normalized.get('vin'),
                normalized.get('plate_country', 'SA'),
                normalized.get('plate_type', 'private'),
            )
            if matches:
                raise ValidationError(_('Vehicle already registered. Select the existing vehicle instead.'))
        vehicles = super().create([self._normalize_identity(vals) for vals in vals_list])
        for vehicle in vehicles:
            self.env['ycm.v2.vehicle.owner'].create({
                'vehicle_id': vehicle.id, 'partner_id': vehicle.partner_id.id,
                'reason': _('Initial registration'),
            })
        return vehicles

    def write(self, vals):
        vals = self._normalize_identity(vals)
        if 'partner_id' in vals:
            new_owner = self.env['res.partner'].browse(vals['partner_id'])
            for vehicle in self:
                if vehicle.partner_id != new_owner and self.env['ycm.v2.order'].search_count([
                    ('vehicle_id', '=', vehicle.id),
                    ('state', 'in', ('estimate', 'approved', 'in_progress')),
                ]):
                    raise ValidationError(_('Ownership transfer requires a controlled workflow while active work orders exist.'))
        transfers = [(vehicle, vehicle.partner_id.id) for vehicle in self] if 'partner_id' in vals else []
        result = super().write(vals)
        for vehicle, previous_owner_id in transfers:
            if vehicle.partner_id.id == previous_owner_id:
                continue
            active_history = self.env['ycm.v2.vehicle.owner'].search([
                ('vehicle_id', '=', vehicle.id), ('date_to', '=', False),
            ])
            active_history.write({'date_to': fields.Datetime.now()})
            self.env['ycm.v2.vehicle.owner'].create({
                'vehicle_id': vehicle.id, 'partner_id': vehicle.partner_id.id,
                'reason': _('Ownership transfer'),
            })
        return result

    @api.constrains('plate_key', 'plate_country', 'plate_type')
    def _validate_plate_identity(self):
        for vehicle in self:
            if not vehicle.plate_key or len(vehicle.plate_key) < 2:
                raise ValidationError(_('Enter a valid plate identity.'))
            if not re.fullmatch(r'[A-Z]{2}', vehicle.plate_country or ''):
                raise ValidationError(_('Plate country must be a two-letter country code.'))


class WorkshopV2VehicleOwner(models.Model):
    _name = 'ycm.v2.vehicle.owner'
    _description = 'Workshop V2 Vehicle Ownership History'
    _order = 'date_from desc, id desc'

    vehicle_id = fields.Many2one('ycm.v2.vehicle', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict')
    date_from = fields.Datetime(required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(readonly=True)
    reason = fields.Char()
    company_id = fields.Many2one('res.company', related='vehicle_id.company_id', store=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_('Ownership end date cannot precede start date.'))
