from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WorkshopVehicleMake(models.Model):
    _name = 'ycm.v2.vehicle.make'
    _description = 'Vehicle Manufacturer'
    _order = 'name'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    model_ids = fields.One2many('ycm.v2.vehicle.model', 'make_id')

    _sql_constraints = [
        ('make_name_unique', 'unique(name)', 'Manufacturer already exists.'),
    ]


class WorkshopVehicleModel(models.Model):
    _name = 'ycm.v2.vehicle.model'
    _description = 'Vehicle Model'
    _order = 'make_id, name'

    name = fields.Char(required=True, index=True)
    make_id = fields.Many2one('ycm.v2.vehicle.make', required=True, ondelete='restrict', index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('make_model_unique', 'unique(make_id, name)', 'Model already exists for this manufacturer.'),
    ]

    @api.constrains('make_id')
    def _check_make(self):
        for record in self:
            if not record.make_id.active:
                raise ValidationError(_('Select an active manufacturer.'))
