# -*- coding: utf-8 -*-
"""Keep visit identity in sync across entry, inspection and work order.

The entry card owns visit data; child screens can edit it, but changes are
written back to the entry card and distributed to all existing child records.
Commercial documents are intentionally never silently rewritten.
"""
from odoo import models, _
from odoo.exceptions import ValidationError

VISIT_FIELDS = (
    'partner_id', 'car_panel_no', 'partner_mobile', 'car_size_id',
    'car_model', 'car_type_id', 'vin_no', 'drum_counter', 'pay_type',
)
SYNC_CONTEXT = 'workshop_visit_sync_in_progress'


def _visit_values(source, target):
    result = {}
    for name in VISIT_FIELDS:
        if name in source._fields and name in target._fields:
            value = source[name]
            result[name] = value.id if source._fields[name].type == 'many2one' else value
    return result


class EntryVisitSync(models.Model):
    _inherit = 'mizan.car.entry.card.master'

    def create_checkup_procedure(self):
        self.ensure_one()
        existing = self.env['mizan.car.checkup.procedure.master'].search([('entry_card_id', '=', self.id)], limit=1)
        if existing:
            if existing.maint_wo_id and not self.user_has_groups('yousentech_car_maintain.group_use_checkup_procedure'):
                return self.call_wo_procedure()
            return self.call_checkup_procedure()
        return super().create_checkup_procedure()

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for card in self:
                if card.maint_wo_id.sale_order_id or (
                    card.checkup_id.create_invoice_manually_id
                    and card.checkup_id.create_invoice_manually_id.state != 'cancel'
                ):
                    raise ValidationError(_('لا يمكن تغيير بيانات الزيارة بعد إنشاء مستند تجاري مرتبط.'))
        result = super().write(vals)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for card in self:
                if not card.id or not isinstance(card.id, int):
                    continue
                for model, relation in (
                    ('mizan.car.checkup.procedure.master', 'entry_card_id'),
                    ('mizan.car.work.procedure.master', 'entry_card_id'),
                ):
                    children = self.env[model].search([(relation, '=', card.id)])
                    for child in children:
                        child.with_context(**{SYNC_CONTEXT: True}).write(
                            {key: value for key, value in _visit_values(card, child).items()
                             if key in changing}
                        )
        return result


class CheckupVisitSync(models.Model):
    _inherit = 'mizan.car.checkup.procedure.master'

    def create_work_order_procedure(self):
        self.ensure_one()
        existing = self.env['mizan.car.work.procedure.master'].search([('checkup_id', '=', self.id)], limit=1)
        if existing:
            return self.call_wo_procedure()
        return super().create_work_order_procedure()

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for record in self.filtered('entry_card_id'):
                card_vals = {key: vals[key] for key in changing if key in record.entry_card_id._fields}
                if card_vals:
                    record.entry_card_id.write(card_vals)
        return super().write(vals)


class WorkOrderVisitSync(models.Model):
    _inherit = 'mizan.car.work.procedure.master'

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for record in self.filtered('entry_card_id'):
                card_vals = {key: vals[key] for key in changing if key in record.entry_card_id._fields}
                if card_vals:
                    record.entry_card_id.write(card_vals)
        return super().write(vals)
