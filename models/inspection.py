from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError


class InspectionCategory(models.Model):
    _name = 'yt.inspection.category'
    _description = 'تصنيف مكونات الفحص'
    _order = 'sequence, id'
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    component_ids = fields.One2many('yt.inspection.component', 'category_id', string='مكونات التصنيف')
    component_count = fields.Integer(compute='_compute_component_count', string='عدد المكونات')

    def _compute_component_count(self):
        for category in self:
            category.component_count = len(category.component_ids)


class InspectionComponent(models.Model):
    _name = 'yt.inspection.component'
    _description = 'مكون الفحص'
    _order = 'category_id, sequence, id'
    name = fields.Char(required=True, translate=True)
    category_id = fields.Many2one('yt.inspection.category', required=True, ondelete='restrict')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    required = fields.Boolean(string='إلزامي', default=False)


class InspectionLine(models.Model):
    _name = 'yt.inspection.line'
    _description = 'نتيجة فحص مكون السيارة'
    _order = 'sequence, id'
    _sql_constraints = [
        ('unique_order_component', 'unique(order_id, component_id)', 'لا يمكن تكرار المكون في الفحص نفسه.')
    ]
    order_id = fields.Many2one('yt.reception.order', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True, readonly=True)
    component_id = fields.Many2one('yt.inspection.component', required=True, ondelete='restrict')
    sequence = fields.Integer(related='component_id.sequence', store=True)
    category_id = fields.Many2one(related='component_id.category_id', readonly=True)
    component_name = fields.Char(string='اسم المكون عند الفحص', readonly=True)
    required_at_inspection = fields.Boolean(readonly=True)
    condition = fields.Selection([
        ('not_checked', 'لم يُفحص'),
        ('good', 'سليم'),
        ('follow_up', 'يحتاج متابعة'),
        ('bad', 'غير سليم')
    ], required=True, default='not_checked', string='الحالة')
    notes = fields.Text(string='ملاحظات المكون')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            component = self.env['yt.inspection.component'].browse(vals.get('component_id')).exists()
            if not component:
                raise ValidationError(_('اختر مكون فحص صحيحاً.'))
            if not component.active:
                raise ValidationError(_('لا يمكن إضافة مكون مؤرشف.'))
            vals['component_name'] = component.name
            vals['required_at_inspection'] = component.required
        return super().create(vals_list)

    def write(self, vals):
        if 'component_id' in vals:
            raise UserError(_('لا يمكن استبدال مكون محفوظ؛ احذف السطر وأضف مكوناً آخر.'))
        if any(line.order_id.inspection_state == 'done' for line in self):
            raise UserError(_('الفحص معتمد ولا يمكن تعديل نتائجه.'))
        return super().write(vals)

    def unlink(self):
        if any(line.order_id.inspection_state == 'done' for line in self):
            raise UserError(_('لا يمكن حذف نتائج فحص معتمد.'))
        return super().unlink()

    @api.constrains('condition', 'notes')
    def _check_line(self):
        for line in self:
            if line.condition in ('bad', 'follow_up') and not (line.notes or '').strip():
                raise ValidationError(_('أضف ملاحظة عند اختيار غير سليم أو يحتاج متابعة: %s') % line.component_name)


class ReceptionInspection(models.Model):
    _inherit = 'yt.reception.order'

    inspection_state = fields.Selection([
        ('draft', 'مسودة'), ('done', 'مكتمل')
    ], default='draft', required=True, copy=False, tracking=True)
    inspection_at = fields.Datetime(default=fields.Datetime.now, copy=False)
    inspector_id = fields.Many2one('res.users', string='فني الفحص السابق', readonly=True)
    inspection_employee_id = fields.Many2one('hr.employee', string='فني الفحص', domain="[('is_workshop_technician', '=', True)]")
    inspection_category_ids = fields.Many2many('yt.inspection.category', string='تصنيفات الفحص')
    inspection_location = fields.Selection([
        ('workshop', 'داخل الورشة'), ('outside', 'خارج الورشة')
    ], default='workshop', required=True)
    inspection_general_notes = fields.Text()
    inspection_exterior_notes = fields.Text()
    inspection_line_ids = fields.One2many('yt.inspection.line', 'order_id', string='مكونات الفحص', copy=False)

    @api.onchange('inspection_category_ids')
    def _onchange_inspection_categories(self):
        """Synchronize components with chosen categories while retaining entered results."""
        for order in self:
            if order.inspection_state == 'done':
                continue
            components = self.env['yt.inspection.component'].search([
                ('active', '=', True),
                ('category_id', 'in', order.inspection_category_ids.ids),
            ], order='category_id,sequence,id')
            previous = {
                line.component_id.id: (line.condition, line.notes)
                for line in order.inspection_line_ids if line.component_id
            }
            order.inspection_line_ids = [
                Command.clear(),
                *[
                    Command.create({
                        'component_id': component.id,
                        'condition': previous.get(component.id, ('not_checked', False))[0],
                        'notes': previous.get(component.id, ('not_checked', False))[1],
                    })
                    for component in components
                ],
            ]

    def action_load_inspection_components(self):
        for order in self:
            if order.state != 'draft' or order.inspection_state == 'done':
                raise UserError(_('لا يمكن تعديل فحص أمر عمل مغلق أو معتمد.'))
            existing = set(order.inspection_line_ids.mapped('component_id').ids)
            components = self.env['yt.inspection.component'].search([('active', '=', True), ('category_id', 'in', order.inspection_category_ids.ids)])
            vals = [{'order_id': order.id, 'component_id': c.id} for c in components if c.id not in existing]
            if vals:
                self.env['yt.inspection.line'].create(vals)
        return True

    def action_finish_inspection(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('لا يمكن اعتماد فحص أمر عمل ملغي.'))
            if order.inspection_state == 'done':
                continue
            if order.inspection_employee_id and not order.inspection_employee_id.is_workshop_technician:
                raise ValidationError(_('فني الفحص يجب أن يكون موظفاً مؤشراً كفني ورشة.'))
            if not order.inspection_employee_id or not order.inspection_at:
                raise ValidationError(_('فني الفحص وتاريخ الفحص مطلوبان.'))
            if not order.inspection_category_ids:
                raise ValidationError(_('اختر تصنيف فحص واحداً على الأقل.'))
            lines = order.inspection_line_ids
            if not lines:
                raise ValidationError(_('أضف مكونات الفحص أولاً.'))
            mandatory = self.env['yt.inspection.component'].search([('active', '=', True), ('required', '=', True), ('category_id', 'in', order.inspection_category_ids.ids)])
            missing = mandatory - lines.mapped('component_id')
            if missing:
                raise ValidationError(_('مكونات إلزامية غير مضافة: %s') % ', '.join(missing.mapped('name')))
            unchecked = lines.filtered(lambda l: l.condition == 'not_checked' and l.required_at_inspection)
            if unchecked:
                raise ValidationError(_('يجب فحص المكونات الإلزامية: %s') % ', '.join(unchecked.mapped('component_name')))
            order.inspection_state = 'done'
        return True

    def action_reopen_inspection(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('إعادة فتح الفحص تتطلب صلاحية مدير النظام.'))
        for order in self:
            if order.state != 'draft':
                raise UserError(_('لا يمكن إعادة فتح فحص أمر ملغي.'))
            order.inspection_state = 'draft'
        return True
