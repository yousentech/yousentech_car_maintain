from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


PERIODIC_GROUP = 'yousentech_car_maintain.group_workshop_periodic'


class WorkshopOilType(models.Model):
    """Oil tracks (engine, gearbox, differential...). Follow-up is per type, not per product."""
    _name = 'yt.oil.type'
    _description = 'نوع الزيت'
    _order = 'sequence, id'

    name = fields.Char(string='نوع الزيت', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_count = fields.Integer(string='الأصناف المرتبطة', compute='_compute_product_count')

    _sql_constraints = [('oil_type_name_unique', 'unique(name)', 'نوع الزيت موجود مسبقاً.')]

    def _compute_product_count(self):
        data = self.env['product.template'].sudo()._read_group(
            [('yt_oil_type_id', 'in', self.ids)], ['yt_oil_type_id'], ['__count'])
        counts = {oil_type.id: count for oil_type, count in data}
        for oil_type in self:
            oil_type.product_count = counts.get(oil_type.id, 0)


class WorkshopProductMaintenance(models.Model):
    _inherit = 'product.template'

    # Periodic maintenance: special interval for a service product (overrides the company default).
    yt_periodic_interval_km = fields.Float(string='فترة الصيانة الدورية الخاصة (كم)')
    yt_periodic_interval_days = fields.Integer(string='فترة الصيانة الدورية الخاصة (يوم)')
    # Oil follow-up.
    yt_is_oil = fields.Boolean(string='صنف زيت')
    yt_oil_type_id = fields.Many2one('yt.oil.type', string='نوع الزيت', ondelete='restrict')
    yt_oil_interval_km = fields.Float(string='الممشى الافتراضي للتغيير القادم (كم)')
    yt_oil_interval_days = fields.Integer(string='فترة التغيير القادم (يوم)')

    @api.constrains('yt_periodic_interval_km', 'yt_periodic_interval_days',
                    'yt_oil_interval_km', 'yt_oil_interval_days', 'yt_is_oil', 'yt_oil_type_id')
    def _check_yt_maintenance_intervals(self):
        for product in self:
            if min(product.yt_periodic_interval_km, product.yt_periodic_interval_days,
                   product.yt_oil_interval_km, product.yt_oil_interval_days) < 0:
                raise ValidationError(_('فترات الصيانة والزيت لا يمكن أن تكون سالبة.'))
            if product.yt_is_oil and not product.yt_oil_type_id:
                raise ValidationError(_('حدد نوع الزيت للصنف: %s') % product.display_name)

    @api.onchange('yt_is_oil')
    def _onchange_yt_is_oil(self):
        for product in self:
            if not product.yt_is_oil:
                product.yt_oil_type_id = False
                product.yt_oil_interval_km = 0.0
                product.yt_oil_interval_days = 0


class WorkshopMaintenanceSettings(models.Model):
    _inherit = 'yt.workshop.finance.settings'

    periodic_interval_km = fields.Float(string='فترة الصيانة الدورية (كم)')
    periodic_interval_days = fields.Integer(string='فترة الصيانة الدورية (يوم)')
    due_soon_days = fields.Integer(string='تنبيه قريب الاستحقاق قبل (يوم)', default=15)
    due_soon_km = fields.Float(string='تنبيه قريب الاستحقاق قبل (كم)', default=500)
    enable_oil_tracking = fields.Boolean(
        string='تفعيل متابعة الزيوت',
        help='عند الإيقاف (الافتراضي) لا تُسجَّل أحداث الزيوت ولا تظهر حقولها وقوائمها وأقسامها في التقارير. '
             'الصيانة الدورية تعمل مستقلة عن هذا الخيار.')
    enforce_maintenance_odometer = fields.Boolean(
        string='منع إكمال أوامر الصيانة والزيوت بدون عداد صحيح',
        help='عند التفعيل: لا يكتمل أمر العمل الذي يحتوي صنف زيت أو مفعَّل كصيانة دورية إذا كان العداد صفراً '
             'أو أقل من آخر قراءة مسجلة للسيارة. باقي أوامر العمل لا تتأثر.')

    @api.model
    def _yt_oil_enabled(self, company):
        return bool(self.sudo().search([('company_id', '=', company.id)], limit=1).enable_oil_tracking)

    @api.model
    def _yt_sync_oil_group(self):
        """Show oil fields/menus to internal users only while at least one company enables oil tracking."""
        group = self.env.ref('yousentech_car_maintain.group_workshop_oil_tracking_enabled', raise_if_not_found=False)
        user_group = self.env.ref('base.group_user')
        if not group:
            return
        enabled = bool(self.sudo().search_count([('enable_oil_tracking', '=', True)]))
        if enabled and group not in user_group.implied_ids:
            user_group.sudo().write({'implied_ids': [(4, group.id)]})
        elif not enabled and group in user_group.implied_ids:
            user_group.sudo().write({'implied_ids': [(3, group.id)]})
            group.sudo().write({'users': [(5, 0, 0)]})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any('enable_oil_tracking' in vals for vals in vals_list):
            self._yt_sync_oil_group()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'enable_oil_tracking' in vals:
            self._yt_sync_oil_group()
        return result

    @api.constrains('periodic_interval_km', 'periodic_interval_days', 'due_soon_days', 'due_soon_km')
    def _check_yt_periodic_settings(self):
        for settings in self:
            if min(settings.periodic_interval_km, settings.periodic_interval_days,
                   settings.due_soon_days, settings.due_soon_km) < 0:
                raise ValidationError(_('فترات الصيانة الدورية وحدود التنبيه لا يمكن أن تكون سالبة.'))


class WorkshopMaintenanceEvent(models.Model):
    """One maintenance event per (work order, track). Intervals and due values are
    snapshots taken at completion and are never recomputed from later settings."""
    _name = 'yt.vehicle.service.event'
    _description = 'حدث صيانة السيارة'
    _order = 'done_date desc, id desc'

    order_id = fields.Many2one('yt.reception.order', string='أمر العمل', required=True,
                               ondelete='cascade', index=True, readonly=True)
    vehicle_id = fields.Many2one('yt.reception.vehicle', string='السيارة', required=True,
                                 ondelete='cascade', index=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='العميل وقت الحدث', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True, index=True)
    track_type = fields.Selection([('periodic', 'صيانة دورية'), ('oil', 'تغيير زيت')],
                                  string='نوع الحدث', required=True, readonly=True)
    oil_type_id = fields.Many2one('yt.oil.type', string='نوع الزيت', readonly=True, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='الصنف', readonly=True)
    track_key = fields.Char(required=True, readonly=True, index=True)
    display_track = fields.Char(string='المسار', compute='_compute_display_track')
    done_date = fields.Date(string='تاريخ التنفيذ', required=True, readonly=True)
    done_odometer = fields.Float(string='ممشى التنفيذ', readonly=True, digits=(16, 0))
    has_odometer = fields.Boolean(string='الممشى متوفر', readonly=True)
    interval_km = fields.Float(string='الفترة المطبقة (كم)', readonly=True, digits=(16, 0))
    interval_days = fields.Integer(string='الفترة المطبقة (يوم)', readonly=True)
    interval_source = fields.Selection([
        ('company', 'إعدادات الشركة'), ('service', 'صنف الخدمة'),
        ('mixed', 'صنف الخدمة + الشركة'), ('oil_product', 'صنف الزيت'),
        ('history', 'ترحيل تاريخي'),
    ], string='مصدر الفترة', readonly=True)
    next_due_date = fields.Date(string='الاستحقاق القادم (تاريخ)', readonly=True)
    next_due_km = fields.Float(string='الاستحقاق القادم (كم)', readonly=True, digits=(16, 0))
    state = fields.Selection([('active', 'فعال'), ('cancelled', 'ملغي')],
                             string='الحالة', default='active', required=True, readonly=True)

    current_state = fields.Selection([
        ('current', 'الحالي'), ('superseded', 'مستبدل بحدث أحدث'), ('cancelled', 'ملغي'),
    ], string='وضع الحدث', compute='_compute_current_state')

    _sql_constraints = [
        ('order_track_unique', 'unique(order_id, track_key)',
         'يوجد حدث صيانة لهذا المسار في أمر العمل نفسه.'),
    ]

    @api.depends('track_type', 'oil_type_id')
    def _compute_display_track(self):
        for event in self:
            event.display_track = (event.oil_type_id.name if event.track_type == 'oil'
                                   else _('الصيانة الدورية'))

    def _compute_current_state(self):
        """Superseded = an active event of the same vehicle/track is more recent (not stored)."""
        active = self.filtered(lambda e: e.state == 'active')
        latest = {}
        if active:
            for event in self.search([('vehicle_id', 'in', active.vehicle_id.ids), ('state', '=', 'active')],
                                     order='done_date desc, id desc'):
                latest.setdefault((event.vehicle_id.id, event.track_key), event.id)
        for event in self:
            if event.state != 'active':
                event.current_state = 'cancelled'
            else:
                is_latest = latest.get((event.vehicle_id.id, event.track_key)) == event.id
                event.current_state = 'current' if is_latest else 'superseded'

    @api.depends('display_track', 'vehicle_id', 'done_date')
    def _compute_display_name(self):
        for event in self:
            event.display_name = '%s · %s · %s' % (
                event.display_track or '', event.vehicle_id.display_name or '', event.done_date or '')


class WorkshopVehicleFollowup(models.Model):
    _name = 'yt.vehicle.followup'
    _description = 'متابعة العميل للصيانة'
    _order = 'date desc, id desc'

    vehicle_id = fields.Many2one('yt.reception.vehicle', string='السيارة', required=True,
                                 ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='العميل', required=True)
    company_id = fields.Many2one('res.company', string='الشركة', required=True,
                                 default=lambda self: self.env.company, index=True)
    track_type = fields.Selection([('periodic', 'صيانة دورية'), ('oil', 'تغيير زيت')], string='المسار')
    oil_type_id = fields.Many2one('yt.oil.type', string='نوع الزيت', ondelete='restrict')
    date = fields.Datetime(string='التاريخ', default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', string='الموظف', default=lambda self: self.env.user, required=True)
    result = fields.Selection([
        ('contacted', 'تم التواصل'), ('no_answer', 'لا يرد'), ('booked', 'حجز موعد'),
        ('refused', 'رفض'), ('sold', 'باع السيارة'),
    ], string='النتيجة', required=True)
    note = fields.Text(string='ملاحظة')
    next_date = fields.Date(string='موعد المتابعة القادمة')

    @api.onchange('vehicle_id')
    def _onchange_followup_vehicle(self):
        for followup in self:
            if followup.vehicle_id:
                followup.partner_id = followup.vehicle_id.partner_id
                followup.company_id = followup.vehicle_id.company_id or self.env.company

    @api.constrains('vehicle_id', 'company_id', 'track_type', 'oil_type_id')
    def _check_followup(self):
        for followup in self:
            if followup.vehicle_id.company_id and followup.vehicle_id.company_id != followup.company_id:
                raise ValidationError(_('المتابعة يجب أن تتبع شركة السيارة.'))
            if followup.track_type == 'oil' and not followup.oil_type_id:
                raise ValidationError(_('حدد نوع الزيت عند متابعة تغيير الزيت.'))


class WorkshopVehicleMaintenance(models.Model):
    _inherit = 'yt.reception.vehicle'

    # Owner changes are tracked; order history keeps the owner at the time of each order.
    partner_id = fields.Many2one(tracking=True)
    service_event_ids = fields.One2many('yt.vehicle.service.event', 'vehicle_id', string='أحداث الصيانة')
    followup_ids = fields.One2many('yt.vehicle.followup', 'vehicle_id', string='المتابعات')


class WorkshopOrderMaintenance(models.Model):
    _inherit = 'yt.reception.order'

    # Every state change (including «إرجاع للمسودة», cancel and re-open) is logged in the chatter.
    state = fields.Selection(tracking=True)
    yt_is_periodic = fields.Boolean(
        string='احتساب هذا الأمر كصيانة دورية', copy=False, tracking=True,
        groups=PERIODIC_GROUP,
        help='خيار داخلي لا يضيف بنداً أو مبلغاً إلى الفاتورة. يُسجَّل حدث الصيانة الدورية عند اكتمال التنفيذ.')
    done_at = fields.Datetime(string='تاريخ الاكتمال', readonly=True, copy=False)
    service_event_ids = fields.One2many('yt.vehicle.service.event', 'order_id', string='أحداث الصيانة')

    def write(self, vals):
        if 'yt_is_periodic' in vals:
            if not self.env.su and not self.env.user.has_group(PERIODIC_GROUP):
                raise UserError(_('تفعيل احتساب الصيانة الدورية يتطلب صلاحية الصيانة الدورية.'))
            if self.filtered(lambda order: order.state in ('done', 'cancelled')):
                raise UserError(_('لا يمكن تغيير احتساب الصيانة الدورية بعد اكتمال أمر العمل أو إلغائه.'))
        was_done = self.filtered(lambda order: order.state == 'done')
        if vals.get('state') == 'done' and 'done_at' not in vals:
            vals = dict(vals, done_at=fields.Datetime.now())
        result = super().write(vals)
        if 'state' in vals:
            if vals['state'] == 'done':
                self._yt_register_maintenance_events()
            else:
                was_done._yt_cancel_maintenance_events()
        return result

    # ------------------------------------------------------------------
    # Maintenance event registration (runs inside the completion transaction)
    # ------------------------------------------------------------------
    def _yt_done_odometer(self):
        """odometer_out when valid (> 0), else odometer_in; 0 means not available."""
        self.ensure_one()
        if self.odometer_out and self.odometer_out > 0:
            return self.odometer_out
        if self.odometer_in and self.odometer_in > 0:
            return self.odometer_in
        return 0.0

    @staticmethod
    def _yt_shortest(values):
        values = [value for value in values if value and value > 0]
        return min(values) if values else 0

    def _yt_periodic_interval(self):
        """Shortest special interval among the order's service products per dimension;
        a dimension without a special value falls back to the company setting."""
        self.ensure_one()
        products = self.sale_line_ids.filtered(
            lambda line: line.product_id.type == 'service').mapped('product_id.product_tmpl_id')
        special_km = self._yt_shortest(products.mapped('yt_periodic_interval_km'))
        special_days = self._yt_shortest(products.mapped('yt_periodic_interval_days'))
        settings = self.env['yt.workshop.finance.settings'].sudo().search(
            [('company_id', '=', self.company_id.id)], limit=1)
        km = special_km or settings.periodic_interval_km or 0.0
        days = special_days or settings.periodic_interval_days or 0
        used_special = bool(special_km or special_days)
        used_company = bool((not special_km and km) or (not special_days and days))
        source = 'mixed' if used_special and used_company else ('service' if used_special else 'company')
        return km, days, source

    def _yt_event_values(self, track_type, track_key, km, days, source, oil_type=False, product=False,
                         done_date=False):
        self.ensure_one()
        done_date = done_date or fields.Date.context_today(self, self.done_at or fields.Datetime.now())
        odometer = self._yt_done_odometer()
        return {
            'order_id': self.id,
            'vehicle_id': self.vehicle_id.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'track_type': track_type,
            'track_key': track_key,
            'oil_type_id': oil_type.id if oil_type else False,
            'product_id': product.id if product else False,
            'done_date': done_date,
            'done_odometer': odometer,
            'has_odometer': bool(odometer),
            'interval_km': km,
            'interval_days': days,
            'interval_source': source,
            'next_due_date': done_date + timedelta(days=days) if days else False,
            'next_due_km': odometer + km if (odometer and km) else 0.0,
            'state': 'active',
        }

    def _yt_register_maintenance_events(self):
        Event = self.env['yt.vehicle.service.event'].sudo()
        for order in self:
            values = []
            if order.sudo().yt_is_periodic:
                km, days, source = order._yt_periodic_interval()
                if km or days:
                    values.append(order._yt_event_values('periodic', 'periodic', km, days, source))
            if self.env['yt.workshop.finance.settings']._yt_oil_enabled(order.company_id):
                values += order._yt_oil_event_values('oil_product')
            existing = Event.with_context(active_test=False).search([('order_id', '=', order.id)])
            keys = set()
            for vals in values:
                keys.add(vals['track_key'])
                event = existing.filtered(lambda e: e.track_key == vals['track_key'])
                if event:
                    # Re-completion updates the same event; no duplicate is created.
                    event.write(vals)
                else:
                    Event.create(vals)
            # A track no longer present after re-completion is deactivated, never deleted.
            existing.filtered(lambda e: e.track_key not in keys and e.state == 'active').write(
                {'state': 'cancelled'})

    def _yt_oil_event_values(self, source, done_date=False):
        """One value dict per oil type found in the order lines (shortest interval per dimension)."""
        self.ensure_one()
        values = []
        oil_lines = self.sale_line_ids.filtered(
            lambda line: line.product_id.product_tmpl_id.yt_is_oil
            and line.product_id.product_tmpl_id.yt_oil_type_id)
        for oil_type in oil_lines.mapped('product_id.product_tmpl_id.yt_oil_type_id'):
            lines = oil_lines.filtered(
                lambda line: line.product_id.product_tmpl_id.yt_oil_type_id == oil_type)
            templates = lines.mapped('product_id.product_tmpl_id')
            km = self._yt_shortest(templates.mapped('yt_oil_interval_km'))
            days = self._yt_shortest(templates.mapped('yt_oil_interval_days'))
            if km or days:
                values.append(self._yt_event_values(
                    'oil', 'oil:%s' % oil_type.id, km, days, source,
                    oil_type=oil_type, product=lines[:1].product_id, done_date=done_date))
        return values

    def _yt_cancel_maintenance_events(self):
        events = self.env['yt.vehicle.service.event'].sudo().search(
            [('order_id', 'in', self.ids), ('state', '=', 'active')])
        events.write({'state': 'cancelled'})
