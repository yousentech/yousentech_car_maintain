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

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._normalize_identity(vals) for vals in vals_list])

    def write(self, vals):
        vals = self._normalize_identity(vals)
        if 'partner_id' in vals:
            new_owner = self.env['res.partner'].browse(vals['partner_id'])
            for vehicle in self:
                if vehicle.partner_id != new_owner and self.env['ycm.v2.order'].search_count([
                    ('vehicle_id', '=', vehicle.id),
                    ('state', 'not in', ('draft', 'cancelled')),
                ]):
                    raise ValidationError(_('Ownership transfer requires a controlled workflow while active work orders exist.'))
        return super().write(vals)

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
