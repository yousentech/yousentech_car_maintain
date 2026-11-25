"""Audit trail in the work order chatter (requested 2026-11-25).

Logging only: nothing here changes a computation, a validation or a workflow.
- Header fields of the work order use Odoo tracking.
- Service / spare-part lines have no chatter of their own, so every create, change and delete
  is posted on the work order with old → new values and the order total before → after.
- Payments linked to the order and the linked sale order are logged as they happen.
"""
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.tools.misc import format_amount


class WorkshopOrderAudit(models.Model):
    _inherit = 'yt.reception.order'

    # Header fields that affect price, stock, customer or vehicle data.
    partner_id = fields.Many2one(tracking=True)
    vehicle_id = fields.Many2one(tracking=True)
    odometer_in = fields.Float(tracking=True)
    odometer_out = fields.Float(tracking=True)
    branch_id = fields.Many2one(tracking=True)
    advisor_id = fields.Many2one(tracking=True)
    warranty = fields.Boolean(tracking=True)
    intake_method = fields.Selection(tracking=True)
    no_parts_needed = fields.Boolean(tracking=True)
    customer_source = fields.Char(tracking=True)
    work_source = fields.Char(tracking=True)
    discount_type = fields.Selection(tracking=True)
    discount_value = fields.Float(tracking=True)
    workshop_tax_id = fields.Many2one(tracking=True)
    location_id = fields.Many2one(tracking=True)
    sale_order_id = fields.Many2one(tracking=True)
    cancel_reason = fields.Text(tracking=True)

    def _yt_audit_total(self):
        self.ensure_one()
        return format_amount(self.env, self.amount_total, self.currency_id)

    def write(self, vals):
        payments_before = {o.id: set(o.advance_payment_ids.ids) for o in self} if 'advance_payment_ids' in vals else {}
        totals_before = ({o.id: o._yt_audit_total() for o in self}
                         if {'discount_type', 'discount_value', 'workshop_tax_id'} & set(vals) else {})
        result = super().write(vals)
        for order in self:
            if order.id in payments_before:
                added = order.advance_payment_ids.filtered(lambda p: p.id not in payments_before[order.id])
                for payment in added:
                    order.message_post(body=Markup(_('ربط دفعة بأمر العمل: %s — %s (%s)')) % (
                        payment._get_html_link(),
                        format_amount(self.env, payment.amount, payment.currency_id),
                        _('تحصيل') if payment.payment_type == 'inbound' else _('رد مبلغ')))
            if order.id in totals_before:
                after = order._yt_audit_total()
                if after != totals_before[order.id]:
                    order.message_post(body=Markup(_('الإجمالي النهائي بعد تعديل الخصم/الضريبة: %s ← %s')) % (
                        totals_before[order.id], after))
        return result


class WorkshopLineAudit(models.Model):
    _inherit = 'yt.reception.sale.line'

    _YT_AUDIT_FIELDS = ('product_id', 'name', 'product_uom_qty', 'price_unit', 'technician_ids',
                        'execution_done', 'pricing_policy_id', 'applied_cost', 'applied_markup')

    def _yt_audit_value(self, field_name):
        self.ensure_one()
        field = self._fields[field_name]
        value = self[field_name]
        if field.type == 'many2one':
            return value.display_name or '—'
        if field.type == 'many2many':
            return '، '.join(value.mapped('display_name')) or '—'
        if field.type == 'boolean':
            return _('نعم') if value else _('لا')
        if field.type == 'float':
            return '{:,.2f}'.format(value or 0.0)
        return value or '—'

    def _yt_audit_kind(self):
        self.ensure_one()
        return _('خدمة') if self.product_id.type == 'service' else _('قطعة غيار')

    def _yt_audit_label(self):
        self.ensure_one()
        return '%s «%s»' % (self._yt_audit_kind(), self.product_id.display_name or self.name or '')

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.env['yt.reception.order'].browse(
            {v.get('order_id') for v in vals_list if v.get('order_id')})
        totals = {o.id: o._yt_audit_total() for o in orders}
        lines = super().create(vals_list)
        for order in lines.mapped('order_id'):
            new_lines = lines.filtered(lambda l: l.order_id == order)
            items = Markup('').join(
                Markup('<li>%s: %s %s × %s</li>') % (
                    line._yt_audit_label(), _('الكمية'), line._yt_audit_value('product_uom_qty'),
                    line._yt_audit_value('price_unit'))
                for line in new_lines)
            order._yt_audit_post(_('إضافة بنود'), items, totals.get(order.id))
        return lines

    def write(self, vals):
        tracked = [f for f in self._YT_AUDIT_FIELDS if f in vals]
        if not tracked:
            return super().write(vals)
        before = {line.id: {f: line._yt_audit_value(f) for f in tracked} for line in self}
        labels = {line.id: line._yt_audit_label() for line in self}
        totals = {o.id: o._yt_audit_total() for o in self.mapped('order_id')}
        result = super().write(vals)
        for order in self.mapped('order_id'):
            items = []
            for line in self.filtered(lambda l: l.order_id == order):
                for field_name in tracked:
                    old, new = before[line.id][field_name], line._yt_audit_value(field_name)
                    if old != new:
                        items.append(Markup('<li>%s — %s: %s ← %s</li>') % (
                            labels[line.id], line._fields[field_name].string, old, new))
            if items:
                order._yt_audit_post(_('تعديل بنود'), Markup('').join(items), totals.get(order.id))
        return result

    def unlink(self):
        details = {}
        for line in self:
            details.setdefault(line.order_id, []).append(Markup('<li>%s: %s %s × %s</li>') % (
                line._yt_audit_label(), _('الكمية'), line._yt_audit_value('product_uom_qty'),
                line._yt_audit_value('price_unit')))
        totals = {o.id: o._yt_audit_total() for o in details}
        result = super().unlink()
        for order, items in details.items():
            if order.exists():
                order._yt_audit_post(_('حذف بنود'), Markup('').join(items), totals.get(order.id))
        return result


class WorkshopOrderAuditPost(models.Model):
    _inherit = 'yt.reception.order'

    def _yt_audit_post(self, title, items, total_before=None):
        self.ensure_one()
        body = Markup('<p><b>%s</b></p><ul>%s</ul>') % (title, items)
        if total_before is not None:
            after = self._yt_audit_total()
            if after != total_before:
                body += Markup('<p>%s: %s ← %s</p>') % (_('الإجمالي النهائي'), total_before, after)
        self.message_post(body=body)


def _yt_display(record, field_name):
    field = record._fields[field_name]
    value = record[field_name]
    if field.type in ('many2one', 'many2many'):
        return '، '.join(value.mapped('display_name')) or '—'
    if field.type == 'boolean':
        return _('نعم') if value else _('لا')
    if field.type == 'selection':
        return dict(field._description_selection(record.env)).get(value, value or '—')
    if field.type == 'float':
        return '{:,.2f}'.format(value or 0.0)
    return value if value not in (False, None, '') else '—'


class YtAuditChangesMixin(models.AbstractModel):
    """Posts «field: old ← new» for every changed stored field on records with a chatter."""
    _name = 'yt.audit.changes.mixin'
    _description = 'Workshop configuration change log'
    _yt_audit_skip = ('message_ids', 'message_follower_ids', 'activity_ids', 'write_date', 'write_uid')

    def _yt_audit_fields(self, vals):
        return [name for name in vals
                if name in self._fields and name not in self._yt_audit_skip
                and self._fields[name].store and self._fields[name].type != 'one2many']

    def _yt_audit_changes(self, before, names):
        items = []
        for name in names:
            new = _yt_display(self, name)
            if before.get(name) != new:
                items.append(Markup('<li>%s: %s ← %s</li>') % (self._fields[name].string, before.get(name), new))
        return items

    def write(self, vals):
        names = self._yt_audit_fields(vals)
        before = {rec.id: {n: _yt_display(rec, n) for n in names} for rec in self} if names else {}
        result = super().write(vals)
        for rec in self:
            items = rec._yt_audit_changes(before.get(rec.id, {}), names)
            if items and hasattr(rec, 'message_post'):
                rec.message_post(body=Markup('<p><b>%s</b></p><ul>%s</ul>') % (_('تعديل الإعدادات'), Markup('').join(items)))
        return result


class WorkshopSettingsAudit(models.Model):
    _name = 'yt.workshop.finance.settings'
    _inherit = ['yt.workshop.finance.settings', 'mail.thread', 'yt.audit.changes.mixin']


class WorkshopPricingAudit(models.Model):
    _name = 'yt.workshop.category.pricing'
    _inherit = ['yt.workshop.category.pricing', 'mail.thread', 'yt.audit.changes.mixin']


class WorkshopPricingTierAudit(models.Model):
    _inherit = 'yt.workshop.pricing.tier'

    def _yt_parent_policy(self):
        for name, field in self._fields.items():
            if field.type == 'many2one' and field.comodel_name == 'yt.workshop.category.pricing':
                return self[name]
        return self.env['yt.workshop.category.pricing']

    def _yt_tier_text(self):
        self.ensure_one()
        names = [n for n, f in self._fields.items()
                 if f.store and f.type in ('float', 'integer', 'monetary', 'char', 'selection')
                 and n not in ('id', 'sequence', 'display_name')]
        return ' · '.join('%s: %s' % (self._fields[n].string, _yt_display(self, n)) for n in names)

    @api.model_create_multi
    def create(self, vals_list):
        tiers = super().create(vals_list)
        for tier in tiers:
            policy = tier._yt_parent_policy()
            if policy:
                policy.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (_('إضافة شريحة تسعير'), tier._yt_tier_text()))
        return tiers

    def write(self, vals):
        before = {t.id: t._yt_tier_text() for t in self}
        result = super().write(vals)
        for tier in self:
            after = tier._yt_tier_text()
            policy = tier._yt_parent_policy()
            if policy and after != before[tier.id]:
                policy.message_post(body=Markup('<p><b>%s</b></p><p>%s</p><p>← %s</p>') % (_('تعديل شريحة تسعير'), before[tier.id], after))
        return result

    def unlink(self):
        details = [(t._yt_parent_policy(), t._yt_tier_text()) for t in self]
        result = super().unlink()
        for policy, text in details:
            if policy.exists():
                policy.message_post(body=Markup('<p><b>%s</b></p><p>%s</p>') % (_('حذف شريحة تسعير'), text))
        return result


class InspectionLineAudit(models.Model):
    """Changes to inspection results after the inspection is completed are logged on the order."""
    _inherit = 'yt.inspection.line'

    def write(self, vals):
        names = [n for n in ('condition', 'notes') if n in vals and n in self._fields]
        watched = self.filtered(lambda l: l.order_id.inspection_state == 'done') if names else self.browse()
        before = {l.id: {n: _yt_display(l, n) for n in names} for l in watched}
        result = super().write(vals)
        for order in watched.mapped('order_id'):
            items = []
            for line in watched.filtered(lambda l: l.order_id == order):
                for name in names:
                    new = _yt_display(line, name)
                    if before[line.id][name] != new:
                        items.append(Markup('<li>%s — %s: %s ← %s</li>') % (
                            line.component_name or line.component_id.display_name,
                            line._fields[name].string, before[line.id][name], new))
            if items:
                order.message_post(body=Markup('<p><b>%s</b></p><ul>%s</ul>') % (
                    _('تعديل نتائج فحص مكتمل'), Markup('').join(items)))
        return result
