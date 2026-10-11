from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WorkshopV2Configuration(models.Model):
    _name = 'ycm.v2.workshop'
    _description = 'Workshop V2 Configuration'
    _check_company_auto = True
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', required=True, check_company=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', required=True, check_company=True, ondelete='restrict',
                                  string='Workshop Internal Location')
    parts_source_location_id = fields.Many2one('stock.location', required=True, check_company=True,
                                               ondelete='restrict', string='Parts Store Location')
    return_location_id = fields.Many2one('stock.location', required=True, check_company=True,
                                        ondelete='restrict', string='Returns Location')
    note = fields.Text()

    _sql_constraints = [
        ('workshop_location_company_unique', 'unique(company_id, location_id)',
         'A workshop location may only be assigned to one workshop in a company.'),
    ]

    @api.constrains('company_id', 'warehouse_id', 'location_id', 'parts_source_location_id', 'return_location_id')
    def _check_locations(self):
        for rec in self:
            if rec.warehouse_id.company_id != rec.company_id:
                raise ValidationError(_('Warehouse must belong to the workshop company.'))
            locations = rec.location_id | rec.parts_source_location_id | rec.return_location_id
            for location in locations:
                if location.usage != 'internal':
                    raise ValidationError(_('Workshop, parts store and returns locations must be internal.'))
                if location.company_id and location.company_id != rec.company_id:
                    raise ValidationError(_('Stock location belongs to another company.'))
            if rec.location_id == rec.parts_source_location_id:
                raise ValidationError(_('Workshop and parts store locations must differ.'))
            if rec.location_id == rec.return_location_id:
                raise ValidationError(_('Workshop and returns locations must differ.'))
