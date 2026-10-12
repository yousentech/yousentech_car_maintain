from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


INSPECTION_COMPONENTS = [
    ('engine', 'المحرك'),
    ('gearbox', 'ناقل الحركة'),
    ('ac', 'نظام التكييف'),
    ('brakes', 'نظام الفرامل'),
    ('steering', 'نظام التوجيه'),
    ('suspension', 'نظام التعليق'),
    ('electrical', 'النظام الكهربائي'),
    ('battery', 'البطارية'),
    ('tires', 'الإطارات'),
    ('fluids', 'الزيوت والسوائل'),
]
INSPECTION_STATES = [
    ('good', 'جيد'),
    ('inspect', 'يحتاج فحص'),
    ('repair', 'يحتاج صيانة'),
    ('damaged', 'تالف'),
]


class WorkshopInspection(models.Model):
    _name = 'ycm.v2.inspection'
    _description = 'Work order vehicle inspection'
    _order = 'id desc'
    _check_company_auto = True

    order_id = fields.Many2one('ycm.v2.order', required=True, index=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, index=True)
    inspector_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    inspected_at = fields.Datetime(required=True, default=fields.Datetime.now)
    exterior_notes = fields.Text()
    additional_notes = fields.Text()
    component_ids = fields.One2many('ycm.v2.inspection.component', 'inspection_id', string='فحص المكونات')

    _sql_constraints = [
        ('one_inspection_per_order', 'unique(order_id)', 'Only one inspection is allowed per work order.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['ycm.v2.order'].browse(vals.get('order_id')).exists()
            if not order or order.state not in ('draft', 'estimate'):
                raise UserError(_('Inspection is only editable before approval.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(rec.order_id.state not in ('draft', 'estimate') for rec in self):
            raise UserError(_('Inspection is locked after approval.'))
        return super().write(vals)

    def unlink(self):
        if any(rec.order_id.state not in ('draft', 'estimate') for rec in self):
            raise UserError(_('Inspection is locked after approval.'))
        return super().unlink()


class WorkshopInspectionComponent(models.Model):
    _name = 'ycm.v2.inspection.component'
    _description = 'Vehicle inspection component result'
    _order = 'id'
    _check_company_auto = True

    inspection_id = fields.Many2one('ycm.v2.inspection', required=True, ondelete='cascade', index=True, check_company=True)
    company_id = fields.Many2one('res.company', related='inspection_id.company_id', store=True, index=True)
    component = fields.Selection(INSPECTION_COMPONENTS, required=True)
    condition = fields.Selection(INSPECTION_STATES, required=True, default='inspect')
    notes = fields.Char()

    _sql_constraints = [
        ('unique_component_per_inspection', 'unique(inspection_id, component)', 'Component already inspected.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            inspection = self.env['ycm.v2.inspection'].browse(vals.get('inspection_id')).exists()
            if not inspection or inspection.order_id.state not in ('draft', 'estimate'):
                raise UserError(_('Inspection is locked after approval.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(line.inspection_id.order_id.state not in ('draft', 'estimate') for line in self):
            raise UserError(_('Inspection is locked after approval.'))
        return super().write(vals)

    def unlink(self):
        if any(line.inspection_id.order_id.state not in ('draft', 'estimate') for line in self):
            raise UserError(_('Inspection is locked after approval.'))
        return super().unlink()


class WorkshopOrderInspection(models.Model):
    _inherit = 'ycm.v2.order'

    inspection_ids = fields.One2many('ycm.v2.inspection', 'order_id', string='فحص السيارة')

    def ui_inspection_detail(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        inspection = self.inspection_ids[:1]
        return {
            'inspector_id': inspection.inspector_id.id if inspection else False,
            'inspected_at': fields.Datetime.to_string(inspection.inspected_at) if inspection else False,
            'exterior_notes': inspection.exterior_notes or '' if inspection else '',
            'additional_notes': inspection.additional_notes or '' if inspection else '',
            'components': {
                line.component: {'condition': line.condition, 'notes': line.notes or ''}
                for line in inspection.component_ids
            } if inspection else {},
        }

    def ui_save_inspection(self, payload):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        if self.state not in ('draft', 'estimate'):
            raise UserError(_('Inspection is locked after approval.'))
        if not isinstance(payload, dict):
            raise ValidationError(_('Invalid inspection data.'))
        allowed = dict(INSPECTION_COMPONENTS)
        conditions = dict(INSPECTION_STATES)
        components = payload.get('components', {})
        if not isinstance(components, dict) or set(components) - set(allowed):
            raise ValidationError(_('Unknown inspection component.'))
        for key, entry in components.items():
            if not isinstance(entry, dict) or entry.get('condition') not in conditions:
                raise ValidationError(_('Invalid component condition: %s') % key)
            if not isinstance(entry.get('notes', ''), str) or len(entry.get('notes', '')) > 500:
                raise ValidationError(_('Invalid component notes.'))
        notes = {}
        for field_name in ('exterior_notes', 'additional_notes'):
            value = payload.get(field_name, '')
            if not isinstance(value, str) or len(value) > 10000:
                raise ValidationError(_('Invalid inspection notes.'))
            notes[field_name] = value
        inspection = self.inspection_ids[:1]
        if inspection:
            inspection.write(notes)
        else:
            inspection = self.env['ycm.v2.inspection'].create({'order_id': self.id, **notes})
        existing = {line.component: line for line in inspection.component_ids}
        for key, entry in components.items():
            values = {'condition': entry['condition'], 'notes': entry.get('notes', '')}
            if key in existing:
                existing[key].write(values)
            else:
                self.env['ycm.v2.inspection.component'].create({
                    'inspection_id': inspection.id, 'component': key, **values,
                })
        return self.ui_inspection_detail()
