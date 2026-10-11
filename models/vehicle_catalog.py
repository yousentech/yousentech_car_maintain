from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


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

class WorkshopVehicleCatalogIntake(models.AbstractModel):
    _name = 'ycm.v2.vehicle.catalog.intake'
    _description = 'Workshop intake catalog quick create'

    @api.model
    def create_make(self, name):
        if not self.env.user.has_group('yousentech_car_maintain.group_workshop_user'):
            raise UserError(_('Workshop access required.'))
        name = ' '.join((name or '').strip().split())
        if not name:
            raise UserError(_('Enter a manufacturer name.'))
        Make = self.env['ycm.v2.vehicle.make']
        found = Make.search([('name', '=ilike', name)], limit=1)
        if found:
            if not found.active:
                raise UserError(_('This manufacturer is archived; ask a manager to reactivate it.'))
            return found.read(['name'])[0]
        # Explicit, narrow sudo: workshop intake staff can register a catalog
        # entry but cannot obtain general catalog management permissions.
        return Make.sudo().create({'name': name}).read(['name'])[0]

    @api.model
    def create_model(self, make_id, name):
        if not self.env.user.has_group('yousentech_car_maintain.group_workshop_user'):
            raise UserError(_('Workshop access required.'))
        name = ' '.join((name or '').strip().split())
        if not name:
            raise UserError(_('Enter a model name.'))
        Make = self.env['ycm.v2.vehicle.make']
        make = Make.browse(int(make_id)).exists()
        if not make or not make.active:
            raise UserError(_('Select an active manufacturer first.'))
        Model = self.env['ycm.v2.vehicle.model']
        found = Model.search([('make_id', '=', make.id), ('name', '=ilike', name)], limit=1)
        if found:
            if not found.active:
                raise UserError(_('This model is archived; ask a manager to reactivate it.'))
            return found.read(['name', 'make_id'])[0]
        return Model.sudo().create({'name': name, 'make_id': make.id}).read(['name', 'make_id'])[0]
